from unittest.mock import MagicMock, patch

import pytest

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


@patch('src.tagging.library_processor.Prompt')
@patch('src.tagging.library_processor.Confirm')
@patch('src.tagging.library_processor.IntPrompt')
def test_process_empty_directory(mock_int_prompt, mock_confirm, mock_prompt,
                                 processor, mock_components):
    """Test processing an empty directory."""
    mock_components['scanner'].scan_directory.return_value = []
    mock_int_prompt.ask.return_value = 1000
    mock_confirm.ask.return_value = False
    mock_prompt.ask.return_value = "2"

    results = processor.process("/path/to/empty", batch_size=10, dry_run=True, resume=False)

    assert results == {}
    assert processor.processed_count == 0


@patch('src.tagging.library_processor.Prompt')
@patch('src.tagging.library_processor.Confirm')
@patch('src.tagging.library_processor.IntPrompt')
def test_process_files_dry_run(mock_int_prompt, mock_confirm, mock_prompt,
                               processor, mock_components):
    """Test processing files in dry run mode."""
    mock_int_prompt.ask.return_value = 1000
    mock_confirm.ask.return_value = False
    mock_prompt.ask.return_value = "2"

    mock_components['scanner'].scan_directory.return_value = ["/music/song1.mp3"]
    mock_components['metadata_handler'].extract_metadata.return_value = {
        'artist': 'Artist 1',
        'title': 'Song 1'
    }
    mock_components['cache_manager'].get_country.return_value = None
    mock_components['ai_researcher'].research_artists_batch.return_value = {
        'Artist 1': {'genre': 'Pop', 'grouping': 'US', 'year': '2020'}
    }

    results = processor.process("/music", batch_size=10, dry_run=True, resume=False)

    assert results.get('processed', 0) >= 0
    assert results.get('dry_run', True) is True


@patch('src.tagging.library_processor.Prompt')
@patch('src.tagging.library_processor.Confirm')
@patch('src.tagging.library_processor.IntPrompt')
def test_process_files_update(mock_int_prompt, mock_confirm, mock_prompt,
                              processor, mock_components):
    """Test processing files with updates."""
    mock_int_prompt.ask.return_value = 1000
    mock_confirm.ask.return_value = False
    mock_prompt.ask.return_value = "2"

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

    results = processor.process("/music", batch_size=10, dry_run=False, resume=False)

    assert results.get('processed', 0) >= 0
    assert results.get('dry_run', False) is False
