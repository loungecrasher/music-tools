"""
Shared utility functions for Music Tools projects.

This module provides reusable utilities for retry logic, validation, file operations,
date handling, HTTP requests, security, and decorators across all Music Tools projects.
"""

# Date utilities
from .date import (
    format_date,
    format_duration,
    get_relative_time,
    get_year_from_date,
    is_recent_date,
    is_valid_date,
    normalize_date,
    parse_date,
    parse_duration,
)

# Decorators
from .decorators import handle_errors, log_execution
from .decorators import retry as retry_decorator
from .decorators import validate_args

# File utilities
from .file import safe_read_json, safe_write_json

# Fuzzy matching
from .fuzzy import find_best_match, similarity_score

# HTTP utilities
from .http import RateLimiter  # Legacy compatibility
from .http import make_request  # Legacy compatibility
from .http import (
    check_url_accessible,
    create_resilient_session,
    get_domain_from_url,
    get_json,
    get_random_user_agent,
    handle_rate_limit,
    post_json,
    safe_request,
)

# Retry utilities (legacy retry function)
from .retry import retry
from .retry import safe_request as retry_safe_request  # noqa: F811
from .retry import setup_logger

# Security utilities
from .security import (
    SecureFileHandler,
    check_path_traversal,
    escape_html,
    is_safe_filename,
    mask_sensitive_value,
    sanitize_artist_name,
    sanitize_command_argument,
    sanitize_log_message,
    secure_permissions,
)
from .security import validate_batch_size as security_validate_batch_size
from .security import validate_file_path as security_validate_file_path
from .security import validate_port, validate_timeout

# Validation utilities
from .validation import validate_email, validate_url

__all__ = [
    # Fuzzy matching
    "find_best_match",
    "similarity_score",
    # Decorators
    "handle_errors",
    "retry_decorator",
    "log_execution",
    "validate_args",
    # Retry
    "retry",
    "safe_request",
    "setup_logger",
    # Validation
    "validate_email",
    "validate_url",
    # File
    "safe_write_json",
    "safe_read_json",
    # Date
    "parse_date",
    "format_date",
    "normalize_date",
    "get_year_from_date",
    "is_valid_date",
    "format_duration",
    "parse_duration",
    "get_relative_time",
    "is_recent_date",
    # HTTP
    "get_random_user_agent",
    "create_resilient_session",
    "safe_request",
    "handle_rate_limit",
    "get_json",
    "post_json",
    "check_url_accessible",
    "get_domain_from_url",
    "RateLimiter",
    "make_request",
    # Security
    "security_validate_file_path",
    "sanitize_artist_name",
    "sanitize_command_argument",
    "mask_sensitive_value",
    "sanitize_log_message",
    "secure_permissions",
    "security_validate_batch_size",
    "validate_timeout",
    "is_safe_filename",
    "escape_html",
    "validate_port",
    "check_path_traversal",
    "SecureFileHandler",
]

__version__ = "1.0.0"
