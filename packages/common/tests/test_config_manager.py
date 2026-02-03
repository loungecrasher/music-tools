"""
Tests for ConfigManager.
"""

import json
import os
import tempfile

import pytest
from music_tools_common.config.manager import ConfigManager


class TestConfigManager:
    """Test suite for ConfigManager."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def manager(self, temp_config_dir):
        """Create a ConfigManager instance with temporary directory."""
        return ConfigManager(config_dir=temp_config_dir)

    def test_initialization(self, manager, temp_config_dir):
        """Test ConfigManager initialization."""
        assert manager.config_dir == temp_config_dir
        assert os.path.exists(manager.config_dir)

    def test_get_config_path(self, manager):
        """Test getting configuration file path."""
        path = manager.get_config_path("spotify")
        assert path == os.path.join(manager.config_dir, "spotify_config.json")

    def test_save_and_load_config(self, manager):
        """Test saving and loading configuration."""
        # Use a non-default key since redirect_uri gets overwritten by env defaults
        test_config = {
            "scope": "test-scope",
            "market": "US",
        }

        result = manager.save_config("spotify", test_config)
        assert result is True

        loaded_config = manager.load_config("spotify", use_cache=False)
        assert loaded_config["scope"] == "test-scope"
        assert loaded_config["market"] == "US"

    def test_sensitive_data_stripped(self, manager):
        """Test that sensitive data is stripped before saving."""
        test_config = {
            "client_id": "test_client_id",
            "client_secret": "test_secret",
            "redirect_uri": "http://localhost:8888/callback",
        }

        manager.save_config("spotify", test_config)

        config_file = manager.get_config_path("spotify")
        with open(config_file, "r") as f:
            saved_data = json.load(f)

        # Sensitive keys should be removed entirely from saved file
        assert "client_id" not in saved_data
        assert "client_secret" not in saved_data
        # Non-sensitive data should be preserved
        assert saved_data["redirect_uri"] == "http://localhost:8888/callback"

    def test_environment_variable_override(self, manager, monkeypatch):
        """Test that environment variables override file-based config."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "env_client_id")
        monkeypatch.setenv("SPOTIPY_REDIRECT_URI", "http://env-redirect.com")

        # Re-create manager so it picks up new env vars in _defaults
        new_manager = ConfigManager(config_dir=manager.config_dir)

        test_config = {"redirect_uri": "http://localhost:8888/callback"}
        new_manager.save_config("spotify", test_config)

        loaded_config = new_manager.load_config("spotify", use_cache=False)
        assert loaded_config["client_id"] == "env_client_id"
        assert loaded_config["redirect_uri"] == "http://env-redirect.com"

    def test_config_caching(self, manager):
        """Test configuration caching."""
        test_config = {"redirect_uri": "http://localhost:8888/callback"}
        manager.save_config("spotify", test_config)

        config1 = manager.load_config("spotify", use_cache=True)
        config2 = manager.load_config("spotify", use_cache=True)

        # Should be the same object (cached)
        assert config1 is config2

        # Load without cache should create new instance
        config3 = manager.load_config("spotify", use_cache=False)
        assert config3 is not config1

    def test_validation(self, manager, monkeypatch):
        """Test configuration validation."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_client_id")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret")

        # Re-create manager to pick up env vars
        new_manager = ConfigManager(config_dir=manager.config_dir)

        test_config = {"redirect_uri": "http://localhost:8888/callback"}
        new_manager.save_config("spotify", test_config)

        # validate_config takes only the service name
        errors = new_manager.validate_config("spotify")
        assert isinstance(errors, list)

    def test_get_all_services(self, manager):
        """Test getting all configured services."""
        manager.save_config("spotify", {"redirect_uri": "http://localhost:8888"})
        manager.save_config("deezer", {"email": "test@example.com"})

        services = manager.get_all_services()
        assert "spotify" in services
        assert "deezer" in services

    def test_secure_permissions(self, manager):
        """Test that configuration files have secure permissions."""
        test_config = {"redirect_uri": "http://localhost:8888/callback"}
        manager.save_config("spotify", test_config)

        config_file = manager.get_config_path("spotify")
        if os.name != "nt":
            stat_info = os.stat(config_file)
            permissions = stat_info.st_mode & 0o777
            # File should be 0o600 (readable/writable by owner only)
            assert permissions == 0o600, f"File has insecure permissions: {oct(permissions)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
