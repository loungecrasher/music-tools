"""
Shared hashing utilities for library indexing and duplicate detection.

This module provides centralized hash calculation functions to ensure consistency
between indexing and duplicate detection operations.

Security Note:
    Uses SHA-256 for content hashing (more collision-resistant than MD5).
    Includes file size in hash to further reduce collision risk.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CHUNK_SIZE: int = 65536  # 64KB chunks for file hashing
NO_METADATA_HASH_MARKER: str = "NO_METADATA_HASH"
HASH_FAILED_MARKER: str = "HASH_FAILED"
MINIMUM_FILE_SIZE_FOR_TWO_CHUNKS: int = DEFAULT_CHUNK_SIZE * 2  # 128KB
MAX_FILE_SIZE_FOR_HASHING: int = 10 * 1024 * 1024 * 1024  # 10GB
# For content hashing, also sample from middle of file for better collision resistance
MIDDLE_CHUNK_THRESHOLD: int = DEFAULT_CHUNK_SIZE * 4  # 256KB - files larger get middle chunk


def calculate_metadata_hash(
    artist: Optional[str], title: Optional[str], filename: Optional[str] = None
) -> str:
    """Calculate MD5 hash of normalized metadata.

    Args:
        artist: Artist name (or None). Can be empty string or whitespace.
        title: Track title (or None). Can be empty string or whitespace.
        filename: Optional filename to use for generating unique hash when metadata is empty.

    Returns:
        MD5 hash as hex string. If both artist and title are empty and filename is provided,
        generates a unique hash from the filename to prevent false positive matches.

    Note:
        If both artist and title are empty:
        - With filename: Returns unique hash based on filename (prevents false matches)
        - Without filename: Returns NO_METADATA_HASH_MARKER constant

        This prevents files without metadata from incorrectly matching each other as duplicates.

    Examples:
        >>> calculate_metadata_hash("The Beatles", "Hey Jude")
        'a1b2c3d4...'
        >>> calculate_metadata_hash(None, None, "song.mp3")
        'unique_hash_based_on_filename...'
        >>> calculate_metadata_hash(None, None)
        'NO_METADATA_HASH'
    """
    # Input validation and normalization
    artist_norm = (artist or "").strip().lower()
    title_norm = (title or "").strip().lower()

    # If both empty, use filename to generate unique hash to prevent false matches
    if not artist_norm and not title_norm:
        if filename:
            # Use filename (without extension) to generate unique hash
            # This prevents all untagged files from matching each other
            filename_stem = Path(filename).stem.lower()
            metadata_key = f"NO_METADATA:{filename_stem}"
            return hashlib.md5(metadata_key.encode("utf-8")).hexdigest()
        else:
            # Fallback if no filename provided
            return NO_METADATA_HASH_MARKER

    metadata_key = f"{artist_norm}|{title_norm}"
    return hashlib.md5(metadata_key.encode("utf-8")).hexdigest()


def calculate_file_hash(file_path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Optional[str]:
    """Calculate SHA-256 hash of file content with enhanced collision resistance.

    Uses SHA-256 (more secure than MD5) and samples first, middle, and last chunks
    for files above threshold. Also incorporates file size into the hash.

    Args:
        file_path: Path to file to hash. Must be a readable file.
        chunk_size: Size of chunks to hash in bytes (default 64KB).
                   Must be positive. For files larger than 2*chunk_size,
                   multiple chunks are hashed.

    Returns:
        SHA-256 hash as hex string (includes file size prefix), or None on error
        (file not found, permission denied, or I/O error).

    Note:
        For performance, samples first, middle (for large files), and last chunks.
        File size is prepended to hash input for additional collision resistance.
        Format: {size}_{sha256_hash}

    Raises:
        ValueError: If chunk_size is not positive.
        No other exceptions raised - returns None on any error and logs warning.

    Examples:
        >>> calculate_file_hash(Path("/path/to/file.mp3"))
        '12345678_a1b2c3d4...'
        >>> calculate_file_hash(Path("/nonexistent.mp3"))
        None
    """
    # Input validation
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")

    if not isinstance(file_path, Path):
        logger.warning(f"file_path should be Path object, got {type(file_path)}")
        try:
            file_path = Path(file_path)
        except Exception as e:
            logger.error(f"Cannot convert to Path: {e}")
            return None

    try:
        file_size = file_path.stat().st_size
    except (OSError, PermissionError) as e:
        logger.warning(f"Cannot get file size for hashing {file_path}: {e}")
        return None

    # Validate file size
    if file_size < 0:
        logger.warning(f"Invalid file size {file_size} for {file_path}")
        return None

    # Check if file is too large to hash (memory protection)
    if file_size > MAX_FILE_SIZE_FOR_HASHING:
        logger.warning(
            f"File too large to hash: {file_path} ({file_size} bytes, max {MAX_FILE_SIZE_FOR_HASHING})"
        )
        return f"{file_size}_FILE_TOO_LARGE"

    # Use SHA-256 for better collision resistance
    hasher = hashlib.sha256()

    # Include file size in hash for additional collision resistance
    hasher.update(str(file_size).encode("utf-8"))

    try:
        with open(file_path, "rb") as f:
            # Hash first chunk
            first_chunk = f.read(chunk_size)
            hasher.update(first_chunk)

            # Hash middle chunk for larger files (reduces collision risk)
            if file_size >= MIDDLE_CHUNK_THRESHOLD:
                try:
                    middle_pos = file_size // 2
                    f.seek(middle_pos)
                    middle_chunk = f.read(chunk_size)
                    hasher.update(middle_chunk)
                except (OSError, IOError) as e:
                    logger.warning(f"Could not read middle chunk from {file_path}: {e}")

            # Hash last chunk if file is large enough
            if file_size >= MINIMUM_FILE_SIZE_FOR_TWO_CHUNKS:
                try:
                    f.seek(-chunk_size, 2)  # Seek to chunk_size bytes before end
                    last_chunk = f.read(chunk_size)
                    hasher.update(last_chunk)
                except (OSError, IOError) as e:
                    # Seek might fail on special files, pipes, etc.
                    logger.warning(f"Could not seek in file {file_path}: {e}")
                    # Continue with just the first chunk

        # Return hash with size prefix for additional uniqueness
        return f"{file_size}_{hasher.hexdigest()}"

    except PermissionError as e:
        logger.warning(f"Permission denied reading file {file_path}: {e}")
        return None
    except FileNotFoundError as e:
        logger.warning(f"File not found during hashing {file_path}: {e}")
        return None
    except IOError as e:
        logger.warning(f"I/O error reading file {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error hashing file {file_path}: {e}")
        return None
