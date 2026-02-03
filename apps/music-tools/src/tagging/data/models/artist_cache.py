"""
Data models for artist cache entries.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ArtistCacheEntry:
    """Represents a cached artist-country mapping."""

    artist_name: str
    country: str
    confidence: float = 1.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    hit_count: int = 0

    def __post_init__(self):
        """Set default timestamps if not provided."""
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            'artist_name': self.artist_name,
            'country': self.country,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'hit_count': self.hit_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ArtistCacheEntry':
        """Create instance from dictionary."""
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])

        updated_at = None
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])

        return cls(
            artist_name=data['artist_name'],
            country=data['country'],
            confidence=data.get('confidence', 1.0),
            created_at=created_at,
            updated_at=updated_at,
            hit_count=data.get('hit_count', 0)
        )

    def update_hit_count(self):
        """Increment hit count and update timestamp."""
        self.hit_count += 1
        self.updated_at = datetime.now()

    def is_recent(self, max_age_days: int = 30) -> bool:
        """Check if the entry is recent."""
        if not self.updated_at:
            return False

        age = datetime.now() - self.updated_at
        return age.days <= max_age_days
