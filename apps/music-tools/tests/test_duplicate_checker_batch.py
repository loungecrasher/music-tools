from unittest.mock import MagicMock, patch

import pytest

# Imports assumed to work after conftest.py adds apps/music-tools to sys.path
from src.library.duplicate_checker import DuplicateChecker, DuplicateResult
from src.library.models import LibraryFile


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def checker(mock_db):
    return DuplicateChecker(mock_db)


@pytest.fixture
def sample_files():
    return [
        LibraryFile(
            file_path="/music/artist1/song1.mp3",
            filename="song1.mp3",
            artist="Artist 1",
            title="Song 1",
            album="Album 1",
            year=2020,
            duration=180,
            file_format="mp3",
            file_size=1024,
            metadata_hash="hash1",
            file_content_hash="content1"
        ),
        LibraryFile(
            file_path="/music/artist2/song2.mp3",
            filename="song2.mp3",
            artist="Artist 2",
            title="Song 2",
            album="Album 2",
            year=2021,
            duration=200,
            file_format="mp3",
            file_size=2048,
            metadata_hash="hash2",
            file_content_hash="content2"
        )
    ]


def test_check_files_batch_empty(checker):
    """Test batch check with empty list raises ValueError."""
    with pytest.raises(ValueError):
        checker.check_files_batch([])


@patch('src.library.duplicate_checker.Path')
@patch('src.library.duplicate_checker.DuplicateChecker._extract_metadata')
def test_check_files_batch_optimization(mock_extract, mock_path, checker, sample_files, mock_db):
    """Test that batch check uses optimization (pre-fetching tracks)."""

    # Setup mocks
    mock_path_obj = MagicMock()
    mock_path_obj.resolve.return_value.exists.return_value = True
    mock_path.return_value = mock_path_obj

    # Return sample files when extracting metadata
    mock_extract.side_effect = sample_files

    # Mock DB responses
    mock_db.batch_get_files_by_hashes.return_value = {}
    mock_db.search_by_artist_title.return_value = []  # No duplicates found

    file_paths = ["/music/artist1/song1.mp3", "/music/artist2/song2.mp3"]

    # Run batch check
    results = checker.check_files_batch(file_paths)

    # Verify results
    assert len(results) == 2
    assert all(not r.is_duplicate for r in results.values())

    # Verify optimization: search_by_artist_title should be called for each unique artist
    assert mock_db.search_by_artist_title.call_count == 2
    mock_db.search_by_artist_title.assert_any_call(artist="Artist 1")
    mock_db.search_by_artist_title.assert_any_call(artist="Artist 2")


@patch('src.library.duplicate_checker.Path')
@patch('src.library.duplicate_checker.DuplicateChecker._extract_metadata')
def test_check_files_batch_fuzzy_match(mock_extract, mock_path, checker, sample_files, mock_db):
    """Test that fuzzy matching works with cached tracks."""

    # Setup mocks
    mock_path_obj = MagicMock()
    mock_path_obj.resolve.return_value.exists.return_value = True
    mock_path.return_value = mock_path_obj

    # File to check
    check_file = sample_files[0]  # Artist 1, Song 1
    mock_extract.return_value = check_file

    # Mock DB to return no exact matches
    mock_db.batch_get_files_by_hashes.return_value = {}

    # Mock DB to return a potential duplicate for Artist 1
    duplicate_file = LibraryFile(
        file_path="/existing/song1_dup.mp3",
        filename="song1_dup.mp3",
        artist="Artist 1",
        title="Song 1 (Remaster)",  # Similar title
        album="Greatest Hits",
        year=2022,
        duration=180,
        file_format="mp3",
        file_size=1024,
        metadata_hash="hash3",
        file_content_hash="content3"
    )

    def search_side_effect(artist=None, title=None):
        if artist == "Artist 1":
            return [duplicate_file]
        return []

    mock_db.search_by_artist_title.side_effect = search_side_effect

    # Run check
    results = checker.check_files_batch(["/music/artist1/song1.mp3"], fuzzy_threshold=0.5)

    # Verify result
    result = results["/music/artist1/song1.mp3"]
    assert result.is_duplicate
    assert result.match_type == 'fuzzy_metadata'
    assert result.matched_file.file_path == "/existing/song1_dup.mp3"
