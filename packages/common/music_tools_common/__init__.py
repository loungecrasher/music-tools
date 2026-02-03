"""
Music Tools Common Library
Shared functionality for Music Tools ecosystem.
"""

__version__ = "1.0.0"

from .config import ConfigManager, config_manager
from .database import Database, CacheManager, get_database, get_cache
from .cli import BaseCLI, InteractiveMenu, ProgressTracker
from .auth import get_spotify_client, get_deezer_client
from .utils import retry, safe_request, setup_logger

__all__ = [
    '__version__',
    'ConfigManager',
    'config_manager',
    'Database',
    'CacheManager',
    'get_database',
    'get_cache',
    'BaseCLI',
    'InteractiveMenu',
    'ProgressTracker',
    'get_spotify_client',
    'get_deezer_client',
    'retry',
    'safe_request',
    'setup_logger',
]
