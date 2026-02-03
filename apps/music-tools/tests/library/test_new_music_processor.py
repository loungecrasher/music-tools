"""Tests for NewMusicProcessor - the unified new music folder workflow.

Includes regression test for the tuple-unpacking bug at line 103.
"""

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from conftest import make_duplicate_result, make_library_file, make_vetting_report
from src.library.models import DuplicateResult, LibraryFile, VettingReport
from src.library.new_music_processor import NewMusicProcessor, ProcessingResult


class TestProcessingResult:
    """Tests for ProcessingResult dataclass."""

    def test_defaults(self):
        r = ProcessingResult()
        assert r.total_files == 0
        assert r.duplicates == []
        assert r.already_reviewed == []
        assert r.truly_new == []

    def test_post_init_none_lists(self):
        r = ProcessingResult(total_files=5, duplicates=None, already_reviewed=None, truly_new=None)
        assert r.duplicates == []
        assert r.already_reviewed == []
        assert r.truly_new == []

    def test_preserves_provided_lists(self):
        dups = ["/a.mp3"]
        r = ProcessingResult(total_files=1, duplicates=dups)
        assert r.duplicates is dups


class TestNewMusicProcessorInit:
    """Tests for NewMusicProcessor initialization."""

    def test_init_with_library_db(self, library_db):
        processor = NewMusicProcessor(library_db)
        assert processor.library_db is library_db
        assert processor.vetter is not None
        assert processor.candidate_manager is not None

    def test_init_with_console(self, library_db):
        from rich.console import Console

        console = Console(file=StringIO())
        processor = NewMusicProcessor(library_db, console=console)
        assert processor.console is console


class TestProcessFolder:
    """Tests for process_folder method."""

    def test_nonexistent_folder_raises(self, library_db):
        processor = NewMusicProcessor(library_db)
        with pytest.raises(FileNotFoundError):
            processor.process_folder("/nonexistent/folder")

    def test_process_folder_with_duplicates(self, library_db, tmp_path):
        """Regression test: vet_report.duplicates are tuples, not objects."""
        from rich.console import Console

        console = Console(file=StringIO())
        processor = NewMusicProcessor(library_db, console=console)

        # Create a fake import folder with one file
        import_dir = tmp_path / "import"
        import_dir.mkdir()
        (import_dir / "dup_song.flac").write_bytes(b"fake")

        # Mock the vetter to return a report with tuple-based duplicates
        matched_file = make_library_file(
            file_path="/library/dup_song.flac", artist="Artist", title="Song"
        )
        dup_result = DuplicateResult(
            is_duplicate=True,
            confidence=1.0,
            match_type="exact_metadata",
            matched_file=matched_file,
        )
        mock_report = VettingReport(
            import_folder=str(import_dir),
            total_files=1,
            threshold=0.8,
            duplicates=[(str(import_dir / "dup_song.flac"), dup_result)],
            new_songs=[],
            uncertain=[],
        )

        with patch.object(processor.vetter, "vet_folder", return_value=mock_report):
            with patch.object(processor.candidate_manager, "check_folder", return_value=[]):
                result = processor.process_folder(str(import_dir))

        # The bug was: dup.import_file on a tuple. After fix: tuple unpacking works.
        assert len(result.duplicates) == 1
        assert result.duplicates[0] == str(import_dir / "dup_song.flac")

    def test_process_folder_new_songs(self, library_db, tmp_path):
        from rich.console import Console

        console = Console(file=StringIO())
        processor = NewMusicProcessor(library_db, console=console)

        import_dir = tmp_path / "import"
        import_dir.mkdir()

        mock_report = VettingReport(
            import_folder=str(import_dir),
            total_files=3,
            threshold=0.8,
            duplicates=[],
            new_songs=["/import/new1.mp3", "/import/new2.mp3", "/import/new3.mp3"],
            uncertain=[],
        )

        with patch.object(processor.vetter, "vet_folder", return_value=mock_report):
            with patch.object(processor.candidate_manager, "check_folder", return_value=[]):
                result = processor.process_folder(str(import_dir))

        assert len(result.truly_new) == 3
        assert result.total_files == 3
        assert len(result.duplicates) == 0

    def test_process_folder_history_matches(self, library_db, tmp_path):
        """Files in history but not in library go to already_reviewed."""
        from rich.console import Console

        console = Console(file=StringIO())
        processor = NewMusicProcessor(library_db, console=console)

        import_dir = tmp_path / "import"
        import_dir.mkdir()

        mock_report = VettingReport(
            import_folder=str(import_dir),
            total_files=2,
            threshold=0.8,
            duplicates=[],
            new_songs=["/import/reviewed.mp3", "/import/new.mp3"],
            uncertain=[],
        )

        history_matches = [
            {"file": "reviewed.mp3", "path": "/import/reviewed.mp3", "added_at": "2024-01-01"}
        ]

        with patch.object(processor.vetter, "vet_folder", return_value=mock_report):
            with patch.object(
                processor.candidate_manager, "check_folder", return_value=history_matches
            ):
                result = processor.process_folder(str(import_dir))

        assert len(result.already_reviewed) == 1
        assert "/import/reviewed.mp3" in result.already_reviewed
        assert len(result.truly_new) == 1
        assert "/import/new.mp3" in result.truly_new


class TestDisplayResults:
    """Tests for display_results method."""

    def test_display_results_does_not_crash(self, library_db):
        from rich.console import Console

        console = Console(file=StringIO())
        processor = NewMusicProcessor(library_db, console=console)

        result = ProcessingResult(
            total_files=10,
            duplicates=["/a.mp3", "/b.mp3"],
            already_reviewed=["/c.mp3"],
            truly_new=["/d.mp3", "/e.mp3", "/f.mp3", "/g.mp3", "/h.mp3", "/i.mp3", "/j.mp3"],
        )
        # Should not raise
        processor.display_results(result)

    def test_display_results_zero_files(self, library_db):
        from rich.console import Console

        console = Console(file=StringIO())
        processor = NewMusicProcessor(library_db, console=console)
        result = ProcessingResult(total_files=0)
        processor.display_results(result)


class TestExportNewSongs:
    """Tests for export_new_songs method."""

    def test_export_creates_file(self, library_db, tmp_path):
        from rich.console import Console

        console = Console(file=StringIO())
        processor = NewMusicProcessor(library_db, console=console)

        result = ProcessingResult(
            total_files=2, truly_new=["/import/song1.flac", "/import/song2.flac"]
        )
        export_path = processor.export_new_songs(result, str(tmp_path))

        assert Path(export_path).exists()
        content = Path(export_path).read_text()
        assert "song1.flac" in content
        assert "song2.flac" in content
