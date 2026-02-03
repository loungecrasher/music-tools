"""Tests for ImportVetter - import folder vetting against library."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from src.library.vetter import ImportVetter, SUPPORTED_AUDIO_FORMATS
from src.library.models import DuplicateResult, VettingReport
from conftest import make_library_file, make_duplicate_result


class TestImportVetterInit:
    """Tests for ImportVetter initialization."""

    def test_init_with_library_db(self, library_db):
        vetter = ImportVetter(library_db)
        assert vetter.db is library_db

    def test_init_none_db_raises(self):
        with pytest.raises(ValueError, match="library_db cannot be None"):
            ImportVetter(None)

    def test_init_with_custom_console(self, library_db):
        from rich.console import Console
        console = Console(file=StringIO())
        vetter = ImportVetter(library_db, console=console)
        assert vetter.console is console


class TestScanImportFolder:
    """Tests for _scan_import_folder."""

    def test_finds_supported_formats(self, library_db, tmp_path):
        vetter = ImportVetter(library_db)
        # Create files of various formats
        (tmp_path / "song.mp3").write_bytes(b"fake")
        (tmp_path / "song.flac").write_bytes(b"fake")
        (tmp_path / "song.m4a").write_bytes(b"fake")
        (tmp_path / "song.wav").write_bytes(b"fake")
        (tmp_path / "readme.txt").write_bytes(b"not audio")
        (tmp_path / "image.jpg").write_bytes(b"not audio")

        files = vetter._scan_import_folder(tmp_path)
        assert len(files) == 4
        extensions = {f.suffix.lower() for f in files}
        assert extensions == {'.mp3', '.flac', '.m4a', '.wav'}

    def test_scans_subdirectories(self, library_db, tmp_path):
        vetter = ImportVetter(library_db)
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "song1.mp3").write_bytes(b"fake")
        (subdir / "song2.flac").write_bytes(b"fake")

        files = vetter._scan_import_folder(tmp_path)
        assert len(files) == 2

    def test_empty_folder(self, library_db, tmp_path):
        vetter = ImportVetter(library_db)
        files = vetter._scan_import_folder(tmp_path)
        assert len(files) == 0

    def test_returns_sorted(self, library_db, tmp_path):
        vetter = ImportVetter(library_db)
        (tmp_path / "z_song.mp3").write_bytes(b"fake")
        (tmp_path / "a_song.mp3").write_bytes(b"fake")
        files = vetter._scan_import_folder(tmp_path)
        assert files[0].name < files[1].name


class TestCategorizeResults:
    """Tests for _categorize_results."""

    def test_categorize_duplicates(self, library_db):
        vetter = ImportVetter(library_db)
        matched = make_library_file()
        dup_result = DuplicateResult(
            is_duplicate=True, confidence=1.0, match_type='exact_metadata', matched_file=matched
        )
        results = [('/import/song.mp3', dup_result)]
        duplicates, new_songs, uncertain = vetter._categorize_results(results, 0.8)
        assert len(duplicates) == 1
        assert len(new_songs) == 0

    def test_categorize_new_songs(self, library_db):
        vetter = ImportVetter(library_db)
        no_match = DuplicateResult(is_duplicate=False, confidence=0.0, match_type='none')
        results = [('/import/new.mp3', no_match)]
        duplicates, new_songs, uncertain = vetter._categorize_results(results, 0.8)
        assert len(new_songs) == 1
        assert len(duplicates) == 0

    def test_categorize_uncertain(self, library_db):
        vetter = ImportVetter(library_db)
        matched = make_library_file()
        uncertain_result = DuplicateResult(
            is_duplicate=False, confidence=0.85, match_type='fuzzy_metadata', matched_file=matched
        )
        results = [('/import/maybe.mp3', uncertain_result)]
        duplicates, new_songs, uncertain = vetter._categorize_results(results, 0.9)
        assert len(uncertain) == 1

    def test_categorize_empty_results(self, library_db):
        vetter = ImportVetter(library_db)
        duplicates, new_songs, uncertain = vetter._categorize_results([], 0.8)
        assert duplicates == []
        assert new_songs == []
        assert uncertain == []

    def test_categorize_none_returns_empty(self, library_db):
        vetter = ImportVetter(library_db)
        duplicates, new_songs, uncertain = vetter._categorize_results(None, 0.8)
        assert duplicates == []


class TestVetFolder:
    """Tests for vet_folder method."""

    def test_empty_folder_raises_nothing(self, library_db, tmp_path):
        from rich.console import Console
        console = Console(file=StringIO())
        vetter = ImportVetter(library_db, console=console)
        report = vetter.vet_folder(str(tmp_path))
        assert report.total_files == 0

    def test_nonexistent_folder_raises(self, library_db):
        vetter = ImportVetter(library_db)
        with pytest.raises(FileNotFoundError):
            vetter.vet_folder("/nonexistent/path")

    def test_empty_path_raises(self, library_db):
        vetter = ImportVetter(library_db)
        with pytest.raises(ValueError, match="import_folder cannot be None or empty"):
            vetter.vet_folder("")

    def test_invalid_threshold_raises(self, library_db, tmp_path):
        vetter = ImportVetter(library_db)
        with pytest.raises(ValueError, match="threshold must be between"):
            vetter.vet_folder(str(tmp_path), threshold=1.5)


class TestExportFunctions:
    """Tests for export_new_songs, export_duplicates, export_uncertain."""

    def test_export_new_songs(self, library_db, tmp_path):
        from rich.console import Console
        console = Console(file=StringIO())
        vetter = ImportVetter(library_db, console=console)

        report = VettingReport(
            import_folder=str(tmp_path),
            total_files=2,
            threshold=0.8,
            new_songs=['/import/song1.mp3', '/import/song2.flac'],
        )
        output_file = str(tmp_path / "new_songs.txt")
        vetter.export_new_songs(report, output_file)

        content = Path(output_file).read_text()
        assert '/import/song1.mp3' in content
        assert '/import/song2.flac' in content

    def test_export_none_report_raises(self, library_db):
        vetter = ImportVetter(library_db)
        with pytest.raises(ValueError, match="report cannot be None"):
            vetter.export_new_songs(None, "/tmp/out.txt")

    def test_export_empty_output_file_raises(self, library_db):
        vetter = ImportVetter(library_db)
        report = VettingReport(import_folder='/tmp', total_files=0, threshold=0.8)
        with pytest.raises(ValueError, match="output_file cannot be None or empty"):
            vetter.export_new_songs(report, "")
