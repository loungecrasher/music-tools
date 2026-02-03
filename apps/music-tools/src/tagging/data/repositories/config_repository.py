"""
Configuration repository for managing application settings.

This module provides abstracted access to configuration data,
supporting different storage backends (files, databases, etc.).
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

from ...core.error_handler import ConfigurationError, with_error_handling
from ...core.validation_service import validation_service

logger = logging.getLogger(__name__)


class ConfigRepositoryInterface(ABC):
    """Abstract interface for configuration repositories."""

    @abstractmethod
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from storage."""
        pass

    @abstractmethod
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to storage."""
        pass

    @abstractmethod
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        pass

    @abstractmethod
    def set_setting(self, key: str, value: Any) -> bool:
        """Set a specific setting value."""
        pass

    @abstractmethod
    def has_setting(self, key: str) -> bool:
        """Check if a setting exists."""
        pass

    @abstractmethod
    def delete_setting(self, key: str) -> bool:
        """Delete a setting."""
        pass

    @abstractmethod
    def backup_config(self, backup_path: Optional[Path] = None) -> bool:
        """Create a backup of the configuration."""
        pass


class JSONConfigRepository(ConfigRepositoryInterface):
    """JSON file-based configuration repository."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config_cache: Optional[Dict[str, Any]] = None
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Ensure the configuration directory exists."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    @with_error_handling("Load configuration", reraise=True)
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            logger.info(f"Configuration file not found: {self.config_path}")
            self._config_cache = {}
            return {}

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Validate the configuration
            validation_result = validation_service.validate_config_dict(config)
            if not validation_result.is_valid:
                raise ConfigurationError(
                    f"Invalid configuration: {validation_result.error_message}"
                )

            if validation_result.warnings:
                for warning in validation_result.warnings:
                    logger.warning(f"Configuration warning: {warning}")

            self._config_cache = config
            logger.debug(f"Configuration loaded from {self.config_path}")
            return config

        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    @with_error_handling("Save configuration", reraise=True)
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to JSON file."""
        # Validate the configuration before saving
        validation_result = validation_service.validate_config_dict(config)
        if not validation_result.is_valid:
            raise ConfigurationError(
                f"Cannot save invalid configuration: {validation_result.error_message}"
            )

        if validation_result.warnings:
            for warning in validation_result.warnings:
                logger.warning(f"Configuration warning: {warning}")

        try:
            # Create backup before saving
            if self.config_path.exists():
                backup_path = self.config_path.with_suffix('.json.backup')
                backup_path.write_text(self.config_path.read_text(encoding='utf-8'))

            # Write new configuration
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self._config_cache = config.copy()
            logger.info(f"Configuration saved to {self.config_path}")
            return True

        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None:
            return default

        # Support dot notation for nested keys
        keys = key.split('.')
        value = self._config_cache

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @with_error_handling("Set setting")
    def set_setting(self, key: str, value: Any) -> bool:
        """Set a specific setting value."""
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None:
            self._config_cache = {}

        # Support dot notation for nested keys
        keys = key.split('.')
        current = self._config_cache

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            elif not isinstance(current[k], dict):
                # Convert non-dict values to dict to support nesting
                current[k] = {}
            current = current[k]

        # Set the final value
        current[keys[-1]] = value

        # Save the updated configuration
        return self.save_config(self._config_cache)

    def has_setting(self, key: str) -> bool:
        """Check if a setting exists."""
        return self.get_setting(key, sentinel := object()) is not sentinel

    @with_error_handling("Delete setting")
    def delete_setting(self, key: str) -> bool:
        """Delete a setting."""
        if self._config_cache is None:
            self.load_config()

        if self._config_cache is None:
            return False

        # Support dot notation for nested keys
        keys = key.split('.')
        current = self._config_cache

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if not isinstance(current, dict) or k not in current:
                return False  # Path doesn't exist
            current = current[k]

        # Delete the final key
        if isinstance(current, dict) and keys[-1] in current:
            del current[keys[-1]]
            return self.save_config(self._config_cache)

        return False

    @with_error_handling("Backup configuration")
    def backup_config(self, backup_path: Optional[Path] = None) -> bool:
        """Create a backup of the configuration."""
        if not self.config_path.exists():
            logger.warning("No configuration file to backup")
            return False

        if backup_path is None:
            timestamp = Path().ctime().replace(':', '-').replace(' ', '_')
            backup_path = self.config_path.with_suffix(f'.backup_{timestamp}.json')

        try:
            backup_path.write_text(
                self.config_path.read_text(encoding='utf-8'),
                encoding='utf-8'
            )
            logger.info(f"Configuration backed up to {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to backup configuration: {e}")
            return False

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration settings."""
        if self._config_cache is None:
            self.load_config()
        return self._config_cache.copy() if self._config_cache else {}

    def reset_to_defaults(self) -> bool:
        """Reset configuration to default values."""
        default_config = {
            'music_directory': '',
            'anthropic_api_key': '',
            'batch_size': 50,
            'recursive_scan': True,
            'update_genre': True,
            'update_grouping': True,
            'update_year': True,
            'dry_run': False,
            'verbose': False,
            'cache_enabled': True,
            'max_cache_age_days': 30,
            'supported_formats': ['.mp3', '.flac', '.m4a', '.wav'],
            'ui_settings': {
                'theme': 'default',
                'show_progress': True,
                'confirmation_prompts': True
            }
        }

        return self.save_config(default_config)


# Convenience class alias
ConfigRepository = JSONConfigRepository