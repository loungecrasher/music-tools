"""Tests for core library data models: LibraryFile, DuplicateResult, VettingReport, LibraryStatistics."""

import pytest
from conftest import make_duplicate_result, make_library_file, make_vetting_report
from src.library.models import (
    MAX_VALID_YEAR,
    METADATA_DELIMITER,
    MIN_VALID_YEAR,
    DuplicateResult,
    LibraryFile,
    LibraryStatistics,
    VettingReport,
)


class TestLibraryFile:
    """Tests for LibraryFile dataclass."""

    def test_creation_with_defaults(self):
        f = make_library_file()
        assert f.file_path == "/music/test.mp3"
        assert f.filename == "test.mp3"
        assert f.file_format == "mp3"
        assert f.is_active is True
        assert f.indexed_at is not None

    def test_filename_derived_from_path(self):
        f = LibraryFile(
            file_path="/music/my_song.flac",
            filename="",
            file_format="flac",
            file_size=100,
            metadata_hash="h",
            file_content_hash="c",
        )
        assert f.filename == "my_song.flac"

    def test_format_derived_from_path(self):
        f = LibraryFile(
            file_path="/music/track.m4a",
            filename="track.m4a",
            file_format="",
            file_size=100,
            metadata_hash="h",
            file_content_hash="c",
        )
        assert f.file_format == "m4a"

    def test_metadata_key_with_artist_title(self):
        f = make_library_file(artist="  The Beatles ", title=" Hey Jude ")
        assert f.metadata_key == f"the beatles{METADATA_DELIMITER}hey jude"

    def test_metadata_key_without_artist_title_uses_filename(self):
        f = make_library_file(artist=None, title=None, filename="unknown.mp3")
        assert "__filename__" in f.metadata_key
        assert "unknown.mp3" in f.metadata_key

    def test_display_name_with_artist_title(self):
        f = make_library_file(artist="Radiohead", title="Creep")
        assert f.display_name == "Radiohead - Creep"

    def test_display_name_without_artist_title(self):
        f = make_library_file(artist=None, title=None, filename="mystery.flac")
        assert f.display_name == "mystery.flac"

    def test_size_mb(self):
        f = make_library_file(file_size=10_485_760)  # 10 MB
        assert abs(f.size_mb - 10.0) < 0.01

    def test_size_mb_negative_returns_zero(self):
        f = make_library_file(file_size=-1)
        assert f.size_mb == 0.0

    def test_year_validation_out_of_range(self):
        f = make_library_file(year=1800)
        assert f.year is None

    def test_year_validation_future(self):
        f = make_library_file(year=MAX_VALID_YEAR + 1)
        assert f.year is None

    def test_year_validation_in_range(self):
        f = make_library_file(year=2024)
        assert f.year == 2024

    def test_duration_negative_set_to_none(self):
        f = make_library_file(duration=-5.0)
        assert f.duration is None

    def test_to_dict_round_trip(self):
        original = make_library_file(artist="Test", title="Song", year=2023, duration=180.0)
        d = original.to_dict()
        restored = LibraryFile.from_dict(d)
        assert restored.artist == original.artist
        assert restored.title == original.title
        assert restored.year == original.year
        assert restored.file_size == original.file_size
        assert restored.metadata_hash == original.metadata_hash

    def test_from_dict_missing_required_field(self):
        with pytest.raises(ValueError, match="Missing required field"):
            LibraryFile.from_dict({"file_path": "/test.mp3"})


class TestDuplicateResult:
    """Tests for DuplicateResult dataclass."""

    def test_creation_no_match(self):
        r = make_duplicate_result()
        assert r.is_duplicate is False
        assert r.confidence == 0.0
        assert r.match_type == "none"

    def test_creation_exact_match(self):
        matched = make_library_file()
        r = DuplicateResult(
            is_duplicate=True, confidence=1.0, match_type="exact_metadata", matched_file=matched
        )
        assert r.is_duplicate is True
        assert r.confidence == 1.0

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValueError, match="Confidence must be between"):
            DuplicateResult(is_duplicate=False, confidence=1.5, match_type="none")

    def test_negative_confidence_raises(self):
        with pytest.raises(ValueError, match="Confidence must be between"):
            DuplicateResult(is_duplicate=False, confidence=-0.1, match_type="none")

    def test_invalid_match_type_raises(self):
        with pytest.raises(ValueError, match="Invalid match_type"):
            DuplicateResult(is_duplicate=False, confidence=0.0, match_type="invalid")

    def test_is_certain(self):
        r = DuplicateResult(is_duplicate=True, confidence=0.96, match_type="exact_metadata")
        assert r.is_certain is True

    def test_is_uncertain(self):
        r = DuplicateResult(is_duplicate=True, confidence=0.85, match_type="fuzzy_metadata")
        assert r.is_uncertain is True

    def test_not_uncertain_when_certain(self):
        r = DuplicateResult(is_duplicate=True, confidence=0.96, match_type="exact_metadata")
        assert r.is_uncertain is False

    def test_get_best_match_from_matched_file(self):
        matched = make_library_file()
        r = DuplicateResult(
            is_duplicate=True, confidence=1.0, match_type="exact_metadata", matched_file=matched
        )
        assert r.get_best_match() is matched

    def test_get_best_match_from_all_matches(self):
        matched = make_library_file()
        r = DuplicateResult(
            is_duplicate=True,
            confidence=0.9,
            match_type="fuzzy_metadata",
            all_matches=[(matched, 0.9)],
        )
        assert r.get_best_match() is matched

    def test_get_best_match_none(self):
        r = make_duplicate_result()
        assert r.get_best_match() is None


class TestVettingReport:
    """Tests for VettingReport dataclass."""

    def test_creation_defaults(self):
        r = make_vetting_report()
        assert r.total_files == 10
        assert r.threshold == 0.8
        assert r.vetted_at is not None
        assert r.duplicate_count == 0
        assert r.new_count == 0

    def test_duplicate_count(self):
        make_library_file()
        dup_result = DuplicateResult(is_duplicate=True, confidence=1.0, match_type="exact_metadata")
        r = make_vetting_report(
            duplicates=[("/import/song.mp3", dup_result), ("/import/song2.mp3", dup_result)]
        )
        assert r.duplicate_count == 2

    def test_new_count(self):
        r = make_vetting_report(
            new_songs=["/import/new1.mp3", "/import/new2.mp3", "/import/new3.mp3"]
        )
        assert r.new_count == 3

    def test_duplicate_percentage(self):
        dup_result = DuplicateResult(is_duplicate=True, confidence=1.0, match_type="exact_metadata")
        r = make_vetting_report(total_files=100, duplicates=[("/import/dup.mp3", dup_result)] * 25)
        assert r.duplicate_percentage == 25.0

    def test_duplicate_percentage_zero_files(self):
        r = make_vetting_report(total_files=0)
        assert r.duplicate_percentage == 0.0

    def test_new_percentage(self):
        r = make_vetting_report(
            total_files=200, new_songs=[f"/import/new{i}.mp3" for i in range(180)]
        )
        assert r.new_percentage == 90.0

    def test_get_summary(self):
        r = make_vetting_report(total_files=50, new_songs=["/a.mp3"] * 45)
        summary = r.get_summary()
        assert summary["total_files"] == 50
        assert summary["new_songs"] == 45
        assert summary["duplicates"] == 0
        assert summary["threshold"] == 0.8

    def test_negative_total_files_raises(self):
        with pytest.raises(ValueError, match="total_files must be non-negative"):
            VettingReport(import_folder="/tmp", total_files=-1, threshold=0.8)

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError, match="threshold must be between"):
            VettingReport(import_folder="/tmp", total_files=10, threshold=1.5)

    def test_negative_scan_duration_raises(self):
        with pytest.raises(ValueError, match="scan_duration must be non-negative"):
            VettingReport(import_folder="/tmp", total_files=10, threshold=0.8, scan_duration=-1.0)


class TestLibraryStatistics:
    """Tests for LibraryStatistics dataclass."""

    def test_total_size_gb(self):
        s = LibraryStatistics(total_files=100, total_size=1024**3)
        assert abs(s.total_size_gb - 1.0) < 0.01

    def test_average_file_size_mb(self):
        s = LibraryStatistics(total_files=2, total_size=2 * 1024**2)
        assert abs(s.average_file_size_mb - 1.0) < 0.01

    def test_average_file_size_mb_zero_files(self):
        s = LibraryStatistics(total_files=0, total_size=0)
        assert s.average_file_size_mb == 0.0

    def test_get_format_percentages(self):
        s = LibraryStatistics(total_files=100, formats_breakdown={"mp3": 60, "flac": 40})
        pcts = s.get_format_percentages()
        assert pcts["mp3"] == 60.0
        assert pcts["flac"] == 40.0

    def test_get_format_percentages_zero_files(self):
        s = LibraryStatistics(total_files=0, formats_breakdown={"mp3": 0})
        assert s.get_format_percentages() == {}
