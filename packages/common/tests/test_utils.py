"""
Comprehensive test suite for music_tools_common.utils module.

Tests all utility functions for correctness, edge cases, and error handling.
"""

import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Import utilities to test
from music_tools_common.utils import (  # Retry; Validation; File; Date; HTTP; Security
    AsyncRateLimiter,
    RetryRateLimiter,
    ValidationResult,
    check_path_traversal,
    check_url_accessible,
    create_resilient_session,
    ensure_directory,
    escape_html,
    exponential_backoff,
    format_date,
    format_duration,
    format_file_size,
    get_domain_from_url,
    get_file_extension,
    get_file_size,
    get_random_user_agent,
    get_year_from_date,
    is_safe_filename,
    is_valid_date,
    is_valid_file,
    load_json,
    mask_sensitive_value,
    normalize_date,
    parse_date,
    parse_duration,
    retry,
    safe_delete_file,
    safe_read_file,
    safe_write_file,
    sanitize_artist_name,
    sanitize_command_argument,
    sanitize_filename,
    sanitize_log_message,
    save_json,
    security_validate_file_path,
    validate_api_key,
    validate_artist_name,
    validate_batch_size,
    validate_confidence_score,
    validate_email,
    validate_file_extension,
    validate_path,
    validate_port,
    validate_url,
    validate_year,
)

# ==================== RETRY TESTS ====================


class TestRetry:
    """Tests for retry utilities."""

    def test_retry_success_first_attempt(self):
        """Test successful execution on first attempt."""
        @retry(max_attempts=3)
        def succeeds_immediately():
            return "success"

        result = succeeds_immediately()
        assert result == "success"

    def test_retry_success_after_failures(self):
        """Test successful execution after some failures."""
        attempts = []

        @retry(max_attempts=3, delay=0.01)
        def succeeds_on_third():
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("Not yet")
            return "success"

        result = succeeds_on_third()
        assert result == "success"
        assert len(attempts) == 3

    def test_retry_exhausts_attempts(self):
        """Test that retry raises after exhausting attempts."""
        @retry(max_attempts=3, delay=0.01)
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_fails()

    def test_rate_limiter(self):
        """Test RateLimiter enforces delays."""
        limiter = RetryRateLimiter(min_delay=0.1, max_delay=0.2)

        start_time = time.time()
        limiter.wait_if_needed('test.com')
        limiter.wait_if_needed('test.com')
        elapsed = time.time() - start_time

        # Should have waited at least min_delay
        assert elapsed >= 0.1


# ==================== VALIDATION TESTS ====================

class TestValidation:
    """Tests for validation utilities."""

    def test_validate_email_valid(self):
        """Test valid email addresses."""
        assert validate_email('user@example.com') is True
        assert validate_email('first.last@domain.co.uk') is True
        assert validate_email('user+tag@example.com') is True

    def test_validate_email_invalid(self):
        """Test invalid email addresses."""
        assert validate_email('invalid') is False
        assert validate_email('@example.com') is False
        assert validate_email('user@') is False
        assert validate_email('') is False

    def test_validate_url_valid(self):
        """Test valid URLs."""
        assert validate_url('https://example.com') is True
        assert validate_url('http://localhost:8080/path') is True
        assert validate_url('https://api.example.com/v1/data?key=value') is True

    def test_validate_url_invalid(self):
        """Test invalid URLs."""
        assert validate_url('javascript:alert(1)') is False
        assert validate_url('file:///etc/passwd') is False
        assert validate_url('not a url') is False
        assert validate_url('') is False

    def test_validate_api_key(self):
        """Test API key validation."""
        result = validate_api_key('sk-ant-api03-' + 'x' * 50, key_type='anthropic')
        assert result.is_valid is True

        result = validate_api_key('short', key_type='generic')
        assert result.is_valid is False

        result = validate_api_key('', key_type='generic')
        assert result.is_valid is False

    def test_validate_year(self):
        """Test year validation."""
        result = validate_year(2024)
        assert result.is_valid is True
        assert result.normalized_value == 2024

        result = validate_year(1850)
        assert result.is_valid is False

        result = validate_year(None)
        assert result.is_valid is True
        assert result.normalized_value is None

    def test_validate_confidence_score(self):
        """Test confidence score validation."""
        result = validate_confidence_score(0.95)
        assert result.is_valid is True

        result = validate_confidence_score(1.5)
        assert result.is_valid is False

        result = validate_confidence_score(-0.1)
        assert result.is_valid is False

    def test_validate_artist_name(self):
        """Test artist name validation."""
        result = validate_artist_name("Daft Punk")
        assert result.is_valid is True
        assert result.normalized_value == "Daft Punk"

        result = validate_artist_name("")
        assert result.is_valid is False

        result = validate_artist_name("unknown")
        assert result.is_valid is True
        assert len(result.warnings) > 0

    def test_validate_batch_size(self):
        """Test batch size validation."""
        result = validate_batch_size(50)
        assert result.is_valid is True
        assert result.normalized_value == 50

        result = validate_batch_size(0)
        assert result.is_valid is False

        result = validate_batch_size("not a number")
        assert result.is_valid is False


# ==================== FILE TESTS ====================

class TestFile:
    """Tests for file utilities."""

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert sanitize_filename('normal_file.txt') == 'normal_file.txt'
        assert '<' not in sanitize_filename('bad<file>.txt')
        assert '/' not in sanitize_filename('path/to/file.txt')

        # Test length limiting
        long_name = 'a' * 300 + '.txt'
        result = sanitize_filename(long_name, max_length=255)
        assert len(result) <= 255

    def test_ensure_directory(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = os.path.join(tmpdir, 'test', 'nested', 'dir')
            success, error = ensure_directory(test_dir)

            assert success is True
            assert error == ""
            assert os.path.exists(test_dir)

    def test_safe_read_write_file(self):
        """Test safe file reading and writing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'test.txt')
            test_content = "Hello, World!"

            # Write
            success, error = safe_write_file(test_file, test_content)
            assert success is True

            # Read
            success, content, error = safe_read_file(test_file)
            assert success is True
            assert content == test_content

    def test_save_load_json(self):
        """Test JSON save and load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, 'data.json')
            test_data = {'name': 'Daft Punk', 'genre': 'Electronic'}

            # Save
            success, error = save_json(test_data, test_file)
            assert success is True

            # Load
            success, data, error = load_json(test_file)
            assert success is True
            assert data == test_data

    def test_get_file_extension(self):
        """Test file extension extraction."""
        assert get_file_extension('song.mp3') == 'mp3'
        assert get_file_extension('track.FLAC') == 'flac'
        assert get_file_extension('/path/to/file.tar.gz') == 'gz'

    def test_format_file_size(self):
        """Test file size formatting."""
        assert format_file_size(1024) == '1.00 KB'
        assert format_file_size(1536000) == '1.46 MB'
        assert format_file_size(500) == '500 B'


# ==================== DATE TESTS ====================

class TestDate:
    """Tests for date utilities."""

    def test_parse_date_various_formats(self):
        """Test parsing different date formats."""
        success, dt, error = parse_date('2024-03-15')
        assert success is True
        assert dt.year == 2024
        assert dt.month == 3
        assert dt.day == 15

        success, dt, error = parse_date('15/03/2024')
        assert success is True

        success, dt, error = parse_date('2024')
        assert success is True

    def test_format_date(self):
        """Test date formatting."""
        dt = datetime(2024, 3, 15, 14, 30)
        formatted = format_date(dt, '%Y-%m-%d')
        assert formatted == '2024-03-15'

        formatted = format_date(dt, '%B %d, %Y')
        assert formatted == 'March 15, 2024'

    def test_normalize_date(self):
        """Test date normalization."""
        assert normalize_date('2024') == '2024-01-01'
        assert normalize_date('2024-03') == '2024-03-01'
        assert normalize_date('15/03/2024') == '2024-03-15'

    def test_get_year_from_date(self):
        """Test year extraction."""
        assert get_year_from_date('2024-03-15') == 2024
        assert get_year_from_date('March 15, 2024') == 2024
        assert get_year_from_date('invalid') is None

    def test_is_valid_date(self):
        """Test date validation."""
        assert is_valid_date('2024-03-15') is True
        assert is_valid_date('1800-01-01') is False
        assert is_valid_date('invalid') is False

    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(125) == '2:05'
        assert format_duration(3725) == '1:02:05'
        assert format_duration(45) == '0:45'

    def test_parse_duration(self):
        """Test duration parsing."""
        assert parse_duration('3:45') == 225
        assert parse_duration('1:23:45') == 5025
        assert parse_duration('180') == 180


# ==================== HTTP TESTS ====================

class TestHTTP:
    """Tests for HTTP utilities."""

    def test_get_random_user_agent(self):
        """Test random user agent generation."""
        agent = get_random_user_agent()
        assert isinstance(agent, str)
        assert len(agent) > 0
        assert 'Mozilla' in agent

    def test_create_resilient_session(self):
        """Test session creation."""
        session = create_resilient_session(max_retries=5)
        assert session is not None
        assert 'User-Agent' in session.headers

    def test_get_domain_from_url(self):
        """Test domain extraction."""
        assert get_domain_from_url('https://api.example.com/path') == 'api.example.com'
        assert get_domain_from_url('http://localhost:8080/test') == 'localhost:8080'

    @patch('requests.head')
    def test_check_url_accessible(self, mock_head):
        """Test URL accessibility check."""
        mock_head.return_value.status_code = 200
        assert check_url_accessible('https://example.com') is True

        mock_head.side_effect = Exception('Connection error')
        assert check_url_accessible('https://example.com') is False


# ==================== SECURITY TESTS ====================

class TestSecurity:
    """Tests for security utilities."""

    def test_sanitize_artist_name(self):
        """Test artist name sanitization."""
        assert sanitize_artist_name('Daft Punk') == 'Daft Punk'
        assert '<script>' not in sanitize_artist_name('<script>alert(1)</script>')

    def test_sanitize_command_argument(self):
        """Test command argument sanitization."""
        assert ';' not in sanitize_command_argument('file.txt; rm -rf /')
        assert '|' not in sanitize_command_argument('cmd | malicious')

    def test_mask_sensitive_value(self):
        """Test sensitive value masking."""
        masked = mask_sensitive_value('sk-ant-api03-1234567890', visible_chars=4)
        assert masked.startswith('sk-a')
        assert '****' in masked
        assert '1234567890' not in masked

    def test_sanitize_log_message(self):
        """Test log message sanitization."""
        message = "API key: sk-ant-api03-secret123"
        sanitized = sanitize_log_message(message)
        assert 'secret123' not in sanitized
        assert 'REDACTED' in sanitized

    def test_is_safe_filename(self):
        """Test filename safety check."""
        assert is_safe_filename('normal_file.txt') is True
        assert is_safe_filename('../../../etc/passwd') is False
        assert is_safe_filename('file/with/path.txt') is False

    def test_escape_html(self):
        """Test HTML escaping."""
        assert escape_html('<script>alert("XSS")</script>') == '&lt;script&gt;alert(&quot;XSS&quot;)&lt;&#x2F;script&gt;'
        assert escape_html('Normal text') == 'Normal text'

    def test_validate_port(self):
        """Test port validation."""
        is_valid, port, error = validate_port(8080)
        assert is_valid is True
        assert port == 8080

        is_valid, port, error = validate_port(99999)
        assert is_valid is False

        is_valid, port, error = validate_port('not a port')
        assert is_valid is False

    def test_check_path_traversal(self):
        """Test path traversal detection."""
        assert check_path_traversal('../../../etc/passwd') is True
        assert check_path_traversal('/safe/path/file.txt') is False

    def test_security_validate_file_path(self):
        """Test secure file path validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, 'test.txt')
            Path(test_file).touch()

            is_valid, safe_path = security_validate_file_path(test_file)
            assert is_valid is True

            # Test path outside base directory
            is_valid, error = security_validate_file_path('/etc/passwd', base_directory=tmpdir)
            assert is_valid is False


# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """Integration tests combining multiple utilities."""

    def test_complete_file_workflow(self):
        """Test complete file processing workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Sanitize filename
            safe_name = sanitize_filename('My Song: The Remix (2024).json')

            # Create directory
            data_dir = os.path.join(tmpdir, 'data')
            success, _ = ensure_directory(data_dir)
            assert success is True

            # Save data
            file_path = os.path.join(data_dir, safe_name)
            data = {
                'artist': sanitize_artist_name('Daft Punk'),
                'year': 2024,
                'duration': format_duration(225)
            }

            success, _ = save_json(data, file_path)
            assert success is True

            # Load and validate
            success, loaded_data, _ = load_json(file_path)
            assert success is True
            assert loaded_data['artist'] == 'Daft Punk'

    def test_validation_pipeline(self):
        """Test validation pipeline for metadata."""
        # Validate artist
        artist_result = validate_artist_name("Daft Punk")
        assert artist_result.is_valid is True

        # Validate year
        year_result = validate_year(2024)
        assert year_result.is_valid is True

        # Validate confidence
        conf_result = validate_confidence_score(0.95)
        assert conf_result.is_valid is True

        # All validations pass
        assert all([
            artist_result.is_valid,
            year_result.is_valid,
            conf_result.is_valid
        ])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
