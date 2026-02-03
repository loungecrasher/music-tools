"""
Database migrations package for Music Tools.

This package contains database migration scripts for evolving the schema over time.
Each migration is numbered and can be applied or rolled back independently.

Available migrations:
    - 002_add_quality_tables: Adds file quality, deduplication, and upgrade tracking

Usage:
    from music_tools_common.database.migrations import apply_migration, rollback_migration

    # Apply a migration
    success, message = apply_migration('002', db_path)

    # Rollback a migration
    success, message = rollback_migration('002', db_path, backup_path)
"""

import importlib
import logging
from typing import Optional, Tuple

logger = logging.getLogger('music_tools.migrations')

# Available migrations
MIGRATIONS = {
    '002': '002_add_quality_tables'
}


def get_migration_module(version: str):
    """
    Import and return a migration module by version.

    Args:
        version: Migration version (e.g., '002')

    Returns:
        Migration module

    Raises:
        ImportError: If migration not found
    """
    if version not in MIGRATIONS:
        raise ImportError(f"Migration {version} not found. Available: {list(MIGRATIONS.keys())}")

    module_name = MIGRATIONS[version]
    return importlib.import_module(f'.{module_name}', package=__package__)


def apply_migration(version: str, db_path: str) -> Tuple[bool, str]:
    """
    Apply a migration by version number.

    Args:
        version: Migration version (e.g., '002')
        db_path: Path to the database file

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        module = get_migration_module(version)
        return module.migrate(db_path)
    except Exception as e:
        error_msg = f"Failed to apply migration {version}: {str(e)}"
        logger.error(error_msg)
        return (False, error_msg)


def rollback_migration(version: str, db_path: str, backup_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Rollback a migration by version number.

    Args:
        version: Migration version (e.g., '002')
        db_path: Path to the database file
        backup_path: Optional path to backup file

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        module = get_migration_module(version)
        return module.rollback(db_path, backup_path)
    except Exception as e:
        error_msg = f"Failed to rollback migration {version}: {str(e)}"
        logger.error(error_msg)
        return (False, error_msg)


def get_migration_status(version: str, db_path: str) -> dict:
    """
    Get the status of a migration.

    Args:
        version: Migration version (e.g., '002')
        db_path: Path to the database file

    Returns:
        Dictionary with migration status
    """
    try:
        module = get_migration_module(version)
        return module.get_migration_status(db_path)
    except Exception as e:
        return {
            'version': version,
            'error': str(e)
        }


def list_migrations() -> dict:
    """
    List all available migrations.

    Returns:
        Dictionary of version -> module_name
    """
    return MIGRATIONS.copy()


__all__ = [
    'apply_migration',
    'rollback_migration',
    'get_migration_status',
    'list_migrations',
    'MIGRATIONS'
]
