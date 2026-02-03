# Quality Analysis Integration Guide

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Module Dependencies](#module-dependencies)
3. [API Reference: quality_analyzer](#api-reference-quality_analyzer)
4. [API Reference: safe_delete](#api-reference-safe_delete)
5. [API Reference: quality_models](#api-reference-quality_models)
6. [Database Schema](#database-schema)
7. [Migration Procedures](#migration-procedures)
8. [Testing Guidelines](#testing-guidelines)
9. [Code Examples](#code-examples)
10. [Best Practices](#best-practices)

---

## Architecture Overview

### System Architecture

The Smart Cleanup system is built on a modular architecture that separates concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     Smart Cleanup Workflow                  │
│                    (smart_cleanup.py)                       │
└──────────────┬──────────────────────────────────────────────┘
               │
       ┌───────┴────────┬─────────────┬──────────────┐
       │                │             │              │
       ▼                ▼             ▼              ▼
┌──────────────┐ ┌────────────┐ ┌──────────┐ ┌─────────────┐
│  Quality     │ │   Safe     │ │ Duplicate│ │  Database   │
│  Analyzer    │ │  Delete    │ │ Checker  │ │  Layer      │
│              │ │            │ │          │ │             │
└──────────────┘ └────────────┘ └──────────┘ └─────────────┘
       │                │             │              │
       ▼                ▼             ▼              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Quality Models                            │
│                  (quality_models.py)                         │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                    External Dependencies                     │
│                   (mutagen, pathlib)                         │
└──────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### Smart Cleanup Workflow
- **Purpose**: Orchestrates the entire cleanup process
- **Responsibilities**:
  - UI/UX presentation (Rich terminal interface)
  - User interaction and confirmation
  - Progress tracking and reporting
  - Session management
- **Key File**: `apps/music-tools/src/library/smart_cleanup.py`

#### Quality Analyzer
- **Purpose**: Analyzes audio file quality and ranks duplicates
- **Responsibilities**:
  - Audio metadata extraction
  - Quality score calculation (0-100 scale)
  - VBR detection
  - Duplicate group ranking
  - Filename normalization
- **Key File**: `apps/music-tools/src/library/quality_analyzer.py`

#### Safe Delete
- **Purpose**: Provides safe file deletion with comprehensive validation
- **Responsibilities**:
  - 7-point safety checklist validation
  - Backup creation and management
  - Deletion execution (dry-run and actual)
  - Detailed logging and statistics
- **Key File**: `apps/music-tools/src/library/safe_delete.py`

#### Duplicate Checker
- **Purpose**: Identifies potential duplicate files
- **Responsibilities**:
  - Metadata-based duplicate detection
  - Content hash matching
  - Fuzzy filename matching
  - Database queries for efficiency
- **Key File**: `apps/music-tools/src/library/duplicate_checker.py`

#### Quality Models
- **Purpose**: Defines data structures for quality analysis
- **Responsibilities**:
  - Type-safe data models
  - Validation and normalization
  - Serialization/deserialization
  - Quality constants and thresholds
- **Key File**: `apps/music-tools/src/library/quality_models.py`

---

## Module Dependencies

### Dependency Graph

```
smart_cleanup.py
├── quality_analyzer.py
│   ├── quality_models.py
│   └── mutagen (external)
├── safe_delete.py
│   └── pathlib (stdlib)
├── duplicate_checker.py
│   └── database.py
└── database.py
    └── sqlite3 (stdlib)
```

### Import Hierarchy

**Level 1: External Dependencies**
- `mutagen`: Audio metadata extraction
- `rich`: Terminal UI components
- `pathlib`: File path handling
- `sqlite3`: Database operations
- `dataclasses`: Data structure definitions
- `datetime`, `logging`, `json`, `csv`: Standard library

**Level 2: Quality Models**
```python
from library.quality_models import (
    AudioQuality,
    DuplicateGroup,
    UpgradeCandidate
)
```

**Level 3: Core Analysis**
```python
from library.quality_analyzer import (
    extract_audio_metadata,
    AudioMetadata,
    calculate_quality_score,
    rank_duplicate_group,
    BitrateType
)
```

**Level 4: Safety Layer**
```python
from library.safe_delete import (
    SafeDeletionPlan,
    DeletionGroup,
    DeletionValidator,
    DeletionStats
)
```

**Level 5: Workflow Orchestration**
```python
from library.smart_cleanup import (
    SmartCleanupWorkflow,
    run_smart_cleanup
)
```

### Version Requirements

```python
# requirements.txt
mutagen>=1.45.0    # Audio metadata extraction
rich>=13.0.0       # Terminal UI
```

### Optional Dependencies

```python
# For development and testing
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0
mypy>=1.0.0
```

---

## API Reference: quality_analyzer

### Module Overview

The `quality_analyzer` module provides production-tested algorithms for audio quality analysis and duplicate ranking.

### Classes

#### AudioMetadata

Complete audio metadata with quality indicators.

```python
@dataclass
class AudioMetadata:
    """Complete audio metadata with quality indicators."""

    filepath: str
    format: str
    bitrate: Optional[int] = None              # kbps
    sample_rate: Optional[int] = None          # Hz
    channels: Optional[int] = None             # 1=mono, 2=stereo
    duration: Optional[float] = None           # seconds
    bitrate_type: BitrateType = BitrateType.UNKNOWN
    file_size: int = 0                         # bytes
    modified_time: Optional[datetime] = None
    is_lossless: bool = False
    quality_score: int = 0                     # 0-100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioMetadata':
        """Create instance from dictionary."""
```

**Usage Example:**
```python
metadata = extract_audio_metadata("/path/to/song.flac")
print(f"Quality: {metadata.quality_score}/100")
print(f"Format: {metadata.format}")
print(f"Lossless: {metadata.is_lossless}")
```

#### BitrateType

Audio bitrate encoding type enumeration.

```python
class BitrateType(Enum):
    """Audio bitrate encoding type."""
    CBR = "cbr"        # Constant Bitrate
    VBR = "vbr"        # Variable Bitrate
    ABR = "abr"        # Average Bitrate
    UNKNOWN = "unknown"
```

### Functions

#### extract_audio_metadata()

Extract comprehensive audio metadata including VBR detection.

```python
def extract_audio_metadata(filepath: str) -> Optional[AudioMetadata]:
    """
    Extract comprehensive audio metadata including VBR detection.

    Args:
        filepath: Path to audio file. Must not be None or empty.

    Returns:
        AudioMetadata object with all extracted properties, or None on error.

    Raises:
        ValueError: If filepath is empty or None.
        ImportError: If mutagen library is not available.

    Example:
        >>> metadata = extract_audio_metadata("/path/to/song.mp3")
        >>> if metadata:
        ...     print(f"Bitrate: {metadata.bitrate} kbps")
        ...     print(f"Type: {metadata.bitrate_type.value}")
    """
```

**Usage:**
```python
from library.quality_analyzer import extract_audio_metadata

# Extract metadata
metadata = extract_audio_metadata("/music/song.flac")

if metadata:
    print(f"File: {metadata.filepath}")
    print(f"Format: {metadata.format}")
    print(f"Quality Score: {metadata.quality_score}/100")
    print(f"Bitrate: {metadata.bitrate} kbps ({metadata.bitrate_type.value})")
    print(f"Sample Rate: {metadata.sample_rate} Hz")
    print(f"Lossless: {metadata.is_lossless}")
else:
    print("Failed to extract metadata")
```

#### calculate_quality_score()

Calculate quality score (0-100) based on audio properties.

```python
def calculate_quality_score(metadata: AudioMetadata) -> int:
    """
    Calculate quality score (0-100) based on audio properties.

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
        VBR encoding gets slight preference (+2 points) over CBR
        at same average bitrate.
    """
```

**Scoring Breakdown:**

| Component | Max Points | Criteria |
|-----------|-----------|----------|
| Format | 40 | FLAC/ALAC=40, WAV=38, MP3=20, etc. |
| Bitrate | 30 | Lossless=30, lossy scaled to 320kbps |
| Sample Rate | 20 | 96kHz+=20, 48kHz=15, 44.1kHz=10 |
| Recency | 10 | <1yr=10, 1-5yr=5, >5yr=0 |
| VBR Bonus | +2 | VBR files get +2 points |

**Usage:**
```python
from library.quality_analyzer import extract_audio_metadata, calculate_quality_score

metadata = extract_audio_metadata("/music/song.mp3")
score = calculate_quality_score(metadata)

if score >= 80:
    print("Excellent quality")
elif score >= 60:
    print("Good quality")
elif score >= 40:
    print("Fair quality")
else:
    print("Poor quality")
```

#### rank_duplicate_group()

Rank a group of duplicate files by quality and return best to keep.

```python
def rank_duplicate_group(
    files: List[AudioMetadata]
) -> Tuple[AudioMetadata, List[AudioMetadata]]:
    """
    Rank a group of duplicate files by quality and return best to keep.

    Uses quality scoring to determine which file to keep. In case of ties,
    prefers larger file size (may indicate better encoding).

    Args:
        files: List of AudioMetadata objects representing duplicates.
               Must not be None or empty.

    Returns:
        Tuple of (file_to_keep, files_to_delete).
        - file_to_keep: AudioMetadata with highest quality score
        - files_to_delete: List of remaining AudioMetadata objects
          sorted by quality (highest to lowest)

    Raises:
        ValueError: If files is None or empty.

    Example:
        >>> files = [metadata1, metadata2, metadata3]
        >>> keep, delete = rank_duplicate_group(files)
        >>> print(f"Keep: {keep.filepath} (score: {keep.quality_score})")
        >>> for f in delete:
        ...     print(f"Delete: {f.filepath} (score: {f.quality_score})")
    """
```

**Usage:**
```python
from library.quality_analyzer import extract_audio_metadata, rank_duplicate_group

# Extract metadata for duplicate files
duplicates = [
    extract_audio_metadata("/music/song.flac"),
    extract_audio_metadata("/music/song.mp3"),
    extract_audio_metadata("/music/song_copy.mp3")
]

# Rank them
keep, delete = rank_duplicate_group(duplicates)

print(f"KEEP: {keep.filepath} (quality: {keep.quality_score}/100)")
for file in delete:
    print(f"DELETE: {file.filepath} (quality: {file.quality_score}/100)")
```

#### compare_audio_quality()

Compare quality of two audio files.

```python
def compare_audio_quality(file1: AudioMetadata, file2: AudioMetadata) -> int:
    """
    Compare quality of two audio files.

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
```

**Usage:**
```python
from library.quality_analyzer import extract_audio_metadata, compare_audio_quality

file1 = extract_audio_metadata("/music/song_v1.mp3")
file2 = extract_audio_metadata("/music/song_v2.mp3")

result = compare_audio_quality(file1, file2)
if result > 0:
    print("File 1 is higher quality")
elif result < 0:
    print("File 2 is higher quality")
else:
    print("Equal quality (file 1 is larger)")
```

#### get_quality_tier()

Get quality tier label for a score.

```python
def get_quality_tier(score: int) -> str:
    """
    Get quality tier label for a score.

    Args:
        score: Quality score (0-100).

    Returns:
        Quality tier: "Excellent", "Good", "Fair", "Poor", or "Unknown".
    """
```

**Quality Tiers:**
- **Excellent**: 80-100 (FLAC, high-bitrate lossless)
- **Good**: 60-79 (320kbps MP3, high-quality AAC)
- **Fair**: 40-59 (128-256kbps MP3)
- **Poor**: 1-39 (<128kbps)
- **Unknown**: 0 (no data)

#### normalize_filename()

Normalize filename for comparison.

```python
def normalize_filename(filename: str) -> str:
    """
    Normalize filename for comparison.

    Removes common variations like brackets, format markers, and
    special characters to enable fuzzy matching of duplicate files
    with different naming conventions.

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
```

**Normalization rules:**
1. Convert to lowercase
2. Multiple spaces → single space
3. Remove brackets and contents: `[320kbps]`, `(VBR)`, etc.
4. Underscores/hyphens → spaces
5. Remove format/bitrate markers: `320`, `v0`, `vbr`, `flac`, etc.
6. Strip and clean whitespace

#### analyze_duplicate_set()

Analyze a set of potential duplicates and recommend action.

```python
def analyze_duplicate_set(filepaths: List[str]) -> Dict[str, Any]:
    """
    Analyze a set of potential duplicates and recommend action.

    Args:
        filepaths: List of file paths to analyze. Must not be empty.

    Returns:
        Dictionary with analysis results:
        {
            'files': List[AudioMetadata],
            'recommended_keep': AudioMetadata,
            'recommended_delete': List[AudioMetadata],
            'quality_range': Tuple[int, int],  # (min_score, max_score)
            'size_saved_mb': float,
            'total_files': int,
            'lossless_count': int,
            'vbr_count': int
        }

    Raises:
        ValueError: If filepaths is None or empty.
    """
```

**Usage:**
```python
from library.quality_analyzer import analyze_duplicate_set

# Analyze a set of duplicates
result = analyze_duplicate_set([
    '/music/song.flac',
    '/music/song.mp3',
    '/music/song_copy.mp3'
])

print(f"Keep: {result['recommended_keep'].filepath}")
print(f"Delete {len(result['recommended_delete'])} files")
print(f"Save {result['size_saved_mb']:.2f} MB")
print(f"Quality range: {result['quality_range'][0]}-{result['quality_range'][1]}")
print(f"Lossless files: {result['lossless_count']}")
print(f"VBR files: {result['vbr_count']}")
```

### Constants

```python
# Quality scoring constants
MAX_QUALITY_SCORE = 100
MIN_QUALITY_SCORE = 0

# Scoring weights
FORMAT_WEIGHT = 40
BITRATE_WEIGHT = 30
SAMPLE_RATE_WEIGHT = 20
RECENCY_WEIGHT = 10

# Format scores
FORMAT_SCORES = {
    'flac': 40, 'alac': 40, 'wav': 38, 'aiff': 38,
    'ape': 37, 'wv': 37, 'tta': 37, 'dsd': 36, 'dsf': 36,
    'aac': 22, 'm4a': 22, 'mp3': 20, 'ogg': 18, 'opus': 18, 'wma': 15
}

# Sample rate thresholds
SAMPLE_RATE_HIGH = 96000      # 96kHz+
SAMPLE_RATE_MEDIUM = 48000    # 48kHz
SAMPLE_RATE_STANDARD = 44100  # 44.1kHz (CD quality)

# Bitrate reference
BITRATE_REFERENCE = 320  # 320kbps for lossy scaling

# Recency thresholds (days)
RECENCY_RECENT = 365      # < 1 year
RECENCY_MODERATE = 1825   # 1-5 years
```

---

## API Reference: safe_delete

### Module Overview

The `safe_delete` module provides safe file deletion with comprehensive validation, backup functionality, and dry-run capabilities.

### Classes

#### ValidationLevel

Validation severity levels.

```python
class ValidationLevel(Enum):
    """Validation severity levels."""
    ERROR = "error"      # Blocks deletion
    WARNING = "warning"  # Allows deletion with warning
    INFO = "info"        # Informational only
```

#### ValidationResult

Result of a validation check.

```python
@dataclass
class ValidationResult:
    """Result of a validation check."""
    level: ValidationLevel
    checkpoint: str                    # e.g., "1. Keep File Exists"
    message: str                       # Human-readable message
    details: Optional[Dict[str, Any]] = None

    def is_blocking(self) -> bool:
        """Check if this validation result should block deletion."""
        return self.level == ValidationLevel.ERROR
```

#### DeletionGroup

Represents a group of files where one is kept and others are deleted.

```python
@dataclass
class DeletionGroup:
    """Represents a group of files where one is kept and others are deleted."""

    keep_file: str                              # File to preserve
    delete_files: List[str]                     # Files to delete
    reason: str                                 # Explanation
    validation_results: List[ValidationResult] = field(default_factory=list)
    group_id: Optional[str] = None              # Auto-generated

    def is_valid(self) -> bool:
        """Check if group passes all validations."""

    def get_errors(self) -> List[ValidationResult]:
        """Get all error-level validation results."""

    def get_warnings(self) -> List[ValidationResult]:
        """Get all warning-level validation results."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
```

**Usage:**
```python
from library.safe_delete import DeletionGroup

group = DeletionGroup(
    keep_file="/music/song.flac",
    delete_files=["/music/song.mp3", "/music/song_copy.mp3"],
    reason="Keep highest quality FLAC"
)

print(f"Group ID: {group.group_id}")
print(f"Keep: {group.keep_file}")
print(f"Delete: {len(group.delete_files)} files")
```

#### DeletionStats

Statistics from deletion operation.

```python
@dataclass
class DeletionStats:
    """Statistics from deletion operation."""

    total_groups: int = 0
    successful_deletions: int = 0
    failed_deletions: int = 0
    files_deleted: int = 0
    files_failed: int = 0
    space_freed_bytes: int = 0
    backup_created: bool = False
    backup_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""

    def __str__(self) -> str:
        """Human-readable statistics."""
```

#### DeletionValidator

Implements 7-point safety checklist for file deletions.

```python
class DeletionValidator:
    """
    Implements 7-point safety checklist for file deletions.

    Safety Checklist:
    1. Keep file must exist
    2. Must have files to delete (not empty)
    3. Warn if deleting higher bitrate
    4. Verify delete files exist
    5. Never delete all files in group
    6. Check file permissions
    7. Validate sufficient disk space for backup
    """

    def validate_group(
        self,
        group: DeletionGroup,
        check_backup_space: bool = True
    ) -> List[ValidationResult]:
        """
        Run all validation checks on a deletion group.

        Args:
            group: DeletionGroup to validate
            check_backup_space: Whether to check disk space for backup

        Returns:
            List of ValidationResult objects
        """
```

**Usage:**
```python
from library.safe_delete import DeletionValidator, DeletionGroup

validator = DeletionValidator()
group = DeletionGroup(
    keep_file="/music/song.flac",
    delete_files=["/music/song.mp3"],
    reason="Quality upgrade"
)

results = validator.validate_group(group)

for result in results:
    if result.level == ValidationLevel.ERROR:
        print(f"ERROR: {result.message}")
    elif result.level == ValidationLevel.WARNING:
        print(f"WARNING: {result.message}")
    else:
        print(f"INFO: {result.message}")

if group.is_valid():
    print("Group passed validation")
else:
    print("Group failed validation")
    for error in group.get_errors():
        print(f"  - {error.message}")
```

#### SafeDeletionPlan

Manages a plan for safely deleting duplicate files.

```python
class SafeDeletionPlan:
    """
    Manages a plan for safely deleting duplicate files.

    Features:
    - Group-based deletion management
    - Comprehensive validation
    - Backup functionality
    - Dry-run capability
    - Detailed logging and statistics
    """

    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize a safe deletion plan.

        Args:
            backup_dir: Optional directory for backing up files
                       before deletion
        """

    def add_group(
        self,
        keep_file: str,
        delete_files: List[str],
        reason: str = ""
    ) -> DeletionGroup:
        """
        Add a deletion group to the plan.

        Args:
            keep_file: Path to the file to keep
            delete_files: List of file paths to delete
            reason: Reason for this deletion group

        Returns:
            The created DeletionGroup
        """

    def validate(
        self,
        check_backup_space: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate all deletion groups.

        Args:
            check_backup_space: Whether to check disk space for backups

        Returns:
            Tuple of (is_valid, list_of_errors)
        """

    def execute(
        self,
        dry_run: bool = False,
        create_backup: bool = True
    ) -> DeletionStats:
        """
        Execute the deletion plan.

        Args:
            dry_run: If True, simulate deletion without actually
                    deleting files
            create_backup: If True, backup files before deletion

        Returns:
            DeletionStats object with operation results
        """

    def export_to_json(self, filepath: str) -> None:
        """
        Export the deletion plan to a JSON file.

        Args:
            filepath: Path where JSON file should be saved
        """
```

**Complete Example:**
```python
from library.safe_delete import SafeDeletionPlan

# Create plan with backup directory
plan = SafeDeletionPlan(backup_dir="/music/.backups")

# Add deletion groups
plan.add_group(
    keep_file="/music/album1/song1.flac",
    delete_files=["/music/album1/song1.mp3", "/music/album1/song1_copy.mp3"],
    reason="Keep FLAC, remove MP3 duplicates"
)

plan.add_group(
    keep_file="/music/album2/song2.flac",
    delete_files=["/music/album2/song2.mp3"],
    reason="Quality upgrade to FLAC"
)

# Validate plan
is_valid, errors = plan.validate()
if not is_valid:
    print("Validation failed:")
    for error in errors:
        print(f"  - {error}")
    exit(1)

# Execute with dry-run first
print("=== Dry Run ===")
dry_stats = plan.execute(dry_run=True, create_backup=False)
print(dry_stats)
print(f"Would delete {dry_stats.files_deleted} files")
print(f"Would save {dry_stats.space_freed_bytes / (1024**3):.2f} GB")

# Confirm and execute for real
confirm = input("Proceed with actual deletion? (yes/no): ")
if confirm.lower() == 'yes':
    print("=== Actual Deletion ===")
    stats = plan.execute(dry_run=False, create_backup=True)
    print(stats)
    print(f"Deleted {stats.files_deleted} files")
    print(f"Freed {stats.space_freed_bytes / (1024**3):.2f} GB")
    print(f"Backup created at: {stats.backup_path}")

    # Export plan for records
    plan.export_to_json("/music/.backups/deletion_plan.json")
else:
    print("Deletion cancelled")
```

### Convenience Functions

#### create_deletion_plan()

Create a new safe deletion plan.

```python
def create_deletion_plan(backup_dir: Optional[str] = None) -> SafeDeletionPlan:
    """
    Create a new safe deletion plan.

    Args:
        backup_dir: Optional directory for file backups

    Returns:
        New SafeDeletionPlan instance
    """
```

#### validate_deletion()

Quick validation of a single deletion operation.

```python
def validate_deletion(
    keep_file: str,
    delete_files: List[str]
) -> Tuple[bool, List[str]]:
    """
    Quick validation of a single deletion operation.

    Args:
        keep_file: File to keep
        delete_files: Files to delete

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
```

**Usage:**
```python
from library.safe_delete import validate_deletion

is_valid, errors = validate_deletion(
    keep_file="/music/song.flac",
    delete_files=["/music/song.mp3", "/music/song_copy.mp3"]
)

if is_valid:
    print("Safe to delete")
else:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
```

---

## API Reference: quality_models

### Module Overview

The `quality_models` module defines data structures for quality analysis with validation and serialization support.

### Classes

#### AudioQuality

Audio file quality metrics.

```python
@dataclass
class AudioQuality:
    """
    Audio file quality metrics.

    Represents comprehensive quality information for an audio file,
    including format, bitrate, sample rate, and overall quality scoring.
    """

    # File identification
    file_path: str

    # Audio format properties
    format: str                        # FLAC, MP3, AAC, etc.
    bitrate: int                       # in bps
    sample_rate: int                   # in Hz
    bit_depth: Optional[int] = None    # Only for lossless formats
    channels: int = 2                  # 1=mono, 2=stereo, etc.
    duration: float = 0.0              # in seconds

    # Quality indicators
    is_lossless: bool = False
    is_vbr: bool = False               # Variable Bitrate
    quality_score: int = 0             # 0-100 calculated score

    # File metadata
    file_size: int = 0                 # in bytes
    last_modified: Optional[datetime] = None

    @property
    def bitrate_kbps(self) -> float:
        """Get bitrate in kilobits per second."""

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""

    @property
    def is_high_quality(self) -> bool:
        """Check if audio meets high quality standards."""

    @property
    def is_cd_quality(self) -> bool:
        """Check if audio meets CD quality standards."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AudioQuality':
        """Create AudioQuality instance from dictionary."""
```

**Usage:**
```python
from library.quality_models import AudioQuality
from datetime import datetime, timezone

quality = AudioQuality(
    file_path="/music/song.flac",
    format="flac",
    bitrate=1411000,  # ~1411 kbps for CD FLAC
    sample_rate=44100,
    bit_depth=16,
    channels=2,
    duration=245.3,
    is_lossless=True,
    is_vbr=False,
    quality_score=95,
    file_size=42_500_000,
    last_modified=datetime.now(timezone.utc)
)

print(f"Bitrate: {quality.bitrate_kbps} kbps")
print(f"Size: {quality.file_size_mb:.2f} MB")
print(f"High Quality: {quality.is_high_quality}")
print(f"CD Quality: {quality.is_cd_quality}")

# Serialize
data = quality.to_dict()
# ... save to database or JSON ...

# Deserialize
restored = AudioQuality.from_dict(data)
```

#### DuplicateGroup

Group of duplicate files with quality analysis.

```python
@dataclass
class DuplicateGroup:
    """
    Group of duplicate files with quality analysis.

    Represents a set of files identified as duplicates of the same track,
    with recommendations on which to keep based on quality metrics.
    """

    # Group identification
    id: str                                    # UUID
    track_hash: str                            # Metadata hash for grouping

    # Duplicate files
    files: List[AudioQuality] = field(default_factory=list)

    # Recommendations
    recommended_keep: Optional[AudioQuality] = None
    recommended_delete: List[AudioQuality] = field(default_factory=list)

    # Analysis metadata
    confidence: float = 0.0                    # 0.0-1.0 confidence
    reason: str = ""                           # Human-readable explanation
    space_savings: int = 0                     # Bytes that would be saved
    discovered_date: Optional[datetime] = None

    @property
    def file_count(self) -> int:
        """Get number of duplicate files in group."""

    @property
    def total_size(self) -> int:
        """Get total size of all files in group (bytes)."""

    @property
    def space_savings_mb(self) -> float:
        """Get space savings in megabytes."""

    @property
    def is_high_confidence(self) -> bool:
        """Check if recommendations have high confidence (>= 0.8)."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DuplicateGroup':
        """Create DuplicateGroup instance from dictionary."""
```

**Usage:**
```python
from library.quality_models import DuplicateGroup, AudioQuality
import uuid

# Create a duplicate group
group = DuplicateGroup(
    id=str(uuid.uuid4()),
    track_hash="artist_title_album_hash",
    files=[quality1, quality2, quality3],  # AudioQuality objects
    recommended_keep=quality1,
    recommended_delete=[quality2, quality3],
    confidence=0.95,
    reason="FLAC is highest quality, remove MP3 duplicates",
    space_savings=17_000_000  # bytes
)

print(f"Group: {group.id}")
print(f"Files: {group.file_count}")
print(f"Total Size: {group.total_size / (1024**2):.2f} MB")
print(f"Savings: {group.space_savings_mb:.2f} MB")
print(f"High Confidence: {group.is_high_confidence}")
print(f"Reason: {group.reason}")
```

#### UpgradeCandidate

Potential quality upgrade opportunity.

```python
@dataclass
class UpgradeCandidate:
    """
    Potential quality upgrade opportunity.

    Represents a file that could be replaced with a higher quality version,
    with analysis of the quality gap and available sources.
    """

    # Current file information
    current_file: AudioQuality

    # Upgrade target
    target_format: str                         # FLAC, etc.
    quality_gap: int                           # Difference in quality scores
    priority_score: int = 0                    # 0-100 priority ranking

    # Source availability
    available_services: List[str] = field(default_factory=list)
    estimated_improvement: str = ""

    @property
    def is_high_priority(self) -> bool:
        """Check if upgrade is high priority (score >= 75)."""

    @property
    def is_lossless_upgrade(self) -> bool:
        """Check if target is lossless format."""

    @property
    def has_available_sources(self) -> bool:
        """Check if any sources are available."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UpgradeCandidate':
        """Create UpgradeCandidate instance from dictionary."""
```

**Usage:**
```python
from library.quality_models import UpgradeCandidate, AudioQuality

# Current low-quality file
current = AudioQuality(
    file_path="/music/song.mp3",
    format="mp3",
    bitrate=128000,
    sample_rate=44100,
    quality_score=42
)

# Potential upgrade
upgrade = UpgradeCandidate(
    current_file=current,
    target_format="flac",
    quality_gap=53,  # 95 (FLAC) - 42 (MP3)
    priority_score=85,
    available_services=["Spotify", "Tidal", "Qobuz"],
    estimated_improvement="Significant quality improvement from lossy to lossless"
)

print(f"Current: {upgrade.current_file.format} @ {upgrade.current_file.quality_score}/100")
print(f"Target: {upgrade.target_format}")
print(f"Quality Gap: {upgrade.quality_gap} points")
print(f"High Priority: {upgrade.is_high_priority}")
print(f"Lossless Upgrade: {upgrade.is_lossless_upgrade}")
print(f"Available from: {', '.join(upgrade.available_services)}")
```

### Constants

```python
# Quality score bounds
MIN_QUALITY_SCORE = 0
MAX_QUALITY_SCORE = 100

# Confidence bounds
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0

# Audio property bounds
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
```

---

## Database Schema

### Overview

The Music Tools database uses SQLite with a normalized schema for efficient storage and querying of music library metadata.

### Entity Relationship Diagram

```
┌──────────────────┐       ┌──────────────────┐
│  library_files   │───┬───│  artists         │
│                  │   │   │                  │
│  id (PK)         │   │   │  id (PK)         │
│  file_path       │   │   │  name            │
│  artist_id (FK)  │───┘   └──────────────────┘
│  album_id (FK)   │───┐
│  title           │   │   ┌──────────────────┐
│  duration        │   └───│  albums          │
│  bitrate         │       │                  │
│  sample_rate     │       │  id (PK)         │
│  format          │       │  name            │
│  file_size       │       │  artist_id (FK)  │
│  metadata_hash   │       └──────────────────┘
│  content_hash    │
│  quality_score   │
│  bitrate_type    │
│  is_lossless     │
│  created_at      │
│  updated_at      │
└──────────────────┘
```

### Table: library_files

Stores comprehensive metadata for each audio file.

```sql
CREATE TABLE library_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,

    -- Relationships
    artist_id INTEGER,
    album_id INTEGER,

    -- Metadata
    title TEXT,
    track_number INTEGER,
    disc_number INTEGER,
    year INTEGER,
    genre TEXT,

    -- Audio properties
    duration REAL,           -- seconds
    bitrate INTEGER,         -- bps
    sample_rate INTEGER,     -- Hz
    bit_depth INTEGER,       -- bits (for lossless)
    channels INTEGER,        -- 1=mono, 2=stereo
    format TEXT,             -- flac, mp3, aac, etc.

    -- File properties
    file_size INTEGER,       -- bytes
    modified_time TIMESTAMP,

    -- Quality analysis
    quality_score INTEGER,   -- 0-100
    bitrate_type TEXT,       -- cbr, vbr, abr, unknown
    is_lossless BOOLEAN,

    -- Duplicate detection
    metadata_hash TEXT,      -- hash of artist+title+album
    content_hash TEXT,       -- MD5 of file content

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (artist_id) REFERENCES artists(id),
    FOREIGN KEY (album_id) REFERENCES albums(id)
);

-- Indexes for performance
CREATE INDEX idx_library_files_artist_id ON library_files(artist_id);
CREATE INDEX idx_library_files_album_id ON library_files(album_id);
CREATE INDEX idx_library_files_metadata_hash ON library_files(metadata_hash);
CREATE INDEX idx_library_files_content_hash ON library_files(content_hash);
CREATE INDEX idx_library_files_quality_score ON library_files(quality_score);
CREATE INDEX idx_library_files_format ON library_files(format);
```

### Table: artists

Stores unique artists.

```sql
CREATE TABLE artists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_artists_name ON artists(name);
```

### Table: albums

Stores unique albums.

```sql
CREATE TABLE albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    artist_id INTEGER,
    year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (artist_id) REFERENCES artists(id),
    UNIQUE(name, artist_id)
);

CREATE INDEX idx_albums_name ON albums(name);
CREATE INDEX idx_albums_artist_id ON albums(artist_id);
```

### Common Queries

#### Find all duplicates by metadata hash

```sql
SELECT
    metadata_hash,
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(file_path, '; ') as file_paths
FROM library_files
WHERE metadata_hash IS NOT NULL
GROUP BY metadata_hash
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
```

#### Find all duplicates by content hash

```sql
SELECT
    content_hash,
    COUNT(*) as duplicate_count,
    GROUP_CONCAT(file_path, '; ') as file_paths
FROM library_files
WHERE content_hash IS NOT NULL
GROUP BY content_hash
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;
```

#### Get quality distribution

```sql
SELECT
    CASE
        WHEN quality_score >= 80 THEN 'Excellent'
        WHEN quality_score >= 60 THEN 'Good'
        WHEN quality_score >= 40 THEN 'Fair'
        ELSE 'Poor'
    END as quality_tier,
    COUNT(*) as count,
    ROUND(AVG(quality_score), 2) as avg_score
FROM library_files
GROUP BY quality_tier
ORDER BY avg_score DESC;
```

#### Find upgrade candidates (low-quality files)

```sql
SELECT
    file_path,
    format,
    quality_score,
    bitrate,
    sample_rate,
    is_lossless
FROM library_files
WHERE quality_score < 60  -- Below "Good" quality
  AND NOT is_lossless     -- Only lossy files
ORDER BY quality_score ASC
LIMIT 100;
```

#### Get library statistics

```sql
SELECT
    COUNT(*) as total_files,
    SUM(file_size) as total_bytes,
    ROUND(SUM(file_size) / (1024.0 * 1024.0 * 1024.0), 2) as total_gb,
    COUNT(DISTINCT artist_id) as artist_count,
    COUNT(DISTINCT album_id) as album_count,
    AVG(quality_score) as avg_quality
FROM library_files;
```

---

## Migration Procedures

### Overview

Migration procedures for integrating quality analysis features into existing Music Tools installations.

### Migration 001: Add Quality Analysis Fields

**Purpose**: Add quality scoring and analysis fields to existing library_files table.

**File**: `packages/common/music_tools_common/database/migrations/001_add_quality_fields.sql`

```sql
-- Migration 001: Add quality analysis fields
-- Date: 2026-01-08
-- Purpose: Support Smart Cleanup quality analysis

BEGIN TRANSACTION;

-- Add quality scoring fields
ALTER TABLE library_files ADD COLUMN quality_score INTEGER DEFAULT 0;
ALTER TABLE library_files ADD COLUMN bitrate_type TEXT DEFAULT 'unknown';
ALTER TABLE library_files ADD COLUMN is_lossless BOOLEAN DEFAULT 0;

-- Add duplicate detection fields
ALTER TABLE library_files ADD COLUMN metadata_hash TEXT;
ALTER TABLE library_files ADD COLUMN content_hash TEXT;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_library_files_quality_score
    ON library_files(quality_score);

CREATE INDEX IF NOT EXISTS idx_library_files_metadata_hash
    ON library_files(metadata_hash);

CREATE INDEX IF NOT EXISTS idx_library_files_content_hash
    ON library_files(content_hash);

-- Update schema version
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES (1, 'Add quality analysis and duplicate detection fields');

COMMIT;
```

### Migration 002: Populate Quality Scores

**Purpose**: Calculate and populate quality scores for existing files.

**Python script**: `scripts/migrations/002_populate_quality_scores.py`

```python
"""
Migration 002: Populate quality scores for existing library files.
"""

import logging
from pathlib import Path
from typing import Optional

from music_tools_common.database import LibraryDatabase
from library.quality_analyzer import extract_audio_metadata, calculate_quality_score

logger = logging.getLogger(__name__)


def migrate_quality_scores(db_path: str, batch_size: int = 100) -> None:
    """
    Populate quality scores for all library files.

    Args:
        db_path: Path to library database
        batch_size: Number of files to process per batch
    """
    db = LibraryDatabase(db_path)

    # Get all files without quality scores
    query = "SELECT id, file_path FROM library_files WHERE quality_score = 0"
    files = db.execute_query(query)

    total = len(files)
    logger.info(f"Processing {total} files...")

    processed = 0
    errors = 0

    for file_id, file_path in files:
        try:
            # Extract metadata
            metadata = extract_audio_metadata(file_path)
            if not metadata:
                logger.warning(f"Could not extract metadata: {file_path}")
                errors += 1
                continue

            # Update database
            update_query = """
                UPDATE library_files
                SET quality_score = ?,
                    bitrate_type = ?,
                    is_lossless = ?
                WHERE id = ?
            """
            db.execute_query(update_query, (
                metadata.quality_score,
                metadata.bitrate_type.value,
                metadata.is_lossless,
                file_id
            ))

            processed += 1

            if processed % batch_size == 0:
                logger.info(f"Processed {processed}/{total} files...")

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            errors += 1

    logger.info(f"Migration complete: {processed} processed, {errors} errors")

    # Mark migration as applied
    db.execute_query(
        "INSERT INTO schema_version (version, description) VALUES (?, ?)",
        (2, "Populate quality scores for existing files")
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    import sys
    if len(sys.argv) < 2:
        print("Usage: python 002_populate_quality_scores.py <db_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    migrate_quality_scores(db_path)
```

**Run migration:**
```bash
python scripts/migrations/002_populate_quality_scores.py \
    /path/to/music/.music_tools/library.db
```

### Migration 003: Generate Duplicate Hashes

**Purpose**: Generate metadata and content hashes for duplicate detection.

**Python script**: `scripts/migrations/003_generate_hashes.py`

```python
"""
Migration 003: Generate metadata and content hashes for duplicate detection.
"""

import hashlib
import logging
from pathlib import Path

from music_tools_common.database import LibraryDatabase

logger = logging.getLogger(__name__)


def generate_metadata_hash(artist: str, title: str, album: str) -> str:
    """Generate metadata hash for duplicate detection."""
    # Normalize strings
    parts = [
        (artist or "").lower().strip(),
        (title or "").lower().strip(),
        (album or "").lower().strip()
    ]

    # Create hash
    hash_input = "|".join(parts).encode('utf-8')
    return hashlib.md5(hash_input).hexdigest()


def generate_content_hash(file_path: str, chunk_size: int = 8192) -> Optional[str]:
    """Generate MD5 hash of file content."""
    try:
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception as e:
        logger.error(f"Error hashing {file_path}: {e}")
        return None


def migrate_hashes(db_path: str, include_content_hash: bool = False) -> None:
    """
    Generate and populate hash fields for duplicate detection.

    Args:
        db_path: Path to library database
        include_content_hash: Whether to generate content hashes
                             (slow for large libraries)
    """
    db = LibraryDatabase(db_path)

    # Get all files
    query = """
        SELECT lf.id, lf.file_path, a.name as artist, lf.title, al.name as album
        FROM library_files lf
        LEFT JOIN artists a ON lf.artist_id = a.id
        LEFT JOIN albums al ON lf.album_id = al.id
    """
    files = db.execute_query(query)

    total = len(files)
    logger.info(f"Processing {total} files...")

    processed = 0

    for file_id, file_path, artist, title, album in files:
        try:
            # Generate metadata hash
            metadata_hash = generate_metadata_hash(artist, title, album)

            # Generate content hash if requested
            content_hash = None
            if include_content_hash:
                content_hash = generate_content_hash(file_path)

            # Update database
            update_query = """
                UPDATE library_files
                SET metadata_hash = ?,
                    content_hash = ?
                WHERE id = ?
            """
            db.execute_query(update_query, (metadata_hash, content_hash, file_id))

            processed += 1

            if processed % 100 == 0:
                logger.info(f"Processed {processed}/{total} files...")

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

    logger.info(f"Migration complete: {processed} processed")

    # Mark migration as applied
    db.execute_query(
        "INSERT INTO schema_version (version, description) VALUES (?, ?)",
        (3, "Generate metadata and content hashes")
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    import sys
    if len(sys.argv) < 2:
        print("Usage: python 003_generate_hashes.py <db_path> [--content-hash]")
        sys.exit(1)

    db_path = sys.argv[1]
    include_content = "--content-hash" in sys.argv

    migrate_hashes(db_path, include_content_hash=include_content)
```

**Run migration:**
```bash
# Metadata hashes only (fast)
python scripts/migrations/003_generate_hashes.py \
    /path/to/music/.music_tools/library.db

# Include content hashes (slow but thorough)
python scripts/migrations/003_generate_hashes.py \
    /path/to/music/.music_tools/library.db --content-hash
```

### Rollback Procedures

**Rollback Migration 001:**
```sql
BEGIN TRANSACTION;

-- Remove added columns
ALTER TABLE library_files DROP COLUMN quality_score;
ALTER TABLE library_files DROP COLUMN bitrate_type;
ALTER TABLE library_files DROP COLUMN is_lossless;
ALTER TABLE library_files DROP COLUMN metadata_hash;
ALTER TABLE library_files DROP COLUMN content_hash;

-- Remove indexes
DROP INDEX IF EXISTS idx_library_files_quality_score;
DROP INDEX IF EXISTS idx_library_files_metadata_hash;
DROP INDEX IF EXISTS idx_library_files_content_hash;

-- Remove version record
DELETE FROM schema_version WHERE version = 1;

COMMIT;
```

---

## Testing Guidelines

### Overview

Comprehensive testing ensures quality analysis features work correctly across diverse music libraries.

### Test Structure

```
tests/
├── test_quality_analyzer.py      # Unit tests for quality analysis
├── test_safe_delete.py            # Unit tests for safe deletion
├── test_quality_models.py         # Unit tests for data models
├── test_smart_cleanup.py          # Integration tests for workflow
├── fixtures/                      # Test audio files
│   ├── test_flac_44100.flac
│   ├── test_mp3_320_cbr.mp3
│   ├── test_mp3_v0_vbr.mp3
│   └── test_aac_256.m4a
└── conftest.py                    # Pytest configuration
```

### Unit Tests: quality_analyzer

**File**: `tests/test_quality_analyzer.py`

```python
"""
Unit tests for quality_analyzer module.
"""

import pytest
from pathlib import Path

from library.quality_analyzer import (
    extract_audio_metadata,
    calculate_quality_score,
    rank_duplicate_group,
    BitrateType,
    get_quality_tier,
    normalize_filename
)


class TestExtractAudioMetadata:
    """Tests for extract_audio_metadata function."""

    def test_extract_flac_metadata(self, flac_file):
        """Test extracting metadata from FLAC file."""
        metadata = extract_audio_metadata(str(flac_file))

        assert metadata is not None
        assert metadata.format == "flac"
        assert metadata.is_lossless is True
        assert metadata.sample_rate == 44100
        assert metadata.quality_score > 0

    def test_extract_mp3_metadata(self, mp3_file):
        """Test extracting metadata from MP3 file."""
        metadata = extract_audio_metadata(str(mp3_file))

        assert metadata is not None
        assert metadata.format == "mp3"
        assert metadata.is_lossless is False
        assert metadata.bitrate > 0

    def test_vbr_detection_mp3(self, mp3_vbr_file):
        """Test VBR detection for MP3 files."""
        metadata = extract_audio_metadata(str(mp3_vbr_file))

        assert metadata is not None
        assert metadata.bitrate_type == BitrateType.VBR

    def test_invalid_file_path(self):
        """Test handling of invalid file path."""
        metadata = extract_audio_metadata("/nonexistent/file.mp3")
        assert metadata is None

    def test_empty_file_path(self):
        """Test handling of empty file path."""
        with pytest.raises(ValueError):
            extract_audio_metadata("")


class TestCalculateQualityScore:
    """Tests for calculate_quality_score function."""

    def test_flac_score(self, flac_metadata):
        """Test quality score for FLAC file."""
        score = calculate_quality_score(flac_metadata)

        # FLAC should score very high
        assert score >= 80
        assert score <= 100

    def test_mp3_320_score(self, mp3_320_metadata):
        """Test quality score for 320kbps MP3."""
        score = calculate_quality_score(mp3_320_metadata)

        # 320kbps MP3 should score in "Good" range
        assert 60 <= score < 80

    def test_mp3_128_score(self, mp3_128_metadata):
        """Test quality score for 128kbps MP3."""
        score = calculate_quality_score(mp3_128_metadata)

        # 128kbps MP3 should score in "Fair" range
        assert 40 <= score < 60

    def test_vbr_bonus(self, mp3_vbr_metadata, mp3_cbr_metadata):
        """Test VBR files get bonus points."""
        vbr_score = calculate_quality_score(mp3_vbr_metadata)
        cbr_score = calculate_quality_score(mp3_cbr_metadata)

        # VBR should score higher (assuming same bitrate)
        assert vbr_score >= cbr_score


class TestRankDuplicateGroup:
    """Tests for rank_duplicate_group function."""

    def test_rank_flac_over_mp3(self, flac_metadata, mp3_metadata):
        """Test FLAC is ranked higher than MP3."""
        files = [mp3_metadata, flac_metadata]

        keep, delete = rank_duplicate_group(files)

        assert keep == flac_metadata
        assert mp3_metadata in delete

    def test_rank_higher_bitrate(self, mp3_320_metadata, mp3_128_metadata):
        """Test higher bitrate ranked higher."""
        files = [mp3_128_metadata, mp3_320_metadata]

        keep, delete = rank_duplicate_group(files)

        assert keep == mp3_320_metadata
        assert mp3_128_metadata in delete

    def test_single_file_group(self, flac_metadata):
        """Test group with single file."""
        files = [flac_metadata]

        keep, delete = rank_duplicate_group(files)

        assert keep == flac_metadata
        assert delete == []

    def test_empty_group_raises(self):
        """Test empty group raises ValueError."""
        with pytest.raises(ValueError):
            rank_duplicate_group([])


class TestGetQualityTier:
    """Tests for get_quality_tier function."""

    def test_excellent_tier(self):
        assert get_quality_tier(95) == "Excellent"
        assert get_quality_tier(80) == "Excellent"

    def test_good_tier(self):
        assert get_quality_tier(75) == "Good"
        assert get_quality_tier(60) == "Good"

    def test_fair_tier(self):
        assert get_quality_tier(55) == "Fair"
        assert get_quality_tier(40) == "Fair"

    def test_poor_tier(self):
        assert get_quality_tier(35) == "Poor"
        assert get_quality_tier(1) == "Poor"

    def test_unknown_tier(self):
        assert get_quality_tier(0) == "Unknown"


class TestNormalizeFilename:
    """Tests for normalize_filename function."""

    def test_remove_brackets(self):
        assert normalize_filename("Song [320kbps].mp3") == "song.mp3"
        assert normalize_filename("Song (VBR).mp3") == "song.mp3"

    def test_underscores_to_spaces(self):
        assert normalize_filename("Artist_Name-Song_Title.flac") == \
               "artist name song title.flac"

    def test_remove_format_markers(self):
        assert normalize_filename("Song 320 MP3.mp3") == "song.mp3"
        assert normalize_filename("Song FLAC.flac") == "song.flac"

    def test_empty_string(self):
        assert normalize_filename("") == ""
        assert normalize_filename(None) == ""


# Fixtures

@pytest.fixture
def flac_file():
    """Path to test FLAC file."""
    return Path("tests/fixtures/test_flac_44100.flac")


@pytest.fixture
def mp3_file():
    """Path to test MP3 file."""
    return Path("tests/fixtures/test_mp3_320_cbr.mp3")


@pytest.fixture
def mp3_vbr_file():
    """Path to test VBR MP3 file."""
    return Path("tests/fixtures/test_mp3_v0_vbr.mp3")


# ... more fixtures for metadata objects
```

### Integration Tests: smart_cleanup

**File**: `tests/test_smart_cleanup.py`

```python
"""
Integration tests for Smart Cleanup workflow.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from library.smart_cleanup import SmartCleanupWorkflow, CleanupStats
from library.database import LibraryDatabase


class TestSmartCleanupWorkflow:
    """Integration tests for complete cleanup workflow."""

    @pytest.fixture
    def temp_library(self):
        """Create temporary library with test files."""
        temp_dir = tempfile.mkdtemp()

        # Copy test files
        test_files = [
            "song1.flac",
            "song1.mp3",
            "song1_copy.mp3",
            "song2.flac",
            "song2.mp3"
        ]

        for filename in test_files:
            source = Path("tests/fixtures") / filename
            dest = Path(temp_dir) / filename
            shutil.copy(source, dest)

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_full_workflow(self, temp_library):
        """Test complete cleanup workflow."""
        # Setup database
        db_path = Path(temp_library) / ".music_tools" / "library.db"
        db_path.parent.mkdir(exist_ok=True)
        db = LibraryDatabase(str(db_path))

        # Scan library
        # ... (populate database with test files)

        # Run workflow
        workflow = SmartCleanupWorkflow(
            library_db=db,
            library_path=temp_library,
            backup_dir=str(Path(temp_library) / ".backups")
        )

        # ... test workflow methods

    # ... more integration tests
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_quality_analyzer.py

# Run with coverage
pytest --cov=library --cov-report=html

# Run specific test
pytest tests/test_quality_analyzer.py::TestExtractAudioMetadata::test_extract_flac_metadata
```

---

## Code Examples

### Example 1: Basic Quality Analysis

```python
from library.quality_analyzer import extract_audio_metadata, get_quality_tier

# Analyze a single file
file_path = "/music/album/song.flac"
metadata = extract_audio_metadata(file_path)

if metadata:
    print(f"File: {metadata.filepath}")
    print(f"Format: {metadata.format.upper()}")
    print(f"Quality Score: {metadata.quality_score}/100")
    print(f"Quality Tier: {get_quality_tier(metadata.quality_score)}")
    print(f"Lossless: {'Yes' if metadata.is_lossless else 'No'}")
    print(f"Bitrate: {metadata.bitrate} kbps ({metadata.bitrate_type.value})")
    print(f"Sample Rate: {metadata.sample_rate} Hz")
else:
    print("Failed to analyze file")
```

### Example 2: Batch Quality Analysis

```python
from pathlib import Path
from library.quality_analyzer import extract_audio_metadata
import csv

# Analyze all files in a directory
music_dir = Path("/music/library")
results = []

for audio_file in music_dir.rglob("*.*"):
    if audio_file.suffix.lower() in ['.flac', '.mp3', '.m4a', '.aac']:
        metadata = extract_audio_metadata(str(audio_file))
        if metadata:
            results.append({
                'file': str(audio_file),
                'format': metadata.format,
                'quality_score': metadata.quality_score,
                'bitrate': metadata.bitrate,
                'lossless': metadata.is_lossless
            })

# Export to CSV
with open('quality_analysis.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['file', 'format', 'quality_score', 'bitrate', 'lossless'])
    writer.writeheader()
    writer.writerows(results)

print(f"Analyzed {len(results)} files")
```

### Example 3: Find and Rank Duplicates

```python
from library.quality_analyzer import extract_audio_metadata, rank_duplicate_group
from pathlib import Path

# Find duplicates by filename similarity
music_dir = Path("/music/library")
potential_duplicates = {}

for audio_file in music_dir.rglob("*.mp3"):
    # Simple duplicate detection by base name
    base_name = audio_file.stem.lower().replace('_', ' ')

    if base_name not in potential_duplicates:
        potential_duplicates[base_name] = []

    potential_duplicates[base_name].append(str(audio_file))

# Rank each duplicate group
for base_name, file_paths in potential_duplicates.items():
    if len(file_paths) > 1:
        # Extract metadata for all files
        files_metadata = []
        for path in file_paths:
            metadata = extract_audio_metadata(path)
            if metadata:
                files_metadata.append(metadata)

        # Rank by quality
        if len(files_metadata) > 1:
            keep, delete = rank_duplicate_group(files_metadata)

            print(f"\nDuplicate Group: {base_name}")
            print(f"  KEEP: {Path(keep.filepath).name} (quality: {keep.quality_score})")
            for file in delete:
                print(f"  DELETE: {Path(file.filepath).name} (quality: {file.quality_score})")
```

### Example 4: Safe Deletion with Validation

```python
from library.safe_delete import SafeDeletionPlan

# Create deletion plan
plan = SafeDeletionPlan(backup_dir="/music/.cleanup_backups")

# Add multiple deletion groups
plan.add_group(
    keep_file="/music/album1/song1.flac",
    delete_files=["/music/album1/song1.mp3", "/music/album1/song1_320.mp3"],
    reason="Keep FLAC, remove MP3 duplicates"
)

plan.add_group(
    keep_file="/music/album2/song2_320.mp3",
    delete_files=["/music/album2/song2_128.mp3"],
    reason="Keep higher bitrate"
)

# Validate all groups
is_valid, errors = plan.validate()

if is_valid:
    print("✓ Validation passed")

    # Dry run first
    dry_stats = plan.execute(dry_run=True, create_backup=False)
    print(f"Dry run: would delete {dry_stats.files_deleted} files")
    print(f"Would save {dry_stats.space_freed_bytes / (1024**2):.2f} MB")

    # Actual execution
    confirm = input("Proceed? (yes/no): ")
    if confirm == 'yes':
        stats = plan.execute(dry_run=False, create_backup=True)
        print(f"Deleted {stats.files_deleted} files")
        print(f"Backup: {stats.backup_path}")
else:
    print("✗ Validation failed:")
    for error in errors:
        print(f"  - {error}")
```

### Example 5: Custom Quality Scoring

```python
from library.quality_analyzer import extract_audio_metadata, AudioMetadata
from library import quality_analyzer

# Customize scoring weights (advanced users)
quality_analyzer.FORMAT_WEIGHT = 50  # Increase format importance
quality_analyzer.BITRATE_WEIGHT = 25
quality_analyzer.SAMPLE_RATE_WEIGHT = 15
quality_analyzer.RECENCY_WEIGHT = 10

# Now use with custom weights
metadata = extract_audio_metadata("/music/song.flac")
print(f"Quality with custom weights: {metadata.quality_score}/100")

# Restore defaults
quality_analyzer.FORMAT_WEIGHT = 40
quality_analyzer.BITRATE_WEIGHT = 30
quality_analyzer.SAMPLE_RATE_WEIGHT = 20
quality_analyzer.RECENCY_WEIGHT = 10
```

---

## Best Practices

### Performance Optimization

1. **Batch Operations**: Process files in batches to reduce database round-trips
   ```python
   # Good: Batch processing
   for batch in chunks(files, batch_size=100):
       metadata_list = [extract_audio_metadata(f) for f in batch]
       db.bulk_insert(metadata_list)

   # Avoid: One-by-one processing
   for file in files:
       metadata = extract_audio_metadata(file)
       db.insert(metadata)  # Slow!
   ```

2. **Index Usage**: Ensure database indexes are used for duplicate detection
   ```python
   # Query uses index on metadata_hash
   query = "SELECT * FROM library_files WHERE metadata_hash = ?"

   # Query does NOT use index (avoid)
   query = "SELECT * FROM library_files WHERE LOWER(title) = ?"
   ```

3. **Lazy Loading**: Don't extract full metadata unless needed
   ```python
   # Good: Only extract quality score
   metadata = extract_audio_metadata(file_path)
   score = metadata.quality_score

   # Avoid: Full metadata extraction for simple checks
   # (This is fine, but don't do unnecessary processing after)
   ```

### Error Handling

1. **Always Validate Inputs**:
   ```python
   from library.quality_analyzer import extract_audio_metadata

   def analyze_file(file_path: str) -> Optional[AudioMetadata]:
       if not file_path:
           raise ValueError("file_path cannot be empty")

       if not Path(file_path).exists():
           logger.warning(f"File does not exist: {file_path}")
           return None

       try:
           return extract_audio_metadata(file_path)
       except Exception as e:
           logger.error(f"Error analyzing {file_path}: {e}")
           return None
   ```

2. **Handle Missing Mutagen Gracefully**:
   ```python
   try:
       from mutagen import File as MutagenFile
   except ImportError:
       print("mutagen library not found. Please install: pip install mutagen")
       sys.exit(1)
   ```

3. **Log Errors with Context**:
   ```python
   import logging

   logger = logging.getLogger(__name__)

   try:
       metadata = extract_audio_metadata(file_path)
   except Exception as e:
       logger.error(
           f"Failed to extract metadata from {file_path}",
           exc_info=True,  # Include stack trace
           extra={'file_path': file_path, 'file_size': Path(file_path).stat().st_size}
       )
   ```

### Code Organization

1. **Separate Concerns**:
   ```python
   # Good: Separate UI from business logic
   from library.quality_analyzer import rank_duplicate_group
   from library.smart_cleanup import SmartCleanupWorkflow

   # UI layer
   def display_duplicates(groups):
       for group in groups:
           print(f"Keep: {group.recommended_keep.filepath}")

   # Business logic layer (in quality_analyzer)
   def rank_duplicate_group(files):
       # ... ranking logic ...
   ```

2. **Use Type Hints**:
   ```python
   from typing import List, Optional, Tuple
   from library.quality_analyzer import AudioMetadata

   def process_duplicates(
       files: List[AudioMetadata]
   ) -> Tuple[AudioMetadata, List[AudioMetadata]]:
       """Clear function signature with types."""
       # ... implementation ...
   ```

3. **Document Public APIs**:
   ```python
   def calculate_quality_score(metadata: AudioMetadata) -> int:
       """
       Calculate quality score (0-100) based on audio properties.

       Scoring formula:
       - Format: Up to 40pts
       - Bitrate: Up to 30pts
       - Sample rate: Up to 20pts
       - Recency: Up to 10pts

       Args:
           metadata: AudioMetadata object. Must not be None.

       Returns:
           Quality score from 0 to 100.

       Raises:
           ValueError: If metadata is None.

       Example:
           >>> metadata = extract_audio_metadata("song.flac")
           >>> score = calculate_quality_score(metadata)
           >>> print(f"Quality: {score}/100")
       """
   ```

### Testing

1. **Test Edge Cases**:
   ```python
   def test_empty_file_path():
       with pytest.raises(ValueError):
           extract_audio_metadata("")

   def test_nonexistent_file():
       metadata = extract_audio_metadata("/does/not/exist.mp3")
       assert metadata is None

   def test_corrupted_file():
       # Create corrupted file for testing
       metadata = extract_audio_metadata("corrupted.mp3")
       assert metadata is None
   ```

2. **Use Fixtures for Test Data**:
   ```python
   @pytest.fixture
   def flac_metadata():
       return AudioMetadata(
           filepath="/test/song.flac",
           format="flac",
           bitrate=1411000,
           sample_rate=44100,
           is_lossless=True,
           quality_score=95
       )

   def test_flac_quality(flac_metadata):
       assert flac_metadata.is_high_quality
       assert flac_metadata.is_lossless
   ```

3. **Test with Real Files**:
   ```python
   # Include small test audio files in tests/fixtures/
   def test_real_flac_file():
       metadata = extract_audio_metadata("tests/fixtures/test.flac")
       assert metadata.format == "flac"
       assert metadata.is_lossless is True
   ```

### Security

1. **Validate File Paths**:
   ```python
   from pathlib import Path

   def safe_file_path(user_input: str) -> Path:
       """Validate and sanitize file path from user input."""
       path = Path(user_input).resolve()

       # Prevent directory traversal
       if ".." in path.parts:
           raise ValueError("Invalid path: directory traversal not allowed")

       # Ensure path is within allowed directory
       allowed_dir = Path("/music/library").resolve()
       if not str(path).startswith(str(allowed_dir)):
           raise ValueError(f"Path must be within {allowed_dir}")

       return path
   ```

2. **Sanitize Database Inputs**:
   ```python
   # Good: Use parameterized queries
   query = "SELECT * FROM library_files WHERE file_path = ?"
   db.execute(query, (file_path,))

   # NEVER: String formatting (SQL injection risk)
   query = f"SELECT * FROM library_files WHERE file_path = '{file_path}'"
   ```

3. **Limit File Size Processing**:
   ```python
   MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

   def safe_extract_metadata(file_path: str) -> Optional[AudioMetadata]:
       file_size = Path(file_path).stat().st_size

       if file_size > MAX_FILE_SIZE:
           logger.warning(f"File too large: {file_path} ({file_size} bytes)")
           return None

       return extract_audio_metadata(file_path)
   ```

---

## Document Version

- **Version**: 1.0.0
- **Last Updated**: 2026-01-08
- **Author**: Music Tools Dev Team
- **Applies to**: Music Tools Dev v1.0+

## Support

For questions or issues with integration:

1. **Review this guide** thoroughly
2. **Check example code** in the repository
3. **Run tests** to verify your environment
4. **Consult API documentation** for specific functions
5. **Contact support** with detailed error messages and logs

---

**Happy coding!** Build amazing music management tools with quality analysis.
