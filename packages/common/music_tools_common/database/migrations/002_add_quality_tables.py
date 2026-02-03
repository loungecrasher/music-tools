"""
Database Migration 002: Add Quality Metrics Tables

This migration adds three new tables for audio quality tracking, deduplication,
and upgrade candidate management, along with 20 performance indexes.

Tables:
    - file_quality: Audio quality metrics for files
    - dedup_history: Audit trail for file deletions during deduplication
    - upgrade_candidates: Tracks files that could be upgraded to better quality

Features:
    - Transactional execution with BEGIN/COMMIT/ROLLBACK
    - Automatic backup creation with timestamp
    - Schema version tracking in settings table
    - 20 performance indexes for optimized queries
    - Foreign key constraints with cascading deletes
    - Default values for all fields
    - Comprehensive validation and error handling

Author: Database Migration Agent
Version: 002
Created: 2026-01-08
"""

import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("migration_002")

# Migration metadata
MIGRATION_VERSION = "002"
MIGRATION_NAME = "add_quality_tables"
MIGRATION_DESCRIPTION = "Add file quality, deduplication history, and upgrade candidate tables"


class MigrationError(Exception):
    """Custom exception for migration errors."""


def create_backup(db_path: str) -> str:
    """
    Create a backup of the database before migration.

    Args:
        db_path: Path to the database file

    Returns:
        Path to the backup file

    Raises:
        MigrationError: If backup creation fails
    """
    try:
        db_file = Path(db_path)
        if not db_file.exists():
            raise MigrationError(f"Database file not found: {db_path}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_file.parent / f"{db_file.stem}_backup_{timestamp}{db_file.suffix}"

        logger.info(f"Creating backup: {backup_path}")
        shutil.copy2(db_path, backup_path)

        logger.info(f"Backup created successfully: {backup_path}")
        return str(backup_path)

    except Exception as e:
        raise MigrationError(f"Failed to create backup: {str(e)}")


def validate_database(conn: sqlite3.Connection) -> bool:
    """
    Validate that the database is ready for migration.

    Args:
        conn: Database connection

    Returns:
        True if validation passes

    Raises:
        MigrationError: If validation fails
    """
    cursor = conn.cursor()

    # Check that required tables exist
    cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name IN ('playlists', 'tracks', 'settings')
    """
    )
    existing_tables = {row[0] for row in cursor.fetchall()}
    required_tables = {"playlists", "tracks", "settings"}

    if not required_tables.issubset(existing_tables):
        missing = required_tables - existing_tables
        raise MigrationError(f"Missing required tables: {missing}")

    # Check that migration hasn't already been applied
    cursor.execute(
        """
        SELECT value FROM settings WHERE key = ?
    """,
        (f"migration_version_{MIGRATION_VERSION}",),
    )

    result = cursor.fetchone()
    if result:
        raise MigrationError(f"Migration {MIGRATION_VERSION} has already been applied")

    logger.info("Database validation passed")
    return True


def migrate(db_path: str) -> Tuple[bool, str]:
    """
    Apply the migration to add quality metrics tables.

    This function:
    1. Creates a backup of the database
    2. Validates the database state
    3. Creates three new tables with proper constraints
    4. Adds 20 performance indexes
    5. Updates schema version tracking

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Tuple of (success: bool, message: str)
    """
    conn = None
    backup_path = None

    try:
        logger.info(f"Starting migration {MIGRATION_VERSION}: {MIGRATION_NAME}")

        # Create backup
        backup_path = create_backup(db_path)

        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Validate database
        validate_database(conn)

        # Begin transaction
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")

        logger.info("Creating file_quality table...")

        # Create file_quality table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL DEFAULT 0,
                format TEXT NOT NULL DEFAULT 'unknown',
                bitrate INTEGER DEFAULT NULL,
                sample_rate INTEGER DEFAULT NULL,
                bit_depth INTEGER DEFAULT NULL,
                channels INTEGER DEFAULT 2,
                duration REAL DEFAULT 0.0,
                codec TEXT DEFAULT NULL,
                quality_score REAL DEFAULT 0.0,
                is_lossy BOOLEAN DEFAULT 1,
                has_metadata BOOLEAN DEFAULT 0,
                track_id TEXT DEFAULT NULL,
                scan_date TEXT NOT NULL,
                last_modified TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE SET NULL
            )
        """
        )

        logger.info("Creating dedup_history table...")

        # Create dedup_history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dedup_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                original_hash TEXT NOT NULL,
                original_size INTEGER NOT NULL DEFAULT 0,
                original_quality_score REAL DEFAULT 0.0,
                kept_path TEXT NOT NULL,
                kept_hash TEXT NOT NULL,
                kept_size INTEGER NOT NULL DEFAULT 0,
                kept_quality_score REAL DEFAULT 0.0,
                deletion_reason TEXT NOT NULL DEFAULT 'duplicate',
                space_saved INTEGER DEFAULT 0,
                track_id TEXT DEFAULT NULL,
                deleted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_by TEXT DEFAULT 'system',
                can_restore BOOLEAN DEFAULT 0,
                restore_location TEXT DEFAULT NULL,
                notes TEXT DEFAULT NULL,
                FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE SET NULL
            )
        """
        )

        logger.info("Creating upgrade_candidates table...")

        # Create upgrade_candidates table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS upgrade_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                current_format TEXT NOT NULL DEFAULT 'unknown',
                current_bitrate INTEGER DEFAULT NULL,
                current_quality_score REAL DEFAULT 0.0,
                suggested_format TEXT DEFAULT 'flac',
                suggested_bitrate INTEGER DEFAULT NULL,
                potential_improvement REAL DEFAULT 0.0,
                priority_score REAL DEFAULT 0.0,
                track_id TEXT DEFAULT NULL,
                track_name TEXT DEFAULT NULL,
                artist_name TEXT DEFAULT NULL,
                availability_checked BOOLEAN DEFAULT 0,
                available_sources TEXT DEFAULT NULL,
                estimated_cost REAL DEFAULT 0.0,
                upgrade_status TEXT DEFAULT 'pending',
                identified_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_checked TEXT DEFAULT NULL,
                upgraded_at TEXT DEFAULT NULL,
                notes TEXT DEFAULT NULL,
                FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
            )
        """
        )

        logger.info("Creating indexes for file_quality table...")

        # Create indexes for file_quality table (7 indexes)
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_file_quality_path
            ON file_quality(file_path)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_file_quality_hash
            ON file_quality(file_hash)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_file_quality_track_id
            ON file_quality(track_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_file_quality_format_bitrate
            ON file_quality(format, bitrate DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_file_quality_score
            ON file_quality(quality_score DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_file_quality_scan_date
            ON file_quality(scan_date DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_file_quality_format_lossy
            ON file_quality(format, is_lossy)
        """
        )

        logger.info("Creating indexes for dedup_history table...")

        # Create indexes for dedup_history table (6 indexes)
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dedup_history_original_hash
            ON dedup_history(original_hash)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dedup_history_kept_hash
            ON dedup_history(kept_hash)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dedup_history_track_id
            ON dedup_history(track_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dedup_history_deleted_at
            ON dedup_history(deleted_at DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dedup_history_can_restore
            ON dedup_history(can_restore, deleted_at DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_dedup_history_reason
            ON dedup_history(deletion_reason, deleted_at DESC)
        """
        )

        logger.info("Creating indexes for upgrade_candidates table...")

        # Create indexes for upgrade_candidates table (7 indexes)
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upgrade_candidates_track_id
            ON upgrade_candidates(track_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upgrade_candidates_priority
            ON upgrade_candidates(priority_score DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upgrade_candidates_status
            ON upgrade_candidates(upgrade_status, priority_score DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upgrade_candidates_quality_improvement
            ON upgrade_candidates(potential_improvement DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upgrade_candidates_format
            ON upgrade_candidates(current_format, current_quality_score)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upgrade_candidates_artist
            ON upgrade_candidates(artist_name, priority_score DESC)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upgrade_candidates_identified
            ON upgrade_candidates(identified_at DESC)
        """
        )

        logger.info("Updating schema version...")

        # Update schema version in settings
        now = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """,
            (f"migration_version_{MIGRATION_VERSION}", now, now),
        )

        # Store migration metadata
        cursor.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """,
            (f"migration_{MIGRATION_VERSION}_name", MIGRATION_NAME, now),
        )

        cursor.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        """,
            (f"migration_{MIGRATION_VERSION}_description", MIGRATION_DESCRIPTION, now),
        )

        # Commit transaction
        conn.commit()
        logger.info("Migration committed successfully")

        # Verify tables were created
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('file_quality', 'dedup_history', 'upgrade_candidates')
        """
        )
        created_tables = [row[0] for row in cursor.fetchall()]

        if len(created_tables) != 3:
            raise MigrationError(f"Not all tables were created. Found: {created_tables}")

        logger.info(f"Migration {MIGRATION_VERSION} completed successfully")
        logger.info(f"Tables created: {', '.join(created_tables)}")
        logger.info("Indexes created: 20 performance indexes")
        logger.info(f"Backup location: {backup_path}")

        return (True, f"Migration {MIGRATION_VERSION} applied successfully. Backup: {backup_path}")

    except Exception as e:
        error_msg = f"Migration failed: {str(e)}"
        logger.error(error_msg)

        if conn:
            try:
                logger.info("Rolling back transaction...")
                conn.rollback()
                logger.info("Rollback successful")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {str(rollback_error)}")

        if backup_path:
            logger.info(f"Backup available at: {backup_path}")
            error_msg += f" Database backup available at: {backup_path}"

        return (False, error_msg)

    finally:
        if conn:
            conn.close()


def rollback(db_path: str, backup_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Rollback the migration by removing the quality tables.

    This function:
    1. Optionally restores from backup if provided
    2. Otherwise, drops the created tables
    3. Removes version tracking entries

    Args:
        db_path: Path to the SQLite database file
        backup_path: Optional path to backup file to restore from

    Returns:
        Tuple of (success: bool, message: str)
    """
    conn = None

    try:
        logger.info(f"Starting rollback of migration {MIGRATION_VERSION}")

        # If backup path provided, restore from backup
        if backup_path and Path(backup_path).exists():
            logger.info(f"Restoring from backup: {backup_path}")
            shutil.copy2(backup_path, db_path)
            logger.info("Database restored from backup")
            return (True, f"Database restored from backup: {backup_path}")

        # Otherwise, drop tables manually
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Begin transaction
        cursor.execute("BEGIN TRANSACTION")

        logger.info("Dropping quality tables...")

        # Drop tables in reverse order (due to foreign keys)
        cursor.execute("DROP TABLE IF EXISTS upgrade_candidates")
        cursor.execute("DROP TABLE IF EXISTS dedup_history")
        cursor.execute("DROP TABLE IF EXISTS file_quality")

        logger.info("Removing version tracking...")

        # Remove version tracking
        cursor.execute(
            """
            DELETE FROM settings WHERE key LIKE ?
        """,
            (f"migration_{MIGRATION_VERSION}%",),
        )

        cursor.execute(
            """
            DELETE FROM settings WHERE key = ?
        """,
            (f"migration_version_{MIGRATION_VERSION}",),
        )

        # Commit transaction
        conn.commit()
        logger.info("Rollback completed successfully")

        return (True, f"Migration {MIGRATION_VERSION} rolled back successfully")

    except Exception as e:
        error_msg = f"Rollback failed: {str(e)}"
        logger.error(error_msg)

        if conn:
            try:
                conn.rollback()
            except Exception as rollback_error:
                logger.error(f"Transaction rollback failed: {str(rollback_error)}")

        return (False, error_msg)

    finally:
        if conn:
            conn.close()


def get_migration_status(db_path: str) -> dict:
    """
    Get the status of this migration.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Dictionary with migration status information
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if migration has been applied
        cursor.execute(
            """
            SELECT value FROM settings WHERE key = ?
        """,
            (f"migration_version_{MIGRATION_VERSION}",),
        )

        result = cursor.fetchone()
        applied = result is not None
        applied_date = result[0] if result else None

        # Check if tables exist
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('file_quality', 'dedup_history', 'upgrade_candidates')
        """
        )
        existing_tables = [row[0] for row in cursor.fetchall()]

        conn.close()

        return {
            "version": MIGRATION_VERSION,
            "name": MIGRATION_NAME,
            "description": MIGRATION_DESCRIPTION,
            "applied": applied,
            "applied_date": applied_date,
            "tables_exist": len(existing_tables) == 3,
            "existing_tables": existing_tables,
        }

    except Exception as e:
        return {"version": MIGRATION_VERSION, "error": str(e)}


if __name__ == "__main__":
    """
    Run migration from command line.

    Usage:
        python 002_add_quality_tables.py migrate <db_path>
        python 002_add_quality_tables.py rollback <db_path> [backup_path]
        python 002_add_quality_tables.py status <db_path>
    """
    import sys

    if len(sys.argv) < 3:
        print("Usage:")
        print("  migrate:  python 002_add_quality_tables.py migrate <db_path>")
        print("  rollback: python 002_add_quality_tables.py rollback <db_path> [backup_path]")
        print("  status:   python 002_add_quality_tables.py status <db_path>")
        sys.exit(1)

    command = sys.argv[1]
    db_path = sys.argv[2]

    if command == "migrate":
        success, message = migrate(db_path)
        print(message)
        sys.exit(0 if success else 1)

    elif command == "rollback":
        backup_path = sys.argv[3] if len(sys.argv) > 3 else None
        success, message = rollback(db_path, backup_path)
        print(message)
        sys.exit(0 if success else 1)

    elif command == "status":
        status = get_migration_status(db_path)
        print(f"Migration {status['version']}: {status['name']}")
        print(f"Description: {status['description']}")
        print(f"Applied: {status.get('applied', False)}")
        if status.get("applied_date"):
            print(f"Applied Date: {status['applied_date']}")
        print(f"Tables Exist: {status.get('tables_exist', False)}")
        if status.get("existing_tables"):
            print(f"Existing Tables: {', '.join(status['existing_tables'])}")
        if "error" in status:
            print(f"Error: {status['error']}")
        sys.exit(0)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
