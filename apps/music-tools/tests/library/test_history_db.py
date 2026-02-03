"""Tests for HistoryDatabase - candidate history tracking."""


import pytest
from src.library.history_db import HistoryDatabase


class TestHistoryDatabaseInit:
    """Tests for HistoryDatabase initialization."""

    def test_creates_database_file(self, tmp_path):
        db_path = str(tmp_path / "test_history.db")
        HistoryDatabase(db_path=db_path)
        assert (tmp_path / "test_history.db").exists()

    def test_creates_table(self, tmp_path):
        import sqlite3
        db_path = str(tmp_path / "test_history.db")
        HistoryDatabase(db_path=db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
        assert cursor.fetchone() is not None
        conn.close()


class TestAddFile:
    """Tests for add_file method."""

    def test_add_file_returns_true(self, tmp_path):
        db = HistoryDatabase(db_path=str(tmp_path / "h.db"))
        assert db.add_file("Artist - Song.flac", "/music/Artist - Song.flac") is True

    def test_add_duplicate_returns_false(self, tmp_path):
        db = HistoryDatabase(db_path=str(tmp_path / "h.db"))
        db.add_file("Artist - Song.flac", "/music/Artist - Song.flac")
        assert db.add_file("Artist - Song.flac", "/other/Artist - Song.flac") is False

    def test_add_different_files(self, tmp_path):
        db = HistoryDatabase(db_path=str(tmp_path / "h.db"))
        assert db.add_file("song1.mp3") is True
        assert db.add_file("song2.mp3") is True

    def test_add_file_empty_source_path(self, tmp_path):
        db = HistoryDatabase(db_path=str(tmp_path / "h.db"))
        assert db.add_file("song.mp3") is True


class TestCheckFile:
    """Tests for check_file method."""

    def test_check_existing_file_returns_datetime(self, tmp_path):
        db = HistoryDatabase(db_path=str(tmp_path / "h.db"))
        db.add_file("known.flac", "/music/known.flac")
        result = db.check_file("known.flac")
        assert result is not None

    def test_check_nonexistent_file_returns_none(self, tmp_path):
        db = HistoryDatabase(db_path=str(tmp_path / "h.db"))
        assert db.check_file("unknown.flac") is None

    def test_check_file_after_multiple_adds(self, tmp_path):
        db = HistoryDatabase(db_path=str(tmp_path / "h.db"))
        db.add_file("song1.mp3")
        db.add_file("song2.mp3")
        db.add_file("song3.mp3")
        assert db.check_file("song2.mp3") is not None
        assert db.check_file("song4.mp3") is None


class TestGetStats:
    """Tests for get_stats method."""

    def test_empty_database_stats(self, tmp_path):
        db = HistoryDatabase(db_path=str(tmp_path / "h.db"))
        stats = db.get_stats()
        assert stats['total_files'] == 0

    def test_stats_after_adds(self, tmp_path):
        db = HistoryDatabase(db_path=str(tmp_path / "h.db"))
        db.add_file("song1.mp3")
        db.add_file("song2.mp3")
        db.add_file("song3.mp3")
        stats = db.get_stats()
        assert stats['total_files'] == 3
        assert stats['last_added'] is not None

    def test_stats_skips_duplicate_count(self, tmp_path):
        db = HistoryDatabase(db_path=str(tmp_path / "h.db"))
        db.add_file("song.mp3")
        db.add_file("song.mp3")  # duplicate, not added
        stats = db.get_stats()
        assert stats['total_files'] == 1
