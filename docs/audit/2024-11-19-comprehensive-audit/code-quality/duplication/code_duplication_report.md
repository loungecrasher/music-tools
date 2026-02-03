# Code Duplication Analysis Report

**Generated**: 2025-11-19
**Duplication Level**: 15-20% (Estimated)
**Severity**: HIGH
**Technical Debt**: 25-30 hours to resolve

---

## Executive Summary

The codebase exhibits **significant code duplication** across multiple dimensions:
- Repeated error handling patterns (40+ instances)
- Similar configuration logic (5+ files)
- Duplicate database connection code (5+ instances)
- Copy-pasted UI rendering patterns (10+ instances)
- Redundant validation logic (8+ instances)

**Impact**: High maintenance cost, bug multiplication, inconsistency

---

## Duplication Categories

### 1. Error Handling Pattern Duplication

**Severity**: CRITICAL
**Instances**: 40+
**Estimated Duplication**: 400-500 lines

#### Pattern A: Try-Except-Log-Print

**Files**:
- `menu.py` (lines: 297-302, 455-510, 755-759, etc.)
- `music_scraper.py` (lines: throughout)
- `cli.py` (lines: throughout)
- `database.py` (lines: 54-56, 122-124, 163-167, etc.)
- `indexer.py` (lines: 136-139, 157-159, etc.)
- And 20+ more files

**Duplicated Code**:
```python
# Pattern repeated 40+ times across codebase:

try:
    # some operation
    result = operation()
except Exception as e:
    logger.error(f"Error in operation: {e}")
    console.print(f"[red]Error: {e}[/red]")
    return None  # or False, or empty dict
```

**Variations Found**:
```python
# Variation 1: With specific exception
try:
    # operation
except SpecificError as e:
    logger.error(f"Error: {str(e)}")
    return False

# Variation 2: With multiple exceptions
try:
    # operation
except ValueError as e:
    logger.error(...)
except IOError as e:
    logger.error(...)

# Variation 3: With console output
try:
    # operation
except Exception as e:
    console.print(f"[red]✗ Failed: {e}[/red]")
    if verbose:
        console.print_exception()
```

**Refactoring Solution**:
```python
# Create error handling decorator
from functools import wraps
from typing import Optional, Any, Callable

def handle_errors(
    log: bool = True,
    display: bool = True,
    default_return: Any = None,
    error_message: Optional[str] = None
):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log:
                    logger.error(f"Error in {func.__name__}: {e}")
                if display:
                    msg = error_message or f"Error: {e}"
                    console.print(f"[red]{msg}[/red]")
                return default_return
        return wrapper
    return decorator

# Usage:
@handle_errors(default_return=None)
def some_operation():
    # operation
    return result
```

**Savings**: ~400 lines, consistent error handling

---

### 2. Database Connection Pattern Duplication

**Severity**: HIGH
**Instances**: 5+
**Estimated Duplication**: 100-150 lines

#### Pattern B: SQLite Connection Setup

**Files**:
- `src/library/database.py` (lines: 74-102)
- `packages/common/database/manager.py` (lines: 43-56)
- Legacy scripts (multiple files)

**Duplicated Code**:
```python
# Repeated in 5+ files:

conn = None
try:
    conn = sqlite3.connect(
        self.db_path,
        timeout=30.0,
        check_same_thread=False,
        isolation_level='DEFERRED'
    )
    conn.row_factory = sqlite3.Row
    yield conn
    conn.commit()
except Exception as e:
    if conn:
        conn.rollback()
    logger.error(f"Database error: {e}")
    raise
finally:
    if conn:
        conn.close()
```

**Refactoring Solution**:
```python
# Create database connection factory

from contextlib import contextmanager
from typing import Generator
import sqlite3

class DatabaseConnectionFactory:
    """Factory for creating database connections with consistent configuration."""

    @staticmethod
    @contextmanager
    def create_connection(
        db_path: str,
        timeout: float = 30.0,
        isolation_level: str = 'DEFERRED'
    ) -> Generator[sqlite3.Connection, None, None]:
        """
        Create a database connection with standard configuration.

        Args:
            db_path: Path to SQLite database
            timeout: Connection timeout in seconds
            isolation_level: Transaction isolation level

        Yields:
            Configured SQLite connection with Row factory

        Raises:
            sqlite3.Error: If connection or operations fail
        """
        conn = None
        try:
            conn = sqlite3.connect(
                db_path,
                timeout=timeout,
                check_same_thread=False,
                isolation_level=isolation_level
            )
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

# Usage:
with DatabaseConnectionFactory.create_connection(db_path) as conn:
    cursor = conn.cursor()
    # ... operations
```

**Savings**: ~100 lines, consistent connection handling

---

### 3. Progress Bar Creation Duplication

**Severity**: MEDIUM-HIGH
**Instances**: 10+
**Estimated Duplication**: 200-250 lines

#### Pattern C: Rich Progress Bar Setup

**Files**:
- `indexer.py` (lines: 112-119, 494-501)
- `cli.py` (lines: 467-474)
- `music_scraper.py` (lines: 167, 614)
- `vetter.py` (similar patterns)
- And 6+ more files

**Duplicated Code**:
```python
# Repeated 10+ times:

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    console=console
) as progress:
    task = progress.add_task("Description...", total=total)
    for item in items:
        # process item
        progress.advance(task)
```

**Variations**:
```python
# Variation 1: With time column
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    MofNCompleteColumn(),
    TimeRemainingColumn(),
    console=console
) as progress:
    # ...

# Variation 2: Different columns
with Progress(
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
) as progress:
    # ...
```

**Refactoring Solution**:
```python
# Create progress bar factory

from enum import Enum
from typing import Optional, List
from rich.progress import (
    Progress, ProgressColumn, SpinnerColumn, TextColumn,
    BarColumn, TaskProgressColumn, MofNCompleteColumn, TimeRemainingColumn
)

class ProgressStyle(Enum):
    """Predefined progress bar styles."""
    SIMPLE = "simple"
    DETAILED = "detailed"
    SPINNING = "spinning"
    TIME_AWARE = "time_aware"

class ProgressBarFactory:
    """Factory for creating consistent progress bars."""

    STYLE_COLUMNS = {
        ProgressStyle.SIMPLE: [
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ],
        ProgressStyle.DETAILED: [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ],
        ProgressStyle.SPINNING: [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
        ],
        ProgressStyle.TIME_AWARE: [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
        ],
    }

    @classmethod
    def create(
        cls,
        style: ProgressStyle = ProgressStyle.DETAILED,
        console: Optional[Console] = None,
        custom_columns: Optional[List[ProgressColumn]] = None
    ) -> Progress:
        """
        Create a progress bar with predefined or custom columns.

        Args:
            style: Predefined style to use
            console: Rich console for output
            custom_columns: Override with custom columns

        Returns:
            Configured Progress object
        """
        columns = custom_columns or cls.STYLE_COLUMNS[style]
        return Progress(*columns, console=console)

# Usage:
with ProgressBarFactory.create(ProgressStyle.TIME_AWARE, console=console) as progress:
    task = progress.add_task("Processing...", total=100)
    # ...
```

**Savings**: ~200 lines, consistent progress UI

---

### 4. Configuration Loading Pattern Duplication

**Severity**: HIGH
**Instances**: 5+
**Estimated Duplication**: 150-200 lines

#### Pattern D: Service Configuration Loading

**Files**:
- `menu.py` (lines: 39-45, 313-320, 405-418)
- `cli.py` (lines: multiple locations)
- `setup_wizard.py`
- Service files

**Duplicated Code**:
```python
# Repeated pattern:

config = get_config('service_name')

if not config:
    console.print("[red]Service not configured[/red]")
    return

if not config.get('client_id'):
    console.print("[red]Missing client ID[/red]")
    return

if not config.get('client_secret'):
    console.print("[red]Missing client secret[/red]")
    return

# More validation...
```

**Refactoring Solution**:
```python
# Create configuration validator

from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ConfigValidationError:
    """Represents a configuration validation error."""
    field: str
    message: str
    severity: str = "error"

class ConfigValidator:
    """Validates service configurations."""

    REQUIRED_FIELDS = {
        'spotify': ['client_id', 'client_secret', 'redirect_uri'],
        'deezer': ['email'],
    }

    @classmethod
    def validate(
        cls,
        service: str,
        config: Dict[str, Any]
    ) -> List[ConfigValidationError]:
        """
        Validate configuration for a service.

        Args:
            service: Service name
            config: Configuration dictionary

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not config:
            errors.append(ConfigValidationError(
                field="config",
                message=f"{service.capitalize()} is not configured"
            ))
            return errors

        required = cls.REQUIRED_FIELDS.get(service, [])
        for field in required:
            if not config.get(field):
                errors.append(ConfigValidationError(
                    field=field,
                    message=f"Missing {service} {field}"
                ))

        return errors

    @classmethod
    def is_valid(cls, service: str, config: Dict[str, Any]) -> bool:
        """Check if configuration is valid."""
        return len(cls.validate(service, config)) == 0

    @classmethod
    def display_errors(
        cls,
        errors: List[ConfigValidationError],
        console: Console
    ) -> None:
        """Display validation errors."""
        for error in errors:
            console.print(f"[red]✗ {error.message}[/red]")

# Usage:
config = get_config('spotify')
errors = ConfigValidator.validate('spotify', config)
if errors:
    ConfigValidator.display_errors(errors, console)
    return
# ... proceed with valid config
```

**Savings**: ~150 lines, consistent validation

---

### 5. File System Operation Duplication

**Severity**: MEDIUM
**Instances**: 8+
**Estimated Duplication**: 100-120 lines

#### Pattern E: Path Validation and Creation

**Files**:
- Multiple across codebase

**Duplicated Code**:
```python
# Repeated pattern:

if not path:
    raise ValueError("path cannot be None or empty")

path = os.path.expanduser(path)

if not os.path.exists(path):
    raise FileNotFoundError(f"Path does not exist: {path}")

if not os.path.isdir(path):
    raise NotADirectoryError(f"Path is not a directory: {path}")
```

**Refactoring Solution**:
```python
# Create path utilities module

from pathlib import Path
from typing import Union

class PathValidator:
    """Utilities for path validation and handling."""

    @staticmethod
    def validate_exists(
        path: Union[str, Path],
        must_be_dir: bool = False,
        must_be_file: bool = False,
        create_if_missing: bool = False
    ) -> Path:
        """
        Validate and resolve a path.

        Args:
            path: Path to validate
            must_be_dir: If True, path must be a directory
            must_be_file: If True, path must be a file
            create_if_missing: If True, create directory if missing

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path is None or empty
            FileNotFoundError: If path doesn't exist
            NotADirectoryError: If must_be_dir and path is not directory
            IsADirectoryError: If must_be_file and path is directory
        """
        if not path:
            raise ValueError("path cannot be None or empty")

        resolved = Path(path).expanduser().resolve()

        if not resolved.exists():
            if create_if_missing and must_be_dir:
                resolved.mkdir(parents=True, exist_ok=True)
                return resolved
            raise FileNotFoundError(f"Path does not exist: {resolved}")

        if must_be_dir and not resolved.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {resolved}")

        if must_be_file and not resolved.is_file():
            raise IsADirectoryError(f"Path is not a file: {resolved}")

        return resolved

# Usage:
library_path = PathValidator.validate_exists(
    path=user_input,
    must_be_dir=True
)
```

**Savings**: ~100 lines, consistent path handling

---

### 6. Console Output Pattern Duplication

**Severity**: MEDIUM
**Instances**: 15+
**Estimated Duplication**: 150-180 lines

#### Pattern F: Success/Error Display

**Files**:
- Throughout codebase

**Duplicated Code**:
```python
# Success pattern (repeated 15+ times):
console.print("[green]✓ Operation successful![/green]")

# Error pattern (repeated 20+ times):
console.print(f"[red]✗ Operation failed: {error}[/red]")

# Warning pattern (repeated 10+ times):
console.print(f"[yellow]⚠ Warning: {message}[/yellow]")

# Info pattern (repeated 8+ times):
console.print(f"[cyan]ℹ Info: {message}[/cyan]")
```

**Refactoring Solution**:
```python
# Create output utility

from enum import Enum
from typing import Optional

class MessageType(Enum):
    """Types of console messages."""
    SUCCESS = ("green", "✓")
    ERROR = ("red", "✗")
    WARNING = ("yellow", "⚠")
    INFO = ("cyan", "ℹ")
    DEBUG = ("dim", "•")

class ConsoleOutput:
    """Consistent console output utilities."""

    def __init__(self, console: Console):
        self.console = console

    def message(
        self,
        text: str,
        msg_type: MessageType = MessageType.INFO,
        prefix: bool = True
    ) -> None:
        """
        Display a formatted message.

        Args:
            text: Message text
            msg_type: Type of message
            prefix: Include icon prefix
        """
        color, icon = msg_type.value
        prefix_str = f"{icon} " if prefix else ""
        self.console.print(f"[{color}]{prefix_str}{text}[/{color}]")

    def success(self, text: str) -> None:
        """Display success message."""
        self.message(text, MessageType.SUCCESS)

    def error(self, text: str) -> None:
        """Display error message."""
        self.message(text, MessageType.ERROR)

    def warning(self, text: str) -> None:
        """Display warning message."""
        self.message(text, MessageType.WARNING)

    def info(self, text: str) -> None:
        """Display info message."""
        self.message(text, MessageType.INFO)

# Usage:
output = ConsoleOutput(console)
output.success("Operation completed!")
output.error(f"Failed: {error}")
output.warning(f"Warning: {message}")
```

**Savings**: ~150 lines, consistent messaging

---

### 7. Import Pattern Duplication

**Severity**: LOW-MEDIUM
**Instances**: 20+
**Estimated Duplication**: 60-80 lines

#### Pattern G: Common Imports

**Files**:
- Nearly all Python files

**Duplicated Code**:
```python
# Repeated in 20+ files:

import os
import sys
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

**Refactoring Solution**:
```python
# Create logging utilities module

# utils/logging_setup.py
import logging
from typing import Optional

def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with consistent configuration.

    Args:
        name: Logger name (usually __name__)
        level: Logging level
        format_string: Custom format string

    Returns:
        Configured logger
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    logging.basicConfig(level=level, format=format_string)
    return logging.getLogger(name)

# Usage in files:
from utils.logging_setup import setup_logger
logger = setup_logger(__name__)
```

**Savings**: ~60 lines, consistent logging

---

## Duplication Summary Statistics

| Pattern Type | Instances | Duplicated Lines | Priority | Savings (hours) |
|--------------|-----------|------------------|----------|-----------------|
| Error Handling | 40+ | 400-500 | Critical | 8-10 |
| Database Connection | 5+ | 100-150 | High | 3-4 |
| Progress Bars | 10+ | 200-250 | Medium-High | 4-5 |
| Configuration Validation | 5+ | 150-200 | High | 3-4 |
| File System Operations | 8+ | 100-120 | Medium | 2-3 |
| Console Output | 15+ | 150-180 | Medium | 3-4 |
| Import/Logging Setup | 20+ | 60-80 | Low-Medium | 1-2 |
| **TOTAL** | **100+** | **1,160-1,480** | **-** | **24-32** |

---

## Clone Detection Results

### Type-1 Clones (Exact Duplicates)

1. **Backup File**: `cli_original_backup_20251119.py`
   - Exact clone of refactored `cli.py`
   - **Action**: DELETE immediately

2. **Database Connection Pattern**: 5 exact clones
   - **Action**: Extract to utility

### Type-2 Clones (Similar with Changes)

1. **Error Handling**: 40+ similar patterns with variable names changed
2. **Progress Bars**: 10+ similar with different column configs
3. **Config Validation**: 5+ similar with different fields

### Type-3 Clones (Structural Similarity)

1. **Menu Display Logic**: Similar structure across different menus
2. **CLI Command Patterns**: Similar flow in different commands

---

## Refactoring Roadmap

### Phase 1: Critical Duplications (Week 1)
1. Create error handling decorator
2. Create database connection factory
3. Remove backup file

**Estimated Savings**: 500+ lines, 10 hours effort

---

### Phase 2: High-Priority Patterns (Week 2)
4. Create configuration validator
5. Create progress bar factory
6. Create path validator

**Estimated Savings**: 400+ lines, 10 hours effort

---

### Phase 3: Medium-Priority Patterns (Week 3)
7. Create console output utility
8. Create logging setup utility
9. Extract common imports

**Estimated Savings**: 260+ lines, 6 hours effort

---

### Phase 4: Consolidation (Week 4)
10. Update all callsites to use new utilities
11. Add tests for new utilities
12. Documentation

**Estimated Effort**: 8 hours

---

## Expected Impact

### Before Refactoring:
- **Total Duplicated LOC**: ~1,200-1,500
- **Duplication %**: 15-20%
- **Maintenance Risk**: HIGH
- **Bug Multiplication**: YES
- **Test Coverage Difficulty**: HIGH

### After Refactoring:
- **Eliminated Duplicated LOC**: ~1,000+
- **Duplication %**: <5%
- **Maintenance Risk**: LOW
- **Bug Multiplication**: NO
- **Test Coverage**: Easier (single implementations)

### ROI Calculation

**Investment**: ~30 hours refactoring
**Returns**:
- **Immediate**: 1,000+ fewer lines to maintain
- **Ongoing**: 20-30% faster feature development
- **Quality**: Consistent error handling, consistent UX
- **Testing**: Easier to test single implementations

**Payback Period**: ~2-3 months

---

## Priority Recommendations

### Must Do (This Sprint):
1. ✅ Remove `cli_original_backup_20251119.py`
2. ✅ Extract error handling decorator
3. ✅ Extract database connection factory

### Should Do (Next Sprint):
4. Extract configuration validator
5. Extract progress bar factory
6. Extract console output utility

### Nice to Have (Future):
7. Extract path validator
8. Extract logging setup
9. Consolidate imports

---

## Monitoring Duplication

### Prevention Strategies

1. **Code Review Checklist**:
   - [ ] Check for duplicated error handling
   - [ ] Check for duplicated configuration validation
   - [ ] Check for duplicated UI patterns

2. **Automated Detection**:
   - Use `pylint` with duplication checker
   - Use `radon` for complexity analysis
   - Pre-commit hook for clone detection

3. **Design Patterns**:
   - Use DRY principle
   - Extract reusable utilities
   - Create shared base classes where appropriate

---

## Conclusion

The codebase has **significant duplication** (15-20%) that can be reduced to <5% with focused refactoring effort. The most impactful improvements come from:

1. Error handling standardization (400-500 lines saved)
2. Progress bar factory (200-250 lines saved)
3. Configuration validation (150-200 lines saved)

**Total Savings**: 1,000+ lines of code
**Total Effort**: 25-30 hours
**Return on Investment**: High

**Recommendation**: Prioritize error handling and database connection patterns for immediate impact.
