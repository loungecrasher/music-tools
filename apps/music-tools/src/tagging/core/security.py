"""
Security Utilities Module

Provides security functions for input validation, path traversal prevention,
and safe command execution.
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Centralized security validation for the application."""

    @staticmethod
    def validate_file_path(file_path: str, base_directory: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate a file path to prevent directory traversal attacks.

        Args:
            file_path: The file path to validate
            base_directory: Optional base directory to restrict access to

        Returns:
            Tuple of (is_valid, sanitized_path or error_message)
        """
        try:
            # Convert to absolute path and resolve any symlinks
            absolute_path = os.path.abspath(os.path.expanduser(file_path))
            real_path = os.path.realpath(absolute_path)

            # Check for null bytes (common injection technique)
            if '\x00' in file_path:
                return False, "Invalid path: contains null bytes"

            # Check for directory traversal patterns
            if '..' in file_path or file_path.startswith('~'):
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

    @staticmethod
    def sanitize_artist_name(artist_name: str, max_length: int = 100) -> str:
        """
        Sanitize artist name to prevent injection attacks.

        Args:
            artist_name: The artist name to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized artist name
        """
        # Remove control characters and limit special characters
        # Allow: alphanumeric, spaces, hyphens, periods, parentheses, commas, apostrophes
        sanitized = re.sub(r'[^\w\s\-\.\(\)\,\'\&]', '', artist_name)

        # Remove multiple spaces
        sanitized = ' '.join(sanitized.split())

        # Limit length to prevent buffer overflow
        sanitized = sanitized[:max_length]

        # Remove leading/trailing whitespace
        return sanitized.strip()

    @staticmethod
    def sanitize_command_argument(argument: str) -> str:
        """
        Sanitize command line arguments to prevent injection.

        Args:
            argument: The argument to sanitize

        Returns:
            Sanitized argument safe for command execution
        """
        # Remove shell metacharacters
        dangerous_chars = ['|', '&', ';', '$', '`', '\\', '"', "'", '\n', '\r', '\t']
        sanitized = argument

        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')

        # Escape remaining special characters
        sanitized = re.sub(r'[<>(){}[\]*?!]', '', sanitized)

        return sanitized

    @staticmethod
    def validate_api_key(api_key: str) -> Tuple[bool, str]:
        """
        Validate API key format.

        Args:
            api_key: The API key to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not api_key:
            return False, "API key is empty"

        # Check for reasonable length (most API keys are 20-200 chars)
        if len(api_key) < 20 or len(api_key) > 200:
            return False, "API key has invalid length"

        # Check for valid characters (alphanumeric plus common separators)
        if not re.match(r'^[a-zA-Z0-9\-_]+$', api_key):
            return False, "API key contains invalid characters"

        # Don't log the actual key for security
        logger.debug("API key validation successful")

        return True, ""

    @staticmethod
    def sanitize_log_message(message: str) -> str:
        """
        Sanitize log messages to prevent log injection.

        Args:
            message: The message to sanitize

        Returns:
            Sanitized message safe for logging
        """
        # Remove line breaks to prevent log injection
        sanitized = message.replace('\n', '\\n').replace('\r', '\\r')

        # Mask potential sensitive data patterns
        # Mask API keys (common patterns)
        sanitized = re.sub(r'(api[_\-]?key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9\-_]{20,})',
                           r'\1***REDACTED***', sanitized, flags=re.IGNORECASE)

        # Mask tokens
        sanitized = re.sub(r'(token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9\-_]{20,})',
                           r'\1***REDACTED***', sanitized, flags=re.IGNORECASE)

        # Mask passwords
        sanitized = re.sub(r'(password["\']?\s*[:=]\s*["\']?)([^\s"\']+)',
                           r'\1***REDACTED***', sanitized, flags=re.IGNORECASE)

        return sanitized

    @staticmethod
    def validate_batch_size(size: int, max_size: int = 1000) -> Tuple[bool, int]:
        """
        Validate batch size to prevent memory exhaustion.

        Args:
            size: The requested batch size
            max_size: Maximum allowed batch size

        Returns:
            Tuple of (is_valid, safe_size)
        """
        if not isinstance(size, int):
            return False, 100  # Default safe size

        if size <= 0:
            return False, 100

        if size > max_size:
            logger.warning(f"Batch size {size} exceeds maximum {max_size}, using {max_size}")
            return True, max_size

        return True, size

    @staticmethod
    def validate_timeout(timeout: int, max_timeout: int = 3600) -> Tuple[bool, int]:
        """
        Validate timeout value to prevent DoS.

        Args:
            timeout: The requested timeout in seconds
            max_timeout: Maximum allowed timeout

        Returns:
            Tuple of (is_valid, safe_timeout)
        """
        if not isinstance(timeout, (int, float)):
            return False, 60  # Default safe timeout

        if timeout <= 0:
            return False, 60

        if timeout > max_timeout:
            logger.warning(f"Timeout {timeout}s exceeds maximum {max_timeout}s, using {max_timeout}s")
            return True, max_timeout

        return True, int(timeout)


class SecureFileHandler:
    """Secure file operations with validation."""

    def __init__(self, base_directory: Optional[str] = None):
        """
        Initialize secure file handler.

        Args:
            base_directory: Optional base directory to restrict file operations to
        """
        self.base_directory = base_directory
        self.validator = SecurityValidator()

    def safe_read(self, file_path: str) -> Tuple[bool, Optional[str], str]:
        """
        Safely read a file with validation.

        Args:
            file_path: Path to the file to read

        Returns:
            Tuple of (success, content, error_message)
        """
        # Validate the file path
        is_valid, safe_path = self.validator.validate_file_path(file_path, self.base_directory)

        if not is_valid:
            return False, None, safe_path  # safe_path contains error message

        try:
            with open(safe_path, 'r', encoding='utf-8') as f:
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
        is_valid, safe_path = self.validator.validate_file_path(file_path, self.base_directory)

        if not is_valid:
            return False, safe_path  # safe_path contains error message

        try:
            # Create parent directory if needed
            parent_dir = os.path.dirname(safe_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, mode=0o755)

            # Write with restricted permissions
            with open(safe_path, 'w', encoding='utf-8') as f:
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
        is_valid, safe_path = self.validator.validate_file_path(file_path, self.base_directory)

        if not is_valid:
            return False, safe_path  # safe_path contains error message

        try:
            if os.path.exists(safe_path):
                os.remove(safe_path)
            return True, ""
        except Exception as e:
            logger.error(f"Failed to delete file {safe_path}: {e}")
            return False, str(e)
