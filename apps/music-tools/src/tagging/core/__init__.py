"""Core services for the music tagger application."""

from .country_service import CountryService, country_service
from .error_handler import (
    APIError,
    CacheError,
    ConfigurationError,
    ErrorHandler,
    MetadataError,
    MusicTaggerError,
    error_handler,
    safe_operation,
    with_error_handling,
    with_retry,
)
from .progress_reporter import (
    ProgressEvent,
    ProgressEventType,
    ProgressReporter,
    ProgressTracker,
    create_progress_tracker,
    get_progress_tracker,
    progress_reporter,
)
from .validation_service import (
    ValidationResult,
    ValidationService,
    validate_api_key,
    validate_artist_name,
    validate_confidence_score,
    validate_file_path,
    validation_service,
)

__all__ = [
    # Country service
    'CountryService', 'country_service',

    # Error handling
    'ErrorHandler', 'error_handler',
    'MusicTaggerError', 'ConfigurationError', 'CacheError', 'MetadataError', 'APIError',
    'with_error_handling', 'with_retry', 'safe_operation',

    # Progress reporting
    'ProgressReporter', 'progress_reporter', 'ProgressTracker', 'ProgressEvent', 'ProgressEventType',
    'create_progress_tracker', 'get_progress_tracker',

    # Validation
    'ValidationService', 'validation_service', 'ValidationResult',
    'validate_file_path', 'validate_artist_name', 'validate_confidence_score', 'validate_api_key'
]
