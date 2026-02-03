"""
Cache Manager Module

Provides intelligent caching for artist-country mappings using SQLite.
Minimizes AI API calls by storing and reusing previous research results.
"""

import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

# Import security utilities
try:
    from .core.security import SecurityValidator
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    SecurityValidator = None

logger = logging.getLogger(__name__)


class CacheError(Exception):
    """Exception raised for cache operations."""


class CacheManager:
    """
    Manages SQLite-based caching for artist country mappings.
    """

    def __init__(self, cache_dir: str, ttl_days: int = 30):
        """
        Initialize cache manager with optimized database configuration.

        Args:
            cache_dir: Directory to store cache database
            ttl_days: Time-to-live for cache entries in days
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / "artist_cache.db"
        self.ttl_days = ttl_days

        # Initialize security validator if available
        self.security_validator = SecurityValidator() if SECURITY_AVAILABLE else None

        # Prepared statement cache for performance
        self._prepared_statements = {}
        self._connection_lock = threading.Lock()

        self.statistics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'entries_added': 0,
            'entries_updated': 0
        }

        # Initialize database with optimizations
        self._init_database()
        self._setup_prepared_statements()

    def _init_database(self):
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Apply performance optimizations
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=MEMORY")

                # Create artist_country table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS artist_country (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        artist_name TEXT NOT NULL UNIQUE,
                        country TEXT NOT NULL,
                        confidence REAL DEFAULT 1.0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        hit_count INTEGER DEFAULT 0
                    )
                ''')

                # Create processing_log table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processing_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL,
                        artist_name TEXT NOT NULL,
                        country TEXT,
                        status TEXT NOT NULL,
                        processed_at TEXT NOT NULL,
                        error_message TEXT
                    )
                ''')

                # Create single-column indexes
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_artist_name
                    ON artist_country(artist_name)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_processing_log_artist
                    ON processing_log(artist_name)
                ''')

                # Create high-impact composite indexes for performance optimization

                # CRITICAL: Composite index for TTL-aware lookups (most common query pattern)
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_artist_updated
                    ON artist_country(artist_name, updated_at DESC)
                ''')

                # Analytics and reporting indexes
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_confidence
                    ON artist_country(confidence DESC)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_hit_count
                    ON artist_country(hit_count DESC)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_country
                    ON artist_country(country)
                ''')

                # Processing log indexes for file history and status tracking
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_processing_log_file
                    ON processing_log(file_path, processed_at DESC)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_processing_log_status
                    ON processing_log(status, processed_at DESC)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_processing_log_date
                    ON processing_log(processed_at DESC)
                ''')

                conn.commit()
                logger.info(f"Cache database initialized at {self.db_path}")

        except sqlite3.Error as e:
            raise CacheError(f"Failed to initialize cache database: {e}")

    def _setup_prepared_statements(self):
        """Setup prepared statements for better performance."""
        self._prepared_statements = {
            'get_country': '''
                SELECT country, confidence, hit_count FROM artist_country
                WHERE artist_name = ? AND updated_at > ?
            ''',
            'get_hit_count': '''
                SELECT hit_count FROM artist_country WHERE artist_name = ?
            ''',
            'insert_country': '''
                INSERT OR REPLACE INTO artist_country
                (artist_name, country, confidence, created_at, updated_at, hit_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''',
            'update_hit_count': '''
                UPDATE artist_country SET hit_count = hit_count + 1, updated_at = ?
                WHERE artist_name = ?
            ''',
            'cleanup_expired': '''
                DELETE FROM artist_country WHERE updated_at < ?
            '''
        }

    def _get_optimized_connection(self):
        """Get optimized database connection with performance settings."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance between performance and safety
        conn.execute("PRAGMA cache_size=10000")  # Increase cache size
        conn.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
        return conn

    def get_country(self, artist_name: str) -> Optional[str]:
        """
        Get cached country for artist.

        Args:
            artist_name: Name of the artist to lookup

        Returns:
            Country name if found in cache, None otherwise
        """
        if not artist_name or not artist_name.strip():
            return None

        try:
            with self._connection_lock:
                with self._get_optimized_connection() as conn:
                    cursor = conn.cursor()

                    # Calculate TTL cutoff
                    ttl_cutoff = (datetime.now() - timedelta(days=self.ttl_days)).isoformat()

                    # Case-insensitive search with TTL check using prepared statement
                    cursor.execute(self._prepared_statements['get_country'],
                                   (artist_name.strip(), ttl_cutoff))

                    result = cursor.fetchone()

                    if result:
                        country, confidence, hit_count = result

                        # FIX: Add pipes if missing (for legacy cache entries)
                        country = self._ensure_pipes_in_grouping(country)

                        # Update hit count using prepared statement
                        cursor.execute(self._prepared_statements['update_hit_count'],
                                       (datetime.now().isoformat(), artist_name.strip()))

                        conn.commit()

                        self.statistics['cache_hits'] += 1
                        logger.debug(f"Cache hit for artist: {artist_name} -> {country}")
                        return country
                    else:
                        self.statistics['cache_misses'] += 1
                        logger.debug(f"Cache miss for artist: {artist_name}")
                        return None

        except sqlite3.Error as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    def _ensure_pipes_in_grouping(self, grouping: str) -> str:
        """
        Ensure grouping value has pipe delimiters (fixes legacy cache entries).

        Args:
            grouping: Grouping value from cache

        Returns:
            Grouping with pipes enforced
        """
        if not grouping:
            return grouping

        # If already has pipes, return as-is
        if '|' in grouping:
            return grouping

        # Legacy format without pipes - try to add them
        # Expected format: "Region Region Country Language" -> "Region Region | Country | Language"
        # Common patterns: "Western Europe France Romance", "North America Canada Romance"
        parts = grouping.strip().split()

        if len(parts) >= 4:
            # Format: [Region Region] [Country] [Language]
            # First 2 words = region, second-to-last = country, last = language
            region = ' '.join(parts[:2])  # e.g., "Western Europe"
            country = ' '.join(parts[2:-1])  # e.g., "France" or "United States"
            language = parts[-1]  # e.g., "Romance"
            fixed = f"{region} | {country} | {language}"
            logger.info(f"Fixed legacy cache entry: '{grouping}' -> '{fixed}'")
            return fixed
        elif len(parts) == 3:
            # Format: [Region] [Country] [Language]
            region = parts[0]
            country = parts[1]
            language = parts[2]
            fixed = f"{region} | {country} | {language}"
            logger.info(f"Fixed legacy cache entry: '{grouping}' -> '{fixed}'")
            return fixed
        elif len(parts) == 2:
            # Region Country or Country Language
            fixed = f"{parts[0]} | {parts[1]} | Unknown"
            logger.info(f"Fixed legacy cache entry: '{grouping}' -> '{fixed}'")
            return fixed
        else:
            # Single word - assume it's a country
            fixed = f"Unknown | {grouping} | Unknown"
            logger.info(f"Fixed legacy cache entry: '{grouping}' -> '{fixed}'")
            return fixed

    def store_country(self, artist_name: str, country: str, confidence: float = 1.0) -> bool:
        """
        Store artist-country mapping in cache with input sanitization.

        Args:
            artist_name: Name of the artist
            country: Country of origin
            confidence: Confidence score (0.0-1.0)

        Returns:
            True if stored successfully, False otherwise
        """
        if not artist_name or not artist_name.strip() or not country:
            return False

        # Sanitize inputs using security validator if available
        if self.security_validator:
            artist_name = self.security_validator.sanitize_artist_name(artist_name)
            country = self.security_validator.sanitize_artist_name(country)  # Same sanitization rules

        # Additional validation
        if not artist_name or not country:
            logger.warning("Artist name or country became empty after sanitization")
            return False

        try:
            with self._connection_lock:
                with self._get_optimized_connection() as conn:
                    cursor = conn.cursor()

                    now = datetime.now().isoformat()

                    # Get existing hit count using prepared statement
                    cursor.execute(self._prepared_statements['get_hit_count'],
                                   (artist_name.strip(),))

                    existing_hit_count = 0
                    result = cursor.fetchone()
                    if result:
                        existing_hit_count = result[0]

                    # Insert or replace using prepared statement
                    cursor.execute(self._prepared_statements['insert_country'],
                                   (artist_name.strip(), country, confidence, now, now, existing_hit_count))

                conn.commit()

                if cursor.rowcount > 0:
                    if cursor.lastrowid:
                        self.statistics['entries_added'] += 1
                        logger.debug(f"Added to cache: {artist_name} -> {country}")
                    else:
                        self.statistics['entries_updated'] += 1
                        logger.debug(f"Updated cache: {artist_name} -> {country}")
                    return True
                else:
                    logger.warning(f"No rows affected when storing {artist_name}")
                    return False

        except sqlite3.Error as e:
            logger.error(f"Error storing in cache: {e}")
            return False

    def cleanup_expired_entries(self) -> int:
        """
        Remove expired cache entries based on TTL.

        Returns:
            Number of entries removed
        """
        try:
            with self._connection_lock:
                with self._get_optimized_connection() as conn:
                    cursor = conn.cursor()

                    # Calculate cutoff date
                    cutoff_date = (datetime.now() - timedelta(days=self.ttl_days)).isoformat()

                    # Remove expired entries using prepared statement
                    cursor.execute(self._prepared_statements['cleanup_expired'], (cutoff_date,))

                    removed_count = cursor.rowcount
                    conn.commit()

                    if removed_count > 0:
                        logger.info(f"Cleaned up {removed_count} expired cache entries")

                    return removed_count

        except sqlite3.Error as e:
            logger.error(f"Error cleaning up expired entries: {e}")
            return 0

    def optimize_database(self):
        """Optimize database performance by running VACUUM and ANALYZE."""
        try:
            with self._connection_lock:
                with self._get_optimized_connection() as conn:
                    # Run VACUUM to reclaim space and defragment
                    conn.execute("VACUUM")
                    # Run ANALYZE to update query planner statistics
                    conn.execute("ANALYZE")
                    logger.info("Database optimization completed")
        except sqlite3.Error as e:
            logger.error(f"Error optimizing database: {e}")

    def log_processing(self, file_path: str, artist_name: str, country: Optional[str],
                       status: str, error_message: Optional[str] = None):
        """
        Log file processing results.

        Args:
            file_path: Path to the processed file
            artist_name: Artist name from metadata
            country: Identified country (if successful)
            status: Processing status (success, error, skipped)
            error_message: Error message if status is error
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO processing_log
                    (file_path, artist_name, country, status, processed_at, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (file_path, artist_name, country, status,
                      datetime.now().isoformat(), error_message))

                conn.commit()

        except sqlite3.Error as e:
            logger.error(f"Error logging processing: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics and analytics.

        Returns:
            Dictionary containing cache statistics
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Total entries
                cursor.execute('SELECT COUNT(*) FROM artist_country')
                total_entries = cursor.fetchone()[0]

                # Cache hit rate calculation
                total_requests = self.statistics['cache_hits'] + self.statistics['cache_misses']
                hit_rate = (self.statistics['cache_hits'] / total_requests * 100) if total_requests > 0 else 0

                # Most recent update
                cursor.execute('SELECT MAX(updated_at) FROM artist_country')
                last_updated = cursor.fetchone()[0] or "Never"

                # Top countries
                cursor.execute('''
                    SELECT country, COUNT(*) as count
                    FROM artist_country
                    GROUP BY country
                    ORDER BY count DESC
                    LIMIT 10
                ''')
                top_countries = cursor.fetchall()

                # Recent entries
                cursor.execute('''
                    SELECT artist_name, country, created_at
                    FROM artist_country
                    ORDER BY created_at DESC
                    LIMIT 5
                ''')
                recent_entries = [
                    {"artist": row[0], "country": row[1], "timestamp": row[2]}
                    for row in cursor.fetchall()
                ]

                # Database size
                db_size = os.path.getsize(str(self.db_path)) if os.path.exists(self.db_path) else 0
                cache_size_mb = db_size / (1024 * 1024)

                return {
                    'total_entries': total_entries,
                    'hit_rate': hit_rate,
                    'last_updated': last_updated,
                    'cache_size_mb': cache_size_mb,
                    'top_countries': top_countries,
                    'recent_entries': recent_entries,
                    'total_api_requests': self.statistics['cache_misses'],
                    **self.statistics
                }

        except sqlite3.Error as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'total_entries': 0,
                'hit_rate': 0,
                'last_updated': 'Error',
                'cache_size_mb': 0,
                'top_countries': [],
                'recent_entries': [],
                'total_api_requests': 0,
                **self.statistics
            }

    def clear_cache(self, confirm: bool = False) -> bool:
        """
        Clear all cached data.

        Args:
            confirm: If True, skip confirmation check

        Returns:
            True if cleared successfully
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute('DELETE FROM artist_country')
                cursor.execute('DELETE FROM processing_log')

                conn.commit()

                # Reset statistics
                self.statistics = {
                    'cache_hits': 0,
                    'cache_misses': 0,
                    'entries_added': 0,
                    'entries_updated': 0
                }

                logger.info("Cache cleared successfully")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    def cleanup_old_entries(self, days_old: int = 90) -> int:
        """
        Remove cache entries older than specified days.

        Args:
            days_old: Remove entries older than this many days

        Returns:
            Number of entries removed
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    DELETE FROM artist_country
                    WHERE created_at < ?
                ''', (cutoff_date,))

                removed_count = cursor.rowcount

                cursor.execute('''
                    DELETE FROM processing_log
                    WHERE processed_at < ?
                ''', (cutoff_date,))

                conn.commit()

                logger.info(f"Cleaned up {removed_count} old cache entries")
                return removed_count

        except sqlite3.Error as e:
            logger.error(f"Error cleaning up cache: {e}")
            return 0

    def export_cache(self, export_path: str, format: str = "json") -> bool:
        """
        Export cache data to file.

        Args:
            export_path: Path to export file
            format: Export format ("json" or "csv")

        Returns:
            True if exported successfully
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT artist_name, country, confidence, created_at, hit_count
                    FROM artist_country
                    ORDER BY hit_count DESC
                ''')

                data = cursor.fetchall()

                if format.lower() == "json":
                    import json
                    export_data = [
                        {
                            "artist": row[0],
                            "country": row[1],
                            "confidence": row[2],
                            "created_at": row[3],
                            "hit_count": row[4]
                        }
                        for row in data
                    ]

                    with open(export_path, 'w') as f:
                        json.dump(export_data, f, indent=2)

                elif format.lower() == "csv":
                    import csv
                    with open(export_path, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Artist', 'Country', 'Confidence', 'Created', 'Hit Count'])
                        writer.writerows(data)

                logger.info(f"Exported {len(data)} cache entries to {export_path}")
                return True

        except Exception as e:
            logger.error(f"Error exporting cache: {e}")
            return False
