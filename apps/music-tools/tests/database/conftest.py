"""
Pytest configuration for database tests
"""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture(scope='session')
def test_data_dir():
    """Create temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_playlist_data():
    """Sample playlist data for testing."""
    return {
        'id': 'pl_001',
        'name': 'Test Playlist',
        'url': 'https://example.com/playlist/001',
        'owner': 'user123',
        'tracks_count': 10,
        'service': 'spotify',
        'is_algorithmic': False
    }


@pytest.fixture
def sample_track_data():
    """Sample track data for testing."""
    return {
        'id': 'tr_001',
        'name': 'Test Song',
        'artist': 'Test Artist',
        'album': 'Test Album',
        'duration': 180000,
        'release_date': '2024-01-01',
        'isrc': 'USRC12345678',
        'service': 'spotify'
    }
