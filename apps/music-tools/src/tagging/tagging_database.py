"""
Tagging Database Module - GLOBAL VERSION

Provides persistent tracking of tagged files with:
- SINGLE global SQLite database for ALL files (any directory)
- Files tracked by HASH for move detection
- Resume capability for interrupted sessions
- Dynamically updates paths when files move

Database location: ~/.music_tagger/global_tagging.db
"""

import hashlib
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class FileStatus(Enum):
    """Status of a file in the tagging database."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FileRecord:
    """Represents a file record in the database."""

    id: int
    file_hash: str
    current_path: Optional[str]
    file_size: int
    artist: Optional[str]
    title: Optional[str]
    status: FileStatus
    genre_applied: Optional[str]
    grouping_applied: Optional[str]
    year_applied: Optional[str]
    processed_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    last_seen_at: datetime


class GlobalTaggingDatabase:
    """
    SINGLE global database for tracking ALL tagged files.

    Key features:
    - Files tracked by HASH (content-based) not path
    - When file moves, path updates automatically
    - Works across ANY directory
    - Grows over time as you tag more files

    Database location: ~/.music_tagger/global_tagging.db
    """

    _instance = None
    _db_path = None

    def __new__(cls, db_dir: Optional[str] = None):
        """Singleton pattern - only one global database instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_dir: Optional[str] = None):
        if self._initialized:
            return

        if db_dir is None:
            db_dir = os.path.expanduser("~/.music_tagger")

        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / "global_tagging.db"
        self._init_db()
        self._initialized = True

    def _init_db(self):
        """Initialize the global tagging database."""
        with sqlite3.connect(self.db_path) as conn:
            # Main file tracking table - keyed by HASH
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tagged_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT UNIQUE NOT NULL,
                    current_path TEXT,
                    file_size INTEGER,
                    artist TEXT,
                    title TEXT,
                    status TEXT DEFAULT 'pending',
                    genre_applied TEXT,
                    grouping_applied TEXT,
                    year_applied TEXT,
                    processed_at TIMESTAMP,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Path history table - track where files have been
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS path_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT NOT NULL,
                    path TEXT NOT NULL,
                    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_hash) REFERENCES tagged_files(file_hash)
                )
            """
            )

            # Session tracking table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_directory TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    files_processed INTEGER DEFAULT 0,
                    files_updated INTEGER DEFAULT 0,
                    files_failed INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running'
                )
            """
            )

            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON tagged_files(file_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON tagged_files(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_artist ON tagged_files(artist)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_path ON tagged_files(current_path)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_path_history_hash ON path_history(file_hash)"
            )
            conn.commit()

            print(f"Global database initialized: {self.db_path}")

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculate MD5 hash of file content."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def get_record_by_hash(self, file_hash: str) -> Optional[FileRecord]:
        """Get full record for a file by its hash."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tagged_files WHERE file_hash = ?", (file_hash,))
            row = cursor.fetchone()
            if not row:
                return None

            return FileRecord(
                id=row["id"],
                file_hash=row["file_hash"],
                current_path=row["current_path"],
                file_size=row["file_size"],
                artist=row["artist"],
                title=row["title"],
                status=FileStatus(row["status"]),
                genre_applied=row["genre_applied"],
                grouping_applied=row["grouping_applied"],
                year_applied=row["year_applied"],
                processed_at=row["processed_at"],
                error_message=row["error_message"],
                retry_count=row["retry_count"],
                created_at=row["created_at"],
                last_seen_at=row["last_seen_at"],
            )

    def get_record_by_path(self, file_path: str) -> Optional[FileRecord]:
        """Get record by current path (less reliable than hash)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tagged_files WHERE current_path = ?", (file_path,))
            row = cursor.fetchone()
            if row:
                return FileRecord(
                    id=row["id"],
                    file_hash=row["file_hash"],
                    current_path=row["current_path"],
                    file_size=row["file_size"],
                    artist=row["artist"],
                    title=row["title"],
                    status=FileStatus(row["status"]),
                    genre_applied=row["genre_applied"],
                    grouping_applied=row["grouping_applied"],
                    year_applied=row["year_applied"],
                    processed_at=row["processed_at"],
                    error_message=row["error_message"],
                    retry_count=row["retry_count"],
                    created_at=row["created_at"],
                    last_seen_at=row["last_seen_at"],
                )
            return None

    def should_process_file(self, file_path: str, force: bool = False) -> Tuple[bool, str]:
        """
        Determine if a file should be processed.
        Uses HASH to check if file was tagged before (even if moved).

        Returns:
            (should_process, reason)
        """
        if force:
            return True, "Force re-tag requested"

        # Calculate file hash
        try:
            file_hash = self.calculate_file_hash(file_path)
        except Exception as e:
            return True, f"New file (couldn't hash: {e})"

        # Check if this hash exists in database
        record = self.get_record_by_hash(file_hash)

        if record:
            # Update current path if file moved
            if record.current_path != file_path:
                self._update_file_path(file_hash, file_path)

            # Already completed
            if record.status == FileStatus.COMPLETED:
                return False, "Already tagged"

            # Failed too many times
            if record.status == FileStatus.FAILED and record.retry_count >= 3:
                return False, "Max retries exceeded"

            # Pending or processing (interrupted session)
            if record.status in (FileStatus.PENDING, FileStatus.PROCESSING):
                return True, "Resume interrupted processing"

            # Failed but can retry
            if record.status == FileStatus.FAILED:
                return True, f"Retry attempt {record.retry_count + 1}"

            # Skipped
            if record.status == FileStatus.SKIPPED:
                return False, "Previously skipped"

        return True, "New file"

    def _update_file_path(self, file_hash: str, new_path: str):
        """Update the current path for a file and log to history."""
        with sqlite3.connect(self.db_path) as conn:
            # Update current path
            conn.execute(
                """
                UPDATE tagged_files SET
                    current_path = ?,
                    last_seen_at = CURRENT_TIMESTAMP
                WHERE file_hash = ?
            """,
                (new_path, file_hash),
            )

            # Add to path history
            conn.execute(
                """
                INSERT INTO path_history (file_hash, path)
                VALUES (?, ?)
            """,
                (file_hash, new_path),
            )

            conn.commit()

    def mark_processing(
        self,
        file_path: str,
        artist: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """Mark a file as currently being processed."""
        try:
            file_hash = self.calculate_file_hash(file_path)
            file_size = os.path.getsize(file_path)
        except Exception:
            return

        with sqlite3.connect(self.db_path) as conn:
            # Check if exists
            cursor = conn.execute("SELECT id FROM tagged_files WHERE file_hash = ?", (file_hash,))
            exists = cursor.fetchone()

            if exists:
                # Update existing
                conn.execute(
                    """
                    UPDATE tagged_files SET
                        status = ?,
                        current_path = ?,
                        artist = COALESCE(?, artist),
                        title = COALESCE(?, title),
                        last_seen_at = CURRENT_TIMESTAMP
                    WHERE file_hash = ?
                """,
                    (FileStatus.PROCESSING.value, file_path, artist, title, file_hash),
                )
            else:
                # Insert new
                conn.execute(
                    """
                    INSERT INTO tagged_files
                    (file_hash, current_path, file_size, status, artist, title)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (file_hash, file_path, file_size, FileStatus.PROCESSING.value, artist, title),
                )

                # Add to path history
                conn.execute(
                    """
                    INSERT INTO path_history (file_hash, path)
                    VALUES (?, ?)
                """,
                    (file_hash, file_path),
                )

            conn.commit()

    def mark_completed(
        self,
        file_path: str,
        genre: Optional[str] = None,
        grouping: Optional[str] = None,
        year: Optional[str] = None,
        artist: Optional[str] = None,
    ):
        """Mark a file as successfully tagged."""
        try:
            file_hash = self.calculate_file_hash(file_path)
        except Exception:
            return

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE tagged_files SET
                    status = ?,
                    genre_applied = COALESCE(?, genre_applied),
                    grouping_applied = COALESCE(?, grouping_applied),
                    year_applied = COALESCE(?, year_applied),
                    artist = COALESCE(?, artist),
                    processed_at = CURRENT_TIMESTAMP,
                    error_message = NULL,
                    last_seen_at = CURRENT_TIMESTAMP
                WHERE file_hash = ?
            """,
                (FileStatus.COMPLETED.value, genre, grouping, year, artist, file_hash),
            )
            conn.commit()

    def mark_failed(self, file_path: str, error_message: str):
        """Mark a file as failed."""
        try:
            file_hash = self.calculate_file_hash(file_path)
        except Exception:
            return

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE tagged_files SET
                    status = ?,
                    error_message = ?,
                    retry_count = retry_count + 1,
                    processed_at = CURRENT_TIMESTAMP,
                    last_seen_at = CURRENT_TIMESTAMP
                WHERE file_hash = ?
            """,
                (FileStatus.FAILED.value, error_message, file_hash),
            )
            conn.commit()

    def mark_skipped(self, file_path: str, reason: str):
        """Mark a file as skipped."""
        try:
            file_hash = self.calculate_file_hash(file_path)
            file_size = os.path.getsize(file_path)
        except Exception:
            return

        with sqlite3.connect(self.db_path) as conn:
            # Check if exists
            cursor = conn.execute("SELECT id FROM tagged_files WHERE file_hash = ?", (file_hash,))
            exists = cursor.fetchone()

            if exists:
                conn.execute(
                    """
                    UPDATE tagged_files SET
                        status = ?,
                        error_message = ?,
                        current_path = ?,
                        last_seen_at = CURRENT_TIMESTAMP
                    WHERE file_hash = ?
                """,
                    (FileStatus.SKIPPED.value, reason, file_path, file_hash),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO tagged_files
                    (file_hash, current_path, file_size, status, error_message)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (file_hash, file_path, file_size, FileStatus.SKIPPED.value, reason),
                )

            conn.commit()

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about ALL tagged files globally."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}

            # Count by status
            cursor = conn.execute(
                """
                SELECT status, COUNT(*) as count
                FROM tagged_files
                GROUP BY status
            """
            )
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}

            stats["total_files"] = sum(status_counts.values())
            stats["completed"] = status_counts.get("completed", 0)
            stats["failed"] = status_counts.get("failed", 0)
            stats["pending"] = status_counts.get("pending", 0)
            stats["skipped"] = status_counts.get("skipped", 0)

            # Unique artists
            cursor = conn.execute(
                """
                SELECT COUNT(DISTINCT artist) FROM tagged_files
                WHERE artist IS NOT NULL
            """
            )
            stats["unique_artists"] = cursor.fetchone()[0]

            # Last processed
            cursor = conn.execute(
                """
                SELECT MAX(processed_at) FROM tagged_files
            """
            )
            stats["last_processed"] = cursor.fetchone()[0]

            return stats

    def reset_processing_status(self):
        """Reset any files stuck in 'processing' status to 'pending'."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE tagged_files
                SET status = 'pending'
                WHERE status = 'processing'
            """
            )
            conn.commit()

    def clear_failed_for_retry(self):
        """Reset all failed files to pending for retry."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE tagged_files
                SET status = 'pending', retry_count = 0, error_message = NULL
                WHERE status = 'failed'
            """
            )
            conn.commit()

    def force_retag_all(self):
        """Mark all files as pending for re-tagging."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE tagged_files
                SET status = 'pending', retry_count = 0, error_message = NULL
            """
            )
            conn.commit()

    def force_retag_artist(self, artist: str):
        """Mark all files by a specific artist as pending."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE tagged_files
                SET status = 'pending', retry_count = 0, error_message = NULL
                WHERE artist = ?
            """,
                (artist,),
            )
            conn.commit()

    # Session management
    def start_session(self, scan_directory: Optional[str] = None) -> int:
        """Start a new processing session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (scan_directory, started_at, status)
                VALUES (?, CURRENT_TIMESTAMP, 'running')
            """,
                (scan_directory,),
            )
            conn.commit()
            return cursor.lastrowid

    def update_session(
        self, session_id: int, files_processed: int, files_updated: int, files_failed: int
    ):
        """Update session statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE sessions SET
                    files_processed = ?,
                    files_updated = ?,
                    files_failed = ?
                WHERE id = ?
            """,
                (files_processed, files_updated, files_failed, session_id),
            )
            conn.commit()

    def end_session(
        self, session_id: int, files_processed: int, files_updated: int, files_failed: int
    ):
        """End a processing session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE sessions SET
                    ended_at = CURRENT_TIMESTAMP,
                    files_processed = ?,
                    files_updated = ?,
                    files_failed = ?,
                    status = 'completed'
                WHERE id = ?
            """,
                (files_processed, files_updated, files_failed, session_id),
            )
            conn.commit()

    def get_last_session(self) -> Optional[Dict[str, Any]]:
        """Get information about the last session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM sessions ORDER BY id DESC LIMIT 1
            """
            )
            row = cursor.fetchone()
            return dict(row) if row else None


# Backward compatibility aliases
TaggingDatabase = GlobalTaggingDatabase
GlobalHashCache = GlobalTaggingDatabase  # No longer needed separately
