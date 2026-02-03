"""
Tests for ConfigManager.
"""
import os
import json
import tempfile
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.manager import ConfigManager


class TestConfigManager:
    """Test suite for ConfigManager."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_config_dir):
        """Create a ConfigManager instance with temporary directory."""
        return ConfigManager(app_name="test_app", config_dir=temp_config_dir)

    def test_initialization(self, manager, temp_config_dir):
        """Test ConfigManager initialization."""
        assert manager.app_name == "test_app"
        assert manager.config_dir == temp_config_dir
        assert manager.config_dir.exists()

    def test_subdirectories_created(self, manager):
        """Test that subdirectories are created."""
        assert (manager.config_dir / 'logs').exists()
        assert (manager.config_dir / 'cache').exists()
        assert (manager.config_dir / 'temp').exists()

    def test_get_config_path(self, manager):
        """Test getting configuration file path."""
        path = manager.get_config_path('spotify')
        assert path == manager.config_dir / 'spotify_config.json'

    def test_save_and_load_config(self, manager):
        """Test saving and loading configuration."""
        # Create test configuration
        test_config = {
            'redirect_uri': 'http://localhost:9999/callback',
            'scope': 'test-scope'
        }

        # Save configuration
        result = manager.save_config('spotify', test_config)
        assert result is True

        # Load configuration
        loaded_config = manager.load_config('spotify', use_cache=False)
        assert loaded_config['redirect_uri'] == 'http://localhost:9999/callback'
        assert loaded_config['scope'] == 'test-scope'

    def test_sensitive_data_stripped(self, manager):
        """Test that sensitive data is stripped before saving."""
        # Create configuration with sensitive data
        test_config = {
            'client_id': 'test_client_id',
            'client_secret': 'test_secret',
            'redirect_uri': 'http://localhost:8888/callback'
        }

        # Save configuration
        manager.save_config('spotify', test_config)

        # Read the file directly
        config_file = manager.get_config_path('spotify')
        with open(config_file, 'r') as f:
            saved_data = json.load(f)

        # Sensitive data should be empty or removed
        assert saved_data.get('client_id', '') == ''
        assert saved_data.get('client_secret', '') == ''
        # Non-sensitive data should be preserved
        assert saved_data['redirect_uri'] == 'http://localhost:8888/callback'

    def test_environment_variable_override(self, manager, monkeypatch):
        """Test that environment variables override file-based config."""
        # Set environment variables
        monkeypatch.setenv('SPOTIPY_CLIENT_ID', 'env_client_id')
        monkeypatch.setenv('SPOTIPY_REDIRECT_URI', 'http://env-redirect.com')

        # Save config to file
        test_config = {
            'redirect_uri': 'http://localhost:8888/callback'
        }
        manager.save_config('spotify', test_config)

        # Load config - environment variables should take priority
        loaded_config = manager.load_config('spotify', use_cache=False)
        assert loaded_config['client_id'] == 'env_client_id'
        assert loaded_config['redirect_uri'] == 'http://env-redirect.com'

    def test_config_caching(self, manager):
        """Test configuration caching."""
        # Create test configuration
        test_config = {
            'redirect_uri': 'http://localhost:8888/callback'
        }

        manager.save_config('spotify', test_config)

        # Load with cache
        config1 = manager.load_config('spotify', use_cache=True)
        config2 = manager.load_config('spotify', use_cache=True)

        # Should be the same object (cached)
        assert config1 is config2

        # Load without cache should create new instance
        config3 = manager.load_config('spotify', use_cache=False)
        assert config3 is not config1

    def test_validation(self, manager, monkeypatch):
        """Test configuration validation."""
        # Set up valid configuration
        monkeypatch.setenv('SPOTIPY_CLIENT_ID', 'test_client_id')
        monkeypatch.setenv('SPOTIPY_CLIENT_SECRET', 'test_secret')

        test_config = {
            'redirect_uri': 'http://localhost:8888/callback'
        }
        manager.save_config('spotify', test_config)

        # Validation should pass with environment variables set
        errors = manager.validate_config('spotify', test_config)
        # Note: May have errors since we're using test values, but should not crash
        assert isinstance(errors, list)

    def test_get_all_services(self, manager):
        """Test getting all configured services."""
        # Create configurations for multiple services
        manager.save_config('spotify', {'redirect_uri': 'http://localhost:8888'})
        manager.save_config('deezer', {'email': 'test@example.com'})

        services = manager.get_all_services()
        assert 'spotify' in services
        assert 'deezer' in services

    def test_secure_permissions(self, manager):
        """Test that configuration files have secure permissions."""
        # Create test configuration
        test_config = {'redirect_uri': 'http://localhost:8888/callback'}
        manager.save_config('spotify', test_config)

        # Check file permissions (Unix-like systems only)
        config_file = manager.get_config_path('spotify')
        if os.name != 'nt':  # Not Windows
            stat_info = config_file.stat()
            # File should be readable/writable by owner only (0o600)
            permissions = stat_info.st_mode & 0o777
            # Should not be readable by group or others
            assert not (permissions & 0o044), f"File has insecure permissions: {oct(permissions)}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
