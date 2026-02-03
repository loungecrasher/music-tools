"""
Database management for Music Tools.
Provides SQLite database interface and caching.
"""

from .manager import Database
from .cache import CacheManager
from .models import Playlist, Track, PlaylistTrack, Setting

# Create convenience functions
def get_database(db_path=None):
    """Get a database instance."""
    return Database(db_path)

def get_cache(cache_dir='cache', ttl_days=30):
    """Get a cache manager instance."""
    return CacheManager(cache_dir, ttl_days)

__all__ = [
    'Database',
    'get_database',
    'CacheManager',
    'get_cache',
    'Playlist',
    'Track',
    'PlaylistTrack',
    'Setting',
]
