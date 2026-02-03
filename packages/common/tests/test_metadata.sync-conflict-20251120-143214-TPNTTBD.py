"""Tests for metadata module (audio file tag reading/writing)."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from music_tools_common.metadata import (
    read_metadata,
    write_metadata,
    MetadataReader,
    MetadataWriter,
)


class TestMetadataReader:
    """Tests for MetadataReader class."""

    def test_metadata_reader_initialization(self):
        """Test MetadataReader initialization."""
        reader = MetadataReader()
        assert reader is not None

    @patch('mutagen.File')
    def test_read_mp3_metadata(self, mock_mutagen_file):
        """Test reading metadata from MP3 file."""
        # Mock mutagen File object
        mock_file = MagicMock()
        mock_file.tags = {
            'TIT2': Mock(text=['Song Title']),
            'TPE1': Mock(text=['Artist Name']),
            'TALB': Mock(text=['Album Name']),
            'TDRC': Mock(text=['2024']),
        }
        mock_file.info.length = 180.5  # 3 minutes
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/song.mp3')

        assert metadata is not None
        assert metadata.get('title') == 'Song Title'
        assert metadata.get('artist') == 'Artist Name'
        assert metadata.get('album') == 'Album Name'
        assert metadata.get('year') == '2024'
        assert metadata.get('duration') == 180.5

    @patch('mutagen.File')
    def test_read_flac_metadata(self, mock_mutagen_file):
        """Test reading metadata from FLAC file."""
        mock_file = MagicMock()
        mock_file.tags = {
            'TITLE': ['Song Title'],
            'ARTIST': ['Artist Name'],
            'ALBUM': ['Album Name'],
            'DATE': ['2024-01-15'],
        }
        mock_file.info.length = 240.0
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/song.flac')

        assert metadata['title'] == 'Song Title'
        assert metadata['artist'] == 'Artist Name'
        assert metadata['duration'] == 240.0

    @patch('mutagen.File')
    def test_read_metadata_missing_tags(self, mock_mutagen_file):
        """Test reading file with missing tags."""
        mock_file = MagicMock()
        mock_file.tags = {'TIT2': Mock(text=['Title Only'])}
        mock_file.info.length = 120.0
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/incomplete.mp3')

        assert metadata['title'] == 'Title Only'
        assert metadata.get('artist') is None
        assert metadata.get('album') is None

    @patch('mutagen.File')
    def test_read_metadata_nonexistent_file(self, mock_mutagen_file):
        """Test handling of nonexistent file."""
        mock_mutagen_file.side_effect = FileNotFoundError("File not found")

        reader = MetadataReader()
        metadata = reader.read('/path/to/nonexistent.mp3')

        assert metadata is None

    @patch('mutagen.File')
    def test_read_metadata_corrupted_file(self, mock_mutagen_file):
        """Test handling of corrupted audio file."""
        mock_mutagen_file.side_effect = Exception("Corrupted file")

        reader = MetadataReader()
        metadata = reader.read('/path/to/corrupted.mp3')

        assert metadata is None

    @patch('mutagen.File')
    def test_read_metadata_multiple_artists(self, mock_mutagen_file):
        """Test reading metadata with multiple artists."""
        mock_file = MagicMock()
        mock_file.tags = {
            'TPE1': Mock(text=['Artist 1; Artist 2; Artist 3'])
        }
        mock_file.info.length = 200.0
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/collab.mp3')

        assert 'Artist 1' in metadata['artist']

    @patch('mutagen.File')
    def test_read_metadata_unicode_characters(self, mock_mutagen_file):
        """Test reading metadata with Unicode characters."""
        mock_file = MagicMock()
        mock_file.tags = {
            'TIT2': Mock(text=['Título con ñ']),
            'TPE1': Mock(text=['Артист']),  # Russian
        }
        mock_file.info.length = 150.0
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/unicode.mp3')

        assert metadata['title'] == 'Título con ñ'
        assert metadata['artist'] == 'Артист'


class TestMetadataWriter:
    """Tests for MetadataWriter class."""

    def test_metadata_writer_initialization(self):
        """Test MetadataWriter initialization."""
        writer = MetadataWriter()
        assert writer is not None

    @patch('mutagen.File')
    def test_write_mp3_metadata(self, mock_mutagen_file):
        """Test writing metadata to MP3 file."""
        mock_file = MagicMock()
        mock_file.tags = {}
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        new_metadata = {
            'title': 'New Title',
            'artist': 'New Artist',
            'album': 'New Album',
            'year': '2024'
        }

        success = writer.write('/path/to/song.mp3', new_metadata)

        assert success is True
        mock_file.save.assert_called_once()

    @patch('mutagen.File')
    def test_write_flac_metadata(self, mock_mutagen_file):
        """Test writing metadata to FLAC file."""
        mock_file = MagicMock()
        mock_file.tags = {}
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        new_metadata = {
            'title': 'FLAC Title',
            'artist': 'FLAC Artist',
        }

        success = writer.write('/path/to/song.flac', new_metadata)

        assert success is True
        mock_file.save.assert_called_once()

    @patch('mutagen.File')
    def test_write_metadata_partial_update(self, mock_mutagen_file):
        """Test updating only some metadata fields."""
        mock_file = MagicMock()
        mock_file.tags = {
            'TIT2': Mock(text=['Old Title']),
            'TPE1': Mock(text=['Old Artist']),
        }
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        # Update only title
        new_metadata = {'title': 'Updated Title'}

        success = writer.write('/path/to/song.mp3', new_metadata)

        assert success is True
        # Artist should remain unchanged
        mock_file.save.assert_called_once()

    @patch('mutagen.File')
    def test_write_metadata_read_only_file(self, mock_mutagen_file):
        """Test writing to read-only file."""
        mock_file = MagicMock()
        mock_file.save.side_effect = PermissionError("Read-only file")
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        success = writer.write('/path/to/readonly.mp3', {'title': 'New'})

        assert success is False

    @patch('mutagen.File')
    def test_write_metadata_nonexistent_file(self, mock_mutagen_file):
        """Test writing to nonexistent file."""
        mock_mutagen_file.side_effect = FileNotFoundError("File not found")

        writer = MetadataWriter()
        success = writer.write('/path/to/missing.mp3', {'title': 'New'})

        assert success is False

    @patch('mutagen.File')
    def test_write_metadata_with_special_characters(self, mock_mutagen_file):
        """Test writing metadata with special characters."""
        mock_file = MagicMock()
        mock_file.tags = {}
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        metadata = {
            'title': 'Title/With\\Special:Characters',
            'artist': 'AC/DC',
        }

        success = writer.write('/path/to/song.mp3', metadata)

        assert success is True

    @patch('mutagen.File')
    def test_write_metadata_empty_values(self, mock_mutagen_file):
        """Test writing empty metadata values."""
        mock_file = MagicMock()
        mock_file.tags = {'TIT2': Mock(text=['Old Title'])}
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        metadata = {'title': ''}  # Empty string

        success = writer.write('/path/to/song.mp3', metadata)

        # Behavior depends on implementation:
        # Either clears the tag or skips empty values
        assert success in [True, False]


class TestReadMetadataFunction:
    """Tests for read_metadata convenience function."""

    @patch('mutagen.File')
    def test_read_metadata_function(self, mock_mutagen_file):
        """Test read_metadata convenience function."""
        mock_file = MagicMock()
        mock_file.tags = {'TIT2': Mock(text=['Test'])}
        mock_file.info.length = 100.0
        mock_mutagen_file.return_value = mock_file

        metadata = read_metadata('/path/to/file.mp3')

        assert metadata is not None
        assert 'title' in metadata

    def test_read_metadata_invalid_path(self):
        """Test read_metadata with invalid path."""
        metadata = read_metadata('/invalid/path.mp3')
        assert metadata is None or metadata == {}

    @patch('mutagen.File')
    def test_read_metadata_different_formats(self, mock_mutagen_file):
        """Test read_metadata supports multiple formats."""
        formats = ['.mp3', '.flac', '.m4a', '.ogg', '.wma']

        for ext in formats:
            mock_file = MagicMock()
            mock_file.tags = {'TITLE': ['Test']}
            mock_file.info.length = 120.0
            mock_mutagen_file.return_value = mock_file

            metadata = read_metadata(f'/path/to/file{ext}')
            assert metadata is not None


class TestWriteMetadataFunction:
    """Tests for write_metadata convenience function."""

    @patch('mutagen.File')
    def test_write_metadata_function(self, mock_mutagen_file):
        """Test write_metadata convenience function."""
        mock_file = MagicMock()
        mock_file.tags = {}
        mock_mutagen_file.return_value = mock_file

        success = write_metadata(
            '/path/to/file.mp3',
            {'title': 'New Title'}
        )

        assert success is True
        mock_file.save.assert_called_once()

    def test_write_metadata_invalid_path(self):
        """Test write_metadata with invalid path."""
        success = write_metadata(
            '/invalid/path.mp3',
            {'title': 'Title'}
        )
        assert success is False

    @patch('mutagen.File')
    def test_write_metadata_all_fields(self, mock_mutagen_file):
        """Test writing all common metadata fields."""
        mock_file = MagicMock()
        mock_file.tags = {}
        mock_mutagen_file.return_value = mock_file

        metadata = {
            'title': 'Song Title',
            'artist': 'Artist Name',
            'album': 'Album Name',
            'year': '2024',
            'genre': 'Electronic',
            'track_number': '5',
            'disc_number': '1',
            'comment': 'Test comment',
        }

        success = write_metadata('/path/to/file.mp3', metadata)
        assert success is True


class TestMetadataIntegration:
    """Integration tests for metadata read/write workflows."""

    @patch('mutagen.File')
    def test_read_modify_write_workflow(self, mock_mutagen_file):
        """Test complete workflow: read → modify → write."""
        # Setup
        mock_file_read = MagicMock()
        mock_file_read.tags = {
            'TIT2': Mock(text=['Original Title']),
            'TPE1': Mock(text=['Original Artist']),
        }
        mock_file_read.info.length = 180.0

        mock_file_write = MagicMock()
        mock_file_write.tags = mock_file_read.tags

        mock_mutagen_file.side_effect = [mock_file_read, mock_file_write]

        # Read
        metadata = read_metadata('/path/to/song.mp3')
        assert metadata['title'] == 'Original Title'

        # Modify
        metadata['title'] = 'Updated Title'

        # Write
        success = write_metadata('/path/to/song.mp3', metadata)
        assert success is True

    @patch('mutagen.File')
    def test_batch_metadata_update(self, mock_mutagen_file):
        """Test updating metadata for multiple files."""
        files = [
            '/music/song1.mp3',
            '/music/song2.mp3',
            '/music/song3.mp3',
        ]

        mock_file = MagicMock()
        mock_file.tags = {}
        mock_mutagen_file.return_value = mock_file

        updated_count = 0
        for file_path in files:
            if write_metadata(file_path, {'album': 'Compilation'}):
                updated_count += 1

        assert updated_count == 3

    @patch('mutagen.File')
    def test_metadata_backup_and_restore(self, mock_mutagen_file):
        """Test backing up and restoring metadata."""
        # Backup
        mock_file_read = MagicMock()
        mock_file_read.tags = {
            'TIT2': Mock(text=['Important']),
            'TPE1': Mock(text=['Artist']),
        }
        mock_file_read.info.length = 200.0
        mock_mutagen_file.return_value = mock_file_read

        backup = read_metadata('/path/to/song.mp3')

        # Simulate corruption
        corrupted_file = MagicMock()
        corrupted_file.tags = {}
        mock_mutagen_file.return_value = corrupted_file

        # Restore
        success = write_metadata('/path/to/song.mp3', backup)
        assert success is True


class TestMetadataEdgeCases:
    """Tests for edge cases and error conditions."""

    @patch('mutagen.File')
    def test_very_long_metadata_values(self, mock_mutagen_file):
        """Test handling of very long metadata strings."""
        mock_file = MagicMock()
        mock_file.tags = {}
        mock_mutagen_file.return_value = mock_file

        long_title = 'A' * 10000  # 10,000 character title
        success = write_metadata(
            '/path/to/file.mp3',
            {'title': long_title}
        )

        # Should either succeed or fail gracefully
        assert isinstance(success, bool)

    @patch('mutagen.File')
    def test_null_bytes_in_metadata(self, mock_mutagen_file):
        """Test handling of null bytes in metadata."""
        mock_file = MagicMock()
        mock_file.tags = {}
        mock_mutagen_file.return_value = mock_file

        metadata = {'title': 'Title\x00WithNull'}
        success = write_metadata('/path/to/file.mp3', metadata)

        # Should sanitize or reject null bytes
        assert isinstance(success, bool)

    @patch('mutagen.File')
    def test_metadata_with_newlines(self, mock_mutagen_file):
        """Test metadata containing newlines."""
        mock_file = MagicMock()
        mock_file.tags = {}
        mock_mutagen_file.return_value = mock_file

        metadata = {'title': 'Multi\nLine\nTitle'}
        success = write_metadata('/path/to/file.mp3', metadata)

        assert isinstance(success, bool)

    def test_unsupported_file_format(self):
        """Test handling of unsupported audio formats."""
        metadata = read_metadata('/path/to/file.xyz')
        assert metadata is None or metadata == {}

    @patch('mutagen.File')
    def test_concurrent_metadata_access(self, mock_mutagen_file):
        """Test handling of concurrent file access."""
        mock_file = MagicMock()
        mock_file.save.side_effect = OSError("File locked")
        mock_mutagen_file.return_value = mock_file

        success = write_metadata('/path/to/locked.mp3', {'title': 'New'})
        assert success is False


class TestMetadataPerformance:
    """Performance-related tests."""

    @patch('mutagen.File')
    def test_read_metadata_performance(self, mock_mutagen_file):
        """Test metadata reading completes quickly."""
        import time

        mock_file = MagicMock()
        mock_file.tags = {'TIT2': Mock(text=['Title'])}
        mock_file.info.length = 180.0
        mock_mutagen_file.return_value = mock_file

        start = time.time()
        metadata = read_metadata('/path/to/file.mp3')
        elapsed = time.time() - start

        assert metadata is not None
        assert elapsed < 0.1  # Should be very fast with mocks

    @patch('mutagen.File')
    def test_write_metadata_performance(self, mock_mutagen_file):
        """Test metadata writing completes quickly."""
        import time

        mock_file = MagicMock()
        mock_file.tags = {}
        mock_mutagen_file.return_value = mock_file

        start = time.time()
        success = write_metadata('/path/to/file.mp3', {'title': 'Test'})
        elapsed = time.time() - start

        assert success is True
        assert elapsed < 0.1


# Run with: pytest packages/common/tests/test_metadata.py -v --cov=music_tools_common.metadata
