"""
Abstract repository interface for cache operations.

This module defines the interface for cache data access, allowing for
different implementations (SQLite, Redis, etc.).
"""

import logging
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ...core.error_handler import CacheError, with_error_handling
from ..models.artist_cache import ArtistCacheEntry
from ..models.processing_stats import ProcessingLogEntry, Statistics

logger = logging.getLogger(__name__)


class CacheRepositoryInterface(ABC):
    """Abstract interface for cache repositories."""

    @abstractmethod
    def get_artist_country(self, artist_name: str) -> Optional[str]:
        """Get cached country for an artist."""

    @abstractmethod
    def store_artist_country(self, entry: ArtistCacheEntry) -> bool:
        """Store an artist-country mapping."""

    @abstractmethod
    def get_artist_entry(self, artist_name: str) -> Optional[ArtistCacheEntry]:
        """Get full cache entry for an artist."""

    @abstractmethod
    def delete_artist(self, artist_name: str) -> bool:
        """Delete an artist from cache."""

    @abstractmethod
    def get_all_artists(self) -> List[ArtistCacheEntry]:
        """Get all cached artists."""

    @abstractmethod
    def clear_cache(self) -> bool:
        """Clear all cache entries."""

    @abstractmethod
    def get_statistics(self) -> Statistics:
        """Get cache statistics."""

    @abstractmethod
    def log_processing(self, entry: ProcessingLogEntry) -> bool:
        """Log a processing operation."""

    @abstractmethod
    def cleanup_old_entries(self, max_age_days: int) -> int:
        """Remove old cache entries."""


class SQLiteCacheRepository(CacheRepositoryInterface):
    """SQLite implementation of cache repository."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.statistics = Statistics()
        self._initialize_database()

    @with_error_handling("Database initialization", reraise=True)
    def _initialize_database(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()

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

            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_artist_name
                ON artist_country(artist_name)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_processing_log_artist
                ON processing_log(artist_name)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_processing_log_status
                ON processing_log(status)
            ''')

            conn.commit()
            logger.info(f"Cache database initialized at {self.db_path}")

    @with_error_handling("Get artist country")
    def get_artist_country(self, artist_name: str) -> Optional[str]:
        """Get cached country for an artist."""
        if not artist_name or not artist_name.strip():
            return None

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT country, hit_count FROM artist_country
                    WHERE LOWER(artist_name) = LOWER(?)
                ''', (artist_name.strip(),))

                result = cursor.fetchone()

                if result:
                    country, hit_count = result

                    # Update hit count
                    cursor.execute('''
                        UPDATE artist_country
                        SET hit_count = hit_count + 1, updated_at = ?
                        WHERE LOWER(artist_name) = LOWER(?)
                    ''', (datetime.now().isoformat(), artist_name.strip()))

                    conn.commit()

                    self.statistics.cache_hits += 1
                    logger.debug(f"Cache hit for artist: {artist_name} -> {country}")
                    return country
                else:
                    self.statistics.cache_misses += 1
                    logger.debug(f"Cache miss for artist: {artist_name}")
                    return None

        except sqlite3.Error as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    @with_error_handling("Store artist country")
    def store_artist_country(self, entry: ArtistCacheEntry) -> bool:
        """Store an artist-country mapping."""
        if not entry.artist_name or not entry.artist_name.strip() or not entry.country:
            return False

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Use INSERT OR REPLACE to handle duplicates
                cursor.execute('''
                    INSERT OR REPLACE INTO artist_country
                    (artist_name, country, confidence, created_at, updated_at, hit_count)
                    VALUES (?, ?, ?, ?, ?,
                        COALESCE((SELECT hit_count FROM artist_country WHERE LOWER(artist_name) = LOWER(?)), 0))
                ''', (
                    entry.artist_name.strip(),
                    entry.country,
                    entry.confidence,
                    entry.created_at.isoformat() if entry.created_at else datetime.now().isoformat(),
                    entry.updated_at.isoformat() if entry.updated_at else datetime.now().isoformat(),
                    entry.artist_name.strip()
                ))

                conn.commit()
                logger.debug(f"Stored in cache: {entry.artist_name} -> {entry.country}")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error storing to cache: {e}")
            return False

    @with_error_handling("Get artist entry")
    def get_artist_entry(self, artist_name: str) -> Optional[ArtistCacheEntry]:
        """Get full cache entry for an artist."""
        if not artist_name or not artist_name.strip():
            return None

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT artist_name, country, confidence, created_at, updated_at, hit_count
                    FROM artist_country
                    WHERE LOWER(artist_name) = LOWER(?)
                ''', (artist_name.strip(),))

                result = cursor.fetchone()

                if result:
                    artist_name, country, confidence, created_at, updated_at, hit_count = result
                    return ArtistCacheEntry(
                        artist_name=artist_name,
                        country=country,
                        confidence=confidence,
                        created_at=datetime.fromisoformat(created_at) if created_at else None,
                        updated_at=datetime.fromisoformat(updated_at) if updated_at else None,
                        hit_count=hit_count
                    )

                return None

        except sqlite3.Error as e:
            logger.error(f"Error retrieving cache entry: {e}")
            return None

    @with_error_handling("Delete artist")
    def delete_artist(self, artist_name: str) -> bool:
        """Delete an artist from cache."""
        if not artist_name or not artist_name.strip():
            return False

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM artist_country
                    WHERE LOWER(artist_name) = LOWER(?)
                ''', (artist_name.strip(),))

                deleted_count = cursor.rowcount
                conn.commit()

                if deleted_count > 0:
                    logger.debug(f"Deleted from cache: {artist_name}")
                    return True
                return False

        except sqlite3.Error as e:
            logger.error(f"Error deleting from cache: {e}")
            return False

    @with_error_handling("Get all artists")
    def get_all_artists(self) -> List[ArtistCacheEntry]:
        """Get all cached artists."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT artist_name, country, confidence, created_at, updated_at, hit_count
                    FROM artist_country
                    ORDER BY updated_at DESC
                ''')

                results = []
                for row in cursor.fetchall():
                    artist_name, country, confidence, created_at, updated_at, hit_count = row
                    entry = ArtistCacheEntry(
                        artist_name=artist_name,
                        country=country,
                        confidence=confidence,
                        created_at=datetime.fromisoformat(created_at) if created_at else None,
                        updated_at=datetime.fromisoformat(updated_at) if updated_at else None,
                        hit_count=hit_count
                    )
                    results.append(entry)

                return results

        except sqlite3.Error as e:
            logger.error(f"Error retrieving all artists: {e}")
            return []

    @with_error_handling("Clear cache")
    def clear_cache(self) -> bool:
        """Clear all cache entries."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM artist_country')
                cursor.execute('DELETE FROM processing_log')
                conn.commit()

                # Reset statistics
                self.statistics.reset()

                logger.info("Cache cleared successfully")
                return True

        except sqlite3.Error as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    @with_error_handling("Get statistics")
    def get_statistics(self) -> Statistics:
        """Get cache statistics."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                # Get cache entry count
                cursor.execute('SELECT COUNT(*) FROM artist_country')
                cache_count = cursor.fetchone()[0]

                # Get processing log statistics
                cursor.execute('''
                    SELECT status, COUNT(*) FROM processing_log
                    GROUP BY status
                ''')

                status_counts = dict(cursor.fetchall())

                # Update statistics object
                self.statistics.cache_entries = cache_count
                self.statistics.files_processed = status_counts.get('success', 0)
                self.statistics.files_with_errors = status_counts.get('error', 0)
                self.statistics.files_skipped = status_counts.get('skipped', 0)

                return self.statistics

        except sqlite3.Error as e:
            logger.error(f"Error getting statistics: {e}")
            return self.statistics

    @with_error_handling("Log processing")
    def log_processing(self, entry: ProcessingLogEntry) -> bool:
        """Log a processing operation."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO processing_log
                    (file_path, artist_name, country, status, processed_at, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    entry.file_path,
                    entry.artist_name,
                    entry.country,
                    entry.status.value,
                    entry.processed_at.isoformat() if entry.processed_at else datetime.now().isoformat(),
                    entry.error_message
                ))
                conn.commit()
                return True

        except sqlite3.Error as e:
            logger.error(f"Error logging processing: {e}")
            return False

    @with_error_handling("Cleanup old entries")
    def cleanup_old_entries(self, max_age_days: int) -> int:
        """Remove old cache entries."""
        try:
            cutoff_date = datetime.now()
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - max_age_days)
            cutoff_str = cutoff_date.isoformat()

            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM artist_country
                    WHERE updated_at < ? AND hit_count = 0
                ''', (cutoff_str,))

                deleted_count = cursor.rowcount
                conn.commit()

                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old cache entries")

                return deleted_count

        except sqlite3.Error as e:
            logger.error(f"Error cleaning up old entries: {e}")
            return 0


# Convenience class alias
CacheRepository = SQLiteCacheRepository
