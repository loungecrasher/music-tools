"""
Configuration management for Music Tools.
Provides unified configuration handling across all projects.
"""

from .manager import ConfigManager, config_manager
from .schema import ConfigSchema, DeezerConfig, SpotifyConfig
from .validation import validate_config, validate_deezer_config, validate_spotify_config

__all__ = [
    "ConfigManager",
    "config_manager",
    "ConfigSchema",
    "SpotifyConfig",
    "DeezerConfig",
    "validate_config",
    "validate_spotify_config",
    "validate_deezer_config",
]
