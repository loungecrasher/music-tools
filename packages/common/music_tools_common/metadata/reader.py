"""
Metadata reader for music files.
"""
from mutagen import File
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger('music_tools_common.metadata')


class MetadataReader:
    """Read metadata from music files."""
    
    @staticmethod
    def read(filepath: str) -> Optional[Dict[str, Any]]:
        """Read metadata from file."""
        try:
            audio = File(filepath, easy=True)
            if audio is None:
                return None
            
            return {
                'title': audio.get('title', [''])[0],
                'artist': audio.get('artist', [''])[0],
                'album': audio.get('album', [''])[0],
                'date': audio.get('date', [''])[0],
                'genre': audio.get('genre', [''])[0],
            }
        except Exception as e:
            logger.error(f"Error reading metadata: {e}")
            return None
