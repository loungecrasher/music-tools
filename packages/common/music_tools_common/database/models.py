"""
Database models for Music Tools.
Defines data structures for playlists, tracks, and settings.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class Playlist:
    """Playlist model."""

    id: str
    name: str
    url: str
    owner: str
    tracks_count: int = 0
    service: str = 'spotify'
    is_algorithmic: bool = False
    added_on: Optional[str] = None
    last_updated: Optional[str] = None

    def __post_init__(self):
        """Set timestamps if not provided."""
        now = datetime.now().isoformat()
        if self.added_on is None:
            self.added_on = now
        if self.last_updated is None:
            self.last_updated = now

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Track:
    """Track model."""

    id: str
    name: str
    artist: str
    album: Optional[str] = None
    duration: int = 0
    release_date: Optional[str] = None
    isrc: Optional[str] = None
    service: str = 'spotify'
    added_on: Optional[str] = None
    last_updated: Optional[str] = None

    def __post_init__(self):
        """Set timestamps if not provided."""
        now = datetime.now().isoformat()
        if self.added_on is None:
            self.added_on = now
        if self.last_updated is None:
            self.last_updated = now

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PlaylistTrack:
    """Playlist-Track relationship model."""

    playlist_id: str
    track_id: str
    added_at: Optional[str] = None
    position: Optional[int] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.added_at is None:
            self.added_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class Setting:
    """Setting model."""

    key: str
    value: Any
    updated_at: Optional[str] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
