"""
Database layer for library management.

Provides SQLite-based persistence for music library indexing and duplicate detection.
"""

import functools
import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

from .batch_operations import BatchOperationsMixin
from .models import LibraryFile, LibraryStatistics

logger = logging.getLogger(__name__)

# Type variable for generic retry decorator
T = TypeVar("T")

# Constants
DEFAULT_VETTING_HISTORY_LIMIT: int = 10
MIN_VETTING_HISTORY_LIMIT: int = 1
MAX_VETTING_HISTORY_LIMIT: int = 1000

# Database configuration for production robustness
DEFAULT_DB_TIMEOUT: float = 30.0  # 30 seconds for concurrent access
DEFAULT_ISOLATION_LEVEL: str = "DEFERRED"  # Allows concurrent reads

# Retry configuration for transient database errors
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_RETRY_DELAY: float = 0.1  # 100ms initial delay
DEFAULT_RETRY_BACKOFF: float = 2.0  # Exponential backoff multiplier
RETRYABLE_ERRORS = (
    "database is locked",
    "database is busy",
    "unable to open database file",
)


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    delay: float = DEFAULT_RETRY_DELAY,
    backoff: float = DEFAULT_RETRY_BACKOFF,
) -> Callable:
    """Decorator to retry database operations on transient errors.

    Args:
        max_retries: Maximum number of retry attempts.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier for delay on each retry.

    Returns:
        Decorated function with retry logic.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    error_msg = str(e).lower()

                    # Check if error is retryable
                    is_retryable = any(retryable in error_msg for retryable in RETRYABLE_ERRORS)

                    if not is_retryable or attempt >= max_retries:
                        raise

                    last_error = e
                    logger.warning(
                        f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {current_delay:.2f}s..."
                    )

                    time.sleep(current_delay)
                    current_delay *= backoff

            # Should not reach here, but raise last error if we do
            if last_error:
                raise last_error

        return wrapper

    return decorator


class LibraryDatabase(BatchOperationsMixin):
    """SQLite database for music library indexing with batch operations support.

    Inherits from BatchOperationsMixin to provide high-performance batch operations:
    - batch_insert_files(): 10-50x faster than individual inserts
    - batch_update_files(): 10-25x faster than individual updates
    - batch_delete_files(): 10-20x faster than individual deletes
    - batch_get_files_by_paths(): 5-20x faster than individual lookups
    - batch_get_files_by_hashes(): 10-30x faster for duplicate checking
    """

    # Whitelist of allowed columns to prevent SQL injection
    ALLOWED_COLUMNS = {
        "id",
        "file_path",
        "filename",
        "artist",
        "title",
        "album",
        "year",
        "duration",
        "file_format",
        "file_size",
        "metadata_hash",
        "file_content_hash",
        "indexed_at",
        "file_mtime",
        "last_verified",
        "is_active",
    }

    def __init__(self, db_path: str):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Parent directories will
                    be created if they don't exist.

        Raises:
            ValueError: If db_path is None or empty.
            OSError: If database directory cannot be created.
        """
        if not db_path:
            raise ValueError("db_path cannot be None or empty")

        self.db_path = db_path
        self._ensure_database_exists()

    def _ensure_database_exists(self) -> None:
        """Create database file and tables if they don't exist.

        Raises:
            OSError: If database directory cannot be created.
        """
        # Create parent directory if needed
        db_file = Path(self.db_path)
        try:
            db_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Cannot create database directory {db_file.parent}: {e}")
            raise

        # Create tables
        self.create_tables()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections.

        Yields:
            sqlite3.Connection: Database connection with Row factory.

        Raises:
            sqlite3.Error: If database connection or operations fail.
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=DEFAULT_DB_TIMEOUT,  # 30.0 seconds for concurrent access
                check_same_thread=False,  # Allow multi-threaded access
                isolation_level=DEFAULT_ISOLATION_LEVEL,  # 'DEFERRED' for concurrent reads
            )
            conn.row_factory = sqlite3.Row  # Access columns by name
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def create_tables(self) -> None:
        """Create database tables and indexes.

        Raises:
            sqlite3.Error: If table creation fails.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Apply performance optimizations
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")

            # Main library index table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS library_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- File information
                    file_path TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,

                    -- Metadata
                    artist TEXT,
                    title TEXT,
                    album TEXT,
                    year INTEGER,
                    duration REAL,
                    file_format TEXT NOT NULL,
                    file_size INTEGER NOT NULL,

                    -- Hashing for duplicate detection
                    metadata_hash TEXT NOT NULL,
                    file_content_hash TEXT NOT NULL,

                    -- Timestamps
                    indexed_at TEXT NOT NULL,
                    file_mtime TEXT NOT NULL,
                    last_verified TEXT,

                    -- Status
                    is_active INTEGER DEFAULT 1
                )
            """)

            # Create indexes for fast lookups
            # Single-column indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_hash
                ON library_index(metadata_hash)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_content_hash
                ON library_index(file_content_hash)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_is_active
                ON library_index(is_active)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_format
                ON library_index(file_format)
            """)

            # Composite indexes for optimized query performance
            # High-impact composite indexes for duplicate detection
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_active_metadata_hash
                ON library_index(is_active, metadata_hash)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_active_content_hash
                ON library_index(is_active, file_content_hash)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_active_format
                ON library_index(is_active, file_format)
            """)

            # Artist/Title searches (case-insensitive queries)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_artist_title
                ON library_index(artist, title)
            """)

            # Album grouping queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_artist_album
                ON library_index(artist, album)
            """)

            # Statistics queries for active files by format
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_active_artist
                ON library_index(is_active, artist)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_active_album
                ON library_index(is_active, album)
            """)

            # Statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS library_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_files INTEGER,
                    total_size INTEGER,
                    formats_breakdown TEXT,
                    artists_count INTEGER,
                    albums_count INTEGER,
                    last_index_time TEXT,
                    index_duration REAL,
                    created_at TEXT
                )
            """)

            # Vetting history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vetting_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    import_folder TEXT NOT NULL,
                    total_files INTEGER,
                    duplicates_found INTEGER,
                    new_songs INTEGER,
                    uncertain_matches INTEGER,
                    threshold_used REAL,
                    vetted_at TEXT NOT NULL
                )
            """)

            # Vetting history index for recent queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vetting_history_date
                ON vetting_history(vetted_at DESC)
            """)

    def add_file(self, file: LibraryFile) -> int:
        """Add a file to the library index.

        Args:
            file: LibraryFile to add. Must not be None.

        Returns:
            Database ID of inserted file (positive integer).

        Raises:
            ValueError: If file is None or contains invalid column names.
            sqlite3.Error: If database insert fails.
        """
        if file is None:
            raise ValueError("file cannot be None")
        with self._get_connection() as conn:
            cursor = conn.cursor()

            file_dict = file.to_dict()
            # Remove id as it's auto-generated
            file_dict.pop("id", None)

            # Validate column names against whitelist to prevent SQL injection
            invalid_columns = set(file_dict.keys()) - self.ALLOWED_COLUMNS
            if invalid_columns:
                raise ValueError(f"Invalid column names: {invalid_columns}")

            columns = ", ".join(file_dict.keys())
            placeholders = ", ".join(["?" for _ in file_dict])

            cursor.execute(
                f"INSERT INTO library_index ({columns}) VALUES ({placeholders})",
                list(file_dict.values()),
            )

            return cursor.lastrowid

    def get_file_by_path(self, path: str) -> Optional[LibraryFile]:
        """Get file by file path.

        Args:
            path: File path to search for

        Returns:
            LibraryFile if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM library_index WHERE file_path = ?", (path,))
            row = cursor.fetchone()

            if row:
                return LibraryFile.from_dict(dict(row))
            return None

    def get_file_by_metadata_hash(self, hash: str) -> Optional[LibraryFile]:
        """Get file by metadata hash.

        Args:
            hash: Metadata hash to search for

        Returns:
            LibraryFile if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM library_index WHERE metadata_hash = ? AND is_active = 1", (hash,)
            )
            row = cursor.fetchone()

            if row:
                return LibraryFile.from_dict(dict(row))
            return None

    def get_files_by_metadata_hash(self, hash: str) -> List[LibraryFile]:
        """Get all files matching a metadata hash.

        Args:
            hash: Metadata hash to search for

        Returns:
            List of matching LibraryFile objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM library_index WHERE metadata_hash = ? AND is_active = 1", (hash,)
            )
            rows = cursor.fetchall()

            return [LibraryFile.from_dict(dict(row)) for row in rows]

    def get_file_by_content_hash(self, hash: str) -> Optional[LibraryFile]:
        """Get file by content hash.

        Args:
            hash: Content hash to search for

        Returns:
            LibraryFile if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM library_index WHERE file_content_hash = ? AND is_active = 1", (hash,)
            )
            row = cursor.fetchone()

            if row:
                return LibraryFile.from_dict(dict(row))
            return None

    def search_by_artist_title(
        self, artist: Optional[str] = None, title: Optional[str] = None
    ) -> List[LibraryFile]:
        """Search files by artist and/or title.

        Args:
            artist: Artist name to search for
            title: Title to search for

        Returns:
            List of matching LibraryFile objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            conditions = ["is_active = 1"]
            params = []

            if artist:
                conditions.append("LOWER(artist) = LOWER(?)")
                params.append(artist)

            if title:
                conditions.append("LOWER(title) = LOWER(?)")
                params.append(title)

            where_clause = " AND ".join(conditions)

            cursor.execute(f"SELECT * FROM library_index WHERE {where_clause}", params)
            rows = cursor.fetchall()

            return [LibraryFile.from_dict(dict(row)) for row in rows]

    def get_all_files(self, active_only: bool = True) -> List[LibraryFile]:
        """Get all files in the library.

        Args:
            active_only: If True, only return active files

        Returns:
            List of all LibraryFile objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if active_only:
                cursor.execute("SELECT * FROM library_index WHERE is_active = 1")
            else:
                cursor.execute("SELECT * FROM library_index")

            rows = cursor.fetchall()
            return [LibraryFile.from_dict(dict(row)) for row in rows]

    def update_file(self, file: LibraryFile) -> None:
        """Update an existing file in the library.

        Args:
            file: LibraryFile with updated data (must have id set)

        Raises:
            ValueError: If file is None, file.id is None, or contains invalid column names.
            sqlite3.Error: If database update fails.
        """
        if file is None:
            raise ValueError("file cannot be None")
        if file.id is None:
            raise ValueError("Cannot update file without id")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            file_dict = file.to_dict()
            file_id = file_dict.pop("id")

            # Validate column names against whitelist to prevent SQL injection
            invalid_columns = set(file_dict.keys()) - self.ALLOWED_COLUMNS
            if invalid_columns:
                raise ValueError(f"Invalid column names: {invalid_columns}")

            set_clause = ", ".join([f"{key} = ?" for key in file_dict.keys()])

            cursor.execute(
                f"UPDATE library_index SET {set_clause} WHERE id = ?",
                list(file_dict.values()) + [file_id],
            )

    def mark_inactive(self, path: str) -> None:
        """Mark a file as inactive (soft delete).

        Args:
            path: File path to mark as inactive. Must not be None or empty.

        Raises:
            ValueError: If path is None or empty.
            sqlite3.Error: If database update fails.
        """
        if not path:
            raise ValueError("path cannot be None or empty")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE library_index SET is_active = 0 WHERE file_path = ?", (path,))

    def delete_file(self, path: str) -> None:
        """Permanently delete a file from the index (hard delete).

        Args:
            path: File path to delete. Must not be None or empty.

        Raises:
            ValueError: If path is None or empty.
            sqlite3.Error: If database delete fails.
        """
        if not path:
            raise ValueError("path cannot be None or empty")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM library_index WHERE file_path = ?", (path,))

    def get_statistics(self) -> LibraryStatistics:
        """Get library statistics.

        Returns:
            LibraryStatistics object with current stats
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get total files and size
            cursor.execute("""
                SELECT
                    COUNT(*) as total_files,
                    SUM(file_size) as total_size
                FROM library_index
                WHERE is_active = 1
            """)
            row = cursor.fetchone()
            total_files = row["total_files"] or 0
            total_size = row["total_size"] or 0

            # Get format breakdown
            cursor.execute("""
                SELECT file_format, COUNT(*) as count
                FROM library_index
                WHERE is_active = 1
                GROUP BY file_format
            """)
            formats_breakdown = {row["file_format"]: row["count"] for row in cursor.fetchall()}

            # Get unique artists and albums
            cursor.execute("""
                SELECT COUNT(DISTINCT artist) as artists_count
                FROM library_index
                WHERE is_active = 1 AND artist IS NOT NULL
            """)
            artists_count = cursor.fetchone()["artists_count"] or 0

            cursor.execute("""
                SELECT COUNT(DISTINCT album) as albums_count
                FROM library_index
                WHERE is_active = 1 AND album IS NOT NULL
            """)
            albums_count = cursor.fetchone()["albums_count"] or 0

            # Get last index time from stats table
            cursor.execute("""
                SELECT last_index_time, index_duration
                FROM library_stats
                ORDER BY created_at DESC
                LIMIT 1
            """)
            stats_row = cursor.fetchone()

            last_index_time = None
            index_duration = 0.0

            if stats_row:
                if stats_row["last_index_time"]:
                    last_index_time = datetime.fromisoformat(stats_row["last_index_time"])
                index_duration = stats_row["index_duration"] or 0.0

            return LibraryStatistics(
                total_files=total_files,
                total_size=total_size,
                formats_breakdown=formats_breakdown,
                artists_count=artists_count,
                albums_count=albums_count,
                last_index_time=last_index_time,
                index_duration=index_duration,
            )

    def save_statistics(self, stats: LibraryStatistics) -> None:
        """Save library statistics to database.

        Args:
            stats: LibraryStatistics object to save. Must not be None.

        Raises:
            ValueError: If stats is None.
            sqlite3.Error: If database insert fails.
        """
        if stats is None:
            raise ValueError("stats cannot be None")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO library_stats (
                    total_files,
                    total_size,
                    formats_breakdown,
                    artists_count,
                    albums_count,
                    last_index_time,
                    index_duration,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    stats.total_files,
                    stats.total_size,
                    json.dumps(stats.formats_breakdown),
                    stats.artists_count,
                    stats.albums_count,
                    stats.last_index_time.isoformat() if stats.last_index_time else None,
                    stats.index_duration,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def save_vetting_result(
        self,
        import_folder: str,
        total_files: int,
        duplicates_found: int,
        new_songs: int,
        uncertain_matches: int,
        threshold_used: float,
    ) -> None:
        """Save vetting result to history.

        Args:
            import_folder: Path to import folder. Must not be None or empty.
            total_files: Total files scanned. Must be non-negative.
            duplicates_found: Number of duplicates found. Must be non-negative.
            new_songs: Number of new songs found. Must be non-negative.
            uncertain_matches: Number of uncertain matches. Must be non-negative.
            threshold_used: Similarity threshold used. Must be between 0.0 and 1.0.

        Raises:
            ValueError: If any parameter is invalid (empty string, negative number, out of range).
            sqlite3.Error: If database insert fails.
        """
        # Input validation
        if not import_folder:
            raise ValueError("import_folder cannot be None or empty")
        if total_files < 0:
            raise ValueError(f"total_files must be non-negative, got {total_files}")
        if duplicates_found < 0:
            raise ValueError(f"duplicates_found must be non-negative, got {duplicates_found}")
        if new_songs < 0:
            raise ValueError(f"new_songs must be non-negative, got {new_songs}")
        if uncertain_matches < 0:
            raise ValueError(f"uncertain_matches must be non-negative, got {uncertain_matches}")
        if not 0.0 <= threshold_used <= 1.0:
            raise ValueError(f"threshold_used must be between 0.0 and 1.0, got {threshold_used}")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO vetting_history (
                    import_folder,
                    total_files,
                    duplicates_found,
                    new_songs,
                    uncertain_matches,
                    threshold_used,
                    vetted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    import_folder,
                    total_files,
                    duplicates_found,
                    new_songs,
                    uncertain_matches,
                    threshold_used,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def get_vetting_history(
        self, limit: int = DEFAULT_VETTING_HISTORY_LIMIT
    ) -> List[Dict[str, Any]]:
        """Get recent vetting history.

        Args:
            limit: Maximum number of records to return. Must be between 1 and 1000.
                  Defaults to 10.

        Returns:
            List of vetting history records as dictionaries. May be empty if no history exists.

        Raises:
            ValueError: If limit is not between 1 and 1000.
            sqlite3.Error: If database query fails.
        """
        # Input validation
        if not MIN_VETTING_HISTORY_LIMIT <= limit <= MAX_VETTING_HISTORY_LIMIT:
            raise ValueError(
                f"limit must be between {MIN_VETTING_HISTORY_LIMIT} and {MAX_VETTING_HISTORY_LIMIT}, got {limit}"
            )

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM vetting_history
                ORDER BY vetted_at DESC
                LIMIT ?
            """,
                (limit,),
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_file_count(self, active_only: bool = True) -> int:
        """Get total file count.

        Args:
            active_only: If True, only count active files

        Returns:
            Number of files in library
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if active_only:
                cursor.execute("SELECT COUNT(*) FROM library_index WHERE is_active = 1")
            else:
                cursor.execute("SELECT COUNT(*) FROM library_index")

            return cursor.fetchone()[0]

    def verify_file_exists(self, path: str) -> bool:
        """Check if a file exists in the database.

        Args:
            path: File path to check. Must not be None or empty.

        Returns:
            True if file exists, False otherwise.

        Raises:
            ValueError: If path is None or empty.
            sqlite3.Error: If database query fails.
        """
        if not path:
            raise ValueError("path cannot be None or empty")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM library_index WHERE file_path = ?", (path,))
            return cursor.fetchone()[0] > 0

    def backup_database(self, backup_path: str) -> None:
        """Create a backup of the database.

        Uses SQLite's backup API to create a consistent copy of the database
        even while other connections may be accessing it.

        Args:
            backup_path: Path where backup should be saved. Must not be None or empty.
                        Parent directories will be created if they don't exist.

        Raises:
            ValueError: If backup_path is None or empty.
            IOError: If backup fails due to permission or disk space issues.
            sqlite3.Error: If database backup operation fails.

        Example:
            >>> db = LibraryDatabase("library.db")
            >>> db.backup_database("backups/library_backup.db")
        """
        if not backup_path:
            raise ValueError("backup_path cannot be None or empty")

        # Create backup directory if needed
        backup_file = Path(backup_path)
        try:
            backup_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Cannot create backup directory {backup_file.parent}: {e}")
            raise IOError(f"Cannot create backup directory: {e}")

        try:
            # Use sqlite3 backup API for consistent backup
            with self._get_connection() as source_conn:
                # Create backup connection
                backup_conn = sqlite3.connect(backup_path)
                try:
                    # Perform backup
                    source_conn.backup(backup_conn)
                    logger.info(f"Database backed up to {backup_path}")
                finally:
                    backup_conn.close()
        except sqlite3.Error as e:
            logger.error(f"Database backup failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during backup: {e}")
            raise IOError(f"Backup failed: {e}")

    def verify_database_integrity(self) -> bool:
        """Verify database integrity using PRAGMA integrity_check.

        Performs a comprehensive integrity check on the database to detect
        any corruption or inconsistencies.

        Returns:
            True if database is valid and has no integrity issues, False otherwise.

        Raises:
            sqlite3.Error: If integrity check query fails.

        Example:
            >>> db = LibraryDatabase("library.db")
            >>> if not db.verify_database_integrity():
            ...     print("Database is corrupted!")
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()

                # integrity_check returns "ok" if database is valid
                is_valid = result and result[0] == "ok"

                if is_valid:
                    logger.info("Database integrity check passed")
                else:
                    logger.warning(f"Database integrity check failed: {result}")

                return is_valid
        except sqlite3.Error as e:
            logger.error(f"Database integrity check failed: {e}")
            raise

    def optimize_database(self) -> None:
        """Optimize database using VACUUM command.

        This reclaims unused space and optimizes the database file by:
        - Rebuilding the database file to reclaim unused space
        - Defragmenting the database
        - Resetting internal statistics

        Note:
            VACUUM requires temporary disk space equal to the database size.
            The database will be locked during this operation.

        Raises:
            sqlite3.Error: If VACUUM operation fails.

        Example:
            >>> db = LibraryDatabase("library.db")
            >>> db.optimize_database()  # Reclaim space and optimize
        """
        try:
            with self._get_connection() as conn:
                # VACUUM must be run outside a transaction
                conn.isolation_level = None
                cursor = conn.cursor()
                cursor.execute("VACUUM")
                logger.info("Database optimized successfully")
        except sqlite3.Error as e:
            logger.error(f"Database optimization failed: {e}")
            raise
