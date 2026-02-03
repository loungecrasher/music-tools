"""
Music Tools Common Library
Shared functionality for Music Tools ecosystem.
"""

__version__ = "1.0.0"

from .auth import get_deezer_client, get_spotify_client
from .cli import BaseCLI, InteractiveMenu, ProgressTracker
from .config import ConfigManager, config_manager
from .database import CacheManager, Database, get_cache, get_database
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
