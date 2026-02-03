# Database Migrations

This directory contains database migration scripts for evolving the Music Tools database schema over time.

## Overview

Each migration script is numbered and designed to be applied sequentially. Migrations include both `migrate()` and `rollback()` functions for forward and backward compatibility.

## Available Migrations

### 002_add_quality_tables.py

Adds three new tables for audio quality tracking and file management:

- **file_quality**: Stores audio quality metrics for each file
- **dedup_history**: Audit trail for file deletions during deduplication
- **upgrade_candidates**: Tracks files that could be upgraded to better quality

**Features**:
- 20 performance indexes
- Foreign key constraints
- Automatic backup creation
- Transaction management
- Schema version tracking

## Usage

### Command Line

```bash
# Apply migration
python 002_add_quality_tables.py migrate /path/to/database.db

# Check migration status
python 002_add_quality_tables.py status /path/to/database.db

# Rollback migration
python 002_add_quality_tables.py rollback /path/to/database.db

# Rollback with backup restoration
python 002_add_quality_tables.py rollback /path/to/database.db /path/to/backup.db
```

### Python API

```python
from music_tools_common.database.migrations import apply_migration, rollback_migration

# Apply migration
success, message = apply_migration('002', '/path/to/database.db')
if success:
    print(f"Migration applied: {message}")
else:
    print(f"Migration failed: {message}")

# Rollback migration
success, message = rollback_migration('002', '/path/to/database.db')
```

### Direct Import

```python
from music_tools_common.database.migrations import migration_002_add_quality_tables

# Apply migration
success, message = migration_002_add_quality_tables.migrate('/path/to/database.db')

# Check status
status = migration_002_add_quality_tables.get_migration_status('/path/to/database.db')
print(f"Applied: {status['applied']}")

# Rollback
success, message = migration_002_add_quality_tables.rollback('/path/to/database.db')
```

## Migration Process

Each migration follows this process:

1. **Validation**: Checks database state and prerequisites
2. **Backup**: Creates timestamped backup of database
3. **Transaction**: Begins database transaction
4. **Schema Changes**: Creates tables, indexes, constraints
5. **Version Tracking**: Updates settings table with migration metadata
6. **Commit**: Commits transaction if successful
7. **Rollback**: Automatic rollback on any error

## Safety Features

- **Automatic Backups**: Every migration creates a timestamped backup
- **Transaction Safety**: All changes in a single transaction
- **Validation**: Pre-flight checks prevent invalid migrations
- **Idempotency**: Migrations check if already applied
- **Rollback Support**: All migrations can be reversed

## Schema Version Tracking

Migrations are tracked in the `settings` table:

```sql
-- Version marker
migration_version_002 = "2026-01-08T10:30:00"

-- Metadata
migration_002_name = "add_quality_tables"
migration_002_description = "Add file quality, deduplication history..."
```

## Creating New Migrations

To create a new migration:

1. Number it sequentially (003, 004, etc.)
2. Follow the template pattern
3. Implement both `migrate()` and `rollback()` functions
4. Add comprehensive error handling
5. Include validation checks
6. Document all schema changes
7. Add to `MIGRATIONS` dict in `__init__.py`

### Migration Template

```python
"""
Database Migration XXX: Description

Brief description of changes
"""

import sqlite3
import shutil
import logging
from typing import Tuple, Optional
from datetime import datetime
from pathlib import Path

MIGRATION_VERSION = 'XXX'
MIGRATION_NAME = 'migration_name'
MIGRATION_DESCRIPTION = 'Description'

def create_backup(db_path: str) -> str:
    # Create backup...
    pass

def validate_database(conn: sqlite3.Connection) -> bool:
    # Validate...
    pass

def migrate(db_path: str) -> Tuple[bool, str]:
    # Apply migration...
    pass

def rollback(db_path: str, backup_path: Optional[str] = None) -> Tuple[bool, str]:
    # Rollback migration...
    pass

def get_migration_status(db_path: str) -> dict:
    # Get status...
    pass
```

## Table Schemas

### file_quality

Stores audio quality metrics for music files:

```sql
CREATE TABLE file_quality (
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
```

**Indexes**:
- `idx_file_quality_path` - File path lookup
- `idx_file_quality_hash` - Duplicate detection
- `idx_file_quality_track_id` - Track relationships
- `idx_file_quality_format_bitrate` - Quality filtering
- `idx_file_quality_score` - Quality sorting
- `idx_file_quality_scan_date` - Recent scans
- `idx_file_quality_format_lossy` - Format queries

### dedup_history

Audit trail for file deletions during deduplication:

```sql
CREATE TABLE dedup_history (
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
```

**Indexes**:
- `idx_dedup_history_original_hash` - Find deleted files
- `idx_dedup_history_kept_hash` - Find kept files
- `idx_dedup_history_track_id` - Track relationships
- `idx_dedup_history_deleted_at` - Deletion timeline
- `idx_dedup_history_can_restore` - Restorable files
- `idx_dedup_history_reason` - Deletion reasons

### upgrade_candidates

Tracks files that could be upgraded to better quality:

```sql
CREATE TABLE upgrade_candidates (
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
```

**Indexes**:
- `idx_upgrade_candidates_track_id` - Track relationships
- `idx_upgrade_candidates_priority` - Priority ordering
- `idx_upgrade_candidates_status` - Status filtering
- `idx_upgrade_candidates_quality_improvement` - Improvement ranking
- `idx_upgrade_candidates_format` - Format queries
- `idx_upgrade_candidates_artist` - Artist filtering
- `idx_upgrade_candidates_identified` - Discovery timeline

## Troubleshooting

### Migration Already Applied

If you see "Migration XXX has already been applied":
- Check status: `python XXX.py status /path/to/db`
- If needed, manually remove from settings table
- Or rollback first: `python XXX.py rollback /path/to/db`

### Transaction Rollback

If migration fails, the transaction is automatically rolled back. Check logs for details.

### Backup Restoration

If you need to restore from backup:
```bash
cp /path/to/backup.db /path/to/database.db
```

Or use rollback with backup path:
```bash
python XXX.py rollback /path/to/database.db /path/to/backup.db
```

## Best Practices

1. **Always test migrations** on a copy of production database
2. **Verify backups** are created before applying
3. **Check migration status** before and after
4. **Keep backups** for at least 30 days
5. **Document changes** in migration description
6. **Test rollback** procedures
7. **Monitor performance** after schema changes
8. **Run ANALYZE** after creating indexes

## Performance Notes

The 20 indexes created by migration 002 are optimized for:
- Fast duplicate detection (hash lookups)
- Quality-based filtering (bitrate, format, score)
- Time-based queries (scan dates, deletion dates)
- Relationship queries (track_id foreign keys)
- Sorting and ranking (priority, quality scores)

After applying migrations with new indexes:
```sql
ANALYZE;
```

This updates SQLite's query planner statistics for optimal performance.

## Support

For issues with migrations:
1. Check logs for detailed error messages
2. Verify database file permissions
3. Ensure sufficient disk space for backups
4. Check SQLite version compatibility
5. Review migration source code comments

## Version History

- **002** (2026-01-08): Add quality metrics tables (file_quality, dedup_history, upgrade_candidates)
