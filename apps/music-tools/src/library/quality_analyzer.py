"""
Quality analysis for music files with production-tested algorithms.

Provides quality scoring (0-100 scale), VBR detection, and duplicate ranking
based on audio format, bitrate, sample rate, and file recency.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

try:
    from mutagen import File as MutagenFile
    from mutagen.mp3 import BitrateMode
except ImportError:
    MutagenFile = None
    BitrateMode = None

logger = logging.getLogger(__name__)

# Constants for quality scoring (0-100 scale)
MAX_QUALITY_SCORE = 100
MIN_QUALITY_SCORE = 0

# Format scoring weights (out of 100 total points)
FORMAT_WEIGHT = 40
BITRATE_WEIGHT = 30
SAMPLE_RATE_WEIGHT = 20
RECENCY_WEIGHT = 10

# Format quality scores (out of FORMAT_WEIGHT points)
FORMAT_SCORES = {
    'flac': 40,    # Lossless, widely supported
    'alac': 40,    # Lossless, Apple ecosystem
    'wav': 38,     # Lossless, uncompressed, no metadata
    'aiff': 38,    # Lossless, uncompressed, no metadata
    'ape': 37,     # Lossless, less common
    'wv': 37,      # WavPack lossless
    'tta': 37,     # True Audio lossless
    'dsd': 36,     # DSD audio (special case)
    'dsf': 36,     # DSD audio
    'aac': 22,     # Lossy, good quality
    'm4a': 22,     # AAC container
    'mp3': 20,     # Lossy, ubiquitous
    'ogg': 18,     # Lossy, Vorbis
    'opus': 18,    # Lossy, modern codec
    'wma': 15,     # Lossy, Windows format
}

# Sample rate quality thresholds
SAMPLE_RATE_HIGH = 96000      # 96kHz+ = 20pts
SAMPLE_RATE_MEDIUM = 48000    # 48kHz = 15pts
SAMPLE_RATE_STANDARD = 44100  # 44.1kHz = 10pts

# Bitrate quality threshold for lossy formats (kbps)
BITRATE_REFERENCE = 320  # 320kbps = max points for lossy

# Recency thresholds (days)
RECENCY_RECENT = 365      # < 1 year = 10pts
RECENCY_MODERATE = 1825   # 1-5 years = 5pts

# File naming normalization patterns
NORMALIZATION_PATTERNS = [
    (r'\s+', ' '),                          # Multiple spaces to single
    (r'[\[\(].*?[\]\)]', ''),              # Remove brackets and contents
    (r'[_-]+', ' '),                        # Underscores/hyphens to spaces
    (r'(?i)(320|v0|vbr|cbr|flac|mp3)', ''), # Remove format/bitrate markers
    (r'\s+', ' '),                          # Clean up spaces again
]


class BitrateType(Enum):
    """Audio bitrate encoding type."""
    CBR = "cbr"  # Constant Bitrate
    VBR = "vbr"  # Variable Bitrate
    ABR = "abr"  # Average Bitrate
    UNKNOWN = "unknown"


@dataclass
class AudioMetadata:
    """Complete audio metadata with quality indicators.

    Attributes:
        filepath: Absolute path to audio file
        format: File format (mp3, flac, etc.)
        bitrate: Bitrate in kbps (average for VBR)
        sample_rate: Sample rate in Hz
        channels: Number of audio channels
        duration: Duration in seconds
        bitrate_type: Encoding type (CBR/VBR/ABR)
        file_size: File size in bytes
        modified_time: Last modification timestamp
        is_lossless: Whether format is lossless
        quality_score: Calculated quality score (0-100)
    """

    filepath: str
    format: str
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    duration: Optional[float] = None
    bitrate_type: BitrateType = BitrateType.UNKNOWN
    file_size: int = 0
    modified_time: Optional[datetime] = None
    is_lossless: bool = False
    quality_score: int = 0

    def __post_init__(self) -> None:
        """Validate and derive properties after initialization."""
        # Validate format
        if not self.format:
            self.format = Path(self.filepath).suffix.lower().lstrip('.')

        # Determine if lossless
        lossless_formats = {'flac', 'alac', 'wav', 'aiff', 'ape', 'wv', 'tta', 'dsd', 'dsf'}
        self.is_lossless = self.format.lower() in lossless_formats

        # Validate bitrate (must be positive or None)
        if self.bitrate is not None and self.bitrate <= 0:
            logger.warning(f"Invalid bitrate {self.bitrate} for {self.filepath}, setting to None")
            self.bitrate = None

        # Validate sample rate
        if self.sample_rate is not None and self.sample_rate <= 0:
            logger.warning(f"Invalid sample_rate {self.sample_rate} for {self.filepath}, setting to None")
            self.sample_rate = None

        # Validate duration
        if self.duration is not None and self.duration < 0:
            logger.warning(f"Invalid duration {self.duration} for {self.filepath}, setting to None")
            self.duration = None

        # Calculate quality score if not already set
        if self.quality_score == 0:
            self.quality_score = calculate_quality_score(self)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'filepath': self.filepath,
            'format': self.format,
            'bitrate': self.bitrate,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'duration': self.duration,
            'bitrate_type': self.bitrate_type.value,
            'file_size': self.file_size,
            'modified_time': self.modified_time.isoformat() if self.modified_time else None,
            'is_lossless': self.is_lossless,
            'quality_score': self.quality_score,
        }


def extract_audio_metadata(filepath: str) -> Optional[AudioMetadata]:
    """Extract comprehensive audio metadata including VBR detection.

    Args:
        filepath: Path to audio file. Must not be None or empty.

    Returns:
        AudioMetadata object with all extracted properties, or None on error.

    Raises:
        ValueError: If filepath is empty or None.
        ImportError: If mutagen library is not available.

    Note:
        Includes VBR detection for MP3 files using BitrateMode.
        For other formats, bitrate_type is set to CBR or UNKNOWN.
    """
    # Input validation
    if not filepath:
        raise ValueError("filepath cannot be None or empty")

    if MutagenFile is None:
        raise ImportError("mutagen library is required for audio metadata extraction")

    try:
        # Resolve and validate path
        file_path = Path(filepath).resolve()

        if not file_path.exists():
            logger.warning(f"File does not exist: {filepath}")
            return None

        # Get file stats
        stat = file_path.stat()
        file_size = stat.st_size
        modified_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

        # Extract metadata using mutagen
        audio = MutagenFile(str(file_path))

        if audio is None or not hasattr(audio, 'info'):
            logger.warning(f"Could not read audio info from {filepath}")
            return None

        # Extract format
        file_format = file_path.suffix.lower().lstrip('.')

        # Extract basic audio properties
        bitrate = None
        sample_rate = None
        channels = None
        duration = None
        bitrate_type = BitrateType.UNKNOWN

        # Get audio info
        info = audio.info

        if hasattr(info, 'bitrate') and info.bitrate:
            bitrate = int(info.bitrate / 1000)  # Convert to kbps

        if hasattr(info, 'sample_rate') and info.sample_rate:
            sample_rate = int(info.sample_rate)

        if hasattr(info, 'channels') and info.channels:
            channels = int(info.channels)

        if hasattr(info, 'length') and info.length:
            duration = float(info.length)

        # VBR detection for MP3 files
        if file_format == 'mp3' and BitrateMode is not None:
            try:
                if hasattr(info, 'bitrate_mode'):
                    mode = info.bitrate_mode
                    if mode == BitrateMode.CBR:
                        bitrate_type = BitrateType.CBR
                    elif mode == BitrateMode.VBR:
                        bitrate_type = BitrateType.VBR
                    elif mode == BitrateMode.ABR:
                        bitrate_type = BitrateType.ABR
                    else:
                        bitrate_type = BitrateType.UNKNOWN
                else:
                    # Fallback: Check if bitrate varies (simple heuristic)
                    bitrate_type = BitrateType.UNKNOWN
            except Exception as e:
                logger.debug(f"Could not detect bitrate mode for {filepath}: {e}")
                bitrate_type = BitrateType.UNKNOWN
        else:
            # For lossless formats, bitrate type is not applicable
            # For other lossy formats, assume CBR unless we can detect otherwise
            if file_format in {'flac', 'alac', 'wav', 'aiff', 'ape', 'wv', 'tta'}:
                bitrate_type = BitrateType.UNKNOWN  # Not applicable
            else:
                bitrate_type = BitrateType.CBR  # Default assumption

        return AudioMetadata(
            filepath=str(file_path),
            format=file_format,
            bitrate=bitrate,
            sample_rate=sample_rate,
            channels=channels,
            duration=duration,
            bitrate_type=bitrate_type,
            file_size=file_size,
            modified_time=modified_time,
        )

    except Exception as e:
        logger.error(f"Error extracting metadata from {filepath}: {e}")
        return None


def calculate_quality_score(metadata: AudioMetadata) -> int:
    """Calculate quality score (0-100) based on audio properties.

    Scoring formula (production-tested from Duplicate Killer):
    - Format: Up to 40pts (FLAC/ALAC=40, WAV/AIFF=38, AAC=22, MP3=20)
    - Bitrate: Up to 30pts (lossless=30, lossy scaled to 320kbps)
    - Sample rate: Up to 20pts (96kHz+=20, 48kHz=15, 44.1kHz=10)
    - Recency: Up to 10pts (<1yr=10, 1-5yr=5, >5yr=0)

    Args:
        metadata: AudioMetadata object. Must not be None.

    Returns:
        Quality score from 0 to 100.

    Raises:
        ValueError: If metadata is None.

    Note:
        VBR encoding gets slight preference over CBR at same average bitrate.
    """
    if metadata is None:
        raise ValueError("metadata cannot be None")

    score = 0

    # 1. Format score (40 points max)
    format_key = metadata.format.lower()
    format_score = FORMAT_SCORES.get(format_key, 10)  # Default 10 for unknown
    score += format_score

    # 2. Bitrate score (30 points max)
    if metadata.is_lossless:
        # Lossless formats get full bitrate points
        bitrate_score = BITRATE_WEIGHT
    elif metadata.bitrate:
        # Lossy formats scaled to reference bitrate (320kbps)
        ratio = min(metadata.bitrate / BITRATE_REFERENCE, 1.0)
        bitrate_score = int(BITRATE_WEIGHT * ratio)

        # VBR bonus: +2 points if VBR (better quality at same bitrate)
        if metadata.bitrate_type == BitrateType.VBR:
            bitrate_score = min(bitrate_score + 2, BITRATE_WEIGHT)
    else:
        # No bitrate info, give minimal points
        bitrate_score = 5

    score += bitrate_score

    # 3. Sample rate score (20 points max)
    if metadata.sample_rate:
        if metadata.sample_rate >= SAMPLE_RATE_HIGH:
            sample_rate_score = SAMPLE_RATE_WEIGHT  # 20 points
        elif metadata.sample_rate >= SAMPLE_RATE_MEDIUM:
            sample_rate_score = 15  # 48kHz
        elif metadata.sample_rate >= SAMPLE_RATE_STANDARD:
            sample_rate_score = 10  # 44.1kHz
        else:
            # Below standard (e.g., 22kHz) gets proportional points
            ratio = metadata.sample_rate / SAMPLE_RATE_STANDARD
            sample_rate_score = int(10 * ratio)
    else:
        # No sample rate info, assume standard
        sample_rate_score = 10

    score += sample_rate_score

    # 4. Recency score (10 points max)
    if metadata.modified_time:
        now = datetime.now(timezone.utc)
        age_days = (now - metadata.modified_time).days

        if age_days < RECENCY_RECENT:
            recency_score = RECENCY_WEIGHT  # 10 points (< 1 year)
        elif age_days < RECENCY_MODERATE:
            recency_score = 5  # 5 points (1-5 years)
        else:
            recency_score = 0  # 0 points (> 5 years)
    else:
        # No timestamp, assume old
        recency_score = 0

    score += recency_score

    # Ensure score is within valid range
    return max(MIN_QUALITY_SCORE, min(score, MAX_QUALITY_SCORE))


def normalize_filename(filename: str) -> str:
    """Normalize filename for comparison.

    Removes common variations like brackets, format markers, and special characters
    to enable fuzzy matching of duplicate files with different naming conventions.

    Args:
        filename: Original filename. Can be None or empty.

    Returns:
        Normalized filename (lowercase, stripped, cleaned).
        Empty string if input is None or empty.

    Example:
        >>> normalize_filename("Song [320kbps].mp3")
        "song.mp3"
        >>> normalize_filename("Track_01-Artist_Name.flac")
        "track 01 artist name.flac"
    """
    if not filename:
        return ""

    # Convert to lowercase
    normalized = filename.lower().strip()

    # Apply normalization patterns
    for pattern, replacement in NORMALIZATION_PATTERNS:
        normalized = re.sub(pattern, replacement, normalized)

    # Final cleanup: strip and remove multiple spaces
    normalized = ' '.join(normalized.split())

    return normalized


def rank_duplicate_group(files: List[AudioMetadata]) -> Tuple[AudioMetadata, List[AudioMetadata]]:
    """Rank a group of duplicate files by quality and return best to keep.

    Uses quality scoring to determine which file to keep. In case of ties,
    prefers larger file size (may indicate better encoding).

    Args:
        files: List of AudioMetadata objects representing duplicates.
               Must not be None or empty.

    Returns:
        Tuple of (file_to_keep, files_to_delete).
        - file_to_keep: AudioMetadata with highest quality score
        - files_to_delete: List of remaining AudioMetadata objects sorted by quality

    Raises:
        ValueError: If files is None or empty.

    Example:
        >>> files = [metadata1, metadata2, metadata3]
        >>> keep, delete = rank_duplicate_group(files)
        >>> print(f"Keep: {keep.filepath} (score: {keep.quality_score})")
        >>> for f in delete:
        ...     print(f"Delete: {f.filepath} (score: {f.quality_score})")
    """
    if not files:
        raise ValueError("files cannot be None or empty")

    if len(files) == 1:
        return files[0], []

    # Sort by quality score (descending), then by file size (descending)
    sorted_files = sorted(
        files,
        key=lambda f: (f.quality_score, f.file_size),
        reverse=True
    )

    # First file is the keeper, rest are to delete
    file_to_keep = sorted_files[0]
    files_to_delete = sorted_files[1:]

    logger.info(
        f"Ranked {len(files)} duplicates: "
        f"Keep {Path(file_to_keep.filepath).name} (score: {file_to_keep.quality_score})"
    )

    return file_to_keep, files_to_delete


def compare_audio_quality(file1: AudioMetadata, file2: AudioMetadata) -> int:
    """Compare quality of two audio files.

    Args:
        file1: First AudioMetadata object. Must not be None.
        file2: Second AudioMetadata object. Must not be None.

    Returns:
        Positive integer if file1 is higher quality.
        Negative integer if file2 is higher quality.
        Zero if equal quality (uses file size as tiebreaker).

    Raises:
        ValueError: If either file is None.
    """
    if file1 is None or file2 is None:
        raise ValueError("Cannot compare None files")

    # Primary comparison: quality score
    score_diff = file1.quality_score - file2.quality_score

    if score_diff != 0:
        return score_diff

    # Tiebreaker: file size (larger is better for same quality)
    return file1.file_size - file2.file_size


def get_quality_tier(score: int) -> str:
    """Get quality tier label for a score.

    Args:
        score: Quality score (0-100).

    Returns:
        Quality tier: "Excellent", "Good", "Fair", "Poor", or "Unknown".
    """
    if score >= 80:
        return "Excellent"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Fair"
    elif score > 0:
        return "Poor"
    else:
        return "Unknown"


def analyze_duplicate_set(filepaths: List[str]) -> Dict[str, Any]:
    """Analyze a set of potential duplicates and recommend action.

    Args:
        filepaths: List of file paths to analyze. Must not be empty.

    Returns:
        Dictionary with analysis results:
        - files: List of AudioMetadata objects
        - recommended_keep: AudioMetadata to keep
        - recommended_delete: List of AudioMetadata to delete
        - quality_range: Tuple of (min_score, max_score)
        - size_saved_mb: Total MB that would be saved

    Raises:
        ValueError: If filepaths is None or empty.

    Example:
        >>> result = analyze_duplicate_set(['file1.mp3', 'file2.flac', 'file3.mp3'])
        >>> print(f"Keep: {result['recommended_keep'].filepath}")
        >>> print(f"Delete {len(result['recommended_delete'])} files")
        >>> print(f"Save {result['size_saved_mb']:.2f} MB")
    """
    if not filepaths:
        raise ValueError("filepaths cannot be None or empty")

    # Extract metadata for all files
    files_metadata = []

    for filepath in filepaths:
        try:
            metadata = extract_audio_metadata(filepath)
            if metadata:
                files_metadata.append(metadata)
        except Exception as e:
            logger.error(f"Error analyzing {filepath}: {e}")

    if not files_metadata:
        raise ValueError("No valid audio files found in provided paths")

    # Rank files
    keep, delete = rank_duplicate_group(files_metadata)

    # Calculate statistics
    scores = [f.quality_score for f in files_metadata]
    quality_range = (min(scores), max(scores))

    # Calculate space savings (MB)
    size_saved_bytes = sum(f.file_size for f in delete)
    size_saved_mb = size_saved_bytes / (1024 * 1024)

    return {
        'files': files_metadata,
        'recommended_keep': keep,
        'recommended_delete': delete,
        'quality_range': quality_range,
        'size_saved_mb': size_saved_mb,
        'total_files': len(files_metadata),
        'lossless_count': sum(1 for f in files_metadata if f.is_lossless),
        'vbr_count': sum(1 for f in files_metadata if f.bitrate_type == BitrateType.VBR),
    }
