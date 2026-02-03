"""
Data models for library management and duplicate detection.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Constants
METADATA_DELIMITER = "|"
MAX_PERCENTAGE = 100.0
CERTAIN_THRESHOLD = 0.95
UNCERTAIN_THRESHOLD_MIN = 0.7
MIN_VALID_YEAR = 1900
MAX_VALID_YEAR = 2100


@dataclass
class LibraryFile:
    """Represents a music file in the library index."""

    # File information
    file_path: str
    filename: str

    # Metadata
    artist: Optional[str] = None
    title: Optional[str] = None
    album: Optional[str] = None
    year: Optional[int] = None
    duration: Optional[float] = None  # in seconds

    # File properties
    file_format: str = ""  # mp3, flac, m4a, wav
    file_size: int = 0  # in bytes

    # Hashes for duplicate detection
    metadata_hash: str = ""  # MD5 of normalized artist|title
    file_content_hash: str = ""  # MD5 of file content (partial for speed)

    # Timestamps
    indexed_at: Optional[datetime] = None
    file_mtime: Optional[datetime] = None
    last_verified: Optional[datetime] = None

    # Status
    is_active: bool = True

    # Database ID (None for new records)
    id: Optional[int] = None

    def __post_init__(self) -> None:
        """Set defaults, validate, and derive properties."""
        try:
            if not self.filename and self.file_path:
                self.filename = Path(self.file_path).name
            elif not self.filename:
                self.filename = "unknown"

            if not self.file_format and self.file_path:
                self.file_format = Path(self.file_path).suffix.lower().lstrip('.')
            elif not self.file_format:
                self.file_format = ""

            # Only set indexed_at for NEW objects (when it's None and id is None)
            if self.indexed_at is None and self.id is None:
                self.indexed_at = datetime.now(timezone.utc)

            # Validate year if present (MEDIUM-4)
            if self.year is not None:
                if not (MIN_VALID_YEAR <= self.year <= MAX_VALID_YEAR):
                    logger.warning(f"Year {self.year} outside valid range {MIN_VALID_YEAR}-{MAX_VALID_YEAR}, setting to None")
                    self.year = None

            # Validate duration if present (LOW-7)
            if self.duration is not None and self.duration < 0:
                logger.warning(f"Duration {self.duration} is negative, setting to None")
                self.duration = None

        except Exception as e:
            logger.warning(f"Error in __post_init__: {e}")
            # Gracefully handle invalid paths
            if not self.filename:
                self.filename = "unknown"
            if not self.file_format:
                self.file_format = ""

    @property
    def metadata_key(self) -> str:
        """Get normalized metadata key for exact matching.

        Uses METADATA_DELIMITER to separate fields. If both artist and title
        are empty, uses filename to prevent false matches between files without metadata.
        """
        artist = (self.artist or "").strip().lower()
        title = (self.title or "").strip().lower()

        # If both are empty, use filename to avoid false matches
        if not artist and not title:
            return f"__filename__{METADATA_DELIMITER}{self.filename.lower()}"

        return f"{artist}{METADATA_DELIMITER}{title}"

    @property
    def display_name(self) -> str:
        """Get display name for UI."""
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        return self.filename

    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        if self.file_size < 0:
            return 0.0
        return self.file_size / (1024 * 1024)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage.

        Performs safe type conversions with validation to prevent data corruption.
        """
        try:
            file_size = max(0, int(self.file_size))
        except (ValueError, TypeError):
            logger.warning(f"Invalid file_size {self.file_size}, using 0")
            file_size = 0

        return {
            'id': self.id,
            'file_path': self.file_path,  # Already string, no need to convert
            'filename': self.filename,  # Already string
            'artist': self.artist,
            'title': self.title,
            'album': self.album,
            'year': self.year,
            'duration': self.duration,
            'file_format': self.file_format,  # Already string
            'file_size': file_size,
            'metadata_hash': self.metadata_hash,  # Already string
            'file_content_hash': self.file_content_hash,  # Already string
            'indexed_at': self.indexed_at.isoformat() if self.indexed_at else None,
            'file_mtime': self.file_mtime.isoformat() if self.file_mtime else None,
            'last_verified': self.last_verified.isoformat() if self.last_verified else None,
            'is_active': 1 if self.is_active else 0,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LibraryFile':
        """Create from database dictionary with comprehensive error handling."""
        # Validate required fields
        required_fields = ['file_path', 'filename', 'file_format', 'file_size',
                          'metadata_hash', 'file_content_hash']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Convert timestamps with error handling
        def safe_datetime_parse(value: Optional[str]) -> Optional[datetime]:
            """Parse ISO format datetime string safely.

            Args:
                value: ISO format datetime string or None

            Returns:
                Parsed datetime object or None if parsing fails
            """
            if not value:
                return None
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse datetime '{value}': {e}")
                return None

        indexed_at = safe_datetime_parse(data.get('indexed_at'))
        file_mtime = safe_datetime_parse(data.get('file_mtime'))
        last_verified = safe_datetime_parse(data.get('last_verified'))

        # Validate and sanitize file_size
        file_size = data.get('file_size', 0)
        try:
            file_size = max(0, int(file_size))
        except (ValueError, TypeError):
            logger.warning(f"Invalid file_size value: {file_size}, using 0")
            file_size = 0

        return cls(
            id=data.get('id'),
            file_path=str(data['file_path']),
            filename=str(data['filename']),
            artist=data.get('artist'),
            title=data.get('title'),
            album=data.get('album'),
            year=data.get('year'),
            duration=data.get('duration'),
            file_format=str(data.get('file_format', '')),
            file_size=file_size,
            metadata_hash=str(data.get('metadata_hash', '')),
            file_content_hash=str(data.get('file_content_hash', '')),
            indexed_at=indexed_at,
            file_mtime=file_mtime,
            last_verified=last_verified,
            is_active=bool(data.get('is_active', 1)),
        )


@dataclass
class DuplicateResult:
    """Result of duplicate detection for a single file.

    Attributes:
        is_duplicate: Whether file is classified as a duplicate
        confidence: Match confidence score from 0.0 to 1.0
        match_type: Type of match found (see VALID_MATCH_TYPES)
        matched_file: The specific file that matched, if any
        all_matches: List of all potential matches with their scores
    """

    is_duplicate: bool
    confidence: float  # 0.0 to 1.0
    match_type: str  # 'exact_metadata', 'fuzzy_metadata', 'exact_file', 'none'
    matched_file: Optional[LibraryFile] = None
    all_matches: List[Tuple[LibraryFile, float]] = field(default_factory=list)

    # Valid match type values
    VALID_MATCH_TYPES = {
        'exact_metadata',  # Exact match on artist|title hash
        'fuzzy_metadata',  # Fuzzy match on normalized metadata
        'exact_file',      # Exact match on file content hash
        'none'            # No match found
    }

    def __post_init__(self) -> None:
        """Validate fields after initialization.

        Raises:
            ValueError: If confidence or match_type are invalid
        """
        # Validate confidence range
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        # Validate match_type
        if self.match_type not in self.VALID_MATCH_TYPES:
            raise ValueError(f"Invalid match_type: {self.match_type}. Must be one of {self.VALID_MATCH_TYPES}")

        # Validate consistency
        if self.is_duplicate and self.confidence == 0.0:
            logger.warning("is_duplicate=True but confidence=0.0")

    @property
    def is_certain(self) -> bool:
        """Check if match is certain (confidence >= CERTAIN_THRESHOLD)."""
        return self.confidence >= CERTAIN_THRESHOLD

    @property
    def is_uncertain(self) -> bool:
        """Check if match is uncertain (UNCERTAIN_THRESHOLD_MIN <= confidence < CERTAIN_THRESHOLD)."""
        return UNCERTAIN_THRESHOLD_MIN <= self.confidence < CERTAIN_THRESHOLD

    def get_best_match(self) -> Optional[LibraryFile]:
        """Get the best matching file."""
        if self.matched_file:
            return self.matched_file
        if self.all_matches:
            return self.all_matches[0][0]
        return None


@dataclass
class VettingReport:
    """Report from vetting an import folder."""

    # Input information
    import_folder: str
    total_files: int
    threshold: float

    # Results categorization
    duplicates: List[Tuple[str, DuplicateResult]] = field(default_factory=list)
    new_songs: List[str] = field(default_factory=list)
    uncertain: List[Tuple[str, DuplicateResult]] = field(default_factory=list)

    # Statistics
    scan_duration: float = 0.0  # seconds
    vetted_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Set defaults and validate.

        Raises:
            ValueError: If any inputs are invalid
        """
        if self.vetted_at is None:
            self.vetted_at = datetime.now(timezone.utc)

        # Validate inputs
        if self.total_files < 0:
            raise ValueError(f"total_files must be non-negative, got {self.total_files}")

        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError(f"threshold must be between 0.0 and 1.0, got {self.threshold}")

        # Validate scan_duration is positive (> 0) or exactly 0 for instant scans
        if self.scan_duration < 0:
            raise ValueError(f"scan_duration must be non-negative, got {self.scan_duration}")

    @property
    def duplicate_count(self) -> int:
        """Count of certain duplicates."""
        return len(self.duplicates)

    @property
    def new_count(self) -> int:
        """Count of new songs."""
        return len(self.new_songs)

    @property
    def uncertain_count(self) -> int:
        """Count of uncertain matches."""
        return len(self.uncertain)

    @property
    def duplicate_percentage(self) -> float:
        """Percentage of duplicates (rounded to 2 decimal places).

        Returns:
            Percentage from 0.0 to MAX_PERCENTAGE (100.0)
        """
        if self.total_files == 0 or self.duplicate_count is None:
            return 0.0
        percentage = (self.duplicate_count / self.total_files) * 100
        return min(MAX_PERCENTAGE, round(percentage, 2))

    @property
    def new_percentage(self) -> float:
        """Percentage of new songs (rounded to 2 decimal places).

        Returns:
            Percentage from 0.0 to MAX_PERCENTAGE (100.0)
        """
        if self.total_files == 0 or self.new_count is None:
            return 0.0
        percentage = (self.new_count / self.total_files) * 100
        return min(MAX_PERCENTAGE, round(percentage, 2))

    def get_summary(self) -> dict:
        """Get summary statistics."""
        return {
            'import_folder': self.import_folder,
            'total_files': self.total_files,
            'duplicates': self.duplicate_count,
            'new_songs': self.new_count,
            'uncertain': self.uncertain_count,
            'duplicate_percentage': self.duplicate_percentage,
            'new_percentage': self.new_percentage,
            'threshold': self.threshold,
            'scan_duration': self.scan_duration,
            'vetted_at': self.vetted_at.isoformat() if self.vetted_at else None,
        }


@dataclass
class LibraryStatistics:
    """Statistics about the library index."""

    total_files: int = 0
    total_size: int = 0  # bytes
    formats_breakdown: dict = field(default_factory=dict)  # {format: count}
    artists_count: int = 0
    albums_count: int = 0
    last_index_time: Optional[datetime] = None
    index_duration: float = 0.0  # seconds

    @property
    def total_size_gb(self) -> float:
        """Total size in gigabytes."""
        return self.total_size / (1024 ** 3)

    @property
    def average_file_size_mb(self) -> float:
        """Average file size in megabytes."""
        if self.total_files == 0:
            return 0.0
        return (self.total_size / self.total_files) / (1024 ** 2)

    def get_format_percentages(self) -> Dict[str, float]:
        """Get percentage breakdown by format.

        Returns:
            Dictionary mapping format name to percentage (0.0-MAX_PERCENTAGE)
        """
        if self.total_files == 0:
            return {}

        percentages = {}
        for fmt, count in self.formats_breakdown.items():
            # Skip invalid counts
            if count is None or count < 0:
                continue
            percentage = (count / self.total_files) * 100
            percentages[fmt] = min(MAX_PERCENTAGE, round(percentage, 2))

        return percentages
