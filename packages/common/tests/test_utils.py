"""
Comprehensive test suite for music_tools_common.utils module.

Tests utility functions for correctness, edge cases, and error handling.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from music_tools_common.utils import (
    check_path_traversal,
    check_url_accessible,
    create_resilient_session,
    escape_html,
    format_date,
    format_duration,
    get_domain_from_url,
    get_random_user_agent,
    get_year_from_date,
    is_safe_filename,
    is_valid_date,
    mask_sensitive_value,
    normalize_date,
    parse_date,
    parse_duration,
    retry,
    sanitize_artist_name,
    sanitize_command_argument,
    sanitize_log_message,
    security_validate_file_path,
    validate_email,
    validate_port,
    validate_url,
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

        with pytest.raises(Exception):
            always_fails()


# ==================== VALIDATION TESTS ====================


class TestValidation:
    """Tests for validation utilities."""

    def test_validate_email_valid(self):
        """Test valid email addresses."""
        assert validate_email("user@example.com") is True
        assert validate_email("first.last@domain.co.uk") is True
        assert validate_email("user+tag@example.com") is True

    def test_validate_email_invalid(self):
        """Test invalid email addresses."""
        assert validate_email("invalid") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("") is False

    def test_validate_url_valid(self):
        """Test valid URLs."""
        assert validate_url("https://example.com") is True
        assert validate_url("http://localhost:8080/path") is True
        assert validate_url("https://api.example.com/v1/data?key=value") is True

    def test_validate_url_invalid(self):
        """Test invalid URLs."""
        assert validate_url("javascript:alert(1)") is False
        assert validate_url("file:///etc/passwd") is False
        assert validate_url("not a url") is False
        assert validate_url("") is False


# ==================== DATE TESTS ====================


class TestDate:
    """Tests for date utilities."""

    def test_parse_date_various_formats(self):
        """Test parsing different date formats."""
        success, dt, error = parse_date("2024-03-15")
        assert success is True
        assert dt.year == 2024
        assert dt.month == 3
        assert dt.day == 15

        success, dt, error = parse_date("15/03/2024")
        assert success is True

        success, dt, error = parse_date("2024")
        assert success is True

    def test_format_date(self):
        """Test date formatting."""
        dt = datetime(2024, 3, 15, 14, 30)
        formatted = format_date(dt, "%Y-%m-%d")
        assert formatted == "2024-03-15"

        formatted = format_date(dt, "%B %d, %Y")
        assert formatted == "March 15, 2024"

    def test_normalize_date(self):
        """Test date normalization."""
        assert normalize_date("2024") == "2024-01-01"
        assert normalize_date("2024-03") == "2024-03-01"
        assert normalize_date("15/03/2024") == "2024-03-15"

    def test_get_year_from_date(self):
        """Test year extraction."""
        assert get_year_from_date("2024-03-15") == 2024
        assert get_year_from_date("March 15, 2024") == 2024
        assert get_year_from_date("invalid") is None

    def test_is_valid_date(self):
        """Test date validation."""
        assert is_valid_date("2024-03-15") is True
        assert is_valid_date("1800-01-01") is False
        assert is_valid_date("invalid") is False

    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(125) == "2:05"
        assert format_duration(3725) == "1:02:05"
        assert format_duration(45) == "0:45"

    def test_parse_duration(self):
        """Test duration parsing."""
        assert parse_duration("3:45") == 225
        assert parse_duration("1:23:45") == 5025
        assert parse_duration("180") == 180


# ==================== HTTP TESTS ====================


class TestHTTP:
    """Tests for HTTP utilities."""

    def test_get_random_user_agent(self):
        """Test random user agent generation."""
        agent = get_random_user_agent()
        assert isinstance(agent, str)
        assert len(agent) > 0
        assert "Mozilla" in agent

    def test_create_resilient_session(self):
        """Test session creation."""
        session = create_resilient_session(max_retries=5)
        assert session is not None
        assert "User-Agent" in session.headers

    def test_get_domain_from_url(self):
        """Test domain extraction."""
        assert get_domain_from_url("https://api.example.com/path") == "api.example.com"
        assert get_domain_from_url("http://localhost:8080/test") == "localhost:8080"

    @patch("requests.head")
    def test_check_url_accessible(self, mock_head):
        """Test URL accessibility check."""
        mock_head.return_value.status_code = 200
        assert check_url_accessible("https://example.com") is True

        mock_head.side_effect = Exception("Connection error")
        assert check_url_accessible("https://example.com") is False


# ==================== SECURITY TESTS ====================


class TestSecurity:
    """Tests for security utilities."""

    def test_sanitize_artist_name(self):
        """Test artist name sanitization."""
        assert sanitize_artist_name("Daft Punk") == "Daft Punk"
        assert "<script>" not in sanitize_artist_name("<script>alert(1)</script>")

    def test_sanitize_command_argument(self):
        """Test command argument sanitization."""
        assert ";" not in sanitize_command_argument("file.txt; rm -rf /")
        assert "|" not in sanitize_command_argument("cmd | malicious")

    def test_mask_sensitive_value(self):
        """Test sensitive value masking."""
        masked = mask_sensitive_value("sk-ant-api03-1234567890", visible_chars=4)
        assert masked.startswith("sk-a")
        assert "****" in masked
        assert "1234567890" not in masked

    def test_sanitize_log_message(self):
        """Test log message sanitization."""
        message = "password=mySecretPass123"
        sanitized = sanitize_log_message(message)
        assert "mySecretPass123" not in sanitized
        assert "REDACTED" in sanitized

    def test_is_safe_filename(self):
        """Test filename safety check."""
        assert is_safe_filename("normal_file.txt") is True
        assert is_safe_filename("../../../etc/passwd") is False
        assert is_safe_filename("file/with/path.txt") is False

    def test_escape_html(self):
        """Test HTML escaping."""
        assert (
            escape_html('<script>alert("XSS")</script>')
            == "&lt;script&gt;alert(&quot;XSS&quot;)&lt;&#x2F;script&gt;"
        )
        assert escape_html("Normal text") == "Normal text"

    def test_validate_port(self):
        """Test port validation."""
        is_valid, port, error = validate_port(8080)
        assert is_valid is True
        assert port == 8080

        is_valid, port, error = validate_port(99999)
        assert is_valid is False

        is_valid, port, error = validate_port("not a port")
        assert is_valid is False

    def test_check_path_traversal(self):
        """Test path traversal detection."""
        assert check_path_traversal("../../../etc/passwd") is True
        assert check_path_traversal("/safe/path/file.txt") is False

    def test_security_validate_file_path(self):
        """Test secure file path validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, "test.txt")
            Path(test_file).touch()

            is_valid, safe_path = security_validate_file_path(test_file)
            assert is_valid is True

            # Test path outside base directory
            is_valid, error = security_validate_file_path("/etc/passwd", base_directory=tmpdir)
            assert is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
