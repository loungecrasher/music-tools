"""
Centralized validation service for common validation logic.

This module provides consistent validation rules and logic used across
different components of the application.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    error_message: Optional[str] = None
    warnings: List[str] = None
    normalized_value: Optional[Any] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class ValidationService:
    """Service for common validation operations."""

    # Audio file extensions that are supported
    SUPPORTED_AUDIO_EXTENSIONS = {'.mp3', '.flac', '.m4a', '.wav', '.ogg'}

    # Maximum reasonable values for metadata
    MAX_ARTIST_NAME_LENGTH = 500
    MAX_ALBUM_NAME_LENGTH = 500
    MAX_TITLE_LENGTH = 500
    MAX_GENRE_LENGTH = 100

    # Regex patterns for validation
    PATTERNS = {
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'api_key': re.compile(r'^sk-[a-zA-Z0-9_-]{40,}$'),  # Anthropic API key pattern
        'safe_filename': re.compile(r'^[a-zA-Z0-9._-]+$'),
        'year': re.compile(r'^(19|20)\d{2}$'),  # Years from 1900-2099
        'confidence': re.compile(r'^[01](\.\d+)?$'),  # 0.0 to 1.0
    }

    def __init__(self):
        """Initialize the validation service."""

    def validate_file_path(self, file_path: str) -> ValidationResult:
        """Validate a file path for audio processing."""

        if not file_path:
            return ValidationResult(
                is_valid=False,
                error_message="File path cannot be empty"
            )

        try:
            path = Path(file_path)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid path format: {e}"
            )

        # Check if file exists
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"File does not exist: {file_path}"
            )

        # Check if it's a file (not directory)
        if not path.is_file():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path is not a file: {file_path}"
            )

        # Check file extension
        extension = path.suffix.lower()
        if extension not in self.SUPPORTED_AUDIO_EXTENSIONS:
            return ValidationResult(
                is_valid=False,
                error_message=f"Unsupported file type: {extension}. "
                f"Supported types: {', '.join(sorted(self.SUPPORTED_AUDIO_EXTENSIONS))}"
            )

        # Check file size (warn if very large)
        warnings = []
        try:
            file_size = path.stat().st_size
            if file_size > 100 * 1024 * 1024:  # 100MB
                warnings.append(f"Large file size: {file_size / (1024*1024):.1f}MB")
            elif file_size == 0:
                return ValidationResult(
                    is_valid=False,
                    error_message="File is empty"
                )
        except OSError as e:
            warnings.append(f"Could not check file size: {e}")

        return ValidationResult(
            is_valid=True,
            warnings=warnings,
            normalized_value=str(path.resolve())
        )

    def validate_directory_path(self, dir_path: str) -> ValidationResult:
        """Validate a directory path for scanning."""

        if not dir_path:
            return ValidationResult(
                is_valid=False,
                error_message="Directory path cannot be empty"
            )

        try:
            path = Path(dir_path)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid path format: {e}"
            )

        # Check if directory exists
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"Directory does not exist: {dir_path}"
            )

        # Check if it's a directory
        if not path.is_dir():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path is not a directory: {dir_path}"
            )

        # Check read permissions
        if not path.readable():
            return ValidationResult(
                is_valid=False,
                error_message=f"Directory is not readable: {dir_path}"
            )

        return ValidationResult(
            is_valid=True,
            normalized_value=str(path.resolve())
        )

    def validate_artist_name(self, artist_name: str) -> ValidationResult:
        """Validate an artist name."""

        if not artist_name:
            return ValidationResult(
                is_valid=False,
                error_message="Artist name cannot be empty"
            )

        # Clean the input
        normalized = artist_name.strip()

        if not normalized:
            return ValidationResult(
                is_valid=False,
                error_message="Artist name cannot be only whitespace"
            )

        # Check length
        if len(normalized) > self.MAX_ARTIST_NAME_LENGTH:
            return ValidationResult(
                is_valid=False,
                error_message=f"Artist name too long: {len(normalized)} > {self.MAX_ARTIST_NAME_LENGTH}"
            )

        # Check for suspicious patterns
        warnings = []
        if normalized.lower() in ['unknown', 'various', 'various artists', 'n/a', 'null']:
            warnings.append("Artist name appears to be a placeholder")

        if len(normalized) < 2:
            warnings.append("Very short artist name")

        return ValidationResult(
            is_valid=True,
            warnings=warnings,
            normalized_value=normalized
        )

    def validate_confidence_score(self, confidence: Any) -> ValidationResult:
        """Validate a confidence score (0.0 to 1.0)."""

        # Try to convert to float
        try:
            conf_float = float(confidence)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                error_message=f"Confidence must be a number, got: {type(confidence).__name__}"
            )

        # Check range
        if not (0.0 <= conf_float <= 1.0):
            return ValidationResult(
                is_valid=False,
                error_message=f"Confidence must be between 0.0 and 1.0, got: {conf_float}"
            )

        # Warnings for edge cases
        warnings = []
        if conf_float == 0.0:
            warnings.append("Confidence is exactly 0.0 - no confidence in result")
        elif conf_float < 0.1:
            warnings.append("Very low confidence score")

        return ValidationResult(
            is_valid=True,
            warnings=warnings,
            normalized_value=conf_float
        )

    def validate_api_key(self, api_key: str) -> ValidationResult:
        """Validate an Anthropic API key format."""

        if not api_key:
            return ValidationResult(
                is_valid=False,
                error_message="API key cannot be empty"
            )

        # Clean the input
        normalized = api_key.strip()

        # Check basic format
        if not self.PATTERNS['api_key'].match(normalized):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid API key format. Expected format: sk-..."
            )

        return ValidationResult(
            is_valid=True,
            normalized_value=normalized
        )

    def validate_year(self, year: Any) -> ValidationResult:
        """Validate a year value."""

        if year is None:
            return ValidationResult(
                is_valid=True,
                normalized_value=None
            )

        # Try to convert to string for pattern matching
        year_str = str(year).strip()

        if not year_str:
            return ValidationResult(
                is_valid=True,
                normalized_value=None
            )

        # Check format
        if not self.PATTERNS['year'].match(year_str):
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid year format: {year_str}. Expected 4-digit year (1900-2099)"
            )

        year_int = int(year_str)

        # Additional validation
        warnings = []
        current_year = 2024  # Update this as needed
        if year_int > current_year:
            warnings.append(f"Future year: {year_int}")

        if year_int < 1900:
            warnings.append(f"Very old year: {year_int}")

        return ValidationResult(
            is_valid=True,
            warnings=warnings,
            normalized_value=year_int
        )

    def validate_metadata_dict(self, metadata: Dict[str, Any]) -> ValidationResult:
        """Validate a metadata dictionary."""

        if not isinstance(metadata, dict):
            return ValidationResult(
                is_valid=False,
                error_message=f"Metadata must be a dictionary, got: {type(metadata).__name__}"
            )

        warnings = []
        normalized = {}

        # Validate individual fields
        for field, value in metadata.items():
            if field in ['artist', 'albumartist']:
                if value:
                    result = self.validate_artist_name(str(value))
                    if not result.is_valid:
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"Invalid {field}: {result.error_message}"
                        )
                    warnings.extend(result.warnings)
                    normalized[field] = result.normalized_value
                else:
                    normalized[field] = None

            elif field in ['album', 'title']:
                if value:
                    value_str = str(value).strip()
                    if len(value_str) > self.MAX_ALBUM_NAME_LENGTH:
                        warnings.append(f"{field} is very long: {len(value_str)} characters")
                    normalized[field] = value_str
                else:
                    normalized[field] = None

            elif field == 'date':
                if value:
                    result = self.validate_year(value)
                    if not result.is_valid:
                        warnings.append(f"Invalid date: {result.error_message}")
                        normalized[field] = value  # Keep original if invalid
                    else:
                        warnings.extend(result.warnings)
                        normalized[field] = result.normalized_value
                else:
                    normalized[field] = None

            else:
                # Pass through other fields
                normalized[field] = value

        return ValidationResult(
            is_valid=True,
            warnings=warnings,
            normalized_value=normalized
        )

    def validate_batch_size(self, batch_size: Any) -> ValidationResult:
        """Validate a batch size parameter."""

        try:
            size_int = int(batch_size)
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                error_message=f"Batch size must be an integer, got: {type(batch_size).__name__}"
            )

        if size_int <= 0:
            return ValidationResult(
                is_valid=False,
                error_message=f"Batch size must be positive, got: {size_int}"
            )

        warnings = []
        if size_int > 100:
            warnings.append("Large batch size may cause memory issues")
        elif size_int == 1:
            warnings.append("Batch size of 1 may be inefficient")

        return ValidationResult(
            is_valid=True,
            warnings=warnings,
            normalized_value=size_int
        )

    def validate_config_dict(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate a configuration dictionary."""

        if not isinstance(config, dict):
            return ValidationResult(
                is_valid=False,
                error_message=f"Configuration must be a dictionary, got: {type(config).__name__}"
            )

        warnings = []
        errors = []

        # Check required fields
        required_fields = ['music_directory']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Validate specific fields
        if 'music_directory' in config:
            result = self.validate_directory_path(config['music_directory'])
            if not result.is_valid:
                errors.append(f"Invalid music_directory: {result.error_message}")

        if 'anthropic_api_key' in config and config['anthropic_api_key']:
            result = self.validate_api_key(config['anthropic_api_key'])
            if not result.is_valid:
                errors.append(f"Invalid API key: {result.error_message}")

        if 'batch_size' in config:
            result = self.validate_batch_size(config['batch_size'])
            if not result.is_valid:
                errors.append(f"Invalid batch_size: {result.error_message}")
            else:
                warnings.extend(result.warnings)

        if errors:
            return ValidationResult(
                is_valid=False,
                error_message="; ".join(errors),
                warnings=warnings
            )

        return ValidationResult(
            is_valid=True,
            warnings=warnings
        )


# Global validation service instance
validation_service = ValidationService()


# Convenience functions
def validate_file_path(file_path: str) -> ValidationResult:
    """Validate a file path."""
    return validation_service.validate_file_path(file_path)


def validate_artist_name(artist_name: str) -> ValidationResult:
    """Validate an artist name."""
    return validation_service.validate_artist_name(artist_name)


def validate_confidence_score(confidence: Any) -> ValidationResult:
    """Validate a confidence score."""
    return validation_service.validate_confidence_score(confidence)


def validate_api_key(api_key: str) -> ValidationResult:
    """Validate an API key."""
    return validation_service.validate_api_key(api_key)
