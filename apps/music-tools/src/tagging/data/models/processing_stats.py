"""
Data models for processing statistics and logs.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ProcessingStatus(Enum):
    """Status of file processing."""

    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    CACHED = "cached"


@dataclass
class ProcessingLogEntry:
    """Represents a processing log entry."""

    file_path: str
    artist_name: str
    status: ProcessingStatus
    processed_at: Optional[datetime] = None
    country: Optional[str] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """Set default timestamp if not provided."""
        if self.processed_at is None:
            self.processed_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            'file_path': self.file_path,
            'artist_name': self.artist_name,
            'status': self.status.value,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'country': self.country,
            'error_message': self.error_message
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessingLogEntry':
        """Create instance from dictionary."""
        processed_at = None
        if data.get('processed_at'):
            processed_at = datetime.fromisoformat(data['processed_at'])

        return cls(
            file_path=data['file_path'],
            artist_name=data['artist_name'],
            status=ProcessingStatus(data['status']),
            processed_at=processed_at,
            country=data.get('country'),
            error_message=data.get('error_message')
        )


@dataclass
class Statistics:
    """Processing and cache statistics."""

    # Cache statistics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_entries: int = 0

    # Processing statistics
    files_processed: int = 0
    files_skipped: int = 0
    files_with_errors: int = 0
    artists_researched: int = 0

    # Metadata statistics
    read_errors: int = 0
    write_errors: int = 0
    metadata_updates: int = 0

    # API statistics
    api_calls: int = 0
    api_errors: int = 0
    batch_calls: int = 0

    # Timing statistics
    total_processing_time: float = 0.0
    average_file_time: float = 0.0

    # Additional metadata
    last_updated: Optional[datetime] = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_entries': self.cache_entries,
            'files_processed': self.files_processed,
            'files_skipped': self.files_skipped,
            'files_with_errors': self.files_with_errors,
            'artists_researched': self.artists_researched,
            'read_errors': self.read_errors,
            'write_errors': self.write_errors,
            'metadata_updates': self.metadata_updates,
            'api_calls': self.api_calls,
            'api_errors': self.api_errors,
            'batch_calls': self.batch_calls,
            'total_processing_time': self.total_processing_time,
            'average_file_time': self.average_file_time,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Statistics':
        """Create instance from dictionary."""
        last_updated = None
        if data.get('last_updated'):
            last_updated = datetime.fromisoformat(data['last_updated'])

        return cls(
            cache_hits=data.get('cache_hits', 0),
            cache_misses=data.get('cache_misses', 0),
            cache_entries=data.get('cache_entries', 0),
            files_processed=data.get('files_processed', 0),
            files_skipped=data.get('files_skipped', 0),
            files_with_errors=data.get('files_with_errors', 0),
            artists_researched=data.get('artists_researched', 0),
            read_errors=data.get('read_errors', 0),
            write_errors=data.get('write_errors', 0),
            metadata_updates=data.get('metadata_updates', 0),
            api_calls=data.get('api_calls', 0),
            api_errors=data.get('api_errors', 0),
            batch_calls=data.get('batch_calls', 0),
            total_processing_time=data.get('total_processing_time', 0.0),
            average_file_time=data.get('average_file_time', 0.0),
            last_updated=last_updated,
            metadata=data.get('metadata', {})
        )

    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total_requests = self.cache_hits + self.cache_misses
        if total_requests == 0:
            return 0.0
        return (self.cache_hits / total_requests) * 100.0

    def get_success_rate(self) -> float:
        """Calculate processing success rate as percentage."""
        total_files = self.files_processed + self.files_with_errors
        if total_files == 0:
            return 0.0
        return (self.files_processed / total_files) * 100.0

    def get_api_success_rate(self) -> float:
        """Calculate API success rate as percentage."""
        if self.api_calls == 0:
            return 0.0
        successful_calls = self.api_calls - self.api_errors
        return (successful_calls / self.api_calls) * 100.0

    def update_processing_time(self, file_time: float):
        """Update processing time statistics."""
        self.total_processing_time += file_time
        if self.files_processed > 0:
            self.average_file_time = self.total_processing_time / self.files_processed
        self.last_updated = datetime.now()

    def reset(self):
        """Reset all statistics to zero."""
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_entries = 0
        self.files_processed = 0
        self.files_skipped = 0
        self.files_with_errors = 0
        self.artists_researched = 0
        self.read_errors = 0
        self.write_errors = 0
        self.metadata_updates = 0
        self.api_calls = 0
        self.api_errors = 0
        self.batch_calls = 0
        self.total_processing_time = 0.0
        self.average_file_time = 0.0
        self.last_updated = datetime.now()
        self.metadata.clear()
