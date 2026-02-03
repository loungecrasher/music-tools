"""
Pytest configuration and fixtures for library tests.

Provides common fixtures for testing quality analysis modules including:
- Mock audio metadata objects
- Sample file fixtures
- Temporary directory setups
- Mock database connections
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock
import sys

# Add apps/music-tools to sys.path to allow importing from src
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import modules after path setup
from src.library.quality_analyzer import AudioMetadata, BitrateType
from src.library.quality_models import AudioQuality, DuplicateGroup, UpgradeCandidate
from src.library.safe_delete import DeletionGroup, ValidationResult, ValidationLevel


# ==================== Audio Metadata Fixtures ====================

@pytest.fixture
def sample_mp3_metadata() -> Dict[str, Any]:
    """Sample MP3 file metadata dictionary."""
    return {
        'filepath': '/music/song.mp3',
        'format': 'mp3',
        'bitrate': 320,
        'sample_rate': 44100,
        'channels': 2,
        'duration': 225.5,
        'bitrate_type': BitrateType.CBR,
        'file_size': 8_000_000,
        'modified_time': datetime.now(timezone.utc) - timedelta(days=30),
        'is_lossless': False,
        'quality_score': 70
    }


@pytest.fixture
def sample_flac_metadata() -> Dict[str, Any]:
    """Sample FLAC file metadata dictionary."""
    return {
        'filepath': '/music/song.flac',
        'format': 'flac',
        'bitrate': 1411,
        'sample_rate': 96000,
        'channels': 2,
        'duration': 225.5,
        'bitrate_type': BitrateType.UNKNOWN,
        'file_size': 25_000_000,
        'modified_time': datetime.now(timezone.utc) - timedelta(days=10),
        'is_lossless': True,
        'quality_score': 100
    }


@pytest.fixture
def sample_vbr_mp3_metadata() -> Dict[str, Any]:
    """Sample VBR MP3 file metadata dictionary."""
    return {
        'filepath': '/music/song_vbr.mp3',
        'format': 'mp3',
        'bitrate': 256,
        'sample_rate': 44100,
        'channels': 2,
        'duration': 225.5,
        'bitrate_type': BitrateType.VBR,
        'file_size': 6_500_000,
        'modified_time': datetime.now(timezone.utc) - timedelta(days=180),
        'is_lossless': False,
        'quality_score': 72
    }


@pytest.fixture
def sample_aac_metadata() -> Dict[str, Any]:
    """Sample AAC file metadata dictionary."""
    return {
        'filepath': '/music/song.m4a',
        'format': 'm4a',
        'bitrate': 256,
        'sample_rate': 48000,
        'channels': 2,
        'duration': 225.5,
        'bitrate_type': BitrateType.CBR,
        'file_size': 7_000_000,
        'modified_time': datetime.now(timezone.utc) - timedelta(days=365),
        'is_lossless': False,
        'quality_score': 67
    }


@pytest.fixture
def sample_low_quality_metadata() -> Dict[str, Any]:
    """Sample low quality file metadata dictionary."""
    return {
        'filepath': '/music/song_low.mp3',
        'format': 'mp3',
        'bitrate': 128,
        'sample_rate': 22050,
        'channels': 1,
        'duration': 225.5,
        'bitrate_type': BitrateType.CBR,
        'file_size': 3_500_000,
        'modified_time': datetime.now(timezone.utc) - timedelta(days=2000),
        'is_lossless': False,
        'quality_score': 35
    }


# ==================== AudioMetadata Object Fixtures ====================

@pytest.fixture
def audio_metadata_mp3(sample_mp3_metadata) -> AudioMetadata:
    """AudioMetadata object for MP3 file."""
    return AudioMetadata(**sample_mp3_metadata)


@pytest.fixture
def audio_metadata_flac(sample_flac_metadata) -> AudioMetadata:
    """AudioMetadata object for FLAC file."""
    return AudioMetadata(**sample_flac_metadata)


@pytest.fixture
def audio_metadata_vbr(sample_vbr_mp3_metadata) -> AudioMetadata:
    """AudioMetadata object for VBR MP3 file."""
    return AudioMetadata(**sample_vbr_mp3_metadata)


@pytest.fixture
def audio_metadata_aac(sample_aac_metadata) -> AudioMetadata:
    """AudioMetadata object for AAC file."""
    return AudioMetadata(**sample_aac_metadata)


@pytest.fixture
def audio_metadata_low_quality(sample_low_quality_metadata) -> AudioMetadata:
    """AudioMetadata object for low quality file."""
    return AudioMetadata(**sample_low_quality_metadata)


# ==================== AudioQuality Fixtures ====================

@pytest.fixture
def audio_quality_flac() -> AudioQuality:
    """AudioQuality object for high-quality FLAC file."""
    return AudioQuality(
        file_path='/music/track.flac',
        format='flac',
        bitrate=1411000,
        sample_rate=96000,
        bit_depth=24,
        channels=2,
        duration=245.0,
        is_lossless=True,
        is_vbr=False,
        quality_score=95,
        file_size=30_000_000,
        last_modified=datetime.now(timezone.utc) - timedelta(days=30)
    )


@pytest.fixture
def audio_quality_mp3_320() -> AudioQuality:
    """AudioQuality object for 320kbps MP3 file."""
    return AudioQuality(
        file_path='/music/track.mp3',
        format='mp3',
        bitrate=320000,
        sample_rate=44100,
        channels=2,
        duration=245.0,
        is_lossless=False,
        is_vbr=False,
        quality_score=70,
        file_size=9_000_000,
        last_modified=datetime.now(timezone.utc) - timedelta(days=60)
    )


@pytest.fixture
def audio_quality_mp3_128() -> AudioQuality:
    """AudioQuality object for 128kbps MP3 file."""
    return AudioQuality(
        file_path='/music/track_low.mp3',
        format='mp3',
        bitrate=128000,
        sample_rate=44100,
        channels=2,
        duration=245.0,
        is_lossless=False,
        is_vbr=False,
        quality_score=45,
        file_size=4_000_000,
        last_modified=datetime.now(timezone.utc) - timedelta(days=365)
    )


# ==================== DuplicateGroup Fixtures ====================

@pytest.fixture
def duplicate_group_simple(audio_quality_flac, audio_quality_mp3_320, audio_quality_mp3_128) -> DuplicateGroup:
    """Simple duplicate group with 3 files."""
    return DuplicateGroup(
        id='test-group-001',
        track_hash='hash123',
        files=[audio_quality_flac, audio_quality_mp3_320, audio_quality_mp3_128],
        recommended_keep=audio_quality_flac,
        recommended_delete=[audio_quality_mp3_320, audio_quality_mp3_128],
        confidence=0.95,
        reason='FLAC has highest quality',
        space_savings=13_000_000,
        discovered_date=datetime.now(timezone.utc)
    )


# ==================== UpgradeCandidate Fixtures ====================

@pytest.fixture
def upgrade_candidate_to_flac(audio_quality_mp3_320) -> UpgradeCandidate:
    """Upgrade candidate from MP3 to FLAC."""
    return UpgradeCandidate(
        current_file=audio_quality_mp3_320,
        target_format='flac',
        quality_gap=30,
        priority_score=80,
        available_services=['Spotify', 'Deezer', 'Tidal'],
        estimated_improvement='Significant quality improvement'
    )


# ==================== DeletionGroup Fixtures ====================

@pytest.fixture
def deletion_group_valid() -> DeletionGroup:
    """Valid deletion group for testing."""
    return DeletionGroup(
        keep_file='/music/keep.flac',
        delete_files=['/music/delete1.mp3', '/music/delete2.mp3'],
        reason='Keep highest quality FLAC file'
    )


@pytest.fixture
def deletion_group_with_validation() -> DeletionGroup:
    """Deletion group with validation results."""
    group = DeletionGroup(
        keep_file='/music/keep.flac',
        delete_files=['/music/delete.mp3'],
        reason='Quality upgrade'
    )
    group.validation_results = [
        ValidationResult(
            level=ValidationLevel.INFO,
            checkpoint='1. Keep File Exists',
            message='Keep file validated',
            details={'keep_file': group.keep_file}
        ),
        ValidationResult(
            level=ValidationLevel.WARNING,
            checkpoint='3. Quality Check',
            message='Deleting higher bitrate file',
            details={'keep_bitrate': 1411, 'delete_bitrate': 320}
        )
    ]
    return group


# ==================== Temporary File Fixtures ====================

@pytest.fixture
def temp_audio_dir(tmp_path) -> Path:
    """Temporary directory with sample audio file structure."""
    audio_dir = tmp_path / 'audio'
    audio_dir.mkdir()

    # Create subdirectories
    (audio_dir / 'duplicates').mkdir()
    (audio_dir / 'originals').mkdir()
    (audio_dir / 'backup').mkdir()

    return audio_dir


@pytest.fixture
def mock_audio_file(temp_audio_dir) -> Path:
    """Create a mock audio file for testing."""
    file_path = temp_audio_dir / 'test_song.mp3'
    file_path.write_bytes(b'FAKE_MP3_DATA' * 1000)  # Create a fake MP3 file
    return file_path


@pytest.fixture
def mock_audio_files(temp_audio_dir) -> List[Path]:
    """Create multiple mock audio files for testing."""
    files = []

    # Create FLAC file
    flac_file = temp_audio_dir / 'song.flac'
    flac_file.write_bytes(b'FAKE_FLAC_DATA' * 2000)
    files.append(flac_file)

    # Create high quality MP3
    mp3_320 = temp_audio_dir / 'song_320.mp3'
    mp3_320.write_bytes(b'FAKE_MP3_320' * 1500)
    files.append(mp3_320)

    # Create medium quality MP3
    mp3_256 = temp_audio_dir / 'song_256.mp3'
    mp3_256.write_bytes(b'FAKE_MP3_256' * 1200)
    files.append(mp3_256)

    # Create low quality MP3
    mp3_128 = temp_audio_dir / 'song_128.mp3'
    mp3_128.write_bytes(b'FAKE_MP3_128' * 600)
    files.append(mp3_128)

    return files


# ==================== Mock Mutagen Fixtures ====================

@pytest.fixture
def mock_mutagen_file():
    """Mock mutagen File object with audio info."""
    mock_file = Mock()
    mock_info = Mock()

    # Set default values
    mock_info.bitrate = 320000
    mock_info.sample_rate = 44100
    mock_info.channels = 2
    mock_info.length = 225.5
    mock_info.bitrate_mode = None

    mock_file.info = mock_info

    return mock_file


@pytest.fixture
def mock_mutagen_flac():
    """Mock mutagen File object for FLAC."""
    mock_file = Mock()
    mock_info = Mock()

    mock_info.bitrate = 1411000
    mock_info.sample_rate = 96000
    mock_info.channels = 2
    mock_info.length = 225.5

    mock_file.info = mock_info

    return mock_file


@pytest.fixture
def mock_mutagen_vbr_mp3():
    """Mock mutagen File object for VBR MP3."""
    from src.library.quality_analyzer import BitrateMode

    mock_file = Mock()
    mock_info = Mock()

    mock_info.bitrate = 256000
    mock_info.sample_rate = 44100
    mock_info.channels = 2
    mock_info.length = 225.5
    mock_info.bitrate_mode = BitrateMode.VBR if BitrateMode else None

    mock_file.info = mock_info

    return mock_file


# ==================== Mock Database Fixtures ====================

@pytest.fixture
def mock_database():
    """Mock database connection for testing."""
    db = Mock()

    # Mock common database operations
    db.execute = Mock(return_value=True)
    db.fetch = Mock(return_value=[])
    db.fetchone = Mock(return_value=None)
    db.commit = Mock(return_value=True)
    db.rollback = Mock(return_value=True)
    db.close = Mock(return_value=True)

    return db


# ==================== Test Data Builders ====================

def create_audio_metadata(
    filepath: str = '/music/test.mp3',
    format: str = 'mp3',
    bitrate: int = 320,
    sample_rate: int = 44100,
    quality_score: int = 70,
    **kwargs
) -> AudioMetadata:
    """Builder function for creating AudioMetadata objects.

    Args:
        filepath: Path to audio file
        format: Audio format (mp3, flac, etc.)
        bitrate: Bitrate in kbps
        sample_rate: Sample rate in Hz
        quality_score: Quality score (0-100)
        **kwargs: Additional AudioMetadata fields

    Returns:
        AudioMetadata object
    """
    defaults = {
        'filepath': filepath,
        'format': format,
        'bitrate': bitrate,
        'sample_rate': sample_rate,
        'channels': 2,
        'duration': 225.0,
        'bitrate_type': BitrateType.CBR,
        'file_size': bitrate * 1000 * 30,  # Rough estimate
        'modified_time': datetime.now(timezone.utc),
        'is_lossless': format in {'flac', 'alac', 'wav', 'aiff'},
        'quality_score': quality_score
    }
    defaults.update(kwargs)
    return AudioMetadata(**defaults)


def create_audio_quality(
    file_path: str = '/music/test.mp3',
    format: str = 'mp3',
    bitrate: int = 320000,
    sample_rate: int = 44100,
    quality_score: int = 70,
    **kwargs
) -> AudioQuality:
    """Builder function for creating AudioQuality objects.

    Args:
        file_path: Path to audio file
        format: Audio format (mp3, flac, etc.)
        bitrate: Bitrate in bps
        sample_rate: Sample rate in Hz
        quality_score: Quality score (0-100)
        **kwargs: Additional AudioQuality fields

    Returns:
        AudioQuality object
    """
    defaults = {
        'file_path': file_path,
        'format': format,
        'bitrate': bitrate,
        'sample_rate': sample_rate,
        'channels': 2,
        'duration': 245.0,
        'is_lossless': format in {'flac', 'alac', 'wav', 'aiff'},
        'is_vbr': False,
        'quality_score': quality_score,
        'file_size': bitrate * 30 // 8,  # Rough estimate
        'last_modified': datetime.now(timezone.utc)
    }
    defaults.update(kwargs)
    return AudioQuality(**defaults)


# Export builder functions
pytest.create_audio_metadata = create_audio_metadata
pytest.create_audio_quality = create_audio_quality


# ==================== Library Core Fixtures ====================

from src.library.models import LibraryFile, DuplicateResult, VettingReport


def make_library_file(**overrides) -> LibraryFile:
    """Builder for LibraryFile test objects."""
    defaults = {
        'file_path': '/music/test.mp3',
        'filename': 'test.mp3',
        'artist': 'Test Artist',
        'title': 'Test Track',
        'album': 'Test Album',
        'year': 2024,
        'duration': 225.5,
        'file_format': 'mp3',
        'file_size': 5_000_000,
        'metadata_hash': 'abc123',
        'file_content_hash': 'def456',
        'file_mtime': datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return LibraryFile(**defaults)


def make_duplicate_result(**overrides) -> DuplicateResult:
    """Builder for DuplicateResult test objects."""
    defaults = {
        'is_duplicate': False,
        'confidence': 0.0,
        'match_type': 'none',
    }
    defaults.update(overrides)
    return DuplicateResult(**defaults)


def make_vetting_report(**overrides) -> VettingReport:
    """Builder for VettingReport test objects."""
    defaults = {
        'import_folder': '/tmp/import',
        'total_files': 10,
        'threshold': 0.8,
    }
    defaults.update(overrides)
    return VettingReport(**defaults)


@pytest.fixture
def library_db(tmp_path):
    """LibraryDatabase with temp SQLite file."""
    from src.library.database import LibraryDatabase
    return LibraryDatabase(str(tmp_path / "test_library.db"))


@pytest.fixture
def populated_library_db(library_db):
    """LibraryDatabase with sample data."""
    files = [
        make_library_file(
            file_path='/music/song1.flac',
            filename='song1.flac',
            artist='Artist A',
            title='Song One',
            file_format='flac',
            file_size=25_000_000,
            metadata_hash='hash_a1',
            file_content_hash='content_a1',
        ),
        make_library_file(
            file_path='/music/song2.mp3',
            filename='song2.mp3',
            artist='Artist B',
            title='Song Two',
            file_format='mp3',
            file_size=8_000_000,
            metadata_hash='hash_b2',
            file_content_hash='content_b2',
        ),
        make_library_file(
            file_path='/music/song3.mp3',
            filename='song3.mp3',
            artist='Artist A',
            title='Song Three',
            file_format='mp3',
            file_size=7_000_000,
            metadata_hash='hash_a3',
            file_content_hash='content_a3',
        ),
    ]
    for f in files:
        library_db.add_file(f)
    return library_db


# Export additional builders
pytest.make_library_file = make_library_file
pytest.make_duplicate_result = make_duplicate_result
pytest.make_vetting_report = make_vetting_report
