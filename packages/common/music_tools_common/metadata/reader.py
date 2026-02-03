"""
Metadata reader for music files.
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from mutagen import File

logger = logging.getLogger('music_tools_common.metadata')


class MetadataReader:
    """Read metadata from music files."""

    @staticmethod
    def read(filepath: str, fallback_to_filename: bool = False) -> Optional[Dict[str, Any]]:
        """Read metadata from file with optional filename fallback.

        Args:
            filepath: Path to audio file
            fallback_to_filename: If True, parse artist/title from filename
                when tags are missing
        """
        try:
            audio = File(filepath, easy=True)
            if audio is None:
                if fallback_to_filename:
                    return MetadataReader._parse_filename(filepath)
                return None

            result = {
                'title': audio.get('title', [''])[0],
                'artist': audio.get('artist', [''])[0],
                'album': audio.get('album', [''])[0],
                'date': audio.get('date', [''])[0],
                'genre': audio.get('genre', [''])[0],
            }

            if fallback_to_filename and (not result.get('artist') or not result.get('title')):
                parsed = MetadataReader._parse_filename(filepath)
                if parsed:
                    if not result['artist']:
                        result['artist'] = parsed.get('artist', '')
                    if not result['title']:
                        result['title'] = parsed.get('title', '')

            return result
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            if fallback_to_filename:
                return MetadataReader._parse_filename(filepath)
            return None

    @staticmethod
    def _parse_filename(filepath: str) -> Optional[Dict[str, Any]]:
        """Parse artist and title from filename pattern: 'Artist - Title.ext'."""
        try:
            filename = Path(filepath).stem

            if ' - ' in filename:
                parts = filename.split(' - ', 1)
                if len(parts) == 2:
                    return {
                        'artist': parts[0].strip(),
                        'title': parts[1].strip(),
                        'album': '',
                        'date': '',
                        'genre': '',
                    }
            elif '-' in filename:
                parts = filename.split('-', 1)
                if len(parts) == 2:
                    return {
                        'artist': parts[0].strip(),
                        'title': parts[1].strip(),
                        'album': '',
                        'date': '',
                        'genre': '',
                    }
            return None
        except Exception:
            return None
