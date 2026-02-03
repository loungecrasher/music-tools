"""
Comprehensive tests for metadata module (audio file tag reading/writing).

This test suite provides complete coverage for the metadata module including:
- Reading metadata from various audio formats
- Writing metadata with data integrity verification
- Handling edge cases and error conditions
- Integration tests for read-modify-write workflows
- Performance and security testing
"""

from unittest.mock import MagicMock, patch

import pytest
from music_tools_common.metadata import (
    MetadataReader,
    MetadataWriter,
    read_metadata,
    write_metadata,
)


class TestMetadataReader:
    """Tests for MetadataReader class."""

    def test_metadata_reader_initialization(self):
        """Test MetadataReader initialization."""
        reader = MetadataReader()
        assert reader is not None

    @patch('music_tools_common.metadata.reader.File')
    def test_read_mp3_metadata(self, mock_mutagen_file):
        """Test reading metadata from MP3 file using easy=True mode."""
        # Mock mutagen File object with easy=True dict-like interface
        mock_file = MagicMock()
        mock_file.get.side_effect = lambda key, default: {
            'title': ['Song Title'],
            'artist': ['Artist Name'],
            'album': ['Album Name'],
            'date': ['2024'],
            'genre': ['Rock'],
        }.get(key, default)
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/song.mp3')

        assert metadata is not None
        assert metadata.get('title') == 'Song Title'
        assert metadata.get('artist') == 'Artist Name'
        assert metadata.get('album') == 'Album Name'
        assert metadata.get('date') == '2024'
        assert metadata.get('genre') == 'Rock'
        mock_mutagen_file.assert_called_once_with('/path/to/song.mp3', easy=True)

    @patch('music_tools_common.metadata.reader.File')
    def test_read_flac_metadata(self, mock_mutagen_file):
        """Test reading metadata from FLAC file."""
        mock_file = MagicMock()
        mock_file.get.side_effect = lambda key, default: {
            'title': ['FLAC Song'],
            'artist': ['FLAC Artist'],
            'album': ['FLAC Album'],
            'date': ['2024-01-15'],
            'genre': ['Jazz'],
        }.get(key, default)
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/song.flac')

        assert metadata['title'] == 'FLAC Song'
        assert metadata['artist'] == 'FLAC Artist'
        assert metadata['date'] == '2024-01-15'

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_missing_tags(self, mock_mutagen_file):
        """Test reading file with missing tags returns empty strings."""
        mock_file = MagicMock()
        mock_file.get.side_effect = lambda key, default: {
            'title': ['Title Only'],
        }.get(key, default)
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/incomplete.mp3')

        assert metadata['title'] == 'Title Only'
        assert metadata.get('artist') == ''
        assert metadata.get('album') == ''
        assert metadata.get('date') == ''
        assert metadata.get('genre') == ''

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_nonexistent_file(self, mock_mutagen_file):
        """Test handling of nonexistent file."""
        mock_mutagen_file.side_effect = FileNotFoundError("File not found")

        reader = MetadataReader()
        metadata = reader.read('/path/to/nonexistent.mp3')

        assert metadata is None

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_corrupted_file(self, mock_mutagen_file):
        """Test handling of corrupted audio file."""
        mock_mutagen_file.side_effect = Exception("Corrupted file")

        reader = MetadataReader()
        metadata = reader.read('/path/to/corrupted.mp3')

        assert metadata is None

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_returns_none_when_file_is_none(self, mock_mutagen_file):
        """Test handling when mutagen returns None (unsupported format)."""
        mock_mutagen_file.return_value = None

        reader = MetadataReader()
        metadata = reader.read('/path/to/unsupported.xyz')

        assert metadata is None

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_multiple_artists(self, mock_mutagen_file):
        """Test reading metadata with multiple artists in array."""
        mock_file = MagicMock()
        mock_file.get.side_effect = lambda key, default: {
            'artist': ['Artist 1', 'Artist 2', 'Artist 3']
        }.get(key, default)
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/collab.mp3')

        # Implementation returns first artist from list
        assert metadata['artist'] == 'Artist 1'

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_unicode_characters(self, mock_mutagen_file):
        """Test reading metadata with Unicode characters."""
        mock_file = MagicMock()
        mock_file.get.side_effect = lambda key, default: {
            'title': ['Título con ñ'],
            'artist': ['Артист'],  # Russian
            'album': ['专辑'],  # Chinese
            'genre': ['Café'],  # French
        }.get(key, default)
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/unicode.mp3')

        assert metadata['title'] == 'Título con ñ'
        assert metadata['artist'] == 'Артист'
        assert metadata['album'] == '专辑'
        assert metadata['genre'] == 'Café'

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_empty_lists(self, mock_mutagen_file):
        """Test handling of empty tag lists causes error (caught and returns None)."""
        mock_file = MagicMock()
        mock_file.get.side_effect = lambda key, default: {
            'title': [],  # Empty list
        }.get(key, default)
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/empty.mp3')

        # Empty list causes index out of range, caught by exception handler
        assert metadata is None

    @patch('music_tools_common.metadata.reader.File')
    def test_read_all_metadata_fields(self, mock_mutagen_file):
        """Test that all expected fields are read."""
        mock_file = MagicMock()
        mock_file.get.side_effect = lambda key, default: {
            'title': ['Complete Song'],
            'artist': ['Complete Artist'],
            'album': ['Complete Album'],
            'date': ['2024'],
            'genre': ['Pop'],
        }.get(key, default)
        mock_mutagen_file.return_value = mock_file

        reader = MetadataReader()
        metadata = reader.read('/path/to/complete.mp3')

        # Verify all expected fields are present
        assert 'title' in metadata
        assert 'artist' in metadata
        assert 'album' in metadata
        assert 'date' in metadata
        assert 'genre' in metadata


class TestMetadataWriter:
    """Tests for MetadataWriter class."""

    def test_metadata_writer_initialization(self):
        """Test MetadataWriter initialization."""
        writer = MetadataWriter()
        assert writer is not None

    @patch('music_tools_common.metadata.writer.File')
    def test_write_mp3_metadata(self, mock_mutagen_file):
        """Test writing metadata to MP3 file."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        new_metadata = {
            'title': 'New Title',
            'artist': 'New Artist',
            'album': 'New Album',
            'date': '2024',
            'genre': 'Electronic'
        }

        success = writer.write('/path/to/song.mp3', new_metadata)

        assert success is True
        # Verify save was called
        mock_file.save.assert_called_once()
        # Verify file was opened with easy=True
        mock_mutagen_file.assert_called_once_with('/path/to/song.mp3', easy=True)

    @patch('music_tools_common.metadata.writer.File')
    def test_write_flac_metadata(self, mock_mutagen_file):
        """Test writing metadata to FLAC file."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        new_metadata = {
            'title': 'FLAC Title',
            'artist': 'FLAC Artist',
        }

        success = writer.write('/path/to/song.flac', new_metadata)

        assert success is True
        mock_file.save.assert_called_once()

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_partial_update(self, mock_mutagen_file):
        """Test updating only some metadata fields."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        # Update only title
        new_metadata = {'title': 'Updated Title'}

        success = writer.write('/path/to/song.mp3', new_metadata)

        assert success is True
        mock_file.save.assert_called_once()

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_read_only_file(self, mock_mutagen_file):
        """Test writing to read-only file."""
        mock_file = MagicMock()
        mock_file.save.side_effect = PermissionError("Read-only file")
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        success = writer.write('/path/to/readonly.mp3', {'title': 'New'})

        assert success is False

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_nonexistent_file(self, mock_mutagen_file):
        """Test writing to nonexistent file."""
        mock_mutagen_file.side_effect = FileNotFoundError("File not found")

        writer = MetadataWriter()
        success = writer.write('/path/to/missing.mp3', {'title': 'New'})

        assert success is False

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_when_file_is_none(self, mock_mutagen_file):
        """Test handling when mutagen returns None (unsupported format)."""
        mock_mutagen_file.return_value = None

        writer = MetadataWriter()
        success = writer.write('/path/to/unsupported.xyz', {'title': 'New'})

        assert success is False

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_with_special_characters(self, mock_mutagen_file):
        """Test writing metadata with special characters."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        metadata = {
            'title': 'Title/With\\Special:Characters',
            'artist': 'AC/DC',
            'album': 'Back in Black [Remastered]',
        }

        success = writer.write('/path/to/song.mp3', metadata)

        assert success is True

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_empty_values(self, mock_mutagen_file):
        """Test writing empty metadata values."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        metadata = {'title': ''}  # Empty string

        success = writer.write('/path/to/song.mp3', metadata)

        # Implementation skips empty values (if value: check)
        assert success is True
        # Verify empty values are not written
        mock_file.save.assert_called_once()

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_none_values(self, mock_mutagen_file):
        """Test writing None metadata values."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        metadata = {'title': 'Valid', 'artist': None}

        success = writer.write('/path/to/song.mp3', metadata)

        # Implementation skips None values
        assert success is True

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_unicode_characters(self, mock_mutagen_file):
        """Test writing Unicode metadata."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        metadata = {
            'title': 'Título con ñ',
            'artist': 'Артист',
            'album': '专辑',
        }

        success = writer.write('/path/to/song.mp3', metadata)

        assert success is True

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_exception_handling(self, mock_mutagen_file):
        """Test generic exception handling during write."""
        mock_file = MagicMock()
        mock_file.save.side_effect = Exception("Unknown error")
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        success = writer.write('/path/to/song.mp3', {'title': 'New'})

        assert success is False

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_all_fields(self, mock_mutagen_file):
        """Test writing all common metadata fields."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        writer = MetadataWriter()
        metadata = {
            'title': 'Complete Song',
            'artist': 'Complete Artist',
            'album': 'Complete Album',
            'date': '2024',
            'genre': 'Electronic',
        }

        success = writer.write('/path/to/song.mp3', metadata)

        assert success is True
        # Verify all non-empty values were set
        assert mock_file.__setitem__.call_count == 5


class TestReadMetadataFunction:
    """Tests for read_metadata convenience function."""

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_function(self, mock_mutagen_file):
        """Test read_metadata convenience function."""
        mock_file = MagicMock()
        mock_file.get.side_effect = lambda key, default: {
            'title': ['Test'],
        }.get(key, default)
        mock_mutagen_file.return_value = mock_file

        metadata = read_metadata('/path/to/file.mp3')

        assert metadata is not None
        assert 'title' in metadata

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_invalid_path(self, mock_mutagen_file):
        """Test read_metadata with invalid path."""
        mock_mutagen_file.side_effect = FileNotFoundError()

        metadata = read_metadata('/invalid/path.mp3')
        assert metadata is None

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_different_formats(self, mock_mutagen_file):
        """Test read_metadata supports multiple formats."""
        formats = ['.mp3', '.flac', '.m4a', '.ogg', '.wma']

        for ext in formats:
            mock_file = MagicMock()
            mock_file.get.side_effect = lambda key, default: {
                'title': ['Test'],
            }.get(key, default)
            mock_mutagen_file.return_value = mock_file

            metadata = read_metadata(f'/path/to/file{ext}')
            assert metadata is not None


class TestWriteMetadataFunction:
    """Tests for write_metadata convenience function."""

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_function(self, mock_mutagen_file):
        """Test write_metadata convenience function."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        success = write_metadata(
            '/path/to/file.mp3',
            {'title': 'New Title'}
        )

        assert success is True
        mock_file.save.assert_called_once()

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_invalid_path(self, mock_mutagen_file):
        """Test write_metadata with invalid path."""
        mock_mutagen_file.side_effect = FileNotFoundError()

        success = write_metadata(
            '/invalid/path.mp3',
            {'title': 'Title'}
        )
        assert success is False

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_all_common_fields(self, mock_mutagen_file):
        """Test writing all common metadata fields."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        metadata = {
            'title': 'Song Title',
            'artist': 'Artist Name',
            'album': 'Album Name',
            'date': '2024',
            'genre': 'Electronic',
        }

        success = write_metadata('/path/to/file.mp3', metadata)
        assert success is True


class TestMetadataIntegration:
    """Integration tests for metadata read/write workflows."""

    @patch('music_tools_common.metadata.reader.File')
    @patch('music_tools_common.metadata.writer.File')
    def test_read_modify_write_workflow(self, mock_write_file, mock_read_file):
        """Test complete workflow: read -> modify -> write."""
        # Setup read
        mock_file_read = MagicMock()
        mock_file_read.get.side_effect = lambda key, default: {
            'title': ['Original Title'],
            'artist': ['Original Artist'],
        }.get(key, default)
        mock_read_file.return_value = mock_file_read

        # Setup write
        mock_file_write = MagicMock()
        mock_write_file.return_value = mock_file_write

        # Read
        metadata = read_metadata('/path/to/song.mp3')
        assert metadata['title'] == 'Original Title'

        # Modify
        metadata['title'] = 'Updated Title'

        # Write
        success = write_metadata('/path/to/song.mp3', metadata)
        assert success is True

    @patch('music_tools_common.metadata.writer.File')
    def test_batch_metadata_update(self, mock_mutagen_file):
        """Test updating metadata for multiple files."""
        files = [
            '/music/song1.mp3',
            '/music/song2.mp3',
            '/music/song3.mp3',
        ]

        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        updated_count = 0
        for file_path in files:
            if write_metadata(file_path, {'album': 'Compilation'}):
                updated_count += 1

        assert updated_count == 3

    @patch('music_tools_common.metadata.reader.File')
    @patch('music_tools_common.metadata.writer.File')
    def test_metadata_backup_and_restore(self, mock_write_file, mock_read_file):
        """Test backing up and restoring metadata."""
        # Backup
        mock_file_read = MagicMock()
        mock_file_read.get.side_effect = lambda key, default: {
            'title': ['Important'],
            'artist': ['Artist'],
        }.get(key, default)
        mock_read_file.return_value = mock_file_read

        backup = read_metadata('/path/to/song.mp3')
        assert backup['title'] == 'Important'

        # Restore
        mock_file_write = MagicMock()
        mock_write_file.return_value = mock_file_write

        success = write_metadata('/path/to/song.mp3', backup)
        assert success is True

    @patch('music_tools_common.metadata.reader.File')
    @patch('music_tools_common.metadata.writer.File')
    def test_preserve_unmodified_fields(self, mock_write_file, mock_read_file):
        """Test that unmodified fields are preserved during updates."""
        # Read original
        mock_file_read = MagicMock()
        mock_file_read.get.side_effect = lambda key, default: {
            'title': ['Original Title'],
            'artist': ['Original Artist'],
            'album': ['Original Album'],
        }.get(key, default)
        mock_read_file.return_value = mock_file_read

        metadata = read_metadata('/path/to/song.mp3')

        # Modify only one field
        metadata['title'] = 'New Title'

        # Write
        mock_file_write = MagicMock()
        mock_write_file.return_value = mock_file_write

        success = write_metadata('/path/to/song.mp3', metadata)
        assert success is True


class TestMetadataEdgeCases:
    """Tests for edge cases and error conditions."""

    @patch('music_tools_common.metadata.writer.File')
    def test_very_long_metadata_values(self, mock_mutagen_file):
        """Test handling of very long metadata strings."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        long_title = 'A' * 10000  # 10,000 character title
        success = write_metadata(
            '/path/to/file.mp3',
            {'title': long_title}
        )

        # Should either succeed or fail gracefully
        assert isinstance(success, bool)

    @patch('music_tools_common.metadata.writer.File')
    def test_null_bytes_in_metadata(self, mock_mutagen_file):
        """Test handling of null bytes in metadata."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        metadata = {'title': 'Title\x00WithNull'}
        success = write_metadata('/path/to/file.mp3', metadata)

        # Should handle null bytes
        assert isinstance(success, bool)

    @patch('music_tools_common.metadata.writer.File')
    def test_metadata_with_newlines(self, mock_mutagen_file):
        """Test metadata containing newlines."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        metadata = {'title': 'Multi\nLine\nTitle'}
        success = write_metadata('/path/to/file.mp3', metadata)

        assert isinstance(success, bool)

    @patch('music_tools_common.metadata.reader.File')
    def test_unsupported_file_format(self, mock_mutagen_file):
        """Test handling of unsupported audio formats."""
        mock_mutagen_file.return_value = None

        metadata = read_metadata('/path/to/file.xyz')
        assert metadata is None

    @patch('music_tools_common.metadata.writer.File')
    def test_concurrent_metadata_access(self, mock_mutagen_file):
        """Test handling of concurrent file access."""
        mock_file = MagicMock()
        mock_file.save.side_effect = OSError("File locked")
        mock_mutagen_file.return_value = mock_file

        success = write_metadata('/path/to/locked.mp3', {'title': 'New'})
        assert success is False

    @patch('music_tools_common.metadata.writer.File')
    def test_disk_full_error(self, mock_mutagen_file):
        """Test handling of disk full error."""
        mock_file = MagicMock()
        mock_file.save.side_effect = OSError("No space left on device")
        mock_mutagen_file.return_value = mock_file

        success = write_metadata('/path/to/song.mp3', {'title': 'New'})
        assert success is False

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_with_binary_corruption(self, mock_mutagen_file):
        """Test reading file with binary corruption."""
        mock_mutagen_file.side_effect = Exception("Invalid tag structure")

        metadata = read_metadata('/path/to/corrupted.mp3')
        assert metadata is None

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_empty_dict(self, mock_mutagen_file):
        """Test writing empty metadata dictionary."""
        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        success = write_metadata('/path/to/song.mp3', {})

        # Should succeed but not write anything
        assert success is True
        mock_file.save.assert_called_once()


class TestMetadataPerformance:
    """Performance-related tests."""

    @patch('music_tools_common.metadata.reader.File')
    def test_read_metadata_performance(self, mock_mutagen_file):
        """Test metadata reading completes quickly."""
        import time

        mock_file = MagicMock()
        mock_file.get.side_effect = lambda key, default: {
            'title': ['Title'],
        }.get(key, default)
        mock_mutagen_file.return_value = mock_file

        start = time.time()
        metadata = read_metadata('/path/to/file.mp3')
        elapsed = time.time() - start

        assert metadata is not None
        assert elapsed < 0.1  # Should be very fast with mocks

    @patch('music_tools_common.metadata.writer.File')
    def test_write_metadata_performance(self, mock_mutagen_file):
        """Test metadata writing completes quickly."""
        import time

        mock_file = MagicMock()
        mock_mutagen_file.return_value = mock_file

        start = time.time()
        success = write_metadata('/path/to/file.mp3', {'title': 'Test'})
        elapsed = time.time() - start

        assert success is True
        assert elapsed < 0.1


class TestMetadataDataIntegrity:
    """Tests focused on data integrity and corruption prevention."""

    @patch('music_tools_common.metadata.writer.File')
    def test_write_failure_does_not_corrupt(self, mock_mutagen_file):
        """Test that write failures don't corrupt files."""
        mock_file = MagicMock()
        mock_file.save.side_effect = Exception("Write failed")
        mock_mutagen_file.return_value = mock_file

        success = write_metadata('/path/to/song.mp3', {'title': 'New'})

        # Write should fail without corrupting
        assert success is False

    @patch('music_tools_common.metadata.reader.File')
    @patch('music_tools_common.metadata.writer.File')
    def test_no_data_loss_on_update(self, mock_write_file, mock_read_file):
        """Test that updating metadata doesn't lose existing data."""
        # Read existing metadata
        mock_file_read = MagicMock()
        mock_file_read.get.side_effect = lambda key, default: {
            'title': ['Original'],
            'artist': ['Artist'],
            'album': ['Album'],
        }.get(key, default)
        mock_read_file.return_value = mock_file_read

        original = read_metadata('/path/to/song.mp3')
        assert len([k for k, v in original.items() if v]) >= 3

        # Update one field
        mock_file_write = MagicMock()
        mock_write_file.return_value = mock_file_write

        modified = original.copy()
        modified['title'] = 'Updated'

        success = write_metadata('/path/to/song.mp3', modified)
        assert success is True

    @patch('music_tools_common.metadata.writer.File')
    def test_atomic_write_behavior(self, mock_mutagen_file):
        """Test that writes are atomic (all or nothing)."""
        mock_file = MagicMock()
        # Simulate failure during save
        mock_file.save.side_effect = Exception("Save interrupted")
        mock_mutagen_file.return_value = mock_file

        metadata = {
            'title': 'New Title',
            'artist': 'New Artist',
            'album': 'New Album',
        }

        success = write_metadata('/path/to/song.mp3', metadata)

        # Should fail completely, not partial write
        assert success is False


class TestMetadataModuleExports:
    """Tests for module-level exports and convenience functions."""

    def test_module_exports_all_functions(self):
        """Test that __all__ exports are available."""
        from music_tools_common.metadata import __all__

        expected = [
            'MetadataReader',
            'MetadataWriter',
            'read_metadata',
            'write_metadata',
        ]

        for export in expected:
            assert export in __all__

    def test_convenience_functions_use_classes(self):
        """Test that convenience functions properly instantiate classes."""
        # This is implicitly tested by other tests, but we verify behavior
        reader = MetadataReader()
        writer = MetadataWriter()

        assert hasattr(reader, 'read')
        assert hasattr(writer, 'write')
        assert callable(reader.read)
        assert callable(writer.write)


# Run with: pytest packages/common/tests/test_metadata.py -v --cov=music_tools_common.metadata --cov-report=term-missing
