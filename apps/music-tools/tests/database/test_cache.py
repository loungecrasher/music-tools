"""
Tests for CacheManager
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from music_tools_common.database import CacheError, CacheManager


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache(temp_cache_dir):
    """Create CacheManager instance."""
    cache = CacheManager(temp_cache_dir, ttl_days=30)
    yield cache
    cache.close()


class TestCacheManager:
    """Test CacheManager functionality."""

    def test_initialization(self, temp_cache_dir):
        """Test cache initialization."""
        cache = CacheManager(temp_cache_dir, ttl_days=30)
        assert cache.cache_dir == temp_cache_dir
        assert cache.ttl_days == 30
        assert (temp_cache_dir / "cache.db").exists()
        cache.close()

    def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        # Set string
        assert cache.set('key1', 'value1')
        assert cache.get('key1') == 'value1'

        # Set integer
        assert cache.set('key2', 42)
        assert cache.get('key2') == 42

        # Set float
        assert cache.set('key3', 3.14)
        assert cache.get('key3') == 3.14

        # Set boolean
        assert cache.set('key4', True)
        assert cache.get('key4') is True

        # Set dict
        data = {'name': 'test', 'value': 123}
        assert cache.set('key5', data)
        assert cache.get('key5') == data

        # Set list
        data_list = [1, 2, 3, 4, 5]
        assert cache.set('key6', data_list)
        assert cache.get('key6') == data_list

    def test_get_default(self, cache):
        """Test get with default value."""
        # Non-existent key
        assert cache.get('nonexistent') is None
        assert cache.get('nonexistent', default='default') == 'default'

    def test_delete(self, cache):
        """Test delete operation."""
        cache.set('key1', 'value1')
        assert cache.exists('key1')

        assert cache.delete('key1')
        assert not cache.exists('key1')

        # Delete non-existent key
        assert not cache.delete('nonexistent')

    def test_exists(self, cache):
        """Test exists operation."""
        cache.set('key1', 'value1')

        assert cache.exists('key1')
        assert not cache.exists('nonexistent')

    def test_ttl_expiration(self, temp_cache_dir):
        """Test TTL-based expiration."""
        # Create cache with very short TTL for testing
        cache = CacheManager(temp_cache_dir, ttl_days=0)

        # Set value (will expire immediately)
        cache.set('key1', 'value1')

        # Manually update expiration to past
        cache.execute(
            'UPDATE cache_entries SET expires_at = ? WHERE key = ?',
            ((datetime.now() - timedelta(days=1)).isoformat(), 'key1'),
            commit=True
        )

        # Should not return expired value
        assert cache.get('key1') is None

        # Should return with ignore_expiration
        assert cache.get('key1', ignore_expiration=True) == 'value1'

        cache.close()

    def test_cleanup_expired(self, temp_cache_dir):
        """Test cleanup of expired entries."""
        cache = CacheManager(temp_cache_dir, ttl_days=30)

        # Add entries
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.set('key3', 'value3')

        # Manually expire some entries
        past_date = (datetime.now() - timedelta(days=1)).isoformat()
        cache.execute(
            'UPDATE cache_entries SET expires_at = ? WHERE key IN (?, ?)',
            (past_date, 'key1', 'key2'),
            commit=True
        )

        # Cleanup
        removed = cache.cleanup_expired()
        assert removed == 2

        # Verify
        assert not cache.exists('key1')
        assert not cache.exists('key2')
        assert cache.exists('key3')

        cache.close()

    def test_hit_count_tracking(self, cache):
        """Test hit count tracking."""
        cache.set('key1', 'value1')

        # Access multiple times
        for _ in range(5):
            cache.get('key1')

        # Check hit count in database
        result = cache.fetch_one(
            'SELECT hit_count FROM cache_entries WHERE key = ?',
            ('key1',)
        )
        assert result['hit_count'] >= 5

    def test_hit_rate_calculation(self, cache):
        """Test cache hit rate calculation."""
        # Set some values
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        # Generate hits and misses
        cache.get('key1')  # hit
        cache.get('key2')  # hit
        cache.get('key3')  # miss
        cache.get('key1')  # hit

        hit_rate = cache.get_hit_rate()
        assert 0 <= hit_rate <= 100
        assert hit_rate == 75.0  # 3 hits, 1 miss

    def test_cache_statistics(self, cache):
        """Test cache statistics."""
        # Add entries
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        # Generate activity
        cache.get('key1')
        cache.get('key2')
        cache.get('nonexistent')

        stats = cache.get_cache_statistics()

        assert 'total_entries' in stats
        assert 'active_entries' in stats
        assert 'hit_rate' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'entries_added' in stats

        assert stats['total_entries'] >= 2
        assert stats['cache_hits'] >= 2
        assert stats['cache_misses'] >= 1

    def test_top_entries(self, cache):
        """Test getting top entries by hit count."""
        # Add entries with different access patterns
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.set('key3', 'value3')

        # Access with different frequencies
        for _ in range(10):
            cache.get('key1')
        for _ in range(5):
            cache.get('key2')
        cache.get('key3')

        # Get top entries
        top = cache.get_top_entries(3)

        assert len(top) == 3
        assert top[0]['key'] == 'key1'
        assert top[0]['hit_count'] >= 10
        assert top[1]['key'] == 'key2'
        assert top[1]['hit_count'] >= 5

    def test_export_import_json(self, cache, temp_cache_dir):
        """Test JSON export and import."""
        # Add data
        cache.set('key1', 'value1')
        cache.set('key2', {'name': 'test', 'value': 123})
        cache.set('key3', [1, 2, 3])

        # Export
        export_path = temp_cache_dir / 'export.json'
        assert cache.export_cache(export_path, format='json')
        assert export_path.exists()

        # Clear cache
        cache.clear(confirm=True)
        assert cache.get('key1') is None

        # Import
        imported = cache.import_cache(export_path, format='json')
        assert imported == 3

        # Verify
        assert cache.get('key1') == 'value1'
        assert cache.get('key2') == {'name': 'test', 'value': 123}
        assert cache.get('key3') == [1, 2, 3]

    def test_export_import_csv(self, cache, temp_cache_dir):
        """Test CSV export and import."""
        # Add data
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        # Export
        export_path = temp_cache_dir / 'export.csv'
        assert cache.export_cache(export_path, format='csv')
        assert export_path.exists()

        # Clear and import
        cache.clear(confirm=True)
        imported = cache.import_cache(export_path, format='csv')
        assert imported == 2

        # Verify
        assert cache.get('key1') == 'value1'
        assert cache.get('key2') == 'value2'

    def test_clear_cache(self, cache):
        """Test clearing cache."""
        # Add data
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        # Clear without confirmation
        assert not cache.clear(confirm=False)

        # Verify data still exists
        assert cache.get('key1') == 'value1'

        # Clear with confirmation
        assert cache.clear(confirm=True)

        # Verify data is gone
        assert cache.get('key1') is None
        assert cache.get('key2') is None

        # Verify statistics reset
        stats = cache.get_cache_statistics()
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0

    def test_metadata_storage(self, cache):
        """Test storing metadata with cache entries."""
        metadata = {
            'source': 'API',
            'confidence': 0.95,
            'timestamp': datetime.now().isoformat()
        }

        cache.set('key1', 'value1', metadata=metadata)

        # Verify metadata is stored
        result = cache.fetch_one(
            'SELECT metadata FROM cache_entries WHERE key = ?',
            ('key1',)
        )

        assert result['metadata'] is not None

    def test_custom_ttl(self, cache):
        """Test custom TTL per entry."""
        # Set with default TTL
        cache.set('key1', 'value1')

        # Set with custom TTL
        cache.set('key2', 'value2', ttl=60)  # 60 days

        # Verify different expiration times
        result1 = cache.fetch_one(
            'SELECT expires_at FROM cache_entries WHERE key = ?',
            ('key1',)
        )
        result2 = cache.fetch_one(
            'SELECT expires_at FROM cache_entries WHERE key = ?',
            ('key2',)
        )

        assert result1['expires_at'] != result2['expires_at']

    def test_empty_key_handling(self, cache):
        """Test handling of empty keys."""
        # Empty key should return False
        assert not cache.set('', 'value')
        assert not cache.set('   ', 'value')

        assert cache.get('') is None
        assert cache.get('   ') is None

    def test_update_existing_key(self, cache):
        """Test updating existing cache entry."""
        # Set initial value
        cache.set('key1', 'value1')
        assert cache.get('key1') == 'value1'

        # Update value
        cache.set('key1', 'value2')
        assert cache.get('key1') == 'value2'

        # Verify statistics
        stats = cache.get_cache_statistics()
        assert stats['entries_updated'] >= 1

    def test_cleanup_old_entries(self, temp_cache_dir):
        """Test cleanup of old entries."""
        cache = CacheManager(temp_cache_dir, ttl_days=30)

        # Add entries
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        # Manually set old created_at
        old_date = (datetime.now() - timedelta(days=100)).isoformat()
        cache.execute(
            'UPDATE cache_entries SET created_at = ? WHERE key = ?',
            (old_date, 'key1'),
            commit=True
        )

        # Cleanup entries older than 90 days
        removed = cache.cleanup_old(days_old=90)
        assert removed == 1

        # Verify
        assert not cache.exists('key1', check_expiration=False)
        assert cache.exists('key2')

        cache.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
