"""
Data models for quality analysis and duplicate management.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Constants
MIN_QUALITY_SCORE = 0
MAX_QUALITY_SCORE = 100
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0
MIN_BITRATE = 0
MIN_SAMPLE_RATE = 0
MIN_CHANNELS = 1
MAX_CHANNELS = 8
MIN_DURATION = 0.0
MIN_FILE_SIZE = 0

# Quality thresholds
LOSSLESS_FORMATS = {'flac', 'wav', 'aiff', 'ape', 'alac'}
HIGH_QUALITY_BITRATE = 320000  # 320 kbps
CD_QUALITY_SAMPLE_RATE = 44100  # 44.1 kHz
CD_QUALITY_BIT_DEPTH = 16
HIGH_RES_SAMPLE_RATE = 96000  # 96 kHz


@dataclass
class AudioQuality:
    """Audio file quality metrics.

    Represents comprehensive quality information for an audio file,
    including format, bitrate, sample rate, and overall quality scoring.
    """

    # File identification
    file_path: str

    # Audio format properties
    format: str  # FLAC, MP3, AAC, etc.
    bitrate: int  # in bps
    sample_rate: int  # in Hz
    bit_depth: Optional[int] = None  # Only for lossless formats
    channels: int = 2  # 1=mono, 2=stereo, etc.
    duration: float = 0.0  # in seconds

    # Quality indicators
    is_lossless: bool = False
    is_vbr: bool = False  # Variable Bitrate vs Constant Bitrate
    quality_score: int = 0  # 0-100 calculated score

    # File metadata
    file_size: int = 0  # in bytes
    last_modified: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate and normalize quality metrics.

        Raises:
            ValueError: If any quality metrics are invalid
        """
        try:
            # Normalize format to lowercase
            if self.format:
                self.format = self.format.lower().strip()

            # Validate bitrate
            if self.bitrate < MIN_BITRATE:
                raise ValueError(f"Bitrate must be >= {MIN_BITRATE}, got {self.bitrate}")

            # Validate sample rate
            if self.sample_rate < MIN_SAMPLE_RATE:
                raise ValueError(f"Sample rate must be >= {MIN_SAMPLE_RATE}, got {self.sample_rate}")

            # Validate channels
            if not MIN_CHANNELS <= self.channels <= MAX_CHANNELS:
                raise ValueError(f"Channels must be between {MIN_CHANNELS} and {MAX_CHANNELS}, got {self.channels}")

            # Validate duration
            if self.duration < MIN_DURATION:
                logger.warning(f"Duration {self.duration} is negative, setting to 0.0")
                self.duration = 0.0

            # Validate file size
            if self.file_size < MIN_FILE_SIZE:
                logger.warning(f"File size {self.file_size} is negative, setting to 0")
                self.file_size = 0

            # Validate quality score range
            if not MIN_QUALITY_SCORE <= self.quality_score <= MAX_QUALITY_SCORE:
                raise ValueError(f"Quality score must be between {MIN_QUALITY_SCORE} and {MAX_QUALITY_SCORE}, got {self.quality_score}")

            # Validate bit depth if present
            if self.bit_depth is not None and self.bit_depth <= 0:
                raise ValueError(f"Bit depth must be positive, got {self.bit_depth}")

            # Auto-detect lossless based on format if not explicitly set
            if not self.is_lossless and self.format in LOSSLESS_FORMATS:
                self.is_lossless = True

            # Set last_modified to now if not provided
            if self.last_modified is None:
                self.last_modified = datetime.now(timezone.utc)

        except Exception as e:
            logger.error(f"Error in AudioQuality.__post_init__: {e}")
            raise

    @property
    def bitrate_kbps(self) -> float:
        """Get bitrate in kilobits per second."""
        return self.bitrate / 1000.0

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)

    @property
    def is_high_quality(self) -> bool:
        """Check if audio meets high quality standards."""
        if self.is_lossless:
            return True
        return self.bitrate >= HIGH_QUALITY_BITRATE

    @property
    def is_cd_quality(self) -> bool:
        """Check if audio meets CD quality standards."""
        return (self.sample_rate >= CD_QUALITY_SAMPLE_RATE and
                (self.bit_depth is None or self.bit_depth >= CD_QUALITY_BIT_DEPTH))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage.

        Returns:
            Dictionary representation of audio quality metrics
        """
        return {
            'file_path': self.file_path,
            'format': self.format,
            'bitrate': self.bitrate,
            'sample_rate': self.sample_rate,
            'bit_depth': self.bit_depth,
            'channels': self.channels,
            'duration': self.duration,
            'is_lossless': self.is_lossless,
            'is_vbr': self.is_vbr,
            'quality_score': self.quality_score,
            'file_size': self.file_size,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioQuality':
        """Create AudioQuality instance from dictionary.

        Args:
            data: Dictionary containing audio quality data

        Returns:
            AudioQuality instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        required_fields = ['file_path', 'format', 'bitrate', 'sample_rate']
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing required field: {field_name}")

        # Parse datetime if present
        last_modified = None
        if data.get('last_modified'):
            try:
                last_modified = datetime.fromisoformat(data['last_modified'])
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse last_modified '{data.get('last_modified')}': {e}")

        return cls(
            file_path=str(data['file_path']),
            format=str(data['format']),
            bitrate=int(data['bitrate']),
            sample_rate=int(data['sample_rate']),
            bit_depth=data.get('bit_depth'),
            channels=int(data.get('channels', 2)),
            duration=float(data.get('duration', 0.0)),
            is_lossless=bool(data.get('is_lossless', False)),
            is_vbr=bool(data.get('is_vbr', False)),
            quality_score=int(data.get('quality_score', 0)),
            file_size=int(data.get('file_size', 0)),
            last_modified=last_modified,
        )


@dataclass
class DuplicateGroup:
    """Group of duplicate files with quality analysis.

    Represents a set of files identified as duplicates of the same track,
    with recommendations on which to keep based on quality metrics.
    """

    # Group identification
    id: str  # UUID
    track_hash: str  # Metadata hash for grouping

    # Duplicate files
    files: List[AudioQuality] = field(default_factory=list)

    # Recommendations
    recommended_keep: Optional[AudioQuality] = None
    recommended_delete: List[AudioQuality] = field(default_factory=list)

    # Analysis metadata
    confidence: float = 0.0  # 0.0-1.0 confidence in recommendations
    reason: str = ""  # Human-readable explanation
    space_savings: int = 0  # Bytes that would be saved
    discovered_date: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate and normalize duplicate group data.

        Raises:
            ValueError: If group data is invalid
        """
        try:
            # Generate UUID if not provided
            if not self.id:
                self.id = str(uuid.uuid4())

            # Validate confidence range
            if not MIN_CONFIDENCE <= self.confidence <= MAX_CONFIDENCE:
                raise ValueError(f"Confidence must be between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}, got {self.confidence}")

            # Validate files list
            if not self.files:
                logger.warning(f"DuplicateGroup {self.id} has no files")

            # Validate recommended_keep is in files list
            if self.recommended_keep and self.recommended_keep not in self.files:
                logger.warning(f"Recommended keep file not in files list for group {self.id}")

            # Validate all recommended_delete are in files list
            for file in self.recommended_delete:
                if file not in self.files:
                    logger.warning(f"Recommended delete file not in files list for group {self.id}")

            # Set discovered_date to now if not provided
            if self.discovered_date is None:
                self.discovered_date = datetime.now(timezone.utc)

            # Calculate space savings if not provided
            if self.space_savings == 0 and self.recommended_delete:
                self.space_savings = sum(f.file_size for f in self.recommended_delete)

        except Exception as e:
            logger.error(f"Error in DuplicateGroup.__post_init__: {e}")
            raise

    @property
    def file_count(self) -> int:
        """Get number of duplicate files in group."""
        return len(self.files)

    @property
    def total_size(self) -> int:
        """Get total size of all files in group (bytes)."""
        return sum(f.file_size for f in self.files)

    @property
    def space_savings_mb(self) -> float:
        """Get space savings in megabytes."""
        return self.space_savings / (1024 * 1024)

    @property
    def is_high_confidence(self) -> bool:
        """Check if recommendations have high confidence (>= 0.8)."""
        return self.confidence >= 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage.

        Returns:
            Dictionary representation of duplicate group
        """
        return {
            'id': self.id,
            'track_hash': self.track_hash,
            'files': [f.to_dict() for f in self.files],
            'recommended_keep': self.recommended_keep.to_dict() if self.recommended_keep else None,
            'recommended_delete': [f.to_dict() for f in self.recommended_delete],
            'confidence': self.confidence,
            'reason': self.reason,
            'space_savings': self.space_savings,
            'discovered_date': self.discovered_date.isoformat() if self.discovered_date else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DuplicateGroup':
        """Create DuplicateGroup instance from dictionary.

        Args:
            data: Dictionary containing duplicate group data

        Returns:
            DuplicateGroup instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        required_fields = ['id', 'track_hash']
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing required field: {field_name}")

        # Parse files list
        files = []
        if data.get('files'):
            try:
                files = [AudioQuality.from_dict(f) for f in data['files']]
            except Exception as e:
                logger.error(f"Failed to parse files list: {e}")
                raise ValueError(f"Invalid files data: {e}")

        # Parse recommended_keep
        recommended_keep = None
        if data.get('recommended_keep'):
            try:
                recommended_keep = AudioQuality.from_dict(data['recommended_keep'])
            except Exception as e:
                logger.warning(f"Failed to parse recommended_keep: {e}")

        # Parse recommended_delete list
        recommended_delete = []
        if data.get('recommended_delete'):
            try:
                recommended_delete = [AudioQuality.from_dict(f) for f in data['recommended_delete']]
            except Exception as e:
                logger.warning(f"Failed to parse recommended_delete: {e}")

        # Parse discovered_date
        discovered_date = None
        if data.get('discovered_date'):
            try:
                discovered_date = datetime.fromisoformat(data['discovered_date'])
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse discovered_date '{data.get('discovered_date')}': {e}")

        return cls(
            id=str(data['id']),
            track_hash=str(data['track_hash']),
            files=files,
            recommended_keep=recommended_keep,
            recommended_delete=recommended_delete,
            confidence=float(data.get('confidence', 0.0)),
            reason=str(data.get('reason', '')),
            space_savings=int(data.get('space_savings', 0)),
            discovered_date=discovered_date,
        )


@dataclass
class UpgradeCandidate:
    """Potential quality upgrade opportunity.

    Represents a file that could be replaced with a higher quality version,
    with analysis of the quality gap and available sources.
    """

    # Current file information
    current_file: AudioQuality

    # Upgrade target
    target_format: str  # FLAC, etc.
    quality_gap: int  # Difference in quality scores
    priority_score: int = 0  # 0-100 priority ranking

    # Source availability
    available_services: List[str] = field(default_factory=list)  # Spotify, Deezer, etc.
    estimated_improvement: str = ""  # Human-readable improvement description

    def __post_init__(self) -> None:
        """Validate and normalize upgrade candidate data.

        Raises:
            ValueError: If candidate data is invalid
        """
        try:
            # Normalize target format to lowercase
            if self.target_format:
                self.target_format = self.target_format.lower().strip()

            # Validate priority score range
            if not MIN_QUALITY_SCORE <= self.priority_score <= MAX_QUALITY_SCORE:
                raise ValueError(f"Priority score must be between {MIN_QUALITY_SCORE} and {MAX_QUALITY_SCORE}, got {self.priority_score}")

            # Validate quality gap
            if self.quality_gap < 0:
                logger.warning(f"Quality gap {self.quality_gap} is negative, setting to 0")
                self.quality_gap = 0

            # Generate estimated improvement if not provided
            if not self.estimated_improvement and self.quality_gap > 0:
                if self.quality_gap >= 50:
                    self.estimated_improvement = "Significant quality improvement"
                elif self.quality_gap >= 25:
                    self.estimated_improvement = "Moderate quality improvement"
                else:
                    self.estimated_improvement = "Minor quality improvement"

        except Exception as e:
            logger.error(f"Error in UpgradeCandidate.__post_init__: {e}")
            raise

    @property
    def is_high_priority(self) -> bool:
        """Check if upgrade is high priority (score >= 75)."""
        return self.priority_score >= 75

    @property
    def is_lossless_upgrade(self) -> bool:
        """Check if target is lossless format."""
        return self.target_format in LOSSLESS_FORMATS

    @property
    def has_available_sources(self) -> bool:
        """Check if any sources are available."""
        return len(self.available_services) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage.

        Returns:
            Dictionary representation of upgrade candidate
        """
        return {
            'current_file': self.current_file.to_dict(),
            'target_format': self.target_format,
            'quality_gap': self.quality_gap,
            'priority_score': self.priority_score,
            'available_services': self.available_services.copy(),
            'estimated_improvement': self.estimated_improvement,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UpgradeCandidate':
        """Create UpgradeCandidate instance from dictionary.

        Args:
            data: Dictionary containing upgrade candidate data

        Returns:
            UpgradeCandidate instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        required_fields = ['current_file', 'target_format', 'quality_gap']
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing required field: {field_name}")

        # Parse current_file
        try:
            current_file = AudioQuality.from_dict(data['current_file'])
        except Exception as e:
            logger.error(f"Failed to parse current_file: {e}")
            raise ValueError(f"Invalid current_file data: {e}")

        # Parse available_services list
        available_services = data.get('available_services', [])
        if not isinstance(available_services, list):
            logger.warning("available_services is not a list, converting to empty list")
            available_services = []

        return cls(
            current_file=current_file,
            target_format=str(data['target_format']),
            quality_gap=int(data['quality_gap']),
            priority_score=int(data.get('priority_score', 0)),
            available_services=available_services,
            estimated_improvement=str(data.get('estimated_improvement', '')),
        )
