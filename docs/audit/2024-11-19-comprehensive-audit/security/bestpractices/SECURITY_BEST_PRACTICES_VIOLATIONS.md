# Security Best Practices Violations

**Project:** Music Tools
**Date:** 2025-11-19
**Focus:** Code quality and security hygiene

---

## Overview

This document catalogs violations of security best practices found in the codebase. While not all issues represent immediate vulnerabilities, they increase risk and should be addressed to maintain a strong security posture.

---

## 1. Secrets Management

### 1.1 .env Files in Repository

**Severity:** MEDIUM
**Category:** Secrets Management
**OWASP:** A02:2021 - Cryptographic Failures

**Issue:**
Two `.env` files exist in the repository (in legacy directories):
```
/apps/music-tools/legacy/Deezer-Playlist-Fixer/.env
/apps/music-tools/legacy/Spotify Script/V2/.env
```

**Current Content:**
```bash
# Deezer .env
DEEZER_APP_ID=YOUR_APP_ID
DEEZER_APP_SECRET=YOUR_APP_SECRET
DEEZER_REDIRECT_URI=http://localhost:8080/callback

# Spotify .env
SPOTIPY_CLIENT_ID=your-client-id-here
SPOTIPY_CLIENT_SECRET=your-client-secret-here
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
```

**Risk:**
- Users might put real credentials in these files
- Files could be accidentally committed with real secrets
- Git history might contain previously committed secrets

**Best Practice:**
```bash
# 1. Remove .env files from repository
git rm apps/music-tools/legacy/Deezer-Playlist-Fixer/.env
git rm "apps/music-tools/legacy/Spotify Script/V2/.env"

# 2. Add to .gitignore
echo "**/.env" >> .gitignore
echo "**/.env.local" >> .gitignore

# 3. Create .env.example files instead
cp .env .env.example
# Then remove real values from .env.example

# 4. Scan git history for secrets
git log -p | grep -i "secret\|password\|api_key"

# 5. Use git-secrets to prevent future commits
git secrets --install
git secrets --register-aws
```

---

### 1.2 API Key Exposure in Logs

**Severity:** LOW-MEDIUM
**Category:** Information Disclosure
**CWE:** CWE-532

**Issue:**
While `sanitize_log_message()` exists, it's not consistently used across all logging statements.

**Example of Good Practice:**
```python
# File: packages/common/music_tools_common/utils/security.py
def sanitize_log_message(message: str) -> str:
    """Sanitize log messages to prevent log injection and mask sensitive data."""
    sanitized = re.sub(
        r'(api[_\-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9\-_]{20,})',
        r'\1***REDACTED***',
        message,
        flags=re.IGNORECASE
    )
    return sanitized
```

**Recommendation:**
```python
# Create custom logging formatter
import logging

class SanitizingFormatter(logging.Formatter):
    """Formatter that automatically sanitizes sensitive data."""

    def format(self, record):
        # Import here to avoid circular imports
        from music_tools_common.utils.security import sanitize_log_message

        # Sanitize the message
        if isinstance(record.msg, str):
            record.msg = sanitize_log_message(record.msg)

        # Sanitize arguments
        if record.args:
            record.args = tuple(
                sanitize_log_message(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )

        return super().format(record)

# Configure logging with sanitizing formatter
handler = logging.StreamHandler()
handler.setFormatter(SanitizingFormatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logging.getLogger().addHandler(handler)
```

---

## 2. Input Validation

### 2.1 Inconsistent Path Validation

**Severity:** MEDIUM
**Category:** Path Traversal Prevention
**CWE:** CWE-22

**Issue:**
User input for file paths is accepted without consistent validation.

**Examples:**
```python
# File: apps/music-tools/src/tagging/cli.py:300
path = input("Enter path to add (or Enter to cancel): ").strip()
# No validation before use
```

**Best Practice Implementation:**
```python
from src.tagging.core.security import SecurityValidator

validator = SecurityValidator()

def get_validated_path(prompt: str, base_dir: Optional[str] = None) -> Optional[str]:
    """
    Get and validate a file path from user input.

    Args:
        prompt: Prompt to display to user
        base_dir: Optional base directory to restrict access

    Returns:
        Validated path or None if cancelled
    """
    while True:
        path = input(prompt).strip()

        if not path:
            return None

        is_valid, result = validator.validate_file_path(path, base_dir)

        if not is_valid:
            console.print(f"[red]Invalid path: {result}[/red]")
            retry = input("Try again? (y/n): ").strip().lower()
            if retry != 'y':
                return None
            continue

        return result

# Usage:
path = get_validated_path("Enter path to add (or Enter to cancel): ")
if path:
    # Use the validated path
    process_path(path)
```

---

### 2.2 Numeric Input Validation Missing

**Severity:** LOW
**Category:** Input Validation
**CWE:** CWE-20

**Issue:**
Numeric inputs (batch sizes, timeouts) sometimes lack validation.

**Best Practice:**
```python
def get_validated_integer(
    prompt: str,
    min_value: int = 1,
    max_value: int = 1000,
    default: Optional[int] = None
) -> int:
    """
    Get and validate an integer from user input.

    Args:
        prompt: Prompt to display
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        default: Default value if user presses Enter

    Returns:
        Validated integer
    """
    while True:
        try:
            user_input = input(prompt).strip()

            if not user_input and default is not None:
                return default

            value = int(user_input)

            if value < min_value or value > max_value:
                console.print(
                    f"[yellow]Value must be between {min_value} and {max_value}[/yellow]"
                )
                continue

            return value

        except ValueError:
            console.print("[red]Please enter a valid number[/red]")

# Usage:
batch_size = get_validated_integer(
    "Enter batch size (1-1000): ",
    min_value=1,
    max_value=1000,
    default=100
)
```

---

## 3. Error Handling & Information Disclosure

### 3.1 Verbose Error Messages

**Severity:** LOW
**Category:** Information Disclosure
**CWE:** CWE-209

**Issue:**
Some error messages expose internal system details.

**Examples to Avoid:**
```python
# Bad: Exposes file system structure
raise ValueError(f"File not found: /home/user/.music_tools/config.json")

# Bad: Exposes database schema
raise Exception(f"Column 'user_password' does not exist")

# Bad: Exposes library versions
raise ImportError(f"Cannot import module 'foo' version 1.2.3")
```

**Best Practice:**
```python
# Good: Generic user-facing message, detailed log
try:
    process_file(path)
except Exception as e:
    logger.error(f"File processing failed: {path} - {e}", exc_info=True)
    raise ValueError("Unable to process file. Please check the path and try again.")

# Good: Sanitize error messages
def sanitize_error_message(error: Exception, debug_mode: bool = False) -> str:
    """
    Create user-friendly error message.

    Args:
        error: The exception
        debug_mode: If True, include more details

    Returns:
        Sanitized error message
    """
    if debug_mode:
        return str(error)

    # Map specific errors to generic messages
    error_map = {
        FileNotFoundError: "The specified file could not be found",
        PermissionError: "Permission denied. Check file permissions",
        ValueError: "Invalid input provided",
        ConnectionError: "Network connection failed",
    }

    error_type = type(error)
    return error_map.get(error_type, "An error occurred. Check logs for details")
```

---

### 3.2 Exception Information Leakage

**Severity:** LOW
**Category:** Information Disclosure

**Issue:**
Stack traces might be displayed to users in production.

**Best Practice:**
```python
import sys
import traceback

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler that prevents information leakage."""

    # Log the full exception
    logger.error(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

    # In production, show generic message
    if not DEBUG_MODE:
        console.print("[red]An error occurred. Please check logs for details.[/red]")
        console.print(f"[dim]Error ID: {generate_error_id()}[/dim]")
    else:
        # In development, show full traceback
        traceback.print_exception(exc_type, exc_value, exc_traceback)

# Install the exception handler
sys.excepthook = handle_exception
```

---

## 4. Authentication & Authorization

### 4.1 No Rate Limiting on API Key Entry

**Severity:** MEDIUM
**Category:** Brute Force Prevention
**CWE:** CWE-307

**Issue:**
API key configuration allows unlimited attempts without delay.

**Best Practice:**
```python
import time
from collections import defaultdict

class AuthenticationRateLimiter:
    """Rate limiter for authentication attempts."""

    def __init__(self, max_attempts: int = 3, lockout_duration: int = 300):
        self.max_attempts = max_attempts
        self.lockout_duration = lockout_duration
        self.attempts = defaultdict(list)

    def check_rate_limit(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if authentication attempt is allowed.

        Args:
            identifier: Unique identifier (IP, user, etc.)

        Returns:
            Tuple of (allowed, seconds_until_retry)
        """
        now = time.time()
        attempts = self.attempts[identifier]

        # Remove old attempts
        attempts[:] = [t for t in attempts if now - t < self.lockout_duration]

        if len(attempts) >= self.max_attempts:
            time_since_first = now - attempts[0]
            wait_time = self.lockout_duration - time_since_first
            return False, int(wait_time)

        return True, 0

    def record_attempt(self, identifier: str):
        """Record an authentication attempt."""
        self.attempts[identifier].append(time.time())

# Usage in API key configuration
rate_limiter = AuthenticationRateLimiter()

def configure_api_key():
    """Configure API key with rate limiting."""
    identifier = "api_key_config"  # Or use IP address

    for attempt in range(5):
        allowed, wait_time = rate_limiter.check_rate_limit(identifier)

        if not allowed:
            console.print(
                f"[red]Too many attempts. Please wait {wait_time} seconds.[/red]"
            )
            return

        api_key = getpass.getpass("Enter API key: ").strip()

        if validate_api_key(api_key):
            config.api_key = api_key
            return

        rate_limiter.record_attempt(identifier)
        console.print("[yellow]Invalid API key. Try again.[/yellow]")

    console.print("[red]Maximum attempts exceeded.[/red]")
```

---

### 4.2 No Session Management

**Severity:** LOW (CLI app)
**Category:** Session Management

**Issue:**
If the application evolves to support web interfaces, session management will be needed.

**Best Practice (for future web features):**
```python
from flask import Flask, session
from flask_session import Session
import secrets

app = Flask(__name__)

# Configure secure sessions
app.config['SECRET_KEY'] = secrets.token_hex(32)
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

Session(app)
```

---

## 5. Data Protection

### 5.1 Database Encryption at Rest

**Severity:** LOW-MEDIUM
**Category:** Data Protection
**CWE:** CWE-311

**Current State:**
SQLite databases are stored without encryption.

**Risk:**
If database contains sensitive data (artist searches, user preferences), it could be read if file system is compromised.

**Best Practice:**
```python
# Option 1: Use SQLCipher (encrypted SQLite)
from pysqlcipher3 import dbapi2 as sqlite

conn = sqlite.connect('encrypted.db')
conn.execute("PRAGMA key='your-encryption-key'")

# Option 2: Encrypt sensitive fields
from cryptography.fernet import Fernet

class EncryptedDatabase:
    """Database with field-level encryption."""

    def __init__(self, db_path: str, encryption_key: bytes):
        self.db_path = db_path
        self.cipher = Fernet(encryption_key)

    def encrypt_value(self, value: str) -> bytes:
        """Encrypt a string value."""
        return self.cipher.encrypt(value.encode())

    def decrypt_value(self, encrypted: bytes) -> str:
        """Decrypt a value."""
        return self.cipher.decrypt(encrypted).decode()

# Store encryption key in secure location
encryption_key = os.environ.get('DB_ENCRYPTION_KEY')
if not encryption_key:
    raise ValueError("DB_ENCRYPTION_KEY environment variable required")
```

---

### 5.2 Insecure File Permissions

**Severity:** MEDIUM
**Category:** Access Control
**CWE:** CWE-732

**Issue:**
Config files and databases created with 0o644 (world-readable).

**Current Code:**
```python
# File: src/tagging/core/security.py:285
os.chmod(safe_path, 0o644)  # rw-r--r--
```

**Best Practice:**
```python
def secure_file_permissions(file_path: Path, file_type: str = 'general') -> None:
    """
    Set appropriate permissions based on file type.

    Args:
        file_path: Path to file
        file_type: Type of file (config, database, general)
    """
    permission_map = {
        'config': 0o600,    # rw------- (owner only)
        'database': 0o600,  # rw------- (owner only)
        'secret': 0o600,    # rw------- (owner only)
        'general': 0o644,   # rw-r--r-- (standard)
        'executable': 0o755 # rwxr-xr-x (executable)
    }

    mode = permission_map.get(file_type, 0o644)
    os.chmod(file_path, mode)

    # Verify permissions were set correctly
    current_mode = file_path.stat().st_mode & 0o777
    if current_mode != mode:
        raise PermissionError(f"Failed to set permissions on {file_path}")

# Usage:
secure_file_permissions(config_file, 'config')
secure_file_permissions(database_file, 'database')
```

---

## 6. Logging & Monitoring

### 6.1 Insufficient Security Event Logging

**Severity:** MEDIUM
**Category:** Security Monitoring
**CWE:** CWE-778

**Issue:**
Security events (failed auth, path validation failures) not consistently logged.

**Best Practice:**
```python
import logging
import json
from datetime import datetime

class SecurityEventLogger:
    """Structured logging for security events."""

    def __init__(self):
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)

        # Create handler for security events
        handler = logging.FileHandler('logs/security_events.log')
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)

    def log_event(
        self,
        event_type: str,
        severity: str,
        details: dict,
        user_id: Optional[str] = None
    ):
        """
        Log a security event.

        Args:
            event_type: Type of event (auth_failure, path_validation_fail, etc.)
            severity: Event severity (info, warning, error)
            details: Event details
            user_id: Optional user identifier
        """
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'details': details,
            'user_id': user_id or 'anonymous'
        }

        self.logger.log(
            getattr(logging, severity.upper()),
            json.dumps(event)
        )

# Usage:
security_logger = SecurityEventLogger()

# Log authentication failure
security_logger.log_event(
    event_type='authentication_failure',
    severity='warning',
    details={
        'method': 'api_key',
        'reason': 'invalid_key'
    }
)

# Log path validation failure
security_logger.log_event(
    event_type='path_validation_failed',
    severity='warning',
    details={
        'path': sanitize_log_message(path),
        'reason': 'directory_traversal_attempt'
    }
)
```

---

### 6.2 No Security Alerting

**Severity:** LOW
**Category:** Incident Response

**Best Practice:**
```python
import smtplib
from email.message import EmailMessage

class SecurityAlertSystem:
    """Alert system for critical security events."""

    def __init__(self, alert_email: str, smtp_config: dict):
        self.alert_email = alert_email
        self.smtp_config = smtp_config
        self.alert_threshold = 5  # Alert after 5 events in 1 hour

    def send_alert(self, event_type: str, event_details: dict):
        """Send security alert email."""
        msg = EmailMessage()
        msg['Subject'] = f'Security Alert: {event_type}'
        msg['From'] = self.smtp_config['from']
        msg['To'] = self.alert_email

        body = f"""
        Security Event Detected

        Event Type: {event_type}
        Time: {datetime.utcnow().isoformat()}

        Details:
        {json.dumps(event_details, indent=2)}

        Please investigate immediately.
        """
        msg.set_content(body)

        # Send email
        with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
            server.starttls()
            server.login(self.smtp_config['user'], self.smtp_config['password'])
            server.send_message(msg)

    def check_and_alert(self, events: List[dict]):
        """Check events and send alert if threshold exceeded."""
        recent_events = [
            e for e in events
            if (datetime.utcnow() - datetime.fromisoformat(e['timestamp'])).seconds < 3600
        ]

        if len(recent_events) >= self.alert_threshold:
            self.send_alert('multiple_security_events', {
                'count': len(recent_events),
                'events': recent_events
            })
```

---

## 7. Code Quality Issues

### 7.1 Lack of Type Hints in Security Functions

**Severity:** LOW
**Category:** Code Quality

**Issue:**
Not all security-critical functions have type hints.

**Best Practice:**
```python
from typing import Tuple, Optional

# Bad: No type hints
def validate_path(path, base_dir):
    # ... implementation

# Good: Clear type hints
def validate_path(
    path: str,
    base_dir: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Validate a file path to prevent directory traversal.

    Args:
        path: Path to validate
        base_dir: Optional base directory restriction

    Returns:
        Tuple of (is_valid, result_or_error)
    """
    # ... implementation
```

---

### 7.2 Missing Security Documentation

**Severity:** LOW
**Category:** Documentation

**Best Practice:**
```python
"""
security.py - Security Utilities

SECURITY CRITICAL MODULE
This module contains functions that prevent security vulnerabilities.
Changes to this module require security review.

Security Features:
- Path traversal prevention
- Input sanitization
- Command injection prevention
- Sensitive data masking

Usage:
    from security import validate_file_path

    is_valid, path = validate_file_path(user_input)
    if not is_valid:
        raise ValueError(f"Invalid path: {path}")

Testing:
    All security functions must have unit tests that include
    malicious input attempts.

Maintenance:
    - Review after any changes to Python version
    - Review when dependencies are updated
    - Review quarterly for new attack vectors
"""
```

---

## Summary Checklist

### Immediate Actions
- [ ] Remove .env files from repository
- [ ] Add .env to .gitignore
- [ ] Scan git history for secrets
- [ ] Implement consistent path validation

### Short-term
- [ ] Add rate limiting to authentication
- [ ] Implement security event logging
- [ ] Update file permissions for sensitive files
- [ ] Add type hints to security functions

### Long-term
- [ ] Set up security alerting
- [ ] Implement database encryption
- [ ] Create security testing suite
- [ ] Document security architecture

### Ongoing
- [ ] Regular security code reviews
- [ ] Update security documentation
- [ ] Monitor security events
- [ ] Train developers on secure coding

---

**Best Practices Compliance Score: 6.5/10**

The codebase shows good security awareness with dedicated security modules, but lacks consistency in applying best practices across all code. Addressing these issues will significantly improve the security posture.
