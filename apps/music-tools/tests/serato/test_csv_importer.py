"""Tests for CSVImporter -- reading CSV playlists and importing to crates."""

import csv
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

# Add apps/music-tools to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Patch serato_tools before importing CSVImporter
with patch.dict("sys.modules", {"serato_tools": MagicMock(), "serato_tools.crate": MagicMock()}):
    from src.services.serato.csv_importer import CSVImporter, ImportResult
    from src.services.serato.models import TrackMetadata


class TestReadCSV:
    """Tests for CSVImporter.read_csv static method."""

    def test_read_csv(self, sample_csv):
        """Reading a valid CSV returns the correct number of (artist, title) tuples."""
        tracks = CSVImporter.read_csv(str(sample_csv))
        assert len(tracks) == 5
        assert all(isinstance(t, tuple) and len(t) == 2 for t in tracks)
        assert tracks[0] == ("Artist Alpha", "Song One")

    def test_read_csv_strips_whitespace(self, tmp_path):
        """Values with surrounding whitespace are stripped."""
        csv_path = tmp_path / "spaces.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Artist", "Title"])
            writer.writerow(["  Led Zeppelin  ", "  Stairway to Heaven  "])
            writer.writerow(["  Pink Floyd ", " Comfortably Numb "])

        tracks = CSVImporter.read_csv(str(csv_path))
        assert len(tracks) == 2
        assert tracks[0] == ("Led Zeppelin", "Stairway to Heaven")
        assert tracks[1] == ("Pink Floyd", "Comfortably Numb")

    def test_read_csv_missing_columns(self, tmp_path):
        """CSV without required 'Artist' column raises ValueError."""
        csv_path = tmp_path / "bad_columns.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Song", "Title"])
            writer.writerow(["Some Song", "Some Title"])

        with pytest.raises(ValueError, match="Artist"):
            CSVImporter.read_csv(str(csv_path))

    def test_read_csv_missing_title_column(self, tmp_path):
        """CSV without required 'Title' column raises ValueError."""
        csv_path = tmp_path / "no_title.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Artist", "Track"])
            writer.writerow(["Artist A", "Track One"])

        with pytest.raises(ValueError, match="Title"):
            CSVImporter.read_csv(str(csv_path))

    def test_read_csv_skips_empty_rows(self, tmp_path):
        """Rows where artist or title is empty after stripping are skipped."""
        csv_path = tmp_path / "with_blanks.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Artist", "Title"])
            writer.writerow(["Good Artist", "Good Title"])
            writer.writerow(["", "No Artist"])
            writer.writerow(["No Title", ""])
            writer.writerow(["  ", "  "])
            writer.writerow(["Valid Artist", "Valid Title"])

        tracks = CSVImporter.read_csv(str(csv_path))
        assert len(tracks) == 2
        assert tracks[0] == ("Good Artist", "Good Title")
        assert tracks[1] == ("Valid Artist", "Valid Title")

    def test_read_csv_file_not_found(self, tmp_path):
        """Attempting to read a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            CSVImporter.read_csv(str(tmp_path / "nonexistent.csv"))

    def test_read_csv_utf8_bom(self, tmp_path):
        """CSV with UTF-8 BOM is read correctly."""
        csv_path = tmp_path / "bom.csv"
        with open(csv_path, "wb") as fh:
            # Write UTF-8 BOM
            fh.write(b"\xef\xbb\xbf")
            fh.write("Artist,Title\n".encode("utf-8"))
            fh.write("Bjork,Army Of Me\n".encode("utf-8"))

        tracks = CSVImporter.read_csv(str(csv_path))
        assert len(tracks) == 1
        assert tracks[0] == ("Bjork", "Army Of Me")


class TestImportCSVToCrate:
    """Tests for the import workflow that matches CSV against an index."""

    def test_import_with_matches(self, sample_csv, populated_index):
        """Importing a CSV with known tracks produces matched results."""
        mock_crate_manager = MagicMock()
        mock_crate_manager.create_crate.return_value = Path("/serato/NewCrate.crate")

        importer = CSVImporter(
            track_index=populated_index,
            crate_manager=mock_crate_manager,
        )
        result = importer.import_csv_to_crate(str(sample_csv), "NewCrate", threshold=60)

        assert isinstance(result, ImportResult)
        assert len(result.matched) > 0
        assert result.crate_path is not None
        mock_crate_manager.create_crate.assert_called_once()

    def test_import_no_matches(self, tmp_path, populated_index):
        """CSV with completely unknown tracks produces only not_found entries."""
        csv_path = tmp_path / "unknown.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Artist", "Title"])
            writer.writerow(["ZZZZZZ Unknown", "XXXXXX Nonexistent"])
            writer.writerow(["YYYYYY Nobody", "WWWWWW Nothing"])

        mock_crate_manager = MagicMock()

        importer = CSVImporter(
            track_index=populated_index,
            crate_manager=mock_crate_manager,
        )
        result = importer.import_csv_to_crate(str(csv_path), "EmptyCrate", threshold=90)

        assert isinstance(result, ImportResult)
        assert len(result.not_found) == 2
        assert len(result.matched) == 0
        assert result.crate_path is None
        mock_crate_manager.create_crate.assert_not_called()

    def test_import_result_defaults(self):
        """ImportResult initialises with empty lists and None crate_path."""
        ir = ImportResult()
        assert ir.matched == []
        assert ir.not_found == []
        assert ir.multiple_matches == []
        assert ir.crate_path is None
