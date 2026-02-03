"""Tests for security utilities module."""

from pathlib import Path

import pytest
from music_tools_common.utils.security import (
    SecureFileHandler,
    check_path_traversal,
    is_safe_filename,
    mask_sensitive_value,
    sanitize_artist_name,
    sanitize_command_args,
    sanitize_filename,
    sanitize_log_message,
    validate_batch_size,
    validate_file_path,
)


class TestPathValidation:
    """Tests for path validation functions."""

    def test_validate_file_path_safe(self, tmp_path):
        """Test validation of safe file path."""
        safe_file = tmp_path / "test.txt"
        safe_file.touch()

        is_valid, result = validate_file_path(str(safe_file), str(tmp_path))
        assert is_valid
        assert Path(result) == safe_file

    def test_validate_file_path_traversal(self, tmp_path):
        """Test rejection of path traversal attempts."""
        traversal_path = str(tmp_path / ".." / ".." / "etc" / "passwd")

        is_valid, error_msg = validate_file_path(traversal_path, str(tmp_path))
        assert not is_valid
        assert "outside base directory" in error_msg.lower()

    def test_validate_file_path_null_byte(self):
        """Test rejection of null byte injection."""
        null_byte_path = "/safe/path\x00/../../etc/passwd"

        is_valid, error_msg = validate_file_path(null_byte_path)
        assert not is_valid
        assert "null byte" in error_msg.lower()

    def test_check_path_traversal_detected(self):
        """Test detection of path traversal patterns."""
        assert check_path_traversal("../../../etc/passwd")
        assert check_path_traversal("..\\..\\windows\\system32")
        assert check_path_traversal("/safe/path/../../../etc")

    def test_check_path_traversal_safe(self):
        """Test acceptance of safe paths."""
        assert not check_path_traversal("/safe/path/to/file.txt")
        assert not check_path_traversal("relative/safe/path.txt")
        assert not check_path_traversal("/path/with/../normalized")

    def test_is_safe_filename_safe(self):
        """Test validation of safe filenames."""
        assert is_safe_filename("document.txt")
        assert is_safe_filename("my_file-2023.pdf")
        assert is_safe_filename("test (1).jpg")

    def test_is_safe_filename_unsafe(self):
        """Test rejection of unsafe filenames."""
        assert not is_safe_filename("../etc/passwd")
        assert not is_safe_filename("/etc/passwd")
        assert not is_safe_filename("file\x00.txt")
        assert not is_safe_filename("file\nwith\nnewlines")


class TestSanitization:
    """Tests for input sanitization functions."""

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        assert sanitize_filename("normal_file.txt") == "normal_file.txt"
        assert sanitize_filename("file with spaces.txt") == "file_with_spaces.txt"

    def test_sanitize_filename_special_chars(self):
        """Test removal of special characters."""
        result = sanitize_filename("file|with<bad>chars*.txt")
        assert "|" not in result
        assert "<" not in result
        assert ">" not in result
        assert "*" not in result

    def test_sanitize_filename_path_separators(self):
        """Test removal of path separators."""
        result = sanitize_filename("../../dangerous/path.txt")
        assert "/" not in result
        assert "\\" not in result

    def test_sanitize_artist_name_basic(self):
        """Test basic artist name sanitization."""
        assert sanitize_artist_name("Taylor Swift") == "Taylor Swift"
        assert sanitize_artist_name("AC/DC") == "AC/DC"

    def test_sanitize_artist_name_control_chars(self):
        """Test removal of control characters."""
        result = sanitize_artist_name("Artist\x00Name\x0B")
        assert "\x00" not in result
        assert "\x0B" not in result

    def test_sanitize_artist_name_length_limit(self):
        """Test length limiting."""
        long_name = "A" * 500
        result = sanitize_artist_name(long_name, max_length=255)
        assert len(result) == 255

    def test_sanitize_command_args_basic(self):
        """Test basic command argument sanitization."""
        assert sanitize_command_args("safe_arg") == "safe_arg"
        assert sanitize_command_args("safe-arg-123") == "safe-arg-123"

    def test_sanitize_command_args_shell_metacharacters(self):
        """Test removal of shell metacharacters."""
        dangerous = "cmd; rm -rf /"
        result = sanitize_command_args(dangerous)
        assert ";" not in result
        assert "|" not in result

    def test_sanitize_command_args_list(self):
        """Test sanitization of command argument list."""
        args = ["safe", "arg;dangerous", "another|bad"]
        result = sanitize_command_args(args)
        assert isinstance(result, list)
        assert result[0] == "safe"
        assert ";" not in result[1]
        assert "|" not in result[2]


class TestBatchValidation:
    """Tests for batch size validation."""

    def test_validate_batch_size_valid(self):
        """Test validation of valid batch sizes."""
        is_valid, size = validate_batch_size(50, max_size=100)
        assert is_valid
        assert size == 50

    def test_validate_batch_size_too_large(self):
        """Test rejection of oversized batches."""
        is_valid, size = validate_batch_size(500, max_size=100)
        assert not is_valid
        assert size == 100  # Capped to max

    def test_validate_batch_size_negative(self):
        """Test rejection of negative batch sizes."""
        is_valid, size = validate_batch_size(-10)
        assert not is_valid
        assert size == 1  # Minimum value

    def test_validate_batch_size_zero(self):
        """Test handling of zero batch size."""
        is_valid, size = validate_batch_size(0)
        assert not is_valid
        assert size == 1  # Minimum value


class TestSensitiveDataHandling:
    """Tests for sensitive data masking and sanitization."""

    def test_mask_sensitive_value_default(self):
        """Test default masking behavior."""
        result = mask_sensitive_value("sk-ant-api-key-12345678")
        assert result.startswith("sk-a")
        assert "***" in result
        assert "5678" in result
        assert len(result) < len("sk-ant-api-key-12345678")

    def test_mask_sensitive_value_custom_chars(self):
        """Test masking with custom visible characters."""
        result = mask_sensitive_value("secret123", visible_chars=2)
        assert result == "se******23"

    def test_mask_sensitive_value_short_string(self):
        """Test masking of very short strings."""
        result = mask_sensitive_value("abc")
        assert "***" in result

    def test_sanitize_log_message_api_keys(self):
        """Test sanitization of API keys in log messages."""
        msg = "Using API key: sk-ant-api-key-12345678"
        result = sanitize_log_message(msg)
        assert "sk-ant-api-key-12345678" not in result
        assert "***" in result

    def test_sanitize_log_message_tokens(self):
        """Test sanitization of auth tokens."""
        msg = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = sanitize_log_message(msg)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "***" in result

    def test_sanitize_log_message_passwords(self):
        """Test sanitization of passwords."""
        msg = "password=mySecretPass123"
        result = sanitize_log_message(msg)
        assert "mySecretPass123" not in result
        assert "***" in result

    def test_sanitize_log_message_newline_injection(self):
        """Test prevention of log injection via newlines."""
        msg = "User input: test\nINJECTED LOG ENTRY"
        result = sanitize_log_message(msg)
        assert "\n" not in result or result.count("\n") == 0


class TestSecureFileHandler:
    """Tests for SecureFileHandler class."""

    def test_secure_file_handler_init(self, tmp_path):
        """Test SecureFileHandler initialization."""
        handler = SecureFileHandler(base_directory=str(tmp_path))
        assert handler.base_directory == str(tmp_path)

    def test_safe_read_success(self, tmp_path):
        """Test successful file reading."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        handler = SecureFileHandler(base_directory=str(tmp_path))
        success, content, error = handler.safe_read(str(test_file))

        assert success
        assert content == "test content"
        assert error is None

    def test_safe_read_traversal_blocked(self, tmp_path):
        """Test blocking of path traversal in read."""
        handler = SecureFileHandler(base_directory=str(tmp_path))
        traversal_path = str(tmp_path / ".." / ".." / "etc" / "passwd")

        success, content, error = handler.safe_read(traversal_path)

        assert not success
        assert content is None
        assert "outside base directory" in error.lower()

    def test_safe_write_success(self, tmp_path):
        """Test successful file writing."""
        handler = SecureFileHandler(base_directory=str(tmp_path))
        test_file = tmp_path / "new_file.txt"

        success, path, error = handler.safe_write(str(test_file), "new content")

        assert success
        assert Path(path).exists()
        assert Path(path).read_text() == "new content"
        # Check secure permissions
        assert oct(Path(path).stat().st_mode)[-3:] == "600"

    def test_safe_write_creates_parent_dirs(self, tmp_path):
        """Test automatic creation of parent directories."""
        handler = SecureFileHandler(base_directory=str(tmp_path))
        nested_file = tmp_path / "dir1" / "dir2" / "file.txt"

        success, path, error = handler.safe_write(str(nested_file), "content")

        assert success
        assert Path(path).exists()
        assert Path(path).parent.exists()

    def test_safe_delete_success(self, tmp_path):
        """Test successful file deletion."""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("content")

        handler = SecureFileHandler(base_directory=str(tmp_path))
        success, error = handler.safe_delete(str(test_file))

        assert success
        assert not test_file.exists()

    def test_safe_delete_traversal_blocked(self, tmp_path):
        """Test blocking of path traversal in delete."""
        handler = SecureFileHandler(base_directory=str(tmp_path))
        traversal_path = str(tmp_path / ".." / ".." / "important" / "file.txt")

        success, error = handler.safe_delete(traversal_path)

        assert not success
        assert "outside base directory" in error.lower()


class TestIntegration:
    """Integration tests for security utilities."""

    def test_end_to_end_safe_file_operations(self, tmp_path):
        """Test complete workflow of secure file operations."""
        handler = SecureFileHandler(base_directory=str(tmp_path))

        # Write a file
        file_path = tmp_path / "sensitive_data.json"
        success, path, _ = handler.safe_write(str(file_path), '{"api_key": "secret"}')
        assert success

        # Verify permissions
        assert oct(Path(path).stat().st_mode)[-3:] == "600"

        # Read it back
        success, content, _ = handler.safe_read(str(file_path))
        assert success
        assert "secret" in content

        # Sanitize for logging
        sanitized = sanitize_log_message(f"Loaded config: {content}")
        assert "secret" not in sanitized

        # Delete it
        success, _ = handler.safe_delete(str(file_path))
        assert success
        assert not file_path.exists()

    def test_artist_name_workflow(self):
        """Test artist name sanitization workflow."""
        # User input with potential issues
        raw_input = "Artist Name\x00../../../etc"

        # Sanitize
        safe_name = sanitize_artist_name(raw_input)

        # Verify safety
        assert "\x00" not in safe_name
        assert not check_path_traversal(safe_name)

        # Safe to log
        log_msg = f"Processing artist: {safe_name}"
        sanitized_log = sanitize_log_message(log_msg)
        assert sanitized_log  # Should not be empty


# Run with: pytest packages/common/tests/test_security.py -v
