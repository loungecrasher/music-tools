"""Tests for LibraryDatabase - SQLite persistence for music library indexing."""

from pathlib import Path

import pytest
from conftest import make_library_file
from src.library.database import LibraryDatabase
from src.library.models import LibraryFile, LibraryStatistics


class TestLibraryDatabaseInit:
    """Tests for LibraryDatabase initialization."""

    def test_creates_database_file(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        LibraryDatabase(db_path)
        assert (tmp_path / "test.db").exists()

    def test_creates_parent_directories(self, tmp_path):
        db_path = str(tmp_path / "subdir" / "deep" / "test.db")
        LibraryDatabase(db_path)
        assert Path(db_path).parent.exists()

    def test_empty_path_raises(self):
        with pytest.raises(ValueError, match="db_path cannot be None or empty"):
            LibraryDatabase("")

    def test_none_path_raises(self):
        with pytest.raises(ValueError, match="db_path cannot be None or empty"):
            LibraryDatabase(None)


class TestAddAndGetFile:
    """Tests for add_file and get_file_by_path."""

    def test_add_file_returns_id(self, library_db):
        f = make_library_file()
        file_id = library_db.add_file(f)
        assert file_id > 0

    def test_get_file_by_path(self, library_db):
        f = make_library_file(file_path='/music/unique.mp3', artist='Artist', title='Title')
        library_db.add_file(f)
        result = library_db.get_file_by_path('/music/unique.mp3')
        assert result is not None
        assert result.artist == 'Artist'
        assert result.title == 'Title'

    def test_get_nonexistent_file_returns_none(self, library_db):
        assert library_db.get_file_by_path('/nonexistent.mp3') is None

    def test_add_none_file_raises(self, library_db):
        with pytest.raises(ValueError, match="file cannot be None"):
            library_db.add_file(None)


class TestHashLookups:
    """Tests for hash-based lookups."""

    def test_get_by_metadata_hash(self, library_db):
        f = make_library_file(metadata_hash='unique_meta_hash')
        library_db.add_file(f)
        result = library_db.get_file_by_metadata_hash('unique_meta_hash')
        assert result is not None
        assert result.metadata_hash == 'unique_meta_hash'

    def test_get_by_metadata_hash_not_found(self, library_db):
        assert library_db.get_file_by_metadata_hash('nonexistent') is None

    def test_get_files_by_metadata_hash(self, populated_library_db):
        # Add a second file with same metadata hash
        f = make_library_file(
            file_path='/music/dup.mp3', metadata_hash='hash_a1',
            file_content_hash='different_content'
        )
        populated_library_db.add_file(f)
        results = populated_library_db.get_files_by_metadata_hash('hash_a1')
        assert len(results) == 2

    def test_get_by_content_hash(self, library_db):
        f = make_library_file(file_content_hash='unique_content_hash')
        library_db.add_file(f)
        result = library_db.get_file_by_content_hash('unique_content_hash')
        assert result is not None

    def test_inactive_files_excluded(self, library_db):
        f = make_library_file(metadata_hash='will_deactivate')
        library_db.add_file(f)
        library_db.mark_inactive(f.file_path)
        assert library_db.get_file_by_metadata_hash('will_deactivate') is None


class TestSearchByArtistTitle:
    """Tests for search_by_artist_title."""

    def test_search_by_artist(self, populated_library_db):
        results = populated_library_db.search_by_artist_title(artist='Artist A')
        assert len(results) == 2

    def test_search_case_insensitive(self, populated_library_db):
        results = populated_library_db.search_by_artist_title(artist='artist a')
        assert len(results) == 2

    def test_search_by_title(self, populated_library_db):
        results = populated_library_db.search_by_artist_title(title='Song Two')
        assert len(results) == 1
        assert results[0].artist == 'Artist B'

    def test_search_no_results(self, populated_library_db):
        results = populated_library_db.search_by_artist_title(artist='Nobody')
        assert len(results) == 0


class TestStatistics:
    """Tests for get_statistics."""

    def test_empty_database_stats(self, library_db):
        stats = library_db.get_statistics()
        assert stats.total_files == 0
        assert stats.total_size == 0
        assert stats.artists_count == 0

    def test_stats_with_files(self, populated_library_db):
        stats = populated_library_db.get_statistics()
        assert stats.total_files == 3
        assert stats.total_size > 0
        assert stats.artists_count == 2  # Artist A, Artist B

    def test_stats_format_breakdown(self, populated_library_db):
        stats = populated_library_db.get_statistics()
        assert 'flac' in stats.formats_breakdown
        assert 'mp3' in stats.formats_breakdown
        assert stats.formats_breakdown['flac'] == 1
        assert stats.formats_breakdown['mp3'] == 2


class TestVettingHistory:
    """Tests for save_vetting_result and get_vetting_history."""

    def test_save_and_retrieve(self, library_db):
        library_db.save_vetting_result(
            import_folder='/import/test',
            total_files=100,
            duplicates_found=10,
            new_songs=85,
            uncertain_matches=5,
            threshold_used=0.8
        )
        history = library_db.get_vetting_history(limit=10)
        assert len(history) == 1
        assert history[0]['total_files'] == 100
        assert history[0]['duplicates_found'] == 10

    def test_multiple_entries_ordered_by_date(self, library_db):
        for i in range(3):
            library_db.save_vetting_result(
                import_folder=f'/import/batch{i}',
                total_files=i * 10 + 10,
                duplicates_found=i,
                new_songs=i * 10,
                uncertain_matches=0,
                threshold_used=0.8
            )
        history = library_db.get_vetting_history(limit=10)
        assert len(history) == 3

    def test_invalid_threshold_raises(self, library_db):
        with pytest.raises(ValueError, match="threshold_used must be between"):
            library_db.save_vetting_result(
                import_folder='/test', total_files=10, duplicates_found=0,
                new_songs=10, uncertain_matches=0, threshold_used=1.5
            )

    def test_negative_total_files_raises(self, library_db):
        with pytest.raises(ValueError, match="total_files must be non-negative"):
            library_db.save_vetting_result(
                import_folder='/test', total_files=-1, duplicates_found=0,
                new_songs=0, uncertain_matches=0, threshold_used=0.8
            )


class TestMarkInactiveAndDelete:
    """Tests for mark_inactive and delete_file."""

    def test_mark_inactive(self, library_db):
        f = make_library_file(file_path='/music/to_deactivate.mp3')
        library_db.add_file(f)
        library_db.mark_inactive('/music/to_deactivate.mp3')
        result = library_db.get_file_by_path('/music/to_deactivate.mp3')
        assert result.is_active is False

    def test_mark_inactive_empty_raises(self, library_db):
        with pytest.raises(ValueError, match="path cannot be None or empty"):
            library_db.mark_inactive("")

    def test_delete_file(self, library_db):
        f = make_library_file(file_path='/music/to_delete.mp3')
        library_db.add_file(f)
        library_db.delete_file('/music/to_delete.mp3')
        assert library_db.get_file_by_path('/music/to_delete.mp3') is None

    def test_delete_empty_raises(self, library_db):
        with pytest.raises(ValueError, match="path cannot be None or empty"):
            library_db.delete_file("")


class TestFileCount:
    """Tests for get_file_count."""

    def test_empty_count(self, library_db):
        assert library_db.get_file_count() == 0

    def test_count_with_files(self, populated_library_db):
        assert populated_library_db.get_file_count() == 3

    def test_count_excludes_inactive(self, populated_library_db):
        populated_library_db.mark_inactive('/music/song1.flac')
        assert populated_library_db.get_file_count(active_only=True) == 2
        assert populated_library_db.get_file_count(active_only=False) == 3


class TestVerifyFileExists:
    """Tests for verify_file_exists."""

    def test_existing_file(self, populated_library_db):
        assert populated_library_db.verify_file_exists('/music/song1.flac') is True

    def test_nonexistent_file(self, populated_library_db):
        assert populated_library_db.verify_file_exists('/music/nope.mp3') is False

    def test_empty_path_raises(self, library_db):
        with pytest.raises(ValueError):
            library_db.verify_file_exists("")
