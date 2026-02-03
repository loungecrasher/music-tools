"""
Tests for Candidate History feature.
"""
import os
import pytest
import sqlite3
from datetime import datetime
from unittest.mock import patch, MagicMock
from src.library.history_db import HistoryDatabase
from src.library.candidate_manager import CandidateManager

# --- Fixtures ---

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test_history.db")

@pytest.fixture
def history_db(temp_db_path):
    """Create a HistoryDatabase instance with a temp DB."""
    return HistoryDatabase(temp_db_path)

@pytest.fixture
def temp_folder(tmp_path):
    """Create a temporary folder with some files."""
    folder = tmp_path / "music"
    folder.mkdir()
    (folder / "song1.mp3").touch()
    (folder / "song2.flac").touch()
    (folder / "text.txt").touch() # Should be ignored
    return str(folder)

# --- HistoryDatabase Tests ---

def test_db_initialization(temp_db_path):
    """Test that the database is initialized correctly."""
    db = HistoryDatabase(temp_db_path)
    assert os.path.exists(temp_db_path)
    
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='history'")
        assert cursor.fetchone() is not None

def test_add_and_check_file(history_db):
    """Test adding and checking files."""
    filename = "Test Artist - Test Track.mp3"
    
    # Add file
    assert history_db.add_file(filename, "/path/to/file") is True
    
    # Check if it exists
    added_at = history_db.check_file(filename)
    assert added_at is not None
    assert isinstance(added_at, (datetime, str))
    
    # Add duplicate
    assert history_db.add_file(filename, "/other/path") is False

def test_check_nonexistent_file(history_db):
    """Test checking a file that doesn't exist."""
    assert history_db.check_file("Nonexistent.mp3") is None

def test_get_stats(history_db):
    """Test getting stats."""
    history_db.add_file("Song 1.mp3")
    history_db.add_file("Song 2.mp3")
    
    stats = history_db.get_stats()
    assert stats['total_files'] == 2
    assert stats['last_added'] is not None

# --- CandidateManager Tests ---

def test_add_folder_to_history(temp_db_path, temp_folder):
    """Test scanning a folder and adding to history."""
    # Mock the DB path in CandidateManager
    with patch('src.library.candidate_manager.HistoryDatabase') as MockDB:
        # Use a real DB instance but injected via mock
        real_db = HistoryDatabase(temp_db_path)
        MockDB.return_value = real_db
        
        manager = CandidateManager()
        stats = manager.add_folder_to_history(temp_folder)
        
        # Should find 2 audio files (song1.mp3, song2.flac)
        assert stats['total'] == 2
        assert stats['added'] == 2
        
        # Verify in DB
        assert real_db.check_file("song1.mp3") is not None
        assert real_db.check_file("song2.flac") is not None

def test_check_folder_matches(temp_db_path, temp_folder):
    """Test checking a folder for matches."""
    # Pre-populate DB
    db = HistoryDatabase(temp_db_path)
    db.add_file("song1.mp3")
    
    with patch('src.library.candidate_manager.HistoryDatabase') as MockDB:
        MockDB.return_value = db
        
        manager = CandidateManager()
        matches = manager.check_folder(temp_folder)
        
        # Should match song1.mp3
        assert len(matches) == 1
        assert matches[0]['file'] == "song1.mp3"

@patch('src.library.candidate_manager.Confirm.ask')
@patch('src.library.candidate_manager.shutil.move')
def test_process_matches_move_to_trash(mock_move, mock_confirm):
    """Test processing matches and moving to trash."""
    mock_confirm.return_value = True # User says Yes
    
    manager = CandidateManager()
    matches = [{
        'file': 'song1.mp3',
        'path': '/path/to/song1.mp3',
        'added_at': datetime.now()
    }]
    
    manager.process_matches(matches)
    
    # Verify move was called
    mock_move.assert_called_once()
    args, _ = mock_move.call_args
    assert args[0] == '/path/to/song1.mp3'
    assert 'song1.mp3' in args[1] # Destination contains filename
