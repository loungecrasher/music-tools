"""Tests for Serato data models: TrackMetadata and CrateInfo."""

import pytest
import sys
from pathlib import Path

# Add apps/music-tools to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.serato.models import TrackMetadata, CrateInfo


class TestTrackMetadata:
    """Tests for the TrackMetadata dataclass."""

    def test_track_metadata_creation(self, sample_track_metadata):
        """Basic creation with all fields populated."""
        tm = sample_track_metadata
        assert tm.path == "/music/Artist Alpha - Song One.mp3"
        assert tm.artist == "Artist Alpha"
        assert tm.title == "Song One"
        assert tm.crate_name == "TestCrate"

    def test_track_metadata_search_string(self, sample_track_metadata):
        """search_string property returns lower-cased 'artist title'."""
        assert sample_track_metadata.search_string == "artist alpha song one"

    def test_track_metadata_search_string_preserves_spaces(self, make_track_metadata):
        """Verify spaces inside artist/title are preserved."""
        tm = make_track_metadata(artist="The Black Keys", title="Lonely Boy")
        assert tm.search_string == "the black keys lonely boy"

    def test_track_metadata_to_dict(self, sample_track_metadata):
        """to_dict returns dict with path, artist, title, crate keys."""
        d = sample_track_metadata.to_dict()
        assert set(d.keys()) == {"path", "artist", "title", "crate"}
        assert d["path"] == "/music/Artist Alpha - Song One.mp3"
        assert d["artist"] == "Artist Alpha"
        assert d["title"] == "Song One"
        assert d["crate"] == "TestCrate"

    def test_track_metadata_from_dict(self, sample_track_metadata):
        """Round-trip: from_dict(to_dict()) reconstructs an equivalent object."""
        d = sample_track_metadata.to_dict()
        restored = TrackMetadata.from_dict(d)
        assert restored.path == sample_track_metadata.path
        assert restored.artist == sample_track_metadata.artist
        assert restored.title == sample_track_metadata.title
        assert restored.crate_name == sample_track_metadata.crate_name

    def test_track_metadata_repr(self, sample_track_metadata):
        """repr is 'Artist - Title'."""
        assert repr(sample_track_metadata) == "Artist Alpha - Song One"

    def test_track_metadata_repr_custom(self, make_track_metadata):
        """repr for a custom track."""
        tm = make_track_metadata(artist="Radiohead", title="Creep")
        assert repr(tm) == "Radiohead - Creep"


class TestCrateInfo:
    """Tests for the CrateInfo dataclass."""

    def test_crate_info_creation(self):
        """Basic creation with all fields."""
        ci = CrateInfo(
            name="My Crate",
            path="/serato/Subcrates/My Crate.crate",
            track_count=42,
            is_subcrate=True,
        )
        assert ci.name == "My Crate"
        assert ci.path == "/serato/Subcrates/My Crate.crate"
        assert ci.track_count == 42
        assert ci.is_subcrate is True

    def test_crate_info_defaults(self):
        """is_subcrate defaults to False."""
        ci = CrateInfo(name="TopLevel", path="/serato/TopLevel.crate", track_count=10)
        assert ci.is_subcrate is False

    def test_crate_info_zero_tracks(self):
        """A crate with zero tracks is valid."""
        ci = CrateInfo(name="Empty", path="/serato/Empty.crate", track_count=0)
        assert ci.track_count == 0
