"""Data models for Serato integration."""
from dataclasses import dataclass


@dataclass
class TrackMetadata:
    """Represents a track's metadata within the Serato index.

    Compatible with the JSON index format used by the original
    csv_to_crate tool -- ``to_dict`` / ``from_dict`` round-trip cleanly.
    """

    path: str
    artist: str
    title: str
    crate_name: str

    @property
    def search_string(self) -> str:
        """Lower-cased artist+title key used for fuzzy matching."""
        return f"{self.artist} {self.title}".lower()

    def to_dict(self) -> dict:
        """Serialise to the JSON index format."""
        return {
            'path': self.path,
            'artist': self.artist,
            'title': self.title,
            'crate': self.crate_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TrackMetadata':
        """Deserialise from the JSON index format."""
        return cls(
            path=data['path'],
            artist=data['artist'],
            title=data['title'],
            crate_name=data['crate'],
        )

    def __repr__(self) -> str:
        return f"{self.artist} - {self.title}"


@dataclass
class CrateInfo:
    """Summary information about a Serato crate file."""

    name: str
    path: str
    track_count: int
    is_subcrate: bool = False
