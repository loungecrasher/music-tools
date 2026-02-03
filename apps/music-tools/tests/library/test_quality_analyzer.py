"""
Comprehensive test suite for quality_analyzer module.

Tests audio quality scoring, metadata extraction, VBR detection,
duplicate ranking, and filename normalization.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.library.quality_analyzer import (  # Constants
    BITRATE_REFERENCE,
    FORMAT_SCORES,
    MAX_QUALITY_SCORE,
    MIN_QUALITY_SCORE,
    SAMPLE_RATE_HIGH,
    SAMPLE_RATE_MEDIUM,
    SAMPLE_RATE_STANDARD,
    AudioMetadata,
    BitrateType,
    analyze_duplicate_set,
    calculate_quality_score,
    compare_audio_quality,
    extract_audio_metadata,
    get_quality_tier,
    normalize_filename,
    rank_duplicate_group,
)

# ==================== AudioMetadata Tests ====================


class TestAudioMetadata:
    """Test AudioMetadata dataclass validation and initialization."""

    def test_audio_metadata_basic_creation(self):
        """Test basic AudioMetadata creation with minimal fields."""
        metadata = AudioMetadata(
            filepath="/music/song.mp3", format="mp3", bitrate=320, sample_rate=44100
        )

        assert metadata.filepath == "/music/song.mp3"
        assert metadata.format == "mp3"
        assert metadata.bitrate == 320
        assert metadata.sample_rate == 44100
        assert metadata.is_lossless is False
        assert metadata.quality_score > 0

    def test_audio_metadata_lossless_detection(self):
        """Test automatic lossless format detection."""
        flac = AudioMetadata(
            filepath="/music/song.flac", format="flac", bitrate=1411, sample_rate=44100
        )
        assert flac.is_lossless is True

        mp3 = AudioMetadata(
            filepath="/music/song.mp3", format="mp3", bitrate=320, sample_rate=44100
        )
        assert mp3.is_lossless is False

        alac = AudioMetadata(
            filepath="/music/song.m4a", format="alac", bitrate=1411, sample_rate=44100
        )
        assert alac.is_lossless is True

    def test_audio_metadata_invalid_bitrate(self):
        """Test handling of invalid negative bitrate."""
        metadata = AudioMetadata(
            filepath="/music/song.mp3", format="mp3", bitrate=-320, sample_rate=44100  # Invalid
        )

        # Should be set to None with warning
        assert metadata.bitrate is None

    def test_audio_metadata_invalid_sample_rate(self):
        """Test handling of invalid sample rate."""
        metadata = AudioMetadata(
            filepath="/music/song.mp3", format="mp3", bitrate=320, sample_rate=-44100  # Invalid
        )

        assert metadata.sample_rate is None

    def test_audio_metadata_negative_duration(self):
        """Test handling of negative duration."""
        metadata = AudioMetadata(
            filepath="/music/song.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            duration=-10.0,  # Invalid
        )

        assert metadata.duration is None

    def test_audio_metadata_format_from_filepath(self):
        """Test format extraction from filepath when format is empty."""
        metadata = AudioMetadata(
            filepath="/music/song.flac", format="", bitrate=1411, sample_rate=44100  # Empty
        )

        assert metadata.format == "flac"

    def test_audio_metadata_to_dict(self):
        """Test AudioMetadata serialization to dictionary."""
        now = datetime.now(timezone.utc)
        metadata = AudioMetadata(
            filepath="/music/song.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            channels=2,
            duration=225.5,
            bitrate_type=BitrateType.VBR,
            file_size=8_000_000,
            modified_time=now,
        )

        data = metadata.to_dict()

        assert data["filepath"] == "/music/song.mp3"
        assert data["format"] == "mp3"
        assert data["bitrate"] == 320
        assert data["bitrate_type"] == "vbr"
        assert data["modified_time"] == now.isoformat()


# ==================== Quality Score Calculation Tests ====================


class TestCalculateQualityScore:
    """Test quality score calculation algorithm."""

    def test_quality_score_flac_maximum(self):
        """Test that high-quality FLAC gets maximum score."""
        metadata = AudioMetadata(
            filepath="/music/song.flac",
            format="flac",
            bitrate=1411,
            sample_rate=96000,  # High res
            modified_time=datetime.now(timezone.utc),  # Recent
        )

        score = calculate_quality_score(metadata)

        # FLAC (40) + Lossless bitrate (30) + High sample rate (20) + Recent (10) = 100
        assert score == MAX_QUALITY_SCORE

    def test_quality_score_mp3_320_cbr(self):
        """Test quality score for 320kbps CBR MP3."""
        metadata = AudioMetadata(
            filepath="/music/song.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            bitrate_type=BitrateType.CBR,
            modified_time=datetime.now(timezone.utc) - timedelta(days=30),
        )

        score = calculate_quality_score(metadata)

        # MP3 (20) + 320kbps (30) + 44.1kHz (10) + Recent (10) = 70
        assert score == 70

    def test_quality_score_mp3_vbr_bonus(self):
        """Test that VBR gets bonus points over CBR at sub-max bitrate."""
        # Use 256kbps so the +2 VBR bonus isn't capped at BITRATE_WEIGHT
        cbr_metadata = AudioMetadata(
            filepath="/music/cbr.mp3",
            format="mp3",
            bitrate=256,
            sample_rate=44100,
            bitrate_type=BitrateType.CBR,
            modified_time=datetime.now(timezone.utc),
        )

        vbr_metadata = AudioMetadata(
            filepath="/music/vbr.mp3",
            format="mp3",
            bitrate=256,
            sample_rate=44100,
            bitrate_type=BitrateType.VBR,
            modified_time=datetime.now(timezone.utc),
        )

        cbr_score = calculate_quality_score(cbr_metadata)
        vbr_score = calculate_quality_score(vbr_metadata)

        # VBR should get +2 bonus
        assert vbr_score == cbr_score + 2

    def test_quality_score_low_bitrate_mp3(self):
        """Test quality score for low bitrate MP3."""
        metadata = AudioMetadata(
            filepath="/music/low.mp3",
            format="mp3",
            bitrate=128,
            sample_rate=44100,
            bitrate_type=BitrateType.CBR,
            modified_time=datetime.now(timezone.utc) - timedelta(days=2000),  # Old
        )

        score = calculate_quality_score(metadata)

        # MP3 (20) + 128kbps (12) + 44.1kHz (10) + Old (0) = 42
        assert 40 <= score <= 45

    def test_quality_score_sample_rate_tiers(self):
        """Test quality score variations with different sample rates."""
        # High res (96kHz+)
        high_res = AudioMetadata(filepath="/music/high.flac", format="flac", sample_rate=96000)
        high_score = calculate_quality_score(high_res)

        # Medium (48kHz)
        medium = AudioMetadata(filepath="/music/med.flac", format="flac", sample_rate=48000)
        medium_score = calculate_quality_score(medium)

        # Standard (44.1kHz)
        standard = AudioMetadata(filepath="/music/std.flac", format="flac", sample_rate=44100)
        standard_score = calculate_quality_score(standard)

        # High res should score higher
        assert high_score > medium_score > standard_score

    def test_quality_score_recency_tiers(self):
        """Test quality score variations based on file age."""
        now = datetime.now(timezone.utc)

        # Recent (< 1 year)
        recent = AudioMetadata(
            filepath="/music/recent.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            modified_time=now - timedelta(days=30),
        )

        # Moderate (1-5 years)
        moderate = AudioMetadata(
            filepath="/music/moderate.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            modified_time=now - timedelta(days=730),  # 2 years
        )

        # Old (> 5 years)
        old = AudioMetadata(
            filepath="/music/old.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            modified_time=now - timedelta(days=2000),  # 5+ years
        )

        recent_score = calculate_quality_score(recent)
        moderate_score = calculate_quality_score(moderate)
        old_score = calculate_quality_score(old)

        # Recent should get 10 pts, moderate 5 pts, old 0 pts
        assert recent_score == moderate_score + 5
        assert moderate_score == old_score + 5

    def test_quality_score_none_metadata_raises(self):
        """Test that None metadata raises ValueError."""
        with pytest.raises(ValueError, match="metadata cannot be None"):
            calculate_quality_score(None)

    def test_quality_score_no_bitrate_info(self):
        """Test quality score when bitrate is None."""
        metadata = AudioMetadata(
            filepath="/music/song.mp3", format="mp3", bitrate=None, sample_rate=44100
        )

        score = calculate_quality_score(metadata)

        # Should get minimal bitrate points (5)
        assert score > 0


# ==================== Metadata Extraction Tests ====================


class TestExtractAudioMetadata:
    """Test audio metadata extraction with mocked mutagen."""

    def test_extract_metadata_empty_filepath_raises(self):
        """Test that empty filepath raises ValueError."""
        with pytest.raises(ValueError, match="filepath cannot be None or empty"):
            extract_audio_metadata("")

        with pytest.raises(ValueError, match="filepath cannot be None or empty"):
            extract_audio_metadata(None)

    @patch("src.library.quality_analyzer.MutagenFile", None)
    def test_extract_metadata_no_mutagen_raises(self):
        """Test that missing mutagen raises ImportError."""
        with pytest.raises(ImportError, match="mutagen library is required"):
            extract_audio_metadata("/music/song.mp3")

    @patch("src.library.quality_analyzer.MutagenFile")
    @patch("src.library.quality_analyzer.Path")
    def test_extract_metadata_file_not_exists(self, mock_path, mock_mutagen):
        """Test handling when file does not exist."""
        mock_file_path = Mock()
        mock_file_path.exists.return_value = False
        mock_path.return_value.resolve.return_value = mock_file_path

        result = extract_audio_metadata("/music/nonexistent.mp3")

        assert result is None

    @patch("src.library.quality_analyzer.MutagenFile")
    @patch("src.library.quality_analyzer.Path")
    def test_extract_metadata_mp3_cbr(self, mock_path, mock_mutagen):
        """Test MP3 metadata extraction with CBR."""
        # Setup mock file
        mock_file_path = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.suffix = ".mp3"
        mock_file_path.stat.return_value.st_size = 8_000_000
        mock_file_path.stat.return_value.st_mtime = datetime.now(timezone.utc).timestamp()
        mock_path.return_value.resolve.return_value = mock_file_path

        # Setup mock mutagen
        mock_audio = Mock()
        mock_info = Mock()
        mock_info.bitrate = 320000
        mock_info.sample_rate = 44100
        mock_info.channels = 2
        mock_info.length = 225.5
        mock_info.bitrate_mode = None  # CBR
        mock_audio.info = mock_info
        mock_mutagen.return_value = mock_audio

        result = extract_audio_metadata("/music/song.mp3")

        assert result is not None
        assert result.format == "mp3"
        assert result.bitrate == 320
        assert result.sample_rate == 44100
        assert result.channels == 2
        assert result.duration == 225.5
        assert result.file_size == 8_000_000

    @patch("src.library.quality_analyzer.MutagenFile")
    @patch("src.library.quality_analyzer.BitrateMode")
    @patch("src.library.quality_analyzer.Path")
    def test_extract_metadata_mp3_vbr_detection(self, mock_path, mock_bitrate_mode, mock_mutagen):
        """Test VBR detection for MP3 files."""
        # Setup BitrateMode enum
        mock_bitrate_mode.VBR = "VBR"
        mock_bitrate_mode.CBR = "CBR"
        mock_bitrate_mode.ABR = "ABR"

        # Setup mock file
        mock_file_path = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.suffix = ".mp3"
        mock_file_path.stat.return_value.st_size = 7_000_000
        mock_file_path.stat.return_value.st_mtime = datetime.now(timezone.utc).timestamp()
        mock_path.return_value.resolve.return_value = mock_file_path

        # Setup mock mutagen with VBR
        mock_audio = Mock()
        mock_info = Mock()
        mock_info.bitrate = 256000
        mock_info.sample_rate = 44100
        mock_info.channels = 2
        mock_info.length = 225.5
        mock_info.bitrate_mode = mock_bitrate_mode.VBR
        mock_audio.info = mock_info
        mock_mutagen.return_value = mock_audio

        result = extract_audio_metadata("/music/vbr.mp3")

        assert result is not None
        assert result.bitrate_type == BitrateType.VBR

    @patch("src.library.quality_analyzer.MutagenFile")
    @patch("src.library.quality_analyzer.Path")
    def test_extract_metadata_flac(self, mock_path, mock_mutagen):
        """Test FLAC metadata extraction."""
        # Setup mock file
        mock_file_path = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.suffix = ".flac"
        mock_file_path.stat.return_value.st_size = 25_000_000
        mock_file_path.stat.return_value.st_mtime = datetime.now(timezone.utc).timestamp()
        mock_path.return_value.resolve.return_value = mock_file_path

        # Setup mock mutagen
        mock_audio = Mock()
        mock_info = Mock()
        mock_info.bitrate = 1411000
        mock_info.sample_rate = 96000
        mock_info.channels = 2
        mock_info.length = 225.5
        mock_audio.info = mock_info
        mock_mutagen.return_value = mock_audio

        result = extract_audio_metadata("/music/song.flac")

        assert result is not None
        assert result.format == "flac"
        assert result.bitrate == 1411
        assert result.sample_rate == 96000
        assert result.is_lossless is True

    @patch("src.library.quality_analyzer.MutagenFile")
    @patch("src.library.quality_analyzer.Path")
    def test_extract_metadata_mutagen_returns_none(self, mock_path, mock_mutagen):
        """Test handling when mutagen cannot read file."""
        mock_file_path = Mock()
        mock_file_path.exists.return_value = True
        mock_path.return_value.resolve.return_value = mock_file_path

        mock_mutagen.return_value = None

        result = extract_audio_metadata("/music/corrupt.mp3")

        assert result is None


# ==================== Filename Normalization Tests ====================


class TestNormalizeFilename:
    """Test filename normalization for duplicate matching."""

    def test_normalize_filename_basic(self):
        """Test basic filename normalization."""
        result = normalize_filename("Song Title.mp3")
        assert result == "song title.mp3"

    def test_normalize_filename_brackets_removed(self):
        """Test that brackets and their contents are removed."""
        result = normalize_filename("Song [320kbps].mp3")
        assert "[" not in result
        assert "320kbps" not in result
        assert "song" in result

        result = normalize_filename("Track (Remastered).flac")
        assert "(" not in result
        assert "remastered" not in result

    def test_normalize_filename_format_markers_removed(self):
        """Test that format markers are removed."""
        result = normalize_filename("Song-320-MP3.mp3")
        assert "320" not in result
        assert "mp3" in result.split(".")[-1]  # Extension preserved

        result = normalize_filename("Track FLAC.flac")
        assert result == "track.flac"

    def test_normalize_filename_underscores_to_spaces(self):
        """Test underscores and hyphens converted to spaces."""
        result = normalize_filename("Artist_Name-Song_Title.mp3")
        assert "_" not in result
        assert "-" not in result
        assert "artist name song title.mp3" == result

    def test_normalize_filename_multiple_spaces_collapsed(self):
        """Test multiple spaces collapsed to single space."""
        result = normalize_filename("Song    With    Spaces.mp3")
        assert "    " not in result
        assert "song with spaces.mp3" == result

    def test_normalize_filename_empty_string(self):
        """Test empty string returns empty."""
        result = normalize_filename("")
        assert result == ""

    def test_normalize_filename_none(self):
        """Test None returns empty string."""
        result = normalize_filename(None)
        assert result == ""

    def test_normalize_filename_complex_example(self):
        """Test complex real-world example."""
        original = "Daft_Punk-Around_The_World-[320kbps]-VBR.mp3"
        result = normalize_filename(original)

        # Should be simplified
        assert "_" not in result
        assert "[" not in result
        assert "320kbps" not in result
        assert "vbr" not in result.lower() or "vbr" not in result
        assert (
            "daft punk around the world.mp3" == result
            or "daft punk around the world .mp3" == result
        )


# ==================== Duplicate Ranking Tests ====================


class TestRankDuplicateGroup:
    """Test duplicate file ranking algorithm."""

    def test_rank_duplicate_group_empty_raises(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="files cannot be None or empty"):
            rank_duplicate_group([])

        with pytest.raises(ValueError, match="files cannot be None or empty"):
            rank_duplicate_group(None)

    def test_rank_duplicate_group_single_file(self):
        """Test ranking with single file returns it as keeper."""
        metadata = AudioMetadata(
            filepath="/music/only.mp3", format="mp3", bitrate=320, sample_rate=44100
        )

        keep, delete = rank_duplicate_group([metadata])

        assert keep == metadata
        assert len(delete) == 0

    def test_rank_duplicate_group_quality_priority(self):
        """Test that highest quality file is kept."""
        flac = AudioMetadata(
            filepath="/music/song.flac",
            format="flac",
            bitrate=1411,
            sample_rate=96000,
            file_size=25_000_000,
        )

        mp3_320 = AudioMetadata(
            filepath="/music/song_320.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            file_size=8_000_000,
        )

        mp3_128 = AudioMetadata(
            filepath="/music/song_128.mp3",
            format="mp3",
            bitrate=128,
            sample_rate=44100,
            file_size=4_000_000,
        )

        files = [mp3_128, mp3_320, flac]  # Intentionally out of order
        keep, delete = rank_duplicate_group(files)

        assert keep == flac
        assert mp3_320 in delete
        assert mp3_128 in delete
        assert len(delete) == 2

    def test_rank_duplicate_group_quality_tie_size_tiebreaker(self):
        """Test that larger file size is used as tiebreaker."""
        # Two MP3s with same quality score but different sizes
        mp3_large = AudioMetadata(
            filepath="/music/large.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            file_size=9_000_000,  # Larger
            modified_time=datetime.now(timezone.utc),
        )

        mp3_small = AudioMetadata(
            filepath="/music/small.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            file_size=7_000_000,  # Smaller
            modified_time=datetime.now(timezone.utc),
        )

        # Force same quality score
        mp3_large.quality_score = 70
        mp3_small.quality_score = 70

        files = [mp3_small, mp3_large]
        keep, delete = rank_duplicate_group(files)

        # Larger file should be kept
        assert keep == mp3_large
        assert delete[0] == mp3_small


# ==================== Quality Comparison Tests ====================


class TestCompareAudioQuality:
    """Test audio quality comparison function."""

    def test_compare_audio_quality_none_raises(self):
        """Test that None arguments raise ValueError."""
        metadata = AudioMetadata(
            filepath="/music/test.mp3", format="mp3", bitrate=320, sample_rate=44100
        )

        with pytest.raises(ValueError, match="Cannot compare None files"):
            compare_audio_quality(None, metadata)

        with pytest.raises(ValueError, match="Cannot compare None files"):
            compare_audio_quality(metadata, None)

    def test_compare_audio_quality_higher_score_wins(self):
        """Test that file with higher quality score wins."""
        flac = AudioMetadata(
            filepath="/music/song.flac", format="flac", bitrate=1411, sample_rate=96000
        )
        mp3 = AudioMetadata(
            filepath="/music/song.mp3", format="mp3", bitrate=320, sample_rate=44100
        )

        result = compare_audio_quality(flac, mp3)

        assert result > 0  # FLAC is higher quality

    def test_compare_audio_quality_same_score_size_tiebreaker(self):
        """Test that file size breaks ties."""
        large = AudioMetadata(
            filepath="/music/large.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            file_size=9_000_000,
        )
        small = AudioMetadata(
            filepath="/music/small.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            file_size=7_000_000,
        )

        # Force same score
        large.quality_score = 70
        small.quality_score = 70

        result = compare_audio_quality(large, small)

        assert result > 0  # Larger file wins


# ==================== Quality Tier Tests ====================


class TestGetQualityTier:
    """Test quality tier labeling."""

    def test_get_quality_tier_excellent(self):
        """Test excellent tier (80+)."""
        assert get_quality_tier(100) == "Excellent"
        assert get_quality_tier(85) == "Excellent"
        assert get_quality_tier(80) == "Excellent"

    def test_get_quality_tier_good(self):
        """Test good tier (60-79)."""
        assert get_quality_tier(79) == "Good"
        assert get_quality_tier(70) == "Good"
        assert get_quality_tier(60) == "Good"

    def test_get_quality_tier_fair(self):
        """Test fair tier (40-59)."""
        assert get_quality_tier(59) == "Fair"
        assert get_quality_tier(50) == "Fair"
        assert get_quality_tier(40) == "Fair"

    def test_get_quality_tier_poor(self):
        """Test poor tier (1-39)."""
        assert get_quality_tier(39) == "Poor"
        assert get_quality_tier(20) == "Poor"
        assert get_quality_tier(1) == "Poor"

    def test_get_quality_tier_unknown(self):
        """Test unknown tier (0)."""
        assert get_quality_tier(0) == "Unknown"


# ==================== Duplicate Set Analysis Tests ====================


class TestAnalyzeDuplicateSet:
    """Test complete duplicate set analysis."""

    def test_analyze_duplicate_set_empty_raises(self):
        """Test that empty filepath list raises ValueError."""
        with pytest.raises(ValueError, match="filepaths cannot be None or empty"):
            analyze_duplicate_set([])

        with pytest.raises(ValueError, match="filepaths cannot be None or empty"):
            analyze_duplicate_set(None)

    @patch("src.library.quality_analyzer.extract_audio_metadata")
    def test_analyze_duplicate_set_success(self, mock_extract):
        """Test successful duplicate set analysis."""
        # Setup mock metadata
        flac_meta = AudioMetadata(
            filepath="/music/song.flac",
            format="flac",
            bitrate=1411,
            sample_rate=96000,
            file_size=25_000_000,
        )
        mp3_meta = AudioMetadata(
            filepath="/music/song.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            file_size=8_000_000,
        )

        mock_extract.side_effect = [flac_meta, mp3_meta]

        result = analyze_duplicate_set(["/music/song.flac", "/music/song.mp3"])

        assert result["total_files"] == 2
        assert result["recommended_keep"] == flac_meta
        assert mp3_meta in result["recommended_delete"]
        assert result["size_saved_mb"] > 0
        assert result["lossless_count"] == 1

    @patch("src.library.quality_analyzer.extract_audio_metadata")
    def test_analyze_duplicate_set_no_valid_files_raises(self, mock_extract):
        """Test that no valid files raises ValueError."""
        mock_extract.return_value = None

        with pytest.raises(ValueError, match="No valid audio files found"):
            analyze_duplicate_set(["/music/corrupt1.mp3", "/music/corrupt2.mp3"])


# ==================== Edge Cases and Error Handling ====================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_quality_score_with_no_sample_rate(self):
        """Test quality score calculation with missing sample rate."""
        metadata = AudioMetadata(
            filepath="/music/song.mp3", format="mp3", bitrate=320, sample_rate=None
        )

        score = calculate_quality_score(metadata)

        # Should still calculate with default sample rate points
        assert score > 0

    def test_quality_score_with_no_modified_time(self):
        """Test quality score calculation with missing modified time."""
        metadata = AudioMetadata(
            filepath="/music/song.mp3",
            format="mp3",
            bitrate=320,
            sample_rate=44100,
            modified_time=None,
        )

        score = calculate_quality_score(metadata)

        # Should assume old (0 recency points)
        assert score > 0

    def test_quality_score_unknown_format(self):
        """Test quality score with unknown format."""
        metadata = AudioMetadata(
            filepath="/music/song.xyz", format="xyz", bitrate=320, sample_rate=44100  # Unknown
        )

        score = calculate_quality_score(metadata)

        # Should get default format score (10)
        assert score > 0


# ==================== Performance Benchmarks ====================


class TestPerformance:
    """Performance benchmark tests."""

    def test_calculate_quality_score_performance(self, benchmark):
        """Benchmark quality score calculation speed."""
        metadata = AudioMetadata(
            filepath="/music/song.mp3", format="mp3", bitrate=320, sample_rate=44100
        )

        # Should complete in < 1ms
        result = benchmark(calculate_quality_score, metadata)
        assert result > 0

    def test_normalize_filename_performance(self, benchmark):
        """Benchmark filename normalization speed."""
        filename = "Artist_Name-Song_Title-[320kbps]-VBR.mp3"

        # Should complete in < 1ms
        result = benchmark(normalize_filename, filename)
        assert len(result) > 0

    def test_rank_duplicate_group_performance(self, benchmark):
        """Benchmark duplicate ranking with large group."""
        # Create 100 files
        files = [
            AudioMetadata(
                filepath=f"/music/song{i}.mp3",
                format="mp3",
                bitrate=128 + (i * 2),  # Varying bitrates
                sample_rate=44100,
                file_size=4_000_000 + (i * 10000),
            )
            for i in range(100)
        ]

        # Should complete in < 10ms
        keep, delete = benchmark(rank_duplicate_group, files)
        assert keep is not None
        assert len(delete) == 99


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-disable"])
