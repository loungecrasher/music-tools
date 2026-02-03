"""
Unified error handling and retry logic for the music tagger application.

This module provides centralized error handling, retry mechanisms, and consistent
error reporting across all components.
"""

import logging
import time
import traceback
from functools import wraps
from typing import Any, Callable, Optional, Type, Union, Tuple, List
from enum import Enum
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types for better handling."""

    TRANSIENT = "transient"  # Temporary errors that might succeed on retry
    PERMANENT = "permanent"  # Errors that won't be fixed by retrying
    CONFIGURATION = "configuration"  # Configuration or setup issues
    NETWORK = "network"  # Network connectivity issues
    FILESYSTEM = "filesystem"  # File system access issues
    DATABASE = "database"  # Database operation issues
    API = "api"  # External API issues
    VALIDATION = "validation"  # Data validation errors


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MusicTaggerError(Exception):
    """Base exception for all music tagger errors."""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.PERMANENT,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        original_error: Optional[Exception] = None,
        context: Optional[dict] = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.severity = severity
        self.original_error = original_error
        self.context = context or {}


class ConfigurationError(MusicTaggerError):
    """Configuration-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_type=ErrorType.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class CacheError(MusicTaggerError):
    """Cache/database-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_type=ErrorType.DATABASE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class MetadataError(MusicTaggerError):
    """Metadata handling errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_type=ErrorType.FILESYSTEM,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class APIError(MusicTaggerError):
    """API-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            error_type=ErrorType.API,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class ErrorHandler:
    """Centralized error handling and retry logic."""

    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        self.error_counts = {}
        self.last_errors = {}

    def classify_error(self, error: Exception) -> ErrorType:
        """Classify an error to determine appropriate handling."""

        # Database errors
        if isinstance(error, sqlite3.Error):
            return ErrorType.DATABASE

        # File system errors
        if isinstance(error, (FileNotFoundError, PermissionError, OSError)):
            return ErrorType.FILESYSTEM

        # Network/API errors
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorType.NETWORK

        # Configuration errors
        if "config" in str(error).lower() or "api_key" in str(error).lower():
            return ErrorType.CONFIGURATION

        # Default to permanent
        return ErrorType.PERMANENT

    def should_retry(self, error: Exception, attempt: int, max_attempts: int) -> bool:
        """Determine if an error should trigger a retry."""

        if attempt >= max_attempts:
            return False

        error_type = self.classify_error(error)

        # Only retry transient errors
        return error_type in (
            ErrorType.TRANSIENT,
            ErrorType.NETWORK,
            ErrorType.API,
            ErrorType.DATABASE  # SQLite temporary lock issues
        )

    def calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay before retry with exponential backoff."""

        delay = config.base_delay * (config.exponential_base ** attempt)
        delay = min(delay, config.max_delay)

        # Add jitter to prevent thundering herd
        if config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)

        return delay

    def record_error(self, operation: str, error: Exception):
        """Record error statistics for monitoring."""

        error_type = self.classify_error(error)
        key = f"{operation}:{error_type.value}"

        self.error_counts[key] = self.error_counts.get(key, 0) + 1
        self.last_errors[key] = {
            'error': str(error),
            'timestamp': time.time(),
            'type': error_type.value
        }

    def format_error_message(
        self,
        operation: str,
        error: Exception,
        context: Optional[dict] = None
    ) -> str:
        """Format a consistent error message."""

        error_type = self.classify_error(error)
        context_str = ""

        if context:
            context_items = [f"{k}={v}" for k, v in context.items()]
            context_str = f" ({', '.join(context_items)})"

        return f"{operation} failed [{error_type.value}]: {error}{context_str}"

    def handle_error(
        self,
        operation: str,
        error: Exception,
        context: Optional[dict] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        reraise: bool = False
    ) -> Optional[str]:
        """Handle an error with consistent logging and formatting."""

        self.record_error(operation, error)
        message = self.format_error_message(operation, error, context)

        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(message)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(message)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(message)
        else:
            self.logger.info(message)

        # Log stack trace for debugging
        if severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            self.logger.debug(traceback.format_exc())

        if reraise:
            raise error

        return message


def with_error_handling(
    operation: str,
    error_handler: Optional[ErrorHandler] = None,
    context: Optional[dict] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    reraise: bool = False,
    default_return: Any = None
):
    """Decorator for consistent error handling."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = error_handler or ErrorHandler()

            try:
                return func(*args, **kwargs)
            except Exception as e:
                handler.handle_error(
                    operation=operation,
                    error=e,
                    context=context,
                    severity=severity,
                    reraise=reraise
                )
                return default_return

        return wrapper
    return decorator


def with_retry(
    operation: str,
    retry_config: Optional[RetryConfig] = None,
    error_handler: Optional[ErrorHandler] = None,
    context: Optional[dict] = None
):
    """Decorator for automatic retry with exponential backoff."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = retry_config or RetryConfig()
            handler = error_handler or ErrorHandler()

            last_error = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    if not handler.should_retry(e, attempt, config.max_attempts):
                        break

                    if attempt < config.max_attempts - 1:  # Don't delay on last attempt
                        delay = handler.calculate_delay(attempt, config)
                        handler.logger.debug(
                            f"Retrying {operation} in {delay:.2f}s (attempt {attempt + 1}/{config.max_attempts})"
                        )
                        time.sleep(delay)

            # All retries exhausted
            handler.handle_error(
                operation=operation,
                error=last_error,
                context={**(context or {}), 'attempts': config.max_attempts},
                severity=ErrorSeverity.HIGH,
                reraise=True
            )

        return wrapper
    return decorator


def safe_operation(
    operation: str,
    default_return: Any = None,
    context: Optional[dict] = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
):
    """Decorator for operations that should never raise exceptions."""

    return with_error_handling(
        operation=operation,
        context=context,
        severity=severity,
        reraise=False,
        default_return=default_return
    )


# Global error handler instance
error_handler = ErrorHandler()


# Convenience functions for common error patterns
def handle_database_error(operation: str, error: Exception, context: Optional[dict] = None):
    """Handle database-specific errors."""
    return error_handler.handle_error(
        operation=operation,
        error=error,
        context=context,
        severity=ErrorSeverity.MEDIUM
    )


def handle_file_error(operation: str, error: Exception, file_path: Optional[str] = None):
    """Handle file system errors."""
    context = {'file_path': file_path} if file_path else None
    return error_handler.handle_error(
        operation=operation,
        error=error,
        context=context,
        severity=ErrorSeverity.MEDIUM
    )


def handle_api_error(operation: str, error: Exception, context: Optional[dict] = None):
    """Handle API errors with potential retry classification."""
    return error_handler.handle_error(
        operation=operation,
        error=error,
        context=context,
        severity=ErrorSeverity.MEDIUM
    )


def handle_config_error(operation: str, error: Exception, context: Optional[dict] = None):
    """Handle configuration errors."""
    return error_handler.handle_error(
        operation=operation,
        error=error,
        context=context,
        severity=ErrorSeverity.HIGH
    )