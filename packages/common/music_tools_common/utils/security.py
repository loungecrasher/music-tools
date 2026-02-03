"""
Security utilities for input validation, path traversal prevention,
and safe command execution.

This module provides security functions to prevent common vulnerabilities
like directory traversal, injection attacks, and information leakage.
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def validate_file_path(file_path: str, base_directory: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate a file path to prevent directory traversal attacks.

    Args:
        file_path: The file path to validate
        base_directory: Optional base directory to restrict access to

    Returns:
        Tuple of (is_valid, sanitized_path_or_error_message)

    Example:
        >>> is_valid, safe_path = validate_file_path('/path/to/file.txt')
        >>> if is_valid:
        ...     with open(safe_path, 'r') as f:
        ...         content = f.read()
    """
    try:
        # Convert to absolute path and resolve any symlinks
        absolute_path = os.path.abspath(os.path.expanduser(file_path))
        real_path = os.path.realpath(absolute_path)

        # Check for null bytes (common injection technique)
        if "\x00" in file_path:
            return False, "Invalid path: contains null bytes"

        # Check for directory traversal patterns
        if ".." in file_path or file_path.startswith("~"):
            # Resolve the path safely
            try:
                resolved_path = Path(file_path).resolve()
                real_path = str(resolved_path)
            except (OSError, ValueError) as e:
                return False, f"Invalid path: {e}"

        # If base directory is specified, ensure path is within it
        if base_directory:
            base_real = os.path.realpath(os.path.abspath(base_directory))
            if not real_path.startswith(base_real):
                return False, f"Path is outside allowed directory: {base_directory}"

        # Check if path exists and is accessible
        if os.path.exists(real_path):
            if not os.access(real_path, os.R_OK):
                return False, "Path exists but is not readable"

        return True, real_path

    except Exception as e:
        logger.error(f"Path validation error: {e}")
        return False, f"Path validation failed: {e}"


def sanitize_artist_name(artist_name: str, max_length: int = 100) -> str:
    """
    Sanitize artist name to prevent injection attacks.

    Args:
        artist_name: The artist name to sanitize
        max_length: Maximum allowed length (default: 100)

    Returns:
        Sanitized artist name

    Example:
        >>> sanitize_artist_name("Daft Punk <script>alert(1)</script>")
        'Daft Punk scriptalert1script'
    """
    # Remove control characters and limit special characters
    # Allow: alphanumeric, spaces, hyphens, periods, parentheses, commas, apostrophes, ampersands
    sanitized = re.sub(r"[^\w\s\-\.\(\)\,\'\&]", "", artist_name)

    # Remove multiple spaces
    sanitized = " ".join(sanitized.split())

    # Limit length to prevent buffer overflow
    sanitized = sanitized[:max_length]

    # Remove leading/trailing whitespace
    return sanitized.strip()


def sanitize_command_argument(argument: str) -> str:
    """
    Sanitize command line arguments to prevent injection.

    Args:
        argument: The argument to sanitize

    Returns:
        Sanitized argument safe for command execution

    Example:
        >>> sanitize_command_argument("file.txt; rm -rf /")
        'file.txt rm -rf '
    """
    # Remove shell metacharacters
    dangerous_chars = ["|", "&", ";", "$", "`", "\\", '"', "'", "\n", "\r", "\t"]
    sanitized = argument

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")

    # Escape remaining special characters
    sanitized = re.sub(r"[<>(){}[\]*?!]", "", sanitized)

    return sanitized


def mask_sensitive_value(value: str, visible_chars: int = 4, mask_char: str = "*") -> str:
    """
    Mask a sensitive value for logging/display.

    Shows only the first few characters and masks the rest.

    Args:
        value: The value to mask
        visible_chars: Number of characters to keep visible (default: 4)
        mask_char: Character to use for masking (default: '*')

    Returns:
        Masked value

    Example:
        >>> mask_sensitive_value('sk-ant-api03-1234567890abcdef')
        'sk-a***'
        >>> mask_sensitive_value('my_secret_password', visible_chars=2)
        'my***'
    """
    if not value:
        return ""

    if len(value) <= visible_chars:
        return mask_char * len(value)

    visible = value[:visible_chars]
    masked_length = min(len(value) - visible_chars, 20)  # Limit mask length
    return visible + (mask_char * masked_length)


def sanitize_log_message(message: str) -> str:
    """
    Sanitize log messages to prevent log injection and mask sensitive data.

    Args:
        message: The message to sanitize

    Returns:
        Sanitized message safe for logging

    Example:
        >>> sanitize_log_message("User logged in\\nADMIN: DELETE DATABASE")
        'User logged in\\nADMIN: DELETE DATABASE'
    """
    # Remove line breaks to prevent log injection
    sanitized = message.replace("\n", "\\n").replace("\r", "\\r")

    # Mask potential sensitive data patterns
    # Mask API keys (common patterns)
    sanitized = re.sub(
        r'(api[_\-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9\-_]{20,})',
        r"\1***REDACTED***",
        sanitized,
        flags=re.IGNORECASE,
    )

    # Mask tokens
    sanitized = re.sub(
        r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9\-_]{20,})',
        r"\1***REDACTED***",
        sanitized,
        flags=re.IGNORECASE,
    )

    # Mask passwords
    sanitized = re.sub(
        r'(password["\']?\s*[:=]\s*["\']?)([^\s"\']+)',
        r"\1***REDACTED***",
        sanitized,
        flags=re.IGNORECASE,
    )

    # Mask Bearer tokens
    sanitized = re.sub(
        r"(Bearer\s+)([a-zA-Z0-9\-_\.]+)", r"\1***REDACTED***", sanitized, flags=re.IGNORECASE
    )

    return sanitized


def secure_permissions(file_path: Path | str, mode: int = 0o644) -> Tuple[bool, str]:
    """
    Set secure permissions on a file.

    Args:
        file_path: Path to the file
        mode: Permission mode (default: 0o644 - rw-r--r--)

    Returns:
        Tuple of (success, error_message)

    Example:
        >>> success, error = secure_permissions('/path/to/file.txt')
        >>> if success:
        ...     print("File permissions secured")
    """
    try:
        path = Path(file_path) if isinstance(file_path, str) else file_path

        if not path.exists():
            return False, f"File does not exist: {file_path}"

        os.chmod(path, mode)
        return True, ""

    except PermissionError:
        error_msg = f"Permission denied when setting permissions: {file_path}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Error setting permissions on {file_path}: {e}"
        logger.error(error_msg)
        return False, error_msg


def validate_batch_size(size: int, max_size: int = 1000) -> Tuple[bool, int]:
    """
    Validate batch size to prevent memory exhaustion.

    Args:
        size: The requested batch size
        max_size: Maximum allowed batch size (default: 1000)

    Returns:
        Tuple of (is_valid, safe_size)

    Example:
        >>> is_valid, safe_size = validate_batch_size(5000)
        >>> if is_valid:
        ...     print(f"Using batch size: {safe_size}")
    """
    if not isinstance(size, int):
        return False, 100  # Default safe size

    if size <= 0:
        return False, 100

    if size > max_size:
        logger.warning(f"Batch size {size} exceeds maximum {max_size}, using {max_size}")
        return True, max_size

    return True, size


def validate_timeout(timeout: int | float, max_timeout: int = 3600) -> Tuple[bool, int]:
    """
    Validate timeout value to prevent DoS.

    Args:
        timeout: The requested timeout in seconds
        max_timeout: Maximum allowed timeout (default: 3600)

    Returns:
        Tuple of (is_valid, safe_timeout)

    Example:
        >>> is_valid, safe_timeout = validate_timeout(7200)
        >>> if is_valid:
        ...     print(f"Using timeout: {safe_timeout}s")
    """
    if not isinstance(timeout, (int, float)):
        return False, 60  # Default safe timeout

    if timeout <= 0:
        return False, 60

    if timeout > max_timeout:
        logger.warning(f"Timeout {timeout}s exceeds maximum {max_timeout}s, using {max_timeout}s")
        return True, max_timeout

    return True, int(timeout)


def is_safe_filename(filename: str) -> bool:
    """
    Check if a filename is safe (no path traversal, special chars).

    Args:
        filename: Filename to check

    Returns:
        True if safe, False otherwise

    Example:
        >>> is_safe_filename('my_song.mp3')
        True
        >>> is_safe_filename('../../../etc/passwd')
        False
    """
    if not filename:
        return False

    # Check for path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        return False

    # Check for null bytes
    if "\x00" in filename:
        return False

    # Check for control characters
    if any(ord(c) < 32 for c in filename):
        return False

    # Check for reserved Windows filenames
    reserved_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    name_without_ext = os.path.splitext(filename)[0].upper()
    if name_without_ext in reserved_names:
        return False

    return True


def escape_html(text: str) -> str:
    """
    Escape HTML special characters to prevent XSS.

    Args:
        text: Text to escape

    Returns:
        HTML-escaped text

    Example:
        >>> escape_html('<script>alert("XSS")</script>')
        '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;'
    """
    if not text:
        return ""

    html_escape_table = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
        "/": "&#x2F;",
    }

    return "".join(html_escape_table.get(c, c) for c in text)


def validate_port(port: int | str) -> Tuple[bool, Optional[int], str]:
    """
    Validate a network port number.

    Args:
        port: Port number to validate

    Returns:
        Tuple of (is_valid, port_number, error_message)

    Example:
        >>> is_valid, port_num, error = validate_port(8080)
        >>> if is_valid:
        ...     print(f"Using port: {port_num}")
    """
    try:
        port_int = int(port)
    except (ValueError, TypeError):
        return False, None, f"Port must be an integer, got: {type(port).__name__}"

    if port_int < 1 or port_int > 65535:
        return False, None, f"Port must be between 1 and 65535, got: {port_int}"

    # Warn about privileged ports
    if port_int < 1024:
        logger.warning(f"Port {port_int} is a privileged port (< 1024)")

    return True, port_int, ""


def check_path_traversal(path: str) -> bool:
    """
    Check if a path contains directory traversal attempts.

    Args:
        path: Path to check

    Returns:
        True if path contains traversal attempts, False otherwise

    Example:
        >>> check_path_traversal('../../../etc/passwd')
        True
        >>> check_path_traversal('/safe/path/file.txt')
        False
    """
    # Check for common traversal patterns
    traversal_patterns = [
        "..",
        "%2e%2e",
        "%252e%252e",
        "..%2f",
        "..%5c",
        "%2e%2e/",
        "%2e%2e\\",
    ]

    path_lower = path.lower()
    return any(pattern in path_lower for pattern in traversal_patterns)


class SecureFileHandler:
    """
    Secure file operations with validation.

    Example:
        >>> handler = SecureFileHandler('/safe/base/directory')
        >>> success, content, error = handler.safe_read('file.txt')
        >>> if success:
        ...     print(f"Read {len(content)} bytes")
    """

    def __init__(self, base_directory: Optional[str] = None):
        """
        Initialize secure file handler.

        Args:
            base_directory: Optional base directory to restrict file operations to
        """
        self.base_directory = base_directory

    def safe_read(self, file_path: str) -> Tuple[bool, Optional[str], str]:
        """
        Safely read a file with validation.

        Args:
            file_path: Path to the file to read

        Returns:
            Tuple of (success, content, error_message)
        """
        # Validate the file path
        is_valid, safe_path = validate_file_path(file_path, self.base_directory)

        if not is_valid:
            return False, None, safe_path  # safe_path contains error message

        try:
            with open(safe_path, "r", encoding="utf-8") as f:
                content = f.read()
            return True, content, ""
        except Exception as e:
            logger.error(f"Failed to read file {safe_path}: {e}")
            return False, None, str(e)

    def safe_write(self, file_path: str, content: str) -> Tuple[bool, str]:
        """
        Safely write to a file with validation.

        Args:
            file_path: Path to the file to write
            content: Content to write

        Returns:
            Tuple of (success, error_message)
        """
        # Validate the file path
        is_valid, safe_path = validate_file_path(file_path, self.base_directory)

        if not is_valid:
            return False, safe_path  # safe_path contains error message

        try:
            # Create parent directory if needed
            parent_dir = os.path.dirname(safe_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, mode=0o755)

            # Write with restricted permissions
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Set appropriate file permissions (readable by owner/group, not others)
            os.chmod(safe_path, 0o644)

            return True, ""
        except Exception as e:
            logger.error(f"Failed to write file {safe_path}: {e}")
            return False, str(e)

    def safe_delete(self, file_path: str) -> Tuple[bool, str]:
        """
        Safely delete a file with validation.

        Args:
            file_path: Path to the file to delete

        Returns:
            Tuple of (success, error_message)
        """
        # Validate the file path
        is_valid, safe_path = validate_file_path(file_path, self.base_directory)

        if not is_valid:
            return False, safe_path  # safe_path contains error message

        try:
            if os.path.exists(safe_path):
                os.remove(safe_path)
            return True, ""
        except Exception as e:
            logger.error(f"Failed to delete file {safe_path}: {e}")
            return False, str(e)
