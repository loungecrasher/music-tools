"""
Configuration Manager for Music Tools.

SECURITY NOTE:
- API keys and secrets should ONLY be stored in environment variables (.env file)
- JSON config files should NOT contain sensitive data
- Always use .env.example as a template for new installations
- Ensure .env is listed in .gitignore
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("music_tools_common.config")


class ConfigManager:
    """Configuration manager for Music Tools."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize the configuration manager.

        Args:
            config_dir: Directory containing configuration files. If None, uses default.
        """
        if config_dir is None:
            # Use environment variable if set, otherwise use default
            config_dir = os.getenv("MUSIC_TOOLS_CONFIG_DIR")
            if config_dir:
                config_dir = os.path.expanduser(config_dir)
            else:
                # Default to ~/.music_tools/config
                config_dir = os.path.expanduser("~/.music_tools/config")

        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)

        # Set secure permissions
        try:
            os.chmod(self.config_dir, 0o700)
        except Exception as e:
            logger.warning(f"Could not set secure permissions: {e}")

        # Configuration cache
        self._config_cache: Dict[str, Dict[str, Any]] = {}

        # Default configurations from environment variables
        self._defaults = {
            "spotify": {
                "client_id": os.getenv("SPOTIPY_CLIENT_ID", ""),
                "client_secret": os.getenv("SPOTIPY_CLIENT_SECRET", ""),
                "redirect_uri": os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback"),
            },
            "deezer": {"email": os.getenv("DEEZER_EMAIL", "")},
        }

    def get_config_path(self, service: str) -> str:
        """Get the path to a service's configuration file.

        Args:
            service: Service name (e.g., 'spotify', 'deezer')

        Returns:
            Path to the configuration file
        """
        return os.path.join(self.config_dir, f"{service}_config.json")

    def load_config(self, service: str, use_cache: bool = True) -> Dict[str, Any]:
        """Load configuration for a specific service.

        Environment variables always take priority over file-based config.

        Args:
            service: Service name (e.g., 'spotify', 'deezer')
            use_cache: Whether to use cached configuration

        Returns:
            Configuration dictionary
        """
        if use_cache and service in self._config_cache:
            return self._config_cache[service]

        config_path = self.get_config_path(service)
        config = self._defaults.get(service, {}).copy()

        # Load from file if it exists
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    file_config = json.load(f)

                    # Warn if sensitive data found
                    sensitive_keys = {
                        "client_id",
                        "client_secret",
                        "api_key",
                        "secret",
                        "password",
                        "token",
                    }
                    found_sensitive = [
                        k
                        for k in file_config.keys()
                        if k in sensitive_keys or "secret" in k.lower() or "key" in k.lower()
                    ]

                    if found_sensitive:
                        logger.warning(
                            f"SECURITY WARNING: Sensitive keys in {config_path}: {found_sensitive}. "
                            f"Move these to .env file!"
                        )

                    # Merge non-sensitive config
                    for key, value in file_config.items():
                        if key not in config or not config[key]:
                            config[key] = value

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in {service} configuration file")
            except Exception as e:
                logger.error(f"Error loading {service} configuration: {e}")

        # Environment variables always take priority
        env_config = self._defaults.get(service, {})
        for key, value in env_config.items():
            if value:
                config[key] = value

        self._config_cache[service] = config
        return config

    def save_config(self, service: str, config: Dict[str, Any]) -> bool:
        """Save configuration for a specific service.

        Sensitive data is automatically stripped before saving.

        Args:
            service: Service name
            config: Configuration dictionary

        Returns:
            True if successful
        """
        config_path = self.get_config_path(service)

        try:
            existing_config = self.load_config(service, use_cache=False)
            existing_config.update(config)

            # Remove sensitive data
            sensitive_keys = {
                "client_id",
                "client_secret",
                "api_key",
                "secret",
                "password",
                "token",
                "access_token",
                "refresh_token",
            }

            safe_config = {}
            removed_keys = []

            for key, value in existing_config.items():
                is_sensitive = (
                    key in sensitive_keys
                    or "secret" in key.lower()
                    or "key" in key.lower()
                    or "password" in key.lower()
                    or "token" in key.lower()
                )

                if is_sensitive:
                    removed_keys.append(key)
                else:
                    safe_config[key] = value

            if removed_keys:
                logger.info(f"Sensitive keys not saved: {removed_keys}")

            with open(config_path, "w") as f:
                json.dump(safe_config, f, indent=2)

            os.chmod(config_path, 0o600)
            self._config_cache[service] = existing_config

            logger.info(f"Saved configuration for {service}")
            return True
        except Exception as e:
            logger.error(f"Error saving {service} configuration: {e}")
            return False

    def validate_config(self, service: str) -> List[str]:
        """Validate configuration for a service.

        Args:
            service: Service name

        Returns:
            List of validation errors (empty if valid)
        """
        config = self.load_config(service)
        errors = []

        if service == "spotify":
            if not config.get("client_id"):
                errors.append("Missing Spotify client ID")
            if not config.get("client_secret"):
                errors.append("Missing Spotify client secret")
            if not config.get("redirect_uri"):
                errors.append("Missing Spotify redirect URI")
        elif service == "deezer":
            if not config.get("email"):
                errors.append("Missing Deezer email")

        return errors

    def get_all_services(self) -> List[str]:
        """Get list of all configured services.

        Returns:
            List of service names
        """
        services = []
        if os.path.exists(self.config_dir):
            for filename in os.listdir(self.config_dir):
                if filename.endswith("_config.json"):
                    service = filename.replace("_config.json", "")
                    services.append(service)
        return services


# Global instance
config_manager = ConfigManager()
