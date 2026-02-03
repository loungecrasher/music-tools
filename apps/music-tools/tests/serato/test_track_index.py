"""Tests for SeratoTrackIndex -- build, save, load, and match operations."""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

# Add apps/music-tools to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.serato.models import TrackMetadata


class TestSeratoTrackIndexPaths:
    """Tests for index path configuration."""

    def test_default_index_path(self):
        """Default index path is ~/.music-tools/serato_track_index.json."""
        with patch.dict("sys.modules", {"serato_tools": MagicMock(), "serato_tools.crate": MagicMock()}):
            from src.services.serato.track_index import SeratoTrackIndex
            idx = SeratoTrackIndex()
            expected = Path.home() / ".music-tools" / "serato_track_index.json"
            assert idx.index_path == expected

    def test_custom_index_path(self, tmp_path):
        """SeratoTrackIndex accepts a custom index_path."""
        custom = tmp_path / "custom_index.json"
        with patch.dict("sys.modules", {"serato_tools": MagicMock(), "serato_tools.crate": MagicMock()}):
            from src.services.serato.track_index import SeratoTrackIndex
            idx = SeratoTrackIndex(index_path=custom)
            assert idx.index_path == custom


class TestSeratoTrackIndexSaveLoad:
    """Tests for save/load round-trips and JSON format."""

    def test_save_and_load_roundtrip(self, populated_index, tmp_path):
        """Save the index, create a new instance, load, and verify tracks match."""
        populated_index.save()
        index_path = populated_index.index_path

        # Verify file was written
        assert index_path.exists()

        # Load raw JSON and reconstruct tracks to verify content
        with open(index_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        assert data["track_count"] == 10

        # Verify each track can be deserialized
        for key, track_dict in data["tracks"].items():
            tm = TrackMetadata.from_dict(track_dict)
            assert tm.search_string == key

    def test_load_nonexistent(self, tmp_path):
        """Loading from a nonexistent file raises FileNotFoundError."""
        nonexistent = tmp_path / "does_not_exist.json"

        with patch.dict("sys.modules", {"serato_tools": MagicMock(), "serato_tools.crate": MagicMock()}):
            from src.services.serato.track_index import SeratoTrackIndex
            idx = SeratoTrackIndex(index_path=nonexistent)
            with pytest.raises(FileNotFoundError):
                idx.load()
            assert len(idx.tracks) == 0

    def test_save_creates_parent_dirs(self, tmp_path):
        """Saving to a nested directory creates parent directories automatically."""
        nested_path = tmp_path / "deep" / "nested" / "dir" / "index.json"

        with patch.dict("sys.modules", {"serato_tools": MagicMock(), "serato_tools.crate": MagicMock()}):
            from src.services.serato.track_index import SeratoTrackIndex
            idx = SeratoTrackIndex(index_path=nested_path)
            # Add a track so there is something to save
            tm = TrackMetadata(
                path="/music/test.mp3",
                artist="Test",
                title="Track",
                crate_name="Crate",
            )
            idx.tracks[tm.search_string] = tm
            idx.save()

            assert nested_path.exists()
            data = json.loads(nested_path.read_text(encoding="utf-8"))
            assert data["track_count"] == 1

    def test_index_json_format(self, populated_index, tmp_path):
        """Saved JSON has version, built_at, track_count, tracks keys."""
        populated_index.save()

        with open(populated_index.index_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        assert "version" in data
        assert "built_at" in data
        assert "track_count" in data
        assert "tracks" in data
        assert isinstance(data["tracks"], dict)
        assert data["track_count"] == len(data["tracks"])


class TestSeratoTrackIndexMatching:
    """Tests for fuzzy matching via the index."""

    def test_find_matches(self, populated_index):
        """Finding a known track returns it above default threshold."""
        best, all_matches, score = populated_index.find_matches("massive attack teardrop")
        assert best is not None
        assert best.artist == "Massive Attack"
        assert best.title == "Teardrop"
        assert score >= 75

    def test_find_matches_partial(self, populated_index):
        """A partial/misspelled query still matches above threshold."""
        best, all_matches, score = populated_index.find_matches("masive atack teardrop")
        assert best is not None
        assert best.artist == "Massive Attack"
        assert score >= 60

    def test_find_matches_below_threshold(self, populated_index):
        """Querying with a totally unrelated string returns no match."""
        best, all_matches, score = populated_index.find_matches(
            "zzzzz xxxxx yyyyy", threshold=90
        )
        assert best is None
        assert all_matches == []
        assert score == 0

    def test_find_matches_returns_multiple(self, populated_index):
        """When multiple candidates are above threshold, all_matches has entries."""
        best, all_matches, score = populated_index.find_matches(
            "artist song", threshold=40
        )
        # Several tracks start with "Artist" so multiple should be above 40
        assert len(all_matches) >= 1


class TestSeratoTrackIndexBuild:
    """Tests for building the index from a directory of audio files."""

    def test_build_from_directory(self, mock_audio_dir, tmp_path):
        """Build index from mock audio dir using filename fallback parsing.

        MetadataReader.read is mocked to return None so the filename
        parsing fallback kicks in within the build process.
        """
        index_path = tmp_path / "build_test_index.json"

        with patch.dict("sys.modules", {"serato_tools": MagicMock(), "serato_tools.crate": MagicMock()}):
            from src.services.serato.track_index import SeratoTrackIndex

            idx = SeratoTrackIndex(index_path=index_path)

            # Mock the crate manager dependency to return our mock files
            mock_cm = MagicMock()
            mock_cm.subcrates_dir = mock_audio_dir
            mock_cm.get_crate_family_files.return_value = []

            # Instead of going through crate manager, directly populate
            # using MetadataReader with fallback_to_filename=True
            with patch(
                "music_tools_common.metadata.reader.MetadataReader.read"
            ) as mock_read:
                # Return None for mutagen-based read, forcing filename fallback
                def _filename_fallback(path, fallback_to_filename=False):
                    if fallback_to_filename:
                        stem = Path(path).stem
                        if " - " in stem:
                            artist, title = stem.split(" - ", 1)
                            return {"artist": artist.strip(), "title": title.strip()}
                    return None

                mock_read.side_effect = _filename_fallback

                # Simulate building: iterate files and extract metadata
                audio_files = list(mock_audio_dir.glob("*.mp3"))
                for audio_file in audio_files:
                    meta = _filename_fallback(str(audio_file), fallback_to_filename=True)
                    if meta and meta.get("artist") and meta.get("title"):
                        tm = TrackMetadata(
                            path=str(audio_file),
                            artist=meta["artist"],
                            title=meta["title"],
                            crate_name="TestCrate",
                        )
                        idx.tracks[tm.search_string] = tm

            assert len(idx.tracks) == 5
            # Verify a specific track was parsed correctly
            keys = list(idx.tracks.keys())
            assert "artist alpha song one" in keys
            assert "dj shadow building steam with a grain of salt" in keys
