"""
Tests for validation utilities.
"""
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.validation import (
    validate_spotify_config,
    validate_deezer_config,
    validate_anthropic_config,
    validate_config,
    validate_path
)


class TestValidation:
    """Test suite for validation functions."""

    def test_validate_spotify_config_valid(self):
        """Test Spotify config validation with valid data."""
        config = {
            'client_id': '12345678901234567890123456789012',  # 32 chars
            'client_secret': '12345678901234567890123456789012',  # 32 chars
            'redirect_uri': 'http://localhost:8888/callback'
        }
        errors = validate_spotify_config(config)
        assert len(errors) == 0

    def test_validate_spotify_config_missing_client_id(self):
        """Test Spotify config validation with missing client_id."""
        config = {
            'client_secret': '12345678901234567890123456789012',
            'redirect_uri': 'http://localhost:8888/callback'
        }
        errors = validate_spotify_config(config)
        assert any('client_id' in error.lower() for error in errors)

    def test_validate_spotify_config_invalid_redirect_uri(self):
        """Test Spotify config validation with invalid redirect URI."""
        config = {
            'client_id': '12345678901234567890123456789012',
            'client_secret': '12345678901234567890123456789012',
            'redirect_uri': 'invalid-uri'
        }
        errors = validate_spotify_config(config)
        assert any('redirect_uri' in error.lower() for error in errors)

    def test_validate_deezer_config_valid(self):
        """Test Deezer config validation with valid data."""
        config = {
            'email': 'test@example.com'
        }
        errors = validate_deezer_config(config)
        assert len(errors) == 0

    def test_validate_deezer_config_invalid_email(self):
        """Test Deezer config validation with invalid email."""
        config = {
            'email': 'invalid-email'
        }
        errors = validate_deezer_config(config)
        assert any('email' in error.lower() for error in errors)

    def test_validate_deezer_config_missing_email(self):
        """Test Deezer config validation with missing email."""
        config = {}
        errors = validate_deezer_config(config)
        assert any('email' in error.lower() for error in errors)

    def test_validate_anthropic_config_valid(self):
        """Test Anthropic config validation with valid data."""
        config = {
            'api_key': 'sk-test-key-12345',
            'model': 'claude-3-5-sonnet-20241022'
        }
        errors = validate_anthropic_config(config)
        assert len(errors) == 0

    def test_validate_anthropic_config_invalid_key(self):
        """Test Anthropic config validation with invalid API key."""
        config = {
            'api_key': 'invalid-key',
            'model': 'claude-3-5-sonnet-20241022'
        }
        errors = validate_anthropic_config(config)
        assert any('api_key' in error.lower() for error in errors)

    def test_validate_anthropic_config_missing_model(self):
        """Test Anthropic config validation with missing model."""
        config = {
            'api_key': 'sk-test-key-12345'
        }
        errors = validate_anthropic_config(config)
        assert any('model' in error.lower() for error in errors)

    def test_validate_config_dispatcher(self):
        """Test that validate_config correctly dispatches to service validators."""
        # Test Spotify
        spotify_config = {
            'client_id': '12345678901234567890123456789012',
            'client_secret': '12345678901234567890123456789012',
            'redirect_uri': 'http://localhost:8888/callback'
        }
        errors = validate_config('spotify', spotify_config)
        assert len(errors) == 0

        # Test Deezer
        deezer_config = {'email': 'test@example.com'}
        errors = validate_config('deezer', deezer_config)
        assert len(errors) == 0

        # Test unknown service
        errors = validate_config('unknown_service', {})
        assert len(errors) == 0  # Should not crash, just log warning

    def test_validate_path_empty(self):
        """Test path validation with empty path."""
        errors = validate_path('')
        assert any('empty' in error.lower() for error in errors)

    def test_validate_path_exists(self, tmp_path):
        """Test path validation with existing path."""
        errors = validate_path(str(tmp_path), must_exist=True)
        assert len(errors) == 0

    def test_validate_path_not_exists(self):
        """Test path validation with non-existing path."""
        errors = validate_path('/nonexistent/path/to/directory', must_exist=True)
        assert any('not exist' in error.lower() for error in errors)

    def test_validate_path_create_if_missing(self, tmp_path):
        """Test path validation with create_if_missing."""
        new_dir = tmp_path / 'new_directory'
        errors = validate_path(str(new_dir), create_if_missing=True)
        assert len(errors) == 0
        assert new_dir.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
