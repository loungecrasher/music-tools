"""
Cache manager for Music Tools.
Provides in-memory and file-based caching with TTL support.
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("music_tools_common.database.cache")


class CacheManager:
    """Cache manager with TTL support."""

    def __init__(self, cache_dir: Optional[str] = None, ttl: int = 3600, max_size: int = 1000):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for file-based cache
            ttl: Time-to-live in seconds
            max_size: Maximum number of cached items
        """
        if cache_dir is None:
            cache_dir = os.path.expanduser("~/.music_tools/cache")

        self.cache_dir = cache_dir
        self.ttl = ttl
        self.max_size = max_size

        os.makedirs(self.cache_dir, exist_ok=True)

        # In-memory cache
        self._memory_cache: Dict[str, Dict[str, Any]] = {}

    def _get_cache_key(self, key: str) -> str:
        """Generate cache key hash.

        Args:
            key: Original cache key

        Returns:
            Hashed cache key
        """
        return hashlib.sha256(key.encode()).hexdigest()

    def _is_expired(self, timestamp: float) -> bool:
        """Check if cache entry is expired.

        Args:
            timestamp: Cache entry timestamp

        Returns:
            True if expired
        """
        return time.time() - timestamp > self.ttl

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache.

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        cache_key = self._get_cache_key(key)

        # Check memory cache first
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if not self._is_expired(entry["timestamp"]):
                return entry["value"]
            else:
                del self._memory_cache[cache_key]

        # Check file cache
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    entry = json.load(f)
                if not self._is_expired(entry["timestamp"]):
                    # Restore to memory cache
                    self._memory_cache[cache_key] = entry
                    return entry["value"]
                else:
                    os.remove(cache_file)
            except Exception as e:
                logger.error(f"Error reading cache file: {e}")

        return default

    def set(self, key: str, value: Any) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        cache_key = self._get_cache_key(key)

        entry = {"timestamp": time.time(), "value": value}

        # Store in memory
        self._memory_cache[cache_key] = entry

        # Enforce max size
        if len(self._memory_cache) > self.max_size:
            # Remove oldest entries
            sorted_entries = sorted(self._memory_cache.items(), key=lambda x: x[1]["timestamp"])
            for old_key, _ in sorted_entries[: len(self._memory_cache) - self.max_size]:
                del self._memory_cache[old_key]

        # Store in file with secure permissions
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        try:
            with open(cache_file, "w") as f:
                json.dump(entry, f)
            # Set secure permissions (owner read/write only)
            os.chmod(cache_file, 0o600)
        except Exception as e:
            logger.error(f"Error writing cache file: {e}")

    def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        cache_key = self._get_cache_key(key)

        # Remove from memory
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]

        # Remove file
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception as e:
                logger.error(f"Error deleting cache file: {e}")

    def clear(self) -> None:
        """Clear all cache entries."""
        self._memory_cache.clear()

        # Remove all cache files
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json"):
                try:
                    os.remove(os.path.join(self.cache_dir, filename))
                except Exception as e:
                    logger.error(f"Error deleting cache file {filename}: {e}")

    def cleanup(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        removed = 0

        # Clean memory cache
        expired_keys = [
            k for k, v in self._memory_cache.items() if self._is_expired(v["timestamp"])
        ]
        for key in expired_keys:
            del self._memory_cache[key]
            removed += 1

        # Clean file cache
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json"):
                cache_file = os.path.join(self.cache_dir, filename)
                try:
                    with open(cache_file, "r") as f:
                        entry = json.load(f)
                    if self._is_expired(entry["timestamp"]):
                        os.remove(cache_file)
                        removed += 1
                except Exception as e:
                    logger.error(f"Error processing cache file {filename}: {e}")

        if removed > 0:
            logger.info(f"Cleaned up {removed} expired cache entries")

        return removed


# Global instance
_cache_manager = None


def get_cache(
    cache_dir: Optional[str] = None, ttl: int = 3600, max_size: int = 1000
) -> CacheManager:
    """Get cache manager instance.

    Args:
        cache_dir: Cache directory
        ttl: Time-to-live in seconds
        max_size: Maximum cache size

    Returns:
        CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(cache_dir, ttl, max_size)
    return _cache_manager
