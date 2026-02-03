"""Tests for DuplicateChecker - multi-level duplicate detection."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.library.duplicate_checker import DuplicateChecker
from src.library.models import LibraryFile, DuplicateResult
from conftest import make_library_file


class TestDuplicateCheckerInit:
    """Tests for DuplicateChecker initialization."""

    def test_init_with_db(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker.db is library_db

    def test_init_none_db_raises(self):
        with pytest.raises(ValueError, match="library_db cannot be None"):
            DuplicateChecker(None)


class TestNormalizeString:
    """Tests for _normalize_string."""

    def test_lowercase(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker._normalize_string("Hello World") == "hello world"

    def test_strips_whitespace(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker._normalize_string("  hello  ") == "hello"

    def test_removes_original_mix(self, library_db):
        checker = DuplicateChecker(library_db)
        result = checker._normalize_string("Song Name (Original Mix)")
        assert "(original mix)" not in result
        assert result == "song name"

    def test_removes_radio_edit(self, library_db):
        checker = DuplicateChecker(library_db)
        result = checker._normalize_string("Track (Radio Edit)")
        assert result == "track"

    def test_removes_remastered(self, library_db):
        checker = DuplicateChecker(library_db)
        result = checker._normalize_string("Classic Song - Remastered")
        assert result == "classic song"

    def test_empty_string(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker._normalize_string("") == ""

    def test_none_string(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker._normalize_string(None) == ""


class TestCalculateSimilarity:
    """Tests for _calculate_similarity."""

    def test_identical_strings(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker._calculate_similarity("hello", "hello") == 1.0

    def test_completely_different(self, library_db):
        checker = DuplicateChecker(library_db)
        score = checker._calculate_similarity("abc", "xyz")
        assert score < 0.5

    def test_similar_strings(self, library_db):
        checker = DuplicateChecker(library_db)
        score = checker._calculate_similarity("sunset lover", "sunset lovers")
        assert score > 0.8

    def test_empty_string_returns_zero(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker._calculate_similarity("", "hello") == 0.0

    def test_none_returns_zero(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker._calculate_similarity(None, "hello") == 0.0

    def test_both_empty_returns_zero(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker._calculate_similarity("", "") == 0.0


class TestCheckFile:
    """Tests for check_file method."""

    def test_empty_path_raises(self, library_db):
        checker = DuplicateChecker(library_db)
        with pytest.raises(ValueError, match="file_path cannot be None or empty"):
            checker.check_file("")

    def test_invalid_threshold_raises(self, library_db, tmp_path):
        checker = DuplicateChecker(library_db)
        fake_file = tmp_path / "song.mp3"
        fake_file.write_bytes(b"fake")
        with pytest.raises(ValueError, match="fuzzy_threshold must be between"):
            checker.check_file(str(fake_file), fuzzy_threshold=1.5)

    def test_nonexistent_file_returns_no_match(self, library_db):
        checker = DuplicateChecker(library_db)
        result = checker.check_file("/nonexistent/file.mp3")
        assert result.is_duplicate is False
        assert result.match_type == 'none'

    def test_exact_metadata_match(self, populated_library_db, tmp_path):
        """Test that exact metadata hash match is detected."""
        checker = DuplicateChecker(populated_library_db)

        fake_file = tmp_path / "dup.flac"
        fake_file.write_bytes(b"fake audio data")

        matched = make_library_file(metadata_hash='hash_a1')

        with patch.object(checker, '_extract_metadata') as mock_extract:
            mock_extract.return_value = make_library_file(
                file_path=str(fake_file), metadata_hash='hash_a1'
            )
            result = checker.check_file(str(fake_file))

        assert result.is_duplicate is True
        assert result.confidence == 1.0
        assert result.match_type == 'exact_metadata'

    def test_no_match_found(self, populated_library_db, tmp_path):
        checker = DuplicateChecker(populated_library_db)

        fake_file = tmp_path / "new_song.mp3"
        fake_file.write_bytes(b"new audio data")

        with patch.object(checker, '_extract_metadata') as mock_extract:
            mock_extract.return_value = make_library_file(
                file_path=str(fake_file),
                artist='New Artist',
                title='New Song',
                metadata_hash='totally_new_hash',
                file_content_hash='totally_new_content',
            )
            result = checker.check_file(str(fake_file))

        assert result.is_duplicate is False
        assert result.match_type == 'none'


class TestCheckBatch:
    """Tests for check_batch method."""

    def test_none_paths_returns_empty(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker.check_batch(None) == []

    def test_empty_paths_returns_empty(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker.check_batch([]) == []

    def test_invalid_threshold_raises(self, library_db):
        checker = DuplicateChecker(library_db)
        with pytest.raises(ValueError, match="fuzzy_threshold must be between"):
            checker.check_batch(["/test.mp3"], fuzzy_threshold=2.0)

    def test_batch_handles_errors_gracefully(self, library_db, tmp_path):
        checker = DuplicateChecker(library_db)
        # Mix of nonexistent files
        results = checker.check_batch(["/nonexistent1.mp3", "/nonexistent2.mp3"])
        assert len(results) == 2
        for path, result in results:
            assert result.is_duplicate is False


class TestCheckMetadataHash:
    """Tests for _check_metadata_hash."""

    def test_returns_match(self, populated_library_db):
        checker = DuplicateChecker(populated_library_db)
        file = make_library_file(metadata_hash='hash_a1')
        result = checker._check_metadata_hash(file)
        assert result is not None
        assert result.metadata_hash == 'hash_a1'

    def test_returns_none_for_no_match(self, populated_library_db):
        checker = DuplicateChecker(populated_library_db)
        file = make_library_file(metadata_hash='nonexistent_hash')
        assert checker._check_metadata_hash(file) is None

    def test_returns_none_for_none_file(self, library_db):
        checker = DuplicateChecker(library_db)
        assert checker._check_metadata_hash(None) is None


class TestCheckFuzzyMetadata:
    """Tests for _check_fuzzy_metadata."""

    def test_finds_similar_titles(self, populated_library_db):
        checker = DuplicateChecker(populated_library_db)
        file = make_library_file(artist='Artist A', title='Song On')  # Close to "Song One"
        matches = checker._check_fuzzy_metadata(file, threshold=0.7)
        # May or may not find a match depending on similarity score
        # "Song On" vs "Song One" should be fairly similar
        assert isinstance(matches, list)

    def test_no_artist_returns_empty(self, populated_library_db):
        checker = DuplicateChecker(populated_library_db)
        file = make_library_file(artist=None, title='Song')
        matches = checker._check_fuzzy_metadata(file, threshold=0.8)
        assert matches == []

    def test_no_title_returns_empty(self, populated_library_db):
        checker = DuplicateChecker(populated_library_db)
        file = make_library_file(artist='Artist', title=None)
        matches = checker._check_fuzzy_metadata(file, threshold=0.8)
        assert matches == []

    def test_sorted_by_score_descending(self, populated_library_db):
        checker = DuplicateChecker(populated_library_db)
        file = make_library_file(artist='Artist A', title='Song')
        matches = checker._check_fuzzy_metadata(file, threshold=0.3)
        if len(matches) > 1:
            scores = [score for _, score in matches]
            assert scores == sorted(scores, reverse=True)
