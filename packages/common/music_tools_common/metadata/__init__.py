"""
Metadata handling for music files.
"""

from typing import Any, Dict, Optional

from .reader import MetadataReader
from .writer import MetadataWriter


def read_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Read metadata from an audio file (convenience function).

    Args:
        file_path: Path to the audio file

    Returns:
        Dictionary containing metadata or None if failed

    Example:
        >>> metadata = read_metadata('/path/to/song.mp3')
        >>> if metadata:
        ...     print(f"Title: {metadata.get('title')}")
    """
    reader = MetadataReader()
    return reader.read(file_path)


def write_metadata(file_path: str, metadata: Dict[str, Any]) -> bool:
    """
    Write metadata to an audio file (convenience function).

    Args:
        file_path: Path to the audio file
        metadata: Dictionary containing metadata to write

    Returns:
        True if successful, False otherwise

    Example:
        >>> success = write_metadata('/path/to/song.mp3', {'title': 'New Title'})
        >>> if success:
        ...     print("Metadata updated successfully")
    """
    writer = MetadataWriter()
    return writer.write(file_path, metadata)


__all__ = [
    "MetadataReader",
    "MetadataWriter",
    "read_metadata",
    "write_metadata",
]
