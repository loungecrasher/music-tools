# Security Remediation Plan

**Project:** Music Tools
**Date:** 2025-11-19
**Duration:** 3 months
**Team Size:** 1 developer + security review

---

## Executive Summary

This document provides a comprehensive remediation plan for the 17 security issues identified in the Music Tools security audit. The plan is divided into 4 phases over 3 months, prioritized by risk and business impact.

**Timeline:**
- Phase 1 (Week 1): Critical and High Priority - 3 issues
- Phase 2 (Weeks 2-4): High and Medium Priority - 8 issues
- Phase 3 (Month 2): Low Priority - 6 issues
- Phase 4 (Month 3): Long-term Improvements

**Total Effort:** ~86 developer hours over 3 months

---

## Phase 1: Critical Fixes (Week 1)

**Goal:** Eliminate immediate security risks
**Duration:** 3 days
**Effort:** 10 hours

### Day 1-2: Command Injection (H-001)

**Issue:** os.system() calls without proper validation

**Tasks:**
1. [ ] Replace os.system() with subprocess.run() or Rich console
2. [ ] Test on Windows and Unix systems
3. [ ] Update all affected files
4. [ ] Run regression tests

**Implementation:**
```python
# File: apps/music-tools/menu.py

# Before:
os.system('cls' if os.name == 'nt' else 'clear')

# After:
from rich.console import Console
console = Console()
console.clear()

# Or:
import subprocess
subprocess.run(['cls' if os.name == 'nt' else 'clear'], shell=False, check=False)
```

**Files to Update:**
- [ ] apps/music-tools/menu.py (10 instances)
- [ ] apps/music-tools/legacy/Library Comparison/duplicate_remover.py
- [ ] apps/music-tools/legacy/Library Comparison/library_comparison.py

**Testing Checklist:**
- [ ] Unit tests pass
- [ ] Manual testing on macOS
- [ ] Manual testing on Windows
- [ ] Manual testing on Linux
- [ ] No regressions in CLI behavior

**Success Criteria:**
- Zero os.system() calls in non-legacy code
- All tests passing
- No user-visible changes in behavior

---

### Day 1: Secrets in Repository (M-001)

**Issue:** .env files with placeholder credentials in repository

**Tasks:**
1. [ ] Remove .env files from repository
2. [ ] Update .gitignore
3. [ ] Create .env.example files
4. [ ] Scan git history for secrets
5. [ ] Set up git-secrets

**Implementation:**
```bash
# Step 1: Remove .env files
git rm apps/music-tools/legacy/Deezer-Playlist-Fixer/.env
git rm "apps/music-tools/legacy/Spotify Script/V2/.env"

# Step 2: Update .gitignore
echo "" >> .gitignore
echo "# Environment variables" >> .gitignore
echo "**/.env" >> .gitignore
echo "**/.env.local" >> .gitignore
echo ".env*" >> .gitignore
echo "!.env.example" >> .gitignore

# Step 3: Create .env.example files
cp .env.example apps/music-tools/legacy/Deezer-Playlist-Fixer/.env.example
cp .env.example "apps/music-tools/legacy/Spotify Script/V2/.env.example"

# Step 4: Scan git history
git log -p | grep -i "secret\|api_key\|password" > secret_scan.txt
# Manual review of secret_scan.txt

# Step 5: Install git-secrets
git secrets --install
git secrets --register-aws
git secrets --add 'SPOTIPY_CLIENT_SECRET'
git secrets --add 'DEEZER_APP_SECRET'
git secrets --add 'ANTHROPIC_API_KEY'
```

**Documentation Update:**
```markdown
# File: README.md

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API credentials
3. Never commit `.env` to version control
```

**Success Criteria:**
- No .env files in repository
- .env.example files present
- .gitignore updated
- git-secrets configured
- No secrets in git history

---

### Day 2-3: Dependency Updates (M-007)

**Issue:** urllib3 1.x EOL, needs upgrade to 2.x

**Tasks:**
1. [ ] Update requirements-core.txt
2. [ ] Test in development environment
3. [ ] Run full test suite
4. [ ] Check for breaking changes
5. [ ] Update documentation

**Implementation:**
```txt
# File: requirements-core.txt

# Before:
# urllib3 (dependency of requests, no direct requirement)

# After:
urllib3>=2.2.0,<3.0.0  # SECURITY: Upgrade from EOL 1.x branch
```

**Testing:**
```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate

# Install updated requirements
pip install -r requirements-core.txt

# Run tests
pytest tests/ -v

# Test HTTP functionality
python -m pytest tests/test_http.py -v

# Test web scraping
python -m pytest apps/music-tools/src/scraping/test_scraper.py -v
```

**Breaking Changes Check:**
```python
# Check for urllib3 API changes
import urllib3

# Verify connection pooling works
http = urllib3.PoolManager()
response = http.request('GET', 'https://httpbin.org/get')

# Verify SSL/TLS works
http_secure = urllib3.PoolManager(
    cert_reqs='CERT_REQUIRED',
    ca_certs='/etc/ssl/certs/ca-certificates.crt'
)
```

**Success Criteria:**
- urllib3 >= 2.2.0 installed
- All tests passing
- No deprecation warnings
- HTTP requests working correctly

---

## Phase 2: High & Medium Priority (Weeks 2-4)

**Goal:** Address major security concerns
**Duration:** 3 weeks
**Effort:** 55 hours

### Week 2: SQL Injection Protection (H-002)

**Issue:** Dynamic SQL with f-strings (mitigated by whitelist)

**Tasks:**
1. [ ] Add comprehensive SQL injection tests
2. [ ] Make ALLOWED_COLUMNS immutable (frozenset)
3. [ ] Add security comments to critical sections
4. [ ] Consider SQLAlchemy migration (long-term)
5. [ ] Document SQL security architecture

**Implementation:**
```python
# File: apps/music-tools/src/library/database.py

class LibraryDatabase:
    # SECURITY CRITICAL: Column name whitelist prevents SQL injection
    # DO NOT MODIFY without security review
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

        Args:
            columns: Set of column names to validate

        Raises:
            ValueError: If any column name is not in whitelist
        """
        invalid = columns - LibraryDatabase.ALLOWED_COLUMNS
        if invalid:
            logger.error(
                f"SQL injection attempt detected: invalid columns {invalid}",
                extra={'security_event': True}
            )
            raise ValueError(
                f"Invalid column names detected (possible SQL injection): {invalid}"
            )

    def add_file(self, file: LibraryFile) -> int:
        """Add a file to the library index."""
        if file is None:
            raise ValueError("file cannot be None")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            file_dict = file.to_dict()
            file_dict.pop('id', None)

            # SECURITY: Validate columns before using in SQL
            self._validate_columns(set(file_dict.keys()))

            columns = ', '.join(file_dict.keys())
            placeholders = ', '.join(['?' for _ in file_dict])

            # Safe because columns are validated against whitelist above
            cursor.execute(
                f"INSERT INTO library_index ({columns}) VALUES ({placeholders})",
                list(file_dict.values())
            )

            return cursor.lastrowid
```

**Testing:**
```python
# File: tests/security/test_sql_injection.py

import pytest
from apps.music_tools.src.library.database import LibraryDatabase
from apps.music_tools.src.library.models import LibraryFile

def test_sql_injection_column_names():
    """Test that malicious column names are rejected."""
    db = LibraryDatabase(':memory:')

    malicious_columns = [
        "'; DROP TABLE library_index; --",
        "id; DELETE FROM library_index; --",
        "1=1 OR '1'='1",
        "file_path' OR '1'='1",
    ]

    for malicious in malicious_columns:
        file = LibraryFile(file_path="test.mp3", filename="test.mp3")
        file_dict = file.to_dict()
        file_dict[malicious] = "value"

        with pytest.raises(ValueError, match="Invalid column names"):
            db._validate_columns(set(file_dict.keys()))

def test_sql_injection_values():
    """Test that malicious values are safely parameterized."""
    db = LibraryDatabase(':memory:')

    malicious_values = [
        "'; DROP TABLE library_index; --",
        "admin' OR '1'='1",
        "test\"; DELETE FROM library_index WHERE \"1\"=\"1",
    ]

    for malicious in malicious_values:
        file = LibraryFile(
            file_path=malicious,
            filename="test.mp3",
            file_format="mp3",
            file_size=1000,
            metadata_hash="test",
            file_content_hash="test",
            indexed_at="2025-01-01T00:00:00",
            file_mtime="2025-01-01T00:00:00"
        )

        # Should not raise an exception - values are parameterized
        file_id = db.add_file(file)
        assert file_id > 0

        # Verify database integrity
        retrieved = db.get_file_by_path(malicious)
        assert retrieved.file_path == malicious
```

**Success Criteria:**
- ALLOWED_COLUMNS is immutable
- All SQL injection tests passing
- Security comments added
- No SQL injection vulnerabilities detected by static analysis

---

### Week 2: Path Validation (H-003, M-004)

**Issue:** subprocess execution and user input without path validation

**Tasks:**
1. [ ] Add path validation to external.py
2. [ ] Add path validation to cli.py user inputs
3. [ ] Create centralized path validation utility
4. [ ] Add tests for path traversal attempts
5. [ ] Document path security requirements

**Implementation:**
```python
# File: apps/music-tools/music_tools_cli/services/external.py

from pathlib import Path
from typing import Optional
from music_tools_common.utils.security import validate_file_path
import logging

logger = logging.getLogger(__name__)

# Whitelist of allowed script directories
ALLOWED_SCRIPT_DIRS = [
    Path(__file__).parent.parent / 'scripts',
    Path.home() / '.music_tools' / 'scripts',
]

def is_path_in_allowed_directory(path: Path) -> bool:
    """
    Check if path is within an allowed directory.

    Args:
        path: Path to check

    Returns:
        True if path is in allowed directory
    """
    try:
        real_path = path.resolve()
        return any(
            real_path.is_relative_to(allowed.resolve())
            for allowed in ALLOWED_SCRIPT_DIRS
        )
    except (ValueError, OSError):
        return False

def run_external_script(
    script_path: Path,
    cwd: Optional[Path] = None
) -> None:
    """
    Run external Python script with security validation.

    Args:
        script_path: Path to Python script
        cwd: Optional working directory

    Raises:
        ValueError: If paths fail security validation
        FileNotFoundError: If script doesn't exist
        PermissionError: If script isn't in allowed directory
    """
    # Validate script path
    is_valid, safe_script_path = validate_file_path(str(script_path))
    if not is_valid:
        logger.error(f"Invalid script path: {safe_script_path}")
        raise ValueError(f"Invalid script path: {safe_script_path}")

    script_path_obj = Path(safe_script_path)

    # Ensure it's a Python file
    if script_path_obj.suffix != '.py':
        raise ValueError("Only .py files can be executed")

    # Check if in allowed directory
    if not is_path_in_allowed_directory(script_path_obj):
        logger.warning(
            f"Script path outside allowed directories: {script_path_obj}",
            extra={'security_event': True}
        )
        raise PermissionError(
            f"Script must be in allowed directory: {ALLOWED_SCRIPT_DIRS}"
        )

    # Validate cwd if provided
    if cwd:
        is_valid, safe_cwd = validate_file_path(str(cwd))
        if not is_valid:
            logger.error(f"Invalid working directory: {safe_cwd}")
            raise ValueError(f"Invalid working directory: {safe_cwd}")
        cwd = Path(safe_cwd)

    # Execute with validated paths
    import subprocess
    import sys

    try:
        subprocess.run(
            [sys.executable, str(script_path_obj)],
            cwd=cwd or script_path_obj.parent,
            check=False,
            timeout=300  # 5 minute timeout
        )
    except subprocess.TimeoutExpired:
        logger.error(f"Script execution timed out: {script_path_obj}")
        raise
```

```python
# File: apps/music-tools/src/tagging/cli.py

from music_tools_common.utils.security import validate_file_path
from rich.console import Console

console = Console()

def get_validated_path_from_user(
    prompt: str,
    base_directory: Optional[str] = None,
    must_exist: bool = True
) -> Optional[str]:
    """
    Get and validate a file path from user input.

    Args:
        prompt: Prompt to display
        base_directory: Optional base directory restriction
        must_exist: If True, path must exist

    Returns:
        Validated path or None if cancelled
    """
    while True:
        user_input = input(prompt).strip()

        if not user_input:
            return None

        is_valid, result = validate_file_path(user_input, base_directory)

        if not is_valid:
            console.print(f"[red]Invalid path: {result}[/red]")
            console.print("[yellow]Please enter a valid path or press Enter to cancel[/yellow]")
            continue

        if must_exist and not Path(result).exists():
            console.print(f"[red]Path does not exist: {result}[/red]")
            continue

        return result

# Usage in configure_paths():
def configure_paths(self) -> None:
    """Configure music library paths."""
    console.print("\n[bold]Configure Music Paths[/bold]")
    console.print("Add directories containing your music files.\n")

    while True:
        path = get_validated_path_from_user(
            "Enter path to add (or Enter to cancel): ",
            base_directory=str(Path.home()),  # Restrict to user's home
            must_exist=True
        )

        if not path:
            break

        self.config.music_paths.append(path)
        console.print(f"[green]Added: {path}[/green]")
```

**Testing:**
```python
# File: tests/security/test_path_traversal.py

import pytest
from pathlib import Path
from apps.music_tools.music_tools_cli.services.external import run_external_script

def test_path_traversal_prevention():
    """Test that path traversal attempts are blocked."""
    malicious_paths = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config",
        "/etc/passwd",
        "~/../../etc/passwd",
        "test/../../../etc/passwd",
    ]

    for malicious_path in malicious_paths:
        with pytest.raises((ValueError, PermissionError)):
            run_external_script(Path(malicious_path))

def test_only_allowed_directories():
    """Test that only allowed directories can be used."""
    # Assume /tmp is not in allowed directories
    disallowed_path = Path("/tmp/test_script.py")

    with pytest.raises(PermissionError, match="allowed directory"):
        run_external_script(disallowed_path)

def test_symlink_attack_prevention():
    """Test that symlinks don't bypass security."""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create symlink to sensitive location
        link_path = Path(tmpdir) / "malicious_link.py"
        os.symlink("/etc/passwd", link_path)

        with pytest.raises((ValueError, PermissionError)):
            run_external_script(link_path)
```

**Success Criteria:**
- All path inputs validated
- Path traversal tests passing
- Only allowed directories accessible
- Symlink attacks prevented

---

### Week 3: File Permissions & HTTPS (M-002, M-003)

**Issue:** Insecure file permissions and missing HTTPS verification

**Tasks:**
1. [ ] Update file permission handling
2. [ ] Add HTTPS verification checks
3. [ ] Test on different platforms
4. [ ] Document permission requirements

**Implementation:**
```python
# File: apps/music-tools/src/tagging/core/security.py

def secure_file_permissions(file_path: Path, file_type: str = 'general') -> None:
    """
    Set appropriate permissions based on file type.

    Args:
        file_path: Path to file
        file_type: Type of file (config, database, secret, general, executable)
    """
    permission_map = {
        'config': 0o600,    # rw------- (owner only)
        'database': 0o600,  # rw------- (owner only)
        'secret': 0o600,    # rw------- (owner only)
        'general': 0o644,   # rw-r--r-- (standard)
        'executable': 0o755 # rwxr-xr-x (executable)
    }

    mode = permission_map.get(file_type, 0o644)

    try:
        os.chmod(file_path, mode)

        # Verify permissions were set correctly
        current_mode = file_path.stat().st_mode & 0o777
        if current_mode != mode:
            logger.warning(f"File permissions may not be set correctly: {file_path}")

    except PermissionError as e:
        logger.error(f"Cannot set permissions on {file_path}: {e}")
        raise
```

```python
# File: packages/common/music_tools_common/utils/http.py

import requests

def create_secure_session() -> requests.Session:
    """
    Create a requests session with secure defaults.

    Returns:
        Configured requests.Session
    """
    session = requests.Session()

    # SECURITY: Always verify SSL certificates
    session.verify = True

    # Set secure headers
    session.headers.update({
        'User-Agent': 'Music-Tools/1.0',
    })

    # Configure retries
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session

# Add verification check
def verify_https_connection(url: str) -> Tuple[bool, str]:
    """
    Verify that URL uses HTTPS and certificate is valid.

    Args:
        url: URL to check

    Returns:
        Tuple of (is_secure, message)
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)

    if parsed.scheme != 'https':
        return False, f"URL does not use HTTPS: {url}"

    try:
        response = requests.get(url, verify=True, timeout=5)
        return True, "HTTPS connection verified"
    except requests.exceptions.SSLError as e:
        return False, f"SSL verification failed: {e}"
    except Exception as e:
        return False, f"Connection failed: {e}"
```

**Success Criteria:**
- Sensitive files have 0o600 permissions
- All HTTP requests verify SSL
- Cross-platform compatibility verified

---

### Week 4: Rate Limiting & API Validation (M-005, M-006)

**Issue:** No rate limiting on authentication, weak API key validation

**Tasks:**
1. [ ] Implement authentication rate limiting
2. [ ] Enhance API key validation
3. [ ] Add security event logging
4. [ ] Test rate limiting effectiveness

**Implementation:**
```python
# File: apps/music-tools/src/tagging/cli.py

import time
from collections import defaultdict
from typing import Dict, List

class AuthenticationRateLimiter:
    """Rate limiter for authentication attempts."""

    def __init__(
        self,
        max_attempts: int = 3,
        lockout_duration: int = 300,  # 5 minutes
        cleanup_interval: int = 3600  # 1 hour
    ):
        self.max_attempts = max_attempts
        self.lockout_duration = lockout_duration
        self.cleanup_interval = cleanup_interval
        self.attempts: Dict[str, List[float]] = defaultdict(list)
        self.last_cleanup = time.time()

    def _cleanup_old_attempts(self):
        """Remove attempts older than cleanup interval."""
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            for identifier in list(self.attempts.keys()):
                self.attempts[identifier] = [
                    t for t in self.attempts[identifier]
                    if now - t < self.cleanup_interval
                ]
            self.last_cleanup = now

    def check_rate_limit(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if authentication attempt is allowed.

        Args:
            identifier: Unique identifier (IP, session, etc.)

        Returns:
            Tuple of (allowed, seconds_until_retry)
        """
        self._cleanup_old_attempts()

        now = time.time()
        attempts = self.attempts[identifier]

        # Remove attempts outside lockout window
        attempts[:] = [t for t in attempts if now - t < self.lockout_duration]

        if len(attempts) >= self.max_attempts:
            wait_time = int(self.lockout_duration - (now - attempts[0]))
            logger.warning(
                f"Authentication rate limit exceeded for {identifier}",
                extra={'security_event': True, 'identifier': identifier}
            )
            return False, max(0, wait_time)

        return True, 0

    def record_attempt(self, identifier: str, success: bool = False):
        """
        Record an authentication attempt.

        Args:
            identifier: Unique identifier
            success: Whether attempt was successful
        """
        self.attempts[identifier].append(time.time())

        if success:
            # Clear attempts on successful auth
            self.attempts[identifier].clear()

        logger.info(
            f"Authentication attempt recorded: {identifier} (success={success})",
            extra={'security_event': True}
        )

# Usage:
rate_limiter = AuthenticationRateLimiter()

def configure_api_key(self) -> None:
    """Configure Anthropic API key with rate limiting."""
    console.print("\n[bold]Configure Claude API Key[/bold]")

    if self.config.anthropic_api_key:
        console.print(f"Current API key: {'*' * 20}{self.config.anthropic_api_key[-8:]}")

    console.print("\nLeave blank to skip or keep existing key.")

    identifier = "api_key_config"
    max_attempts = 5

    for attempt in range(max_attempts):
        # Check rate limit
        allowed, wait_time = rate_limiter.check_rate_limit(identifier)

        if not allowed:
            console.print(
                f"[red]Too many failed attempts. "
                f"Please wait {wait_time} seconds before trying again.[/red]"
            )
            return

        # Get API key
        api_key = getpass.getpass(
            f"Enter your Claude API key (attempt {attempt + 1}/{max_attempts}): "
        ).strip()

        if not api_key:
            return

        # Validate API key
        is_valid, error_message = self._validate_api_key_format(api_key)

        if is_valid:
            # Test API key by making a request
            if self._test_api_key(api_key):
                self.config.anthropic_api_key = api_key
                rate_limiter.record_attempt(identifier, success=True)
                console.print("[green]API key configured successfully![/green]")
                return
            else:
                error_message = "API key is invalid or inactive"

        # Record failed attempt
        rate_limiter.record_attempt(identifier, success=False)

        console.print(f"[red]Invalid API key: {error_message}[/red]")
        console.print(f"[yellow]Attempts remaining: {max_attempts - attempt - 1}[/yellow]")

    console.print("[red]Maximum attempts exceeded. Please try again later.[/red]")

def _validate_api_key_format(self, api_key: str) -> Tuple[bool, str]:
    """
    Enhanced API key validation.

    Args:
        api_key: API key to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check length
    if len(api_key) < 20:
        return False, "API key is too short (minimum 20 characters)"

    if len(api_key) > 200:
        return False, "API key is too long (maximum 200 characters)"

    # Check format (Anthropic API keys start with sk-ant-)
    if not api_key.startswith('sk-'):
        return False, "Invalid API key format (should start with 'sk-')"

    # Check character set
    import re
    if not re.match(r'^sk-[a-zA-Z0-9\-_]+$', api_key):
        return False, "API key contains invalid characters"

    # Check entropy (basic check)
    unique_chars = len(set(api_key))
    if unique_chars < 10:
        return False, "API key appears to have low entropy"

    return True, ""

def _test_api_key(self, api_key: str) -> bool:
    """
    Test API key by making a simple API request.

    Args:
        api_key: API key to test

    Returns:
        True if key is valid
    """
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)

        # Make a minimal test request
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": "test"}]
        )

        return True

    except Exception as e:
        logger.error(f"API key test failed: {e}")
        return False
```

**Success Criteria:**
- Rate limiting prevents brute force
- Enhanced API key validation
- Security events logged
- User experience not degraded

---

### Week 4: Security Logging (M-008)

**Issue:** Insufficient security event logging

**Implementation:**
```python
# File: packages/common/music_tools_common/utils/security_logging.py

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class SecurityEventLogger:
    """
    Structured logging for security events.

    Logs security-relevant events in a structured format for
    analysis and monitoring.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize security event logger.

        Args:
            log_dir: Directory for log files (default: ~/.music_tools/logs)
        """
        if log_dir is None:
            log_dir = Path.home() / '.music_tools' / 'logs'

        log_dir.mkdir(parents=True, exist_ok=True)

        self.log_file = log_dir / 'security_events.log'
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)

        # Create file handler
        handler = logging.FileHandler(self.log_file)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)

        # Also log to console in debug mode
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(
            logging.Formatter('[SECURITY] %(levelname)s: %(message)s')
        )
        self.logger.addHandler(console_handler)

    def log_event(
        self,
        event_type: str,
        severity: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        Log a security event.

        Args:
            event_type: Type of event (auth_failure, path_traversal, etc.)
            severity: Event severity (info, warning, error, critical)
            details: Event details dictionary
            user_id: Optional user identifier
            ip_address: Optional IP address
        """
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'details': details,
            'user_id': user_id or 'anonymous',
            'ip_address': ip_address or 'unknown'
        }

        # Sanitize sensitive data
        from music_tools_common.utils.security import sanitize_log_message
        event_json = json.dumps(event)
        sanitized_json = sanitize_log_message(event_json)

        # Log based on severity
        level = getattr(logging, severity.upper(), logging.INFO)
        self.logger.log(level, sanitized_json)

    def log_authentication_failure(
        self,
        reason: str,
        username: Optional[str] = None
    ):
        """Log authentication failure."""
        self.log_event(
            event_type='authentication_failure',
            severity='warning',
            details={
                'reason': reason,
                'username': username
            }
        )

    def log_path_validation_failure(
        self,
        path: str,
        reason: str
    ):
        """Log path validation failure."""
        self.log_event(
            event_type='path_validation_failure',
            severity='warning',
            details={
                'path': path,
                'reason': reason
            }
        )

    def log_sql_injection_attempt(
        self,
        query_fragment: str,
        blocked_columns: set
    ):
        """Log potential SQL injection attempt."""
        self.log_event(
            event_type='sql_injection_attempt',
            severity='error',
            details={
                'query_fragment': query_fragment,
                'blocked_columns': list(blocked_columns)
            }
        )

    def log_rate_limit_exceeded(
        self,
        identifier: str,
        limit_type: str
    ):
        """Log rate limit exceeded."""
        self.log_event(
            event_type='rate_limit_exceeded',
            severity='warning',
            details={
                'identifier': identifier,
                'limit_type': limit_type
            }
        )

# Global instance
security_logger = SecurityEventLogger()
```

**Success Criteria:**
- All security events logged
- Structured log format
- Sensitive data sanitized
- Log rotation configured

---

## Phase 3: Low Priority (Month 2)

**Goal:** Address remaining security improvements
**Duration:** 4 weeks
**Effort:** 21 hours

### Tasks:
1. [ ] L-001: Secure exec_module() usage
2. [ ] L-002: Consistent input() sanitization
3. [ ] L-003: Prevent sensitive data in logs
4. [ ] L-004: Add security headers (future web features)
5. [ ] L-005: CSRF protection (future web features)
6. [ ] L-006: Improve error messages

**Weekly Schedule:**
- Week 1: L-001, L-002 (10 hours)
- Week 2: L-003, L-006 (7 hours)
- Week 3: Documentation and testing (4 hours)
- Week 4: Code review and refinement

---

## Phase 4: Long-term Improvements (Month 3)

**Goal:** Establish ongoing security practices
**Duration:** Ongoing
**Effort:** Variable

### Tasks:
1. [ ] Set up automated security scanning
2. [ ] Implement CI/CD security checks
3. [ ] Create security documentation
4. [ ] Establish security review process
5. [ ] Plan SQLAlchemy migration
6. [ ] Set up monitoring and alerting

---

## Success Metrics

### Quantitative
- [ ] Zero HIGH severity issues
- [ ] < 3 MEDIUM severity issues
- [ ] 100% test coverage for security functions
- [ ] Zero secrets in repository
- [ ] All dependencies up-to-date

### Qualitative
- [ ] Security architecture documented
- [ ] Development team trained
- [ ] Incident response plan in place
- [ ] Regular security audits scheduled

---

## Risk Mitigation

### Rollback Plan
Each phase has a rollback plan:
- Git tags before changes
- Feature flags for risky changes
- Staged deployment to catch issues early

### Testing Strategy
- Unit tests for all fixes
- Integration tests for workflows
- Manual testing of critical paths
- Automated security scans

---

## Resource Requirements

### Development
- 1 developer @ 86 hours over 3 months
- Code review: 10 hours
- Testing: 15 hours
- **Total:** ~111 hours

### Tools
- Static analysis: Bandit, pylint
- Dependency scanning: pip-audit, Safety
- Secret scanning: git-secrets, truffleHog
- CI/CD: GitHub Actions

### Training
- Security coding practices: 4 hours
- Tool training: 2 hours
- Ongoing: Monthly security updates

---

## Communication Plan

### Weekly Updates
- Status report to stakeholders
- Issue tracking updates
- Risk assessment updates

### Milestones
- Phase 1 complete: Week 1
- Phase 2 complete: Week 4
- Phase 3 complete: Month 2
- Phase 4 ongoing: Month 3+

---

## Approval & Sign-off

**Prepared by:** Security Auditor Agent
**Date:** 2025-11-19

**Approvals Required:**
- [ ] Development Lead
- [ ] Security Team
- [ ] Product Owner

**Start Date:** ___________
**Target Completion:** ___________

---

## Appendix: Quick Reference

### High Priority Fixes (Week 1)
1. Replace os.system() with safe alternatives
2. Remove .env files from repository
3. Update urllib3 to 2.x

### Scripts for Common Tasks

**Run security scan:**
```bash
bandit -r apps/ packages/ -f json -o security_scan.json
pip-audit --desc
```

**Test a specific fix:**
```bash
pytest tests/security/test_sql_injection.py -v
```

**Deploy a fix:**
```bash
git checkout -b security/fix-command-injection
# Make changes
pytest tests/ -v
git commit -m "Security: Fix command injection in menu.py"
git push origin security/fix-command-injection
# Create PR for review
```
