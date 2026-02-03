"""
Metadata Handler Module

Handles reading and writing audio file metadata using the Mutagen library.
Supports MP3, FLAC, M4A, and other common audio formats.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from mutagen import File as MutagenFile
    from mutagen.flac import FLAC
    from mutagen.id3 import ID3, TALB, TCON, TDRC, TIT1, TIT2, TPE1
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    MutagenFile = None
    MP3 = FLAC = MP4 = ID3 = None
    TIT2 = TPE1 = TALB = TDRC = TCON = TIT1 = None

logger = logging.getLogger(__name__)


class MetadataError(Exception):
    """Exception raised for metadata operations."""


class MetadataHandler:
    """
    Handler for reading and writing audio file metadata.
    """

    def __init__(self):
        """Initialize metadata handler."""
        if not MUTAGEN_AVAILABLE:
            raise MetadataError(
                "Mutagen library not available. Install with: pip install mutagen"
            )

        self.statistics = {
            'files_read': 0,
            'files_written': 0,
            'read_errors': 0,
            'write_errors': 0
        }

    def extract_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Extract metadata from audio file.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary containing metadata or None if failed
        """
        try:
            self.statistics['files_read'] += 1

            audio_file = MutagenFile(file_path)
            if audio_file is None:
                logger.warning(f"Could not read metadata from {file_path}")
                self.statistics['read_errors'] += 1
                return None

            metadata = {}

            # Extract common metadata fields
            if isinstance(audio_file, MP3):
                metadata = self._extract_mp3_metadata(audio_file)
            elif isinstance(audio_file, FLAC):
                metadata = self._extract_flac_metadata(audio_file)
            elif isinstance(audio_file, MP4):
                metadata = self._extract_mp4_metadata(audio_file)
            else:
                # Generic extraction for other formats
                metadata = self._extract_generic_metadata(audio_file)

            # Add file information
            metadata['file_path'] = file_path
            metadata['file_format'] = Path(file_path).suffix.lower()

            logger.debug(f"Extracted metadata from {file_path}: {metadata.get('artist', 'Unknown')} - {metadata.get('title', 'Unknown')}")
            return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            self.statistics['read_errors'] += 1
            return None

    def _extract_mp3_metadata(self, audio_file: MP3) -> Dict[str, Any]:
        """Extract metadata from MP3 file."""
        metadata = {}

        if audio_file.tags:
            # ID3 tags
            metadata['title'] = self._get_text_frame(audio_file.tags, 'TIT2')
            metadata['artist'] = self._get_text_frame(audio_file.tags, 'TPE1')
            metadata['album'] = self._get_text_frame(audio_file.tags, 'TALB')
            metadata['date'] = self._get_text_frame(audio_file.tags, 'TDRC')
            metadata['genre'] = self._get_text_frame(audio_file.tags, 'TCON')
            metadata['grouping'] = self._get_text_frame(audio_file.tags, 'TIT1')

        # Audio properties
        if audio_file.info:
            metadata['length'] = audio_file.info.length
            metadata['bitrate'] = audio_file.info.bitrate

        return metadata

    def _extract_flac_metadata(self, audio_file: FLAC) -> Dict[str, Any]:
        """Extract metadata from FLAC file."""
        metadata = {}

        if audio_file.tags:
            # Vorbis comments
            metadata['title'] = self._get_vorbis_field(audio_file, 'TITLE')
            metadata['artist'] = self._get_vorbis_field(audio_file, 'ARTIST')
            metadata['album'] = self._get_vorbis_field(audio_file, 'ALBUM')
            metadata['date'] = self._get_vorbis_field(audio_file, 'DATE')
            metadata['genre'] = self._get_vorbis_field(audio_file, 'GENRE')
            metadata['grouping'] = self._get_vorbis_field(audio_file, 'GROUPING')

        # Audio properties
        if audio_file.info:
            metadata['length'] = audio_file.info.length
            metadata['bitrate'] = audio_file.info.bitrate if hasattr(audio_file.info, 'bitrate') else None

        return metadata

    def _extract_mp4_metadata(self, audio_file: MP4) -> Dict[str, Any]:
        """Extract metadata from MP4/M4A file."""
        metadata = {}

        if audio_file.tags:
            # MP4 tags
            metadata['title'] = self._get_mp4_field(audio_file, '\xa9nam')
            metadata['artist'] = self._get_mp4_field(audio_file, '\xa9ART')
            metadata['album'] = self._get_mp4_field(audio_file, '\xa9alb')
            metadata['date'] = self._get_mp4_field(audio_file, '\xa9day')
            metadata['genre'] = self._get_mp4_field(audio_file, '\xa9gen')
            metadata['grouping'] = self._get_mp4_field(audio_file, '\xa9grp')

        # Audio properties
        if audio_file.info:
            metadata['length'] = audio_file.info.length
            metadata['bitrate'] = audio_file.info.bitrate

        return metadata

    def _extract_generic_metadata(self, audio_file) -> Dict[str, Any]:
        """Extract metadata from generic audio file."""
        metadata = {}

        # Try common field names
        common_fields = ['title', 'artist', 'album', 'date', 'genre', 'grouping']

        for field in common_fields:
            if hasattr(audio_file, 'tags') and audio_file.tags:
                value = audio_file.tags.get(field)
                if value:
                    if isinstance(value, list) and value:
                        metadata[field] = str(value[0])
                    else:
                        metadata[field] = str(value)

        # Audio properties
        if hasattr(audio_file, 'info') and audio_file.info:
            metadata['length'] = getattr(audio_file.info, 'length', None)
            metadata['bitrate'] = getattr(audio_file.info, 'bitrate', None)

        return metadata

    def _get_text_frame(self, tags, frame_id: str) -> Optional[str]:
        """Get text from ID3 frame."""
        frame = tags.get(frame_id)
        if frame and frame.text:
            return str(frame.text[0]) if frame.text else None
        return None

    def _get_vorbis_field(self, audio_file, field: str) -> Optional[str]:
        """Get field from Vorbis comments."""
        if audio_file.tags and field in audio_file.tags:
            value = audio_file.tags[field]
            if isinstance(value, list) and value:
                return str(value[0])
            return str(value) if value else None
        return None

    def _get_mp4_field(self, audio_file, field: str) -> Optional[str]:
        """Get field from MP4 tags."""
        if audio_file.tags and field in audio_file.tags:
            value = audio_file.tags[field]
            if isinstance(value, list) and value:
                return str(value[0])
            return str(value) if value else None
        return None

    def update_genre_field(self, file_path: str, genre: str) -> bool:
        """
        Update the genre field in audio file metadata.

        Args:
            file_path: Path to audio file
            genre: Genre string to write to genre field

        Returns:
            True if successful, False otherwise
        """
        try:
            self.statistics['files_written'] += 1

            audio_file = MutagenFile(file_path)
            if audio_file is None:
                logger.error(f"Could not open file for writing: {file_path}")
                self.statistics['write_errors'] += 1
                return False

            # Update based on file type
            if isinstance(audio_file, MP3):
                success = self._update_mp3_genre(audio_file, genre)
            elif isinstance(audio_file, FLAC):
                success = self._update_flac_genre(audio_file, genre)
            elif isinstance(audio_file, MP4):
                success = self._update_mp4_genre(audio_file, genre)
            else:
                success = self._update_generic_genre(audio_file, genre)

            if success:
                audio_file.save()
                logger.info(f"Updated genre field to '{genre}' in {file_path}")
                return True
            else:
                self.statistics['write_errors'] += 1
                return False

        except Exception as e:
            logger.error(f"Error updating genre metadata in {file_path}: {e}")
            self.statistics['write_errors'] += 1
            return False

    def update_year_field(self, file_path: str, year: str) -> bool:
        """
        Update the year field in audio file metadata.

        Args:
            file_path: Path to audio file
            year: Year string to write to year/date field

        Returns:
            True if successful, False otherwise
        """
        try:
            self.statistics['files_written'] += 1

            audio_file = MutagenFile(file_path)
            if audio_file is None:
                logger.error(f"Could not open file for writing: {file_path}")
                self.statistics['write_errors'] += 1
                return False

            # Update based on file type
            if isinstance(audio_file, MP3):
                success = self._update_mp3_year(audio_file, year)
            elif isinstance(audio_file, FLAC):
                success = self._update_flac_year(audio_file, year)
            elif isinstance(audio_file, MP4):
                success = self._update_mp4_year(audio_file, year)
            else:
                success = self._update_generic_year(audio_file, year)

            if success:
                audio_file.save()
                logger.info(f"Updated year field to '{year}' in {file_path}")
                return True
            else:
                self.statistics['write_errors'] += 1
                return False

        except Exception as e:
            logger.error(f"Error updating year metadata in {file_path}: {e}")
            self.statistics['write_errors'] += 1
            return False

    def update_grouping_field(self, file_path: str, country: str) -> bool:
        """
        Update the grouping field in audio file metadata.

        Args:
            file_path: Path to audio file
            country: Country string to write to grouping field

        Returns:
            True if successful, False otherwise
        """
        try:
            self.statistics['files_written'] += 1

            audio_file = MutagenFile(file_path)
            if audio_file is None:
                logger.error(f"Could not open file for writing: {file_path}")
                self.statistics['write_errors'] += 1
                return False

            # Update based on file type
            if isinstance(audio_file, MP3):
                success = self._update_mp3_grouping(audio_file, country)
            elif isinstance(audio_file, FLAC):
                success = self._update_flac_grouping(audio_file, country)
            elif isinstance(audio_file, MP4):
                success = self._update_mp4_grouping(audio_file, country)
            else:
                success = self._update_generic_grouping(audio_file, country)

            if success:
                audio_file.save()
                logger.info(f"Updated grouping field to '{country}' in {file_path}")
                return True
            else:
                self.statistics['write_errors'] += 1
                return False

        except Exception as e:
            logger.error(f"Error updating metadata in {file_path}: {e}")
            self.statistics['write_errors'] += 1
            return False

    def _update_mp3_genre(self, audio_file: MP3, genre: str) -> bool:
        """Update genre field in MP3 file."""
        try:
            if audio_file.tags is None:
                audio_file.add_tags()

            audio_file.tags.add(TCON(encoding=3, text=genre))
            return True

        except Exception as e:
            logger.error(f"Error updating MP3 genre: {e}")
            return False

    def _update_flac_genre(self, audio_file: FLAC, genre: str) -> bool:
        """Update genre field in FLAC file."""
        try:
            if audio_file.tags is None:
                audio_file.add_tags()

            audio_file['GENRE'] = genre
            return True

        except Exception as e:
            logger.error(f"Error updating FLAC genre: {e}")
            return False

    def _update_mp4_genre(self, audio_file: MP4, genre: str) -> bool:
        """Update genre field in MP4 file."""
        try:
            if audio_file.tags is None:
                audio_file.add_tags()

            audio_file['\xa9gen'] = genre
            return True

        except Exception as e:
            logger.error(f"Error updating MP4 genre: {e}")
            return False

    def _update_generic_genre(self, audio_file, genre: str) -> bool:
        """Update genre field in generic audio file."""
        try:
            if not hasattr(audio_file, 'tags') or audio_file.tags is None:
                return False

            audio_file.tags['genre'] = genre
            return True

        except Exception as e:
            logger.error(f"Error updating generic genre: {e}")
            return False

    def _update_mp3_year(self, audio_file: MP3, year: str) -> bool:
        """Update year field in MP3 file."""
        try:
            if audio_file.tags is None:
                audio_file.add_tags()

            audio_file.tags.add(TDRC(encoding=3, text=year))
            return True

        except Exception as e:
            logger.error(f"Error updating MP3 year: {e}")
            return False

    def _update_flac_year(self, audio_file: FLAC, year: str) -> bool:
        """Update year field in FLAC file."""
        try:
            if audio_file.tags is None:
                audio_file.add_tags()

            audio_file['DATE'] = year
            return True

        except Exception as e:
            logger.error(f"Error updating FLAC year: {e}")
            return False

    def _update_mp4_year(self, audio_file: MP4, year: str) -> bool:
        """Update year field in MP4 file."""
        try:
            if audio_file.tags is None:
                audio_file.add_tags()

            audio_file['\xa9day'] = year
            return True

        except Exception as e:
            logger.error(f"Error updating MP4 year: {e}")
            return False

    def _update_generic_year(self, audio_file, year: str) -> bool:
        """Update year field in generic audio file."""
        try:
            if not hasattr(audio_file, 'tags') or audio_file.tags is None:
                return False

            audio_file.tags['date'] = year
            return True

        except Exception as e:
            logger.error(f"Error updating generic year: {e}")
            return False

    def _update_mp3_grouping(self, audio_file: MP3, country: str) -> bool:
        """Update grouping field in MP3 file."""
        try:
            if audio_file.tags is None:
                audio_file.add_tags()

            audio_file.tags.add(TIT1(encoding=3, text=country))
            return True

        except Exception as e:
            logger.error(f"Error updating MP3 grouping: {e}")
            return False

    def _update_flac_grouping(self, audio_file: FLAC, country: str) -> bool:
        """Update grouping field in FLAC file."""
        try:
            if audio_file.tags is None:
                audio_file.add_tags()

            audio_file['GROUPING'] = country
            return True

        except Exception as e:
            logger.error(f"Error updating FLAC grouping: {e}")
            return False

    def _update_mp4_grouping(self, audio_file: MP4, country: str) -> bool:
        """Update grouping field in MP4 file."""
        try:
            if audio_file.tags is None:
                audio_file.add_tags()

            audio_file['\xa9grp'] = country
            return True

        except Exception as e:
            logger.error(f"Error updating MP4 grouping: {e}")
            return False

    def _update_generic_grouping(self, audio_file, country: str) -> bool:
        """Update grouping field in generic audio file."""
        try:
            if not hasattr(audio_file, 'tags') or audio_file.tags is None:
                return False

            audio_file.tags['grouping'] = country
            return True

        except Exception as e:
            logger.error(f"Error updating generic grouping: {e}")
            return False

    def update_metadata(self, file_path: str, updates: Dict[str, str]) -> bool:
        """
        Update multiple metadata fields in audio file.

        Args:
            file_path: Path to audio file
            updates: Dictionary of field names to values (supports 'genre', 'grouping', 'year')

        Returns:
            True if all updates successful, False if any failed
        """
        success = True

        for field, value in updates.items():
            if field == 'genre':
                if not self.update_genre_field(file_path, value):
                    success = False
            elif field == 'grouping':
                if not self.update_grouping_field(file_path, value):
                    success = False
            elif field == 'year':
                if not self.update_year_field(file_path, value):
                    success = False
            else:
                logger.warning(f"Unknown metadata field: {field}")

        return success

    def get_statistics(self) -> Dict[str, int]:
        """
        Get metadata handler statistics.

        Returns:
            Dictionary containing statistics
        """
        return self.statistics.copy()

    def reset_statistics(self):
        """Reset metadata handler statistics."""
        self.statistics = {
            'files_read': 0,
            'files_written': 0,
            'read_errors': 0,
            'write_errors': 0
        }
