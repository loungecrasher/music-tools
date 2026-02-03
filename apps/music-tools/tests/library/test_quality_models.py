"""
Comprehensive test suite for quality_models module.

Tests AudioQuality, DuplicateGroup, and UpgradeCandidate dataclasses
including validation, serialization, and property calculations.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.library.quality_models import (  # Constants
    CD_QUALITY_BIT_DEPTH,
    CD_QUALITY_SAMPLE_RATE,
    HIGH_QUALITY_BITRATE,
    HIGH_RES_SAMPLE_RATE,
    LOSSLESS_FORMATS,
    MAX_CHANNELS,
    MAX_CONFIDENCE,
    MAX_QUALITY_SCORE,
    MIN_BITRATE,
    MIN_CHANNELS,
    MIN_CONFIDENCE,
    MIN_DURATION,
    MIN_FILE_SIZE,
    MIN_QUALITY_SCORE,
    MIN_SAMPLE_RATE,
    AudioQuality,
    DuplicateGroup,
    UpgradeCandidate,
)

# ==================== AudioQuality Tests ====================


class TestAudioQuality:
    """Test AudioQuality dataclass validation and properties."""

    def test_audio_quality_basic_creation(self):
        """Test basic AudioQuality creation."""
        audio = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            quality_score=70,
        )

        assert audio.file_path == "/music/song.mp3"
        assert audio.format == "mp3"
        assert audio.bitrate == 320000
        assert audio.sample_rate == 44100
        assert audio.quality_score == 70

    def test_audio_quality_lossless_auto_detection(self):
        """Test automatic lossless format detection."""
        flac = AudioQuality(
            file_path="/music/song.flac",
            format="flac",
            bitrate=1411000,
            sample_rate=44100,
            quality_score=95,
        )

        assert flac.is_lossless is True

        mp3 = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            quality_score=70,
        )

        assert mp3.is_lossless is False

    def test_audio_quality_format_normalization(self):
        """Test format string normalization to lowercase."""
        audio = AudioQuality(
            file_path="/music/song.mp3",
            format="MP3",  # Uppercase
            bitrate=320000,
            sample_rate=44100,
            quality_score=70,
        )

        assert audio.format == "mp3"  # Should be lowercase

    def test_audio_quality_invalid_bitrate_raises(self):
        """Test that invalid bitrate raises ValueError."""
        with pytest.raises(ValueError, match="Bitrate must be"):
            AudioQuality(
                file_path="/music/song.mp3",
                format="mp3",
                bitrate=-1000,  # Invalid
                sample_rate=44100,
                quality_score=70,
            )

    def test_audio_quality_invalid_sample_rate_raises(self):
        """Test that invalid sample rate raises ValueError."""
        with pytest.raises(ValueError, match="Sample rate must be"):
            AudioQuality(
                file_path="/music/song.mp3",
                format="mp3",
                bitrate=320000,
                sample_rate=-44100,  # Invalid
                quality_score=70,
            )

    def test_audio_quality_invalid_channels_raises(self):
        """Test that invalid channels raises ValueError."""
        with pytest.raises(ValueError, match="Channels must be between"):
            AudioQuality(
                file_path="/music/song.mp3",
                format="mp3",
                bitrate=320000,
                sample_rate=44100,
                channels=0,  # Invalid
                quality_score=70,
            )

        with pytest.raises(ValueError, match="Channels must be between"):
            AudioQuality(
                file_path="/music/song.mp3",
                format="mp3",
                bitrate=320000,
                sample_rate=44100,
                channels=10,  # Too many
                quality_score=70,
            )

    def test_audio_quality_negative_duration_corrected(self):
        """Test that negative duration is corrected to 0."""
        audio = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            duration=-10.0,  # Invalid
            quality_score=70,
        )

        assert audio.duration == 0.0

    def test_audio_quality_negative_file_size_corrected(self):
        """Test that negative file size is corrected to 0."""
        audio = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            file_size=-1000,  # Invalid
            quality_score=70,
        )

        assert audio.file_size == 0

    def test_audio_quality_invalid_quality_score_raises(self):
        """Test that quality score outside 0-100 raises ValueError."""
        with pytest.raises(ValueError, match="Quality score must be between"):
            AudioQuality(
                file_path="/music/song.mp3",
                format="mp3",
                bitrate=320000,
                sample_rate=44100,
                quality_score=150,  # Too high
            )

        with pytest.raises(ValueError, match="Quality score must be between"):
            AudioQuality(
                file_path="/music/song.mp3",
                format="mp3",
                bitrate=320000,
                sample_rate=44100,
                quality_score=-10,  # Negative
            )

    def test_audio_quality_invalid_bit_depth_raises(self):
        """Test that invalid bit depth raises ValueError."""
        with pytest.raises(ValueError, match="Bit depth must be positive"):
            AudioQuality(
                file_path="/music/song.flac",
                format="flac",
                bitrate=1411000,
                sample_rate=44100,
                bit_depth=-24,  # Invalid
                quality_score=95,
            )

    def test_audio_quality_last_modified_default(self):
        """Test that last_modified defaults to current time if not provided."""
        before = datetime.now(timezone.utc)

        audio = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            quality_score=70,
        )

        after = datetime.now(timezone.utc)

        assert before <= audio.last_modified <= after

    def test_audio_quality_bitrate_kbps_property(self):
        """Test bitrate_kbps calculated property."""
        audio = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,  # 320 kbps
            sample_rate=44100,
            quality_score=70,
        )

        assert audio.bitrate_kbps == 320.0

    def test_audio_quality_file_size_mb_property(self):
        """Test file_size_mb calculated property."""
        audio = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            file_size=10_485_760,  # 10 MB
            quality_score=70,
        )

        assert audio.file_size_mb == 10.0

    def test_audio_quality_is_high_quality_lossless(self):
        """Test is_high_quality property for lossless."""
        audio = AudioQuality(
            file_path="/music/song.flac",
            format="flac",
            bitrate=1411000,
            sample_rate=44100,
            is_lossless=True,
            quality_score=95,
        )

        assert audio.is_high_quality is True

    def test_audio_quality_is_high_quality_320kbps(self):
        """Test is_high_quality property for 320kbps MP3."""
        audio = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,  # 320 kbps
            sample_rate=44100,
            quality_score=70,
        )

        assert audio.is_high_quality is True

    def test_audio_quality_is_not_high_quality_128kbps(self):
        """Test is_high_quality property for 128kbps MP3."""
        audio = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=128000,  # 128 kbps
            sample_rate=44100,
            quality_score=45,
        )

        assert audio.is_high_quality is False

    def test_audio_quality_is_cd_quality(self):
        """Test is_cd_quality property."""
        cd_quality = AudioQuality(
            file_path="/music/song.flac",
            format="flac",
            bitrate=1411000,
            sample_rate=44100,  # CD quality
            bit_depth=16,  # CD quality
            quality_score=95,
        )

        assert cd_quality.is_cd_quality is True

    def test_audio_quality_is_not_cd_quality_low_sample_rate(self):
        """Test is_cd_quality property with low sample rate."""
        low_sample = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=128000,
            sample_rate=22050,  # Below CD quality
            quality_score=40,
        )

        assert low_sample.is_cd_quality is False

    def test_audio_quality_to_dict(self):
        """Test AudioQuality serialization to dictionary."""
        now = datetime.now(timezone.utc)

        audio = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            bit_depth=None,
            channels=2,
            duration=245.5,
            is_lossless=False,
            is_vbr=True,
            quality_score=72,
            file_size=9_000_000,
            last_modified=now,
        )

        data = audio.to_dict()

        assert data["file_path"] == "/music/song.mp3"
        assert data["format"] == "mp3"
        assert data["bitrate"] == 320000
        assert data["sample_rate"] == 44100
        assert data["is_vbr"] is True
        assert data["quality_score"] == 72
        assert data["last_modified"] == now.isoformat()

    def test_audio_quality_from_dict(self):
        """Test AudioQuality deserialization from dictionary."""
        now = datetime.now(timezone.utc)

        data = {
            "file_path": "/music/song.flac",
            "format": "flac",
            "bitrate": 1411000,
            "sample_rate": 96000,
            "bit_depth": 24,
            "channels": 2,
            "duration": 225.0,
            "is_lossless": True,
            "is_vbr": False,
            "quality_score": 100,
            "file_size": 30_000_000,
            "last_modified": now.isoformat(),
        }

        audio = AudioQuality.from_dict(data)

        assert audio.file_path == "/music/song.flac"
        assert audio.format == "flac"
        assert audio.bitrate == 1411000
        assert audio.sample_rate == 96000
        assert audio.bit_depth == 24
        assert audio.is_lossless is True
        assert audio.quality_score == 100

    def test_audio_quality_from_dict_missing_required_field_raises(self):
        """Test that from_dict raises ValueError when required field is missing."""
        data = {
            "file_path": "/music/song.mp3",
            # Missing 'format'
            "bitrate": 320000,
            "sample_rate": 44100,
        }

        with pytest.raises(ValueError, match="Missing required field"):
            AudioQuality.from_dict(data)

    def test_audio_quality_from_dict_optional_fields(self):
        """Test from_dict with minimal required fields."""
        data = {
            "file_path": "/music/song.mp3",
            "format": "mp3",
            "bitrate": 320000,
            "sample_rate": 44100,
        }

        audio = AudioQuality.from_dict(data)

        assert audio.file_path == "/music/song.mp3"
        assert audio.channels == 2  # Default
        assert audio.duration == 0.0  # Default


# ==================== DuplicateGroup Tests ====================


class TestDuplicateGroup:
    """Test DuplicateGroup dataclass validation and properties."""

    def test_duplicate_group_basic_creation(self):
        """Test basic DuplicateGroup creation."""
        file1 = AudioQuality(
            file_path="/music/song.flac",
            format="flac",
            bitrate=1411000,
            sample_rate=96000,
            quality_score=100,
        )

        file2 = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            quality_score=70,
        )

        group = DuplicateGroup(
            id="test-group-123",
            track_hash="hash123",
            files=[file1, file2],
            recommended_keep=file1,
            recommended_delete=[file2],
            confidence=0.95,
            reason="FLAC has highest quality",
        )

        assert group.id == "test-group-123"
        assert group.track_hash == "hash123"
        assert len(group.files) == 2
        assert group.recommended_keep == file1
        assert group.confidence == 0.95

    def test_duplicate_group_auto_generates_id(self):
        """Test that ID is auto-generated if not provided."""
        group = DuplicateGroup(id="", track_hash="hash123", files=[])  # Empty ID

        assert len(group.id) > 0
        assert "-" in group.id  # UUID format

    def test_duplicate_group_invalid_confidence_raises(self):
        """Test that confidence outside 0-1 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            DuplicateGroup(id="test", track_hash="hash", confidence=1.5)  # Too high

        with pytest.raises(ValueError, match="Confidence must be between"):
            DuplicateGroup(id="test", track_hash="hash", confidence=-0.1)  # Negative

    def test_duplicate_group_discovered_date_default(self):
        """Test that discovered_date defaults to current time."""
        before = datetime.now(timezone.utc)

        group = DuplicateGroup(id="test", track_hash="hash")

        after = datetime.now(timezone.utc)

        assert before <= group.discovered_date <= after

    def test_duplicate_group_space_savings_auto_calculated(self):
        """Test that space_savings is auto-calculated from recommended_delete."""
        file1 = AudioQuality(
            file_path="/music/keep.flac",
            format="flac",
            bitrate=1411000,
            sample_rate=96000,
            file_size=30_000_000,
            quality_score=100,
        )

        file2 = AudioQuality(
            file_path="/music/delete1.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            file_size=8_000_000,
            quality_score=70,
        )

        file3 = AudioQuality(
            file_path="/music/delete2.mp3",
            format="mp3",
            bitrate=128000,
            sample_rate=44100,
            file_size=4_000_000,
            quality_score=45,
        )

        group = DuplicateGroup(
            id="test",
            track_hash="hash",
            files=[file1, file2, file3],
            recommended_keep=file1,
            recommended_delete=[file2, file3],
            confidence=0.9,
        )

        # Should be sum of delete file sizes
        assert group.space_savings == 12_000_000  # 8M + 4M

    def test_duplicate_group_file_count_property(self):
        """Test file_count calculated property."""
        files = [
            AudioQuality(
                file_path=f"/music/song{i}.mp3",
                format="mp3",
                bitrate=320000,
                sample_rate=44100,
                quality_score=70,
            )
            for i in range(5)
        ]

        group = DuplicateGroup(id="test", track_hash="hash", files=files)

        assert group.file_count == 5

    def test_duplicate_group_total_size_property(self):
        """Test total_size calculated property."""
        files = [
            AudioQuality(
                file_path=f"/music/song{i}.mp3",
                format="mp3",
                bitrate=320000,
                sample_rate=44100,
                file_size=8_000_000,  # 8 MB each
                quality_score=70,
            )
            for i in range(3)
        ]

        group = DuplicateGroup(id="test", track_hash="hash", files=files)

        assert group.total_size == 24_000_000  # 8M * 3

    def test_duplicate_group_space_savings_mb_property(self):
        """Test space_savings_mb calculated property."""
        group = DuplicateGroup(id="test", track_hash="hash", space_savings=10_485_760)  # 10 MB

        assert group.space_savings_mb == 10.0

    def test_duplicate_group_is_high_confidence(self):
        """Test is_high_confidence property."""
        high_conf = DuplicateGroup(id="test1", track_hash="hash1", confidence=0.85)

        low_conf = DuplicateGroup(id="test2", track_hash="hash2", confidence=0.75)

        assert high_conf.is_high_confidence is True
        assert low_conf.is_high_confidence is False

    def test_duplicate_group_to_dict(self):
        """Test DuplicateGroup serialization to dictionary."""
        file1 = AudioQuality(
            file_path="/music/keep.flac",
            format="flac",
            bitrate=1411000,
            sample_rate=96000,
            quality_score=100,
        )

        file2 = AudioQuality(
            file_path="/music/delete.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            quality_score=70,
        )

        now = datetime.now(timezone.utc)

        group = DuplicateGroup(
            id="test-123",
            track_hash="hash456",
            files=[file1, file2],
            recommended_keep=file1,
            recommended_delete=[file2],
            confidence=0.95,
            reason="Quality difference",
            space_savings=8_000_000,
            discovered_date=now,
        )

        data = group.to_dict()

        assert data["id"] == "test-123"
        assert data["track_hash"] == "hash456"
        assert len(data["files"]) == 2
        assert data["recommended_keep"] is not None
        assert len(data["recommended_delete"]) == 1
        assert data["confidence"] == 0.95
        assert data["discovered_date"] == now.isoformat()

    def test_duplicate_group_from_dict(self):
        """Test DuplicateGroup deserialization from dictionary."""
        now = datetime.now(timezone.utc)

        data = {
            "id": "test-789",
            "track_hash": "hash999",
            "files": [
                {
                    "file_path": "/music/file1.flac",
                    "format": "flac",
                    "bitrate": 1411000,
                    "sample_rate": 96000,
                    "quality_score": 100,
                },
                {
                    "file_path": "/music/file2.mp3",
                    "format": "mp3",
                    "bitrate": 320000,
                    "sample_rate": 44100,
                    "quality_score": 70,
                },
            ],
            "recommended_keep": {
                "file_path": "/music/file1.flac",
                "format": "flac",
                "bitrate": 1411000,
                "sample_rate": 96000,
                "quality_score": 100,
            },
            "recommended_delete": [
                {
                    "file_path": "/music/file2.mp3",
                    "format": "mp3",
                    "bitrate": 320000,
                    "sample_rate": 44100,
                    "quality_score": 70,
                }
            ],
            "confidence": 0.92,
            "reason": "Test reason",
            "space_savings": 8_000_000,
            "discovered_date": now.isoformat(),
        }

        group = DuplicateGroup.from_dict(data)

        assert group.id == "test-789"
        assert group.track_hash == "hash999"
        assert len(group.files) == 2
        assert group.confidence == 0.92
        assert group.recommended_keep is not None

    def test_duplicate_group_from_dict_missing_required_field_raises(self):
        """Test that from_dict raises ValueError when required field is missing."""
        data = {
            # Missing 'id'
            "track_hash": "hash123"
        }

        with pytest.raises(ValueError, match="Missing required field"):
            DuplicateGroup.from_dict(data)


# ==================== UpgradeCandidate Tests ====================


class TestUpgradeCandidate:
    """Test UpgradeCandidate dataclass validation and properties."""

    def test_upgrade_candidate_basic_creation(self):
        """Test basic UpgradeCandidate creation."""
        current = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            quality_score=70,
        )

        candidate = UpgradeCandidate(
            current_file=current, target_format="flac", quality_gap=30, priority_score=80
        )

        assert candidate.current_file == current
        assert candidate.target_format == "flac"
        assert candidate.quality_gap == 30
        assert candidate.priority_score == 80

    def test_upgrade_candidate_target_format_normalization(self):
        """Test target format normalization to lowercase."""
        current = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=128000,
            sample_rate=44100,
            quality_score=45,
        )

        candidate = UpgradeCandidate(
            current_file=current, target_format="FLAC", quality_gap=50  # Uppercase
        )

        assert candidate.target_format == "flac"  # Should be lowercase

    def test_upgrade_candidate_invalid_priority_score_raises(self):
        """Test that priority score outside 0-100 raises ValueError."""
        current = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            quality_score=70,
        )

        with pytest.raises(ValueError, match="Priority score must be between"):
            UpgradeCandidate(
                current_file=current,
                target_format="flac",
                quality_gap=30,
                priority_score=150,  # Too high
            )

    def test_upgrade_candidate_negative_quality_gap_corrected(self):
        """Test that negative quality gap is corrected to 0."""
        current = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            quality_score=70,
        )

        candidate = UpgradeCandidate(
            current_file=current, target_format="flac", quality_gap=-10  # Invalid
        )

        assert candidate.quality_gap == 0

    def test_upgrade_candidate_estimated_improvement_auto_generated(self):
        """Test that estimated_improvement is auto-generated based on quality_gap."""
        current = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=128000,
            sample_rate=44100,
            quality_score=40,
        )

        # Significant improvement (gap >= 50)
        significant = UpgradeCandidate(current_file=current, target_format="flac", quality_gap=60)
        assert "significant" in significant.estimated_improvement.lower()

        # Moderate improvement (25 <= gap < 50)
        moderate = UpgradeCandidate(current_file=current, target_format="flac", quality_gap=30)
        assert "moderate" in moderate.estimated_improvement.lower()

        # Minor improvement (gap < 25)
        minor = UpgradeCandidate(current_file=current, target_format="aac", quality_gap=10)
        assert "minor" in minor.estimated_improvement.lower()

    def test_upgrade_candidate_is_high_priority(self):
        """Test is_high_priority property."""
        current = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=128000,
            sample_rate=44100,
            quality_score=45,
        )

        high_priority = UpgradeCandidate(
            current_file=current, target_format="flac", quality_gap=50, priority_score=80
        )

        low_priority = UpgradeCandidate(
            current_file=current, target_format="aac", quality_gap=10, priority_score=50
        )

        assert high_priority.is_high_priority is True
        assert low_priority.is_high_priority is False

    def test_upgrade_candidate_is_lossless_upgrade(self):
        """Test is_lossless_upgrade property."""
        current = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            quality_score=70,
        )

        lossless = UpgradeCandidate(current_file=current, target_format="flac", quality_gap=30)

        lossy = UpgradeCandidate(current_file=current, target_format="aac", quality_gap=5)

        assert lossless.is_lossless_upgrade is True
        assert lossy.is_lossless_upgrade is False

    def test_upgrade_candidate_has_available_sources(self):
        """Test has_available_sources property."""
        current = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=128000,
            sample_rate=44100,
            quality_score=45,
        )

        with_sources = UpgradeCandidate(
            current_file=current,
            target_format="flac",
            quality_gap=50,
            available_services=["Spotify", "Deezer"],
        )

        without_sources = UpgradeCandidate(
            current_file=current, target_format="flac", quality_gap=50, available_services=[]
        )

        assert with_sources.has_available_sources is True
        assert without_sources.has_available_sources is False

    def test_upgrade_candidate_to_dict(self):
        """Test UpgradeCandidate serialization to dictionary."""
        current = AudioQuality(
            file_path="/music/song.mp3",
            format="mp3",
            bitrate=320000,
            sample_rate=44100,
            quality_score=70,
        )

        candidate = UpgradeCandidate(
            current_file=current,
            target_format="flac",
            quality_gap=30,
            priority_score=85,
            available_services=["Spotify", "Tidal"],
            estimated_improvement="Significant quality improvement",
        )

        data = candidate.to_dict()

        assert "current_file" in data
        assert data["target_format"] == "flac"
        assert data["quality_gap"] == 30
        assert data["priority_score"] == 85
        assert len(data["available_services"]) == 2

    def test_upgrade_candidate_from_dict(self):
        """Test UpgradeCandidate deserialization from dictionary."""
        data = {
            "current_file": {
                "file_path": "/music/track.mp3",
                "format": "mp3",
                "bitrate": 256000,
                "sample_rate": 44100,
                "quality_score": 65,
            },
            "target_format": "flac",
            "quality_gap": 35,
            "priority_score": 75,
            "available_services": ["Deezer", "Qobuz"],
            "estimated_improvement": "Moderate quality improvement",
        }

        candidate = UpgradeCandidate.from_dict(data)

        assert candidate.target_format == "flac"
        assert candidate.quality_gap == 35
        assert candidate.priority_score == 75
        assert len(candidate.available_services) == 2

    def test_upgrade_candidate_from_dict_missing_required_field_raises(self):
        """Test that from_dict raises ValueError when required field is missing."""
        data = {
            "current_file": {
                "file_path": "/music/song.mp3",
                "format": "mp3",
                "bitrate": 320000,
                "sample_rate": 44100,
                "quality_score": 70,
            },
            # Missing 'target_format' and 'quality_gap'
        }

        with pytest.raises(ValueError, match="Missing required field"):
            UpgradeCandidate.from_dict(data)


# ==================== Edge Cases and Integration Tests ====================


class TestEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_audio_quality_round_trip_serialization(self):
        """Test complete round-trip serialization/deserialization."""
        original = AudioQuality(
            file_path="/music/song.flac",
            format="flac",
            bitrate=1411000,
            sample_rate=96000,
            bit_depth=24,
            channels=2,
            duration=245.5,
            is_lossless=True,
            is_vbr=False,
            quality_score=100,
            file_size=35_000_000,
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = AudioQuality.from_dict(data)

        # Compare
        assert restored.file_path == original.file_path
        assert restored.format == original.format
        assert restored.bitrate == original.bitrate
        assert restored.sample_rate == original.sample_rate
        assert restored.quality_score == original.quality_score

    def test_duplicate_group_round_trip_serialization(self):
        """Test complete round-trip serialization/deserialization."""
        files = [
            AudioQuality(
                file_path=f"/music/file{i}.mp3",
                format="mp3",
                bitrate=320000,
                sample_rate=44100,
                quality_score=70,
            )
            for i in range(3)
        ]

        original = DuplicateGroup(
            id="test-round-trip",
            track_hash="hash123",
            files=files,
            recommended_keep=files[0],
            recommended_delete=files[1:],
            confidence=0.88,
            reason="Test round trip",
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = DuplicateGroup.from_dict(data)

        # Compare
        assert restored.id == original.id
        assert restored.track_hash == original.track_hash
        assert len(restored.files) == len(original.files)
        assert restored.confidence == original.confidence

    def test_upgrade_candidate_round_trip_serialization(self):
        """Test complete round-trip serialization/deserialization."""
        current = AudioQuality(
            file_path="/music/old.mp3",
            format="mp3",
            bitrate=128000,
            sample_rate=44100,
            quality_score=40,
        )

        original = UpgradeCandidate(
            current_file=current,
            target_format="flac",
            quality_gap=60,
            priority_score=90,
            available_services=["Spotify", "Deezer", "Tidal"],
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = UpgradeCandidate.from_dict(data)

        # Compare
        assert restored.target_format == original.target_format
        assert restored.quality_gap == original.quality_gap
        assert restored.priority_score == original.priority_score


# ==================== Performance Tests ====================


class TestPerformance:
    """Performance benchmark tests."""

    def test_audio_quality_creation_performance(self, benchmark):
        """Benchmark AudioQuality object creation."""

        def create_audio():
            return AudioQuality(
                file_path="/music/song.mp3",
                format="mp3",
                bitrate=320000,
                sample_rate=44100,
                quality_score=70,
            )

        audio = benchmark(create_audio)
        assert audio is not None

    def test_audio_quality_serialization_performance(self, benchmark):
        """Benchmark AudioQuality serialization."""
        audio = AudioQuality(
            file_path="/music/song.flac",
            format="flac",
            bitrate=1411000,
            sample_rate=96000,
            bit_depth=24,
            quality_score=100,
        )

        data = benchmark(audio.to_dict)
        assert "file_path" in data

    def test_duplicate_group_with_many_files_performance(self, benchmark):
        """Benchmark DuplicateGroup with large number of files."""
        files = [
            AudioQuality(
                file_path=f"/music/file{i}.mp3",
                format="mp3",
                bitrate=320000,
                sample_rate=44100,
                quality_score=70,
            )
            for i in range(100)
        ]

        def create_group():
            return DuplicateGroup(id="perf-test", track_hash="hash", files=files)

        group = benchmark(create_group)
        assert group.file_count == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-disable"])
