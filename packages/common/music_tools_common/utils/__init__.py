"""
Shared utility functions for Music Tools projects.

This module provides reusable utilities for retry logic, validation, file operations,
date handling, HTTP requests, security, and decorators across all Music Tools projects.
"""

# Decorators
from .decorators import (
    handle_errors,
    retry as retry_decorator,
    log_execution,
    validate_args
)

# Retry utilities (legacy retry function)
from .retry import (
    retry,
    safe_request,
    setup_logger
)

# Validation utilities
from .validation import (
    validate_email,
    validate_url
)

# File utilities
from .file import (
    safe_write_json,
    safe_read_json
)

# Date utilities
from .date import (
    parse_date,
    format_date,
    normalize_date,
    get_year_from_date,
    is_valid_date,
    format_duration,
    parse_duration,
    get_relative_time,
    is_recent_date
)

# HTTP utilities
from .http import (
    get_random_user_agent,
    create_resilient_session,
    safe_request,
    handle_rate_limit,
    get_json,
    post_json,
    check_url_accessible,
    get_domain_from_url,
    RateLimiter,  # Legacy compatibility
    make_request  # Legacy compatibility
)

# Security utilities
from .security import (
    validate_file_path as security_validate_file_path,
    sanitize_artist_name,
    sanitize_command_argument,
    mask_sensitive_value,
    sanitize_log_message,
    secure_permissions,
    validate_batch_size as security_validate_batch_size,
    validate_timeout,
    is_safe_filename,
    escape_html,
    validate_port,
    check_path_traversal,
    SecureFileHandler
)

__all__ = [
    # Decorators
    'handle_errors',
    'retry_decorator',
    'log_execution',
    'validate_args',

    # Retry
    'retry',
    'safe_request',
    'setup_logger',

    # Validation
    'validate_email',
    'validate_url',

    # File
    'safe_write_json',
    'safe_read_json',

    # Date
    'parse_date',
    'format_date',
    'normalize_date',
    'get_year_from_date',
    'is_valid_date',
    'format_duration',
    'parse_duration',
    'get_relative_time',
    'is_recent_date',

    # HTTP
    'get_random_user_agent',
    'create_resilient_session',
    'safe_request',
    'handle_rate_limit',
    'get_json',
    'post_json',
    'check_url_accessible',
    'get_domain_from_url',
    'RateLimiter',
    'make_request',

    # Security
    'security_validate_file_path',
    'sanitize_artist_name',
    'sanitize_command_argument',
    'mask_sensitive_value',
    'sanitize_log_message',
    'secure_permissions',
    'security_validate_batch_size',
    'validate_timeout',
    'is_safe_filename',
    'escape_html',
    'validate_port',
    'check_path_traversal',
    'SecureFileHandler',
]

__version__ = '1.0.0'
