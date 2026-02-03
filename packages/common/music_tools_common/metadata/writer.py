"""
Metadata writer for music files.
"""
from mutagen import File
from typing import Dict, Any
import logging

logger = logging.getLogger('music_tools_common.metadata')


class MetadataWriter:
    """Write metadata to music files."""
    
    @staticmethod
    def write(filepath: str, metadata: Dict[str, Any]) -> bool:
        """Write metadata to file."""
        try:
            audio = File(filepath, easy=True)
            if audio is None:
                return False
            
            for key, value in metadata.items():
                if value:
                    audio[key] = value
            
            audio.save()
            return True
        except Exception as e:
            logger.error(f"Error writing metadata: {e}")
            return False
