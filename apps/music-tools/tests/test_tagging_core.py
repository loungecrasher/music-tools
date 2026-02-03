import pytest
from unittest.mock import Mock, MagicMock, patch
# Imports assumed to work after conftest.py adds apps/music-tools to sys.path
from src.tagging.library_processor import MusicLibraryProcessor

@pytest.fixture
def mock_components():
    return {
        'scanner': MagicMock(),
        'metadata_handler': MagicMock(),
        'ai_researcher': MagicMock(),
        'cache_manager': MagicMock(),
        'config': MagicMock()
    }

@pytest.fixture
def processor(mock_components):
    return MusicLibraryProcessor(
        mock_components['scanner'],
        mock_components['metadata_handler'],
        mock_components['ai_researcher'],
        mock_components['cache_manager'],
        mock_components['config']
    )

def test_process_empty_directory(processor, mock_components):
    """Test processing an empty directory."""
    mock_components['scanner'].scan_directory.return_value = []
    
    results = processor.process("/path/to/empty", batch_size=10, dry_run=True, resume=False)
    
    assert results == {}
    assert processor.processed_count == 0

@patch('src.tagging.library_processor.Confirm')
def test_process_files_dry_run(mock_confirm, processor, mock_components):
    """Test processing files in dry run mode."""
    # Setup mocks
    mock_components['scanner'].scan_directory.return_value = ["/music/song1.mp3"]
    mock_components['metadata_handler'].extract_metadata.return_value = {
        'artist': 'Artist 1',
        'title': 'Song 1'
    }
    mock_components['cache_manager'].get_country.return_value = None
    mock_components['ai_researcher'].research_artists_batch.return_value = {
        'Artist 1': {'genre': 'Pop', 'grouping': 'US', 'year': '2020'}
    }
    
    # Mock user confirmation
    mock_confirm.ask.return_value = True
    
    # Run process
    results = processor.process("/music", batch_size=10, dry_run=True, resume=False)
    
    # Verify results
    assert results['processed'] == 1
    assert results['updated'] == 0 # Dry run shouldn't update
    assert results['dry_run'] is True
    
    # Verify interactions
    mock_components['ai_researcher'].research_artists_batch.assert_called_once()
    mock_components['metadata_handler'].update_metadata.assert_not_called()

@patch('src.tagging.library_processor.Confirm')
def test_process_files_update(mock_confirm, processor, mock_components):
    """Test processing files with updates."""
    # Setup mocks
    mock_components['scanner'].scan_directory.return_value = ["/music/song1.mp3"]
    mock_components['metadata_handler'].extract_metadata.return_value = {
        'artist': 'Artist 1',
        'title': 'Song 1'
    }
    mock_components['cache_manager'].get_country.return_value = None
    mock_components['ai_researcher'].research_artists_batch.return_value = {
        'Artist 1': {'genre': 'Pop', 'grouping': 'US', 'year': '2020'}
    }
    mock_components['config'].overwrite_existing_tags = True
    
    # Mock user confirmation
    mock_confirm.ask.return_value = True
    
    # Run process
    results = processor.process("/music", batch_size=10, dry_run=False, resume=False)
    
    # Verify results
    assert results['processed'] == 1
    assert results['updated'] == 1
    assert results['dry_run'] is False
    
    # Verify update called
    mock_components['metadata_handler'].update_metadata.assert_called_once()
    args = mock_components['metadata_handler'].update_metadata.call_args
    assert args[0][0] == "/music/song1.mp3"
    assert args[0][1] == {'genre': 'Pop', 'grouping': 'US', 'year': '2020'}
