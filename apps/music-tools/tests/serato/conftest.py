"""
Pytest configuration and fixtures for Serato integration tests.

Provides common fixtures for testing Serato service modules including:
- TrackMetadata builders and samples
- CSV file generators
- Pre-populated track index instances
- Mock audio directory structures
"""

import csv
import json
import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, MagicMock, patch
import sys

# Add apps/music-tools to sys.path to allow importing from src
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.serato.models import TrackMetadata, CrateInfo


# ==================== Track Metadata Fixtures ====================

SAMPLE_TRACKS = [
    ("Artist Alpha", "Song One"),
    ("Artist Beta", "Song Two"),
    ("Artist Gamma", "Song Three"),
    ("Artist Delta", "Song Four"),
    ("Artist Epsilon", "Song Five"),
    ("DJ Shadow", "Building Steam With A Grain Of Salt"),
    ("Massive Attack", "Teardrop"),
    ("Portishead", "Glory Box"),
    ("Boards of Canada", "Roygbiv"),
    ("Aphex Twin", "Windowlicker"),
]


@pytest.fixture
def sample_track_metadata() -> TrackMetadata:
    """A single TrackMetadata instance for basic tests."""
    return TrackMetadata(
        path="/music/Artist Alpha - Song One.mp3",
        artist="Artist Alpha",
        title="Song One",
        crate_name="TestCrate",
    )


@pytest.fixture
def make_track_metadata():
    """Builder function fixture -- call with overrides to customise.

    Usage::

        track = make_track_metadata(artist="Custom", title="Track")
    """

    def _factory(**overrides) -> TrackMetadata:
        defaults: Dict[str, Any] = {
            "path": "/music/Test Artist - Test Track.mp3",
            "artist": "Test Artist",
            "title": "Test Track",
            "crate_name": "DefaultCrate",
        }
        defaults.update(overrides)
        return TrackMetadata(**defaults)

    return _factory


# ==================== CSV Fixtures ====================

@pytest.fixture
def sample_csv(tmp_path) -> Path:
    """Write a CSV file with Artist,Title columns and 5 test rows.

    Returns the path to the written file.
    """
    csv_path = tmp_path / "playlist.csv"
    rows = SAMPLE_TRACKS[:5]

    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Artist", "Title"])
        for artist, title in rows:
            writer.writerow([artist, title])

    return csv_path


# ==================== Track Index Fixtures ====================

@pytest.fixture
def populated_index(tmp_path):
    """Create a SeratoTrackIndex pre-loaded with 10 tracks.

    The index uses a temporary JSON path so tests never touch real data.
    Returns the index instance.
    """
    index_path = tmp_path / "serato_track_index.json"

    # Build track dict keyed by search_string
    tracks: Dict[str, TrackMetadata] = {}
    for artist, title in SAMPLE_TRACKS:
        tm = TrackMetadata(
            path=f"/music/{artist} - {title}.mp3",
            artist=artist,
            title=title,
            crate_name="SourceCrate",
        )
        tracks[tm.search_string] = tm

    # Patch the import so we don't need track_index.py to exist at import time
    # We build a lightweight mock that behaves like SeratoTrackIndex
    index = Mock()
    index.index_path = index_path
    index.tracks = tracks

    # Implement save() to write real JSON
    def _save():
        data = {
            "version": 1,
            "built_at": "2025-01-01T00:00:00",
            "track_count": len(tracks),
            "tracks": {k: v.to_dict() for k, v in tracks.items()},
        }
        index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    index.save = _save

    # Implement find_matches() using the real fuzzy module
    def _find_matches(query, threshold=75):
        from music_tools_common.utils.fuzzy import find_best_match
        return find_best_match(query, tracks, threshold=threshold)

    index.find_matches = _find_matches

    return index


# ==================== Mock Audio Directory ====================

@pytest.fixture
def mock_audio_dir(tmp_path) -> Path:
    """Create a directory with fake audio files for testing.

    Files are empty but named in ``Artist - Title.mp3`` format so that
    filename-based metadata parsing can be validated.
    """
    audio_dir = tmp_path / "music_library"
    audio_dir.mkdir()

    filenames = [
        "Artist Alpha - Song One.mp3",
        "Artist Beta - Song Two.mp3",
        "Artist Gamma - Song Three.mp3",
        "DJ Shadow - Building Steam With A Grain Of Salt.mp3",
        "Massive Attack - Teardrop.mp3",
    ]

    for name in filenames:
        (audio_dir / name).write_bytes(b"")

    return audio_dir
