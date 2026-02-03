"""
Database module for Music Tools.
Provides a SQLite database interface for storing and retrieving data.
"""
import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('music_tools.database')


class Database:
    """SQLite database interface for Music Tools."""

    def __init__(self, db_path: str = None):
        """Initialize the database.

        Args:
            db_path: Path to the SQLite database file. If None, uses default.
        """
        if db_path is None:
            # Default to data directory in the project root
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, 'music_tools.db')
        else:
            self.db_path = db_path

        self.conn = None
        self.cursor = None

        # Initialize database
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Initialize the database connection and create tables if they don't exist."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.cursor = self.conn.cursor()

            # Apply performance optimizations (SQLite PRAGMAs)
            self._apply_performance_pragmas()

            # Create tables
            self._create_tables()

            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    def _apply_performance_pragmas(self) -> None:
        """Apply SQLite performance optimization PRAGMAs."""
        # Enable Write-Ahead Logging for better concurrency
        self.cursor.execute("PRAGMA journal_mode=WAL")

        # Increase cache size to 10MB (default is 2MB)
        self.cursor.execute("PRAGMA cache_size=-10000")

        # Use NORMAL synchronous mode (faster, still safe)
        self.cursor.execute("PRAGMA synchronous=NORMAL")

        # Store temp tables in memory
        self.cursor.execute("PRAGMA temp_store=MEMORY")

        # Enable memory-mapped I/O (32MB)
        self.cursor.execute("PRAGMA mmap_size=33554432")

        logger.debug("Applied SQLite performance optimizations")

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        # Playlists table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            owner TEXT,
            tracks_count INTEGER DEFAULT 0,
            service TEXT NOT NULL,
            is_algorithmic BOOLEAN DEFAULT 0,
            added_on TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
        ''')

        # Tracks table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            artist TEXT NOT NULL,
            album TEXT,
            duration INTEGER,
            release_date TEXT,
            isrc TEXT,
            service TEXT NOT NULL,
            added_on TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
        ''')

        # Playlist tracks table (many-to-many relationship)
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlist_tracks (
            playlist_id TEXT,
            track_id TEXT,
            added_at TEXT,
            position INTEGER,
            PRIMARY KEY (playlist_id, track_id),
            FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
            FOREIGN KEY (track_id) REFERENCES tracks(id) ON DELETE CASCADE
        )
        ''')

        # Settings table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT NOT NULL
        )
        ''')

        # Create high-impact composite indexes for performance optimization

        # Playlist indexes - optimize filtered queries by service and type
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_playlists_service_algorithmic
        ON playlists(service, is_algorithmic)
        ''')

        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_playlists_service_name
        ON playlists(service, name)
        ''')

        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_playlists_last_updated
        ON playlists(last_updated DESC)
        ''')

        # Track indexes - optimize searches by artist, service, and release date
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tracks_artist_name
        ON tracks(artist, name)
        ''')

        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tracks_service_release
        ON tracks(service, release_date)
        ''')

        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tracks_isrc
        ON tracks(isrc)
        ''')

        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tracks_artist
        ON tracks(artist)
        ''')

        # Playlist tracks indexes - optimize ordered retrieval and lookups
        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_playlist_tracks_position
        ON playlist_tracks(playlist_id, position)
        ''')

        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_playlist_tracks_track
        ON playlist_tracks(track_id)
        ''')

        self.cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_playlist_tracks_added
        ON playlist_tracks(added_at DESC)
        ''')

        # Commit changes
        self.conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    # Playlist methods

    def add_playlist(self, playlist: Dict[str, Any], service: str) -> bool:
        """Add a playlist to the database.

        Args:
            playlist: Playlist data
            service: Service name (e.g., 'spotify', 'deezer')

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now().isoformat()

            self.cursor.execute('''
            INSERT OR REPLACE INTO playlists (
                id, name, url, owner, tracks_count, service, is_algorithmic, added_on, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                playlist['id'],
                playlist['name'],
                playlist.get('url', f"https://open.spotify.com/playlist/{playlist['id']}"),
                playlist.get('owner', 'unknown'),
                playlist.get('tracks', 0),
                service,
                1 if playlist.get('algorithmic', False) else 0,
                playlist.get('added_on', now),
                now
            ))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding playlist: {str(e)}")
            self.conn.rollback()
            return False

    def get_playlist(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get a playlist from the database.

        Args:
            playlist_id: Playlist ID

        Returns:
            Playlist data or None if not found
        """
        try:
            self.cursor.execute('''
            SELECT * FROM playlists WHERE id = ?
            ''', (playlist_id,))

            row = self.cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error getting playlist: {str(e)}")
            return None

    def get_playlists(self, service: str = None, algorithmic_only: bool = False) -> List[Dict[str, Any]]:
        """Get playlists from the database.

        Args:
            service: Service name to filter by (e.g., 'spotify', 'deezer')
            algorithmic_only: Whether to only return algorithmic playlists

        Returns:
            List of playlist data
        """
        try:
            query = "SELECT * FROM playlists"
            params = []

            conditions = []
            if service:
                conditions.append("service = ?")
                params.append(service)

            if algorithmic_only:
                conditions.append("is_algorithmic = 1")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY name"

            self.cursor.execute(query, params)

            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting playlists: {str(e)}")
            return []

    def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a playlist from the database.

        Args:
            playlist_id: Playlist ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cursor.execute('''
            DELETE FROM playlists WHERE id = ?
            ''', (playlist_id,))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting playlist: {str(e)}")
            self.conn.rollback()
            return False

    def update_playlist(self, playlist_id: str, updates: Dict[str, Any]) -> bool:
        """Update a playlist in the database.

        Args:
            playlist_id: Playlist ID
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current playlist data
            current = self.get_playlist(playlist_id)
            if not current:
                return False

            # Add last_updated field
            updates['last_updated'] = datetime.now().isoformat()

            # Build update query
            fields = []
            values = []

            for key, value in updates.items():
                if key in ['id', 'added_on']:  # Don't update these fields
                    continue
                fields.append(f"{key} = ?")
                values.append(value)

            if not fields:
                return True  # Nothing to update

            # Add playlist_id to values
            values.append(playlist_id)

            query = f"UPDATE playlists SET {', '.join(fields)} WHERE id = ?"

            self.cursor.execute(query, values)
            self.conn.commit()

            return True
        except Exception as e:
            logger.error(f"Error updating playlist: {str(e)}")
            self.conn.rollback()
            return False

    # Track methods

    def add_track(self, track: Dict[str, Any], service: str) -> bool:
        """Add a track to the database.

        Args:
            track: Track data
            service: Service name (e.g., 'spotify', 'deezer')

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now().isoformat()

            self.cursor.execute('''
            INSERT OR REPLACE INTO tracks (
                id, name, artist, album, duration, release_date, isrc, service, added_on, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                track['id'],
                track['name'],
                track.get('artist', 'Unknown Artist'),
                track.get('album', ''),
                track.get('duration', 0),
                track.get('release_date', ''),
                track.get('isrc', ''),
                service,
                track.get('added_on', now),
                now
            ))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding track: {str(e)}")
            self.conn.rollback()
            return False

    def get_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get a track from the database.

        Args:
            track_id: Track ID

        Returns:
            Track data or None if not found
        """
        try:
            self.cursor.execute('''
            SELECT * FROM tracks WHERE id = ?
            ''', (track_id,))

            row = self.cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"Error getting track: {str(e)}")
            return None

    def get_tracks(self, service: str = None, release_after: str = None) -> List[Dict[str, Any]]:
        """Get tracks from the database.

        Args:
            service: Service name to filter by (e.g., 'spotify', 'deezer')
            release_after: Only return tracks released after this date (YYYY-MM-DD)

        Returns:
            List of track data
        """
        try:
            query = "SELECT * FROM tracks"
            params = []

            conditions = []
            if service:
                conditions.append("service = ?")
                params.append(service)

            if release_after:
                conditions.append("release_date > ?")
                params.append(release_after)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY name"

            self.cursor.execute(query, params)

            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting tracks: {str(e)}")
            return []

    # Playlist track methods

    def add_track_to_playlist(self, playlist_id: str, track_id: str, added_at: str = None, position: int = None) -> bool:
        """Add a track to a playlist.

        Args:
            playlist_id: Playlist ID
            track_id: Track ID
            added_at: When the track was added to the playlist (ISO format)
            position: Position in the playlist

        Returns:
            True if successful, False otherwise
        """
        try:
            if added_at is None:
                added_at = datetime.now().isoformat()

            self.cursor.execute('''
            INSERT OR REPLACE INTO playlist_tracks (
                playlist_id, track_id, added_at, position
            ) VALUES (?, ?, ?, ?)
            ''', (
                playlist_id,
                track_id,
                added_at,
                position
            ))

            # Update tracks_count in playlists table
            self.cursor.execute('''
            UPDATE playlists
            SET tracks_count = (
                SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = ?
            )
            WHERE id = ?
            ''', (playlist_id, playlist_id))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding track to playlist: {str(e)}")
            self.conn.rollback()
            return False

    def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get tracks in a playlist.

        Args:
            playlist_id: Playlist ID

        Returns:
            List of track data with added_at and position
        """
        try:
            self.cursor.execute('''
            SELECT t.*, pt.added_at, pt.position
            FROM tracks t
            JOIN playlist_tracks pt ON t.id = pt.track_id
            WHERE pt.playlist_id = ?
            ORDER BY pt.position
            ''', (playlist_id,))

            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting playlist tracks: {str(e)}")
            return []

    def remove_track_from_playlist(self, playlist_id: str, track_id: str) -> bool:
        """Remove a track from a playlist.

        Args:
            playlist_id: Playlist ID
            track_id: Track ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cursor.execute('''
            DELETE FROM playlist_tracks
            WHERE playlist_id = ? AND track_id = ?
            ''', (playlist_id, track_id))

            # Update tracks_count in playlists table
            self.cursor.execute('''
            UPDATE playlists
            SET tracks_count = (
                SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = ?
            )
            WHERE id = ?
            ''', (playlist_id, playlist_id))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing track from playlist: {str(e)}")
            self.conn.rollback()
            return False

    def clear_playlist_tracks(self, playlist_id: str) -> bool:
        """Remove all tracks from a playlist.

        Args:
            playlist_id: Playlist ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cursor.execute('''
            DELETE FROM playlist_tracks
            WHERE playlist_id = ?
            ''', (playlist_id,))

            # Update tracks_count in playlists table
            self.cursor.execute('''
            UPDATE playlists
            SET tracks_count = 0
            WHERE id = ?
            ''', (playlist_id,))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error clearing playlist tracks: {str(e)}")
            self.conn.rollback()
            return False

    # Settings methods

    def set_setting(self, key: str, value: Any) -> bool:
        """Set a setting in the database.

        Args:
            key: Setting key
            value: Setting value (will be converted to JSON)

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now().isoformat()

            # Convert value to JSON string
            if not isinstance(value, str):
                value = json.dumps(value)

            self.cursor.execute('''
            INSERT OR REPLACE INTO settings (
                key, value, updated_at
            ) VALUES (?, ?, ?)
            ''', (
                key,
                value,
                now
            ))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error setting setting: {str(e)}")
            self.conn.rollback()
            return False

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting from the database.

        Args:
            key: Setting key
            default: Default value if setting not found

        Returns:
            Setting value (converted from JSON if possible)
        """
        try:
            self.cursor.execute('''
            SELECT value FROM settings WHERE key = ?
            ''', (key,))

            row = self.cursor.fetchone()
            if row:
                value = row['value']
                try:
                    # Try to parse as JSON
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    # Return as string if not valid JSON
                    logger.debug(f"Setting value is not JSON, returning as string: {e}")
                    return value
            return default
        except Exception as e:
            logger.error(f"Error getting setting: {str(e)}")
            return default

    def delete_setting(self, key: str) -> bool:
        """Delete a setting from the database.

        Args:
            key: Setting key

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cursor.execute('''
            DELETE FROM settings WHERE key = ?
            ''', (key,))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting setting: {str(e)}")
            self.conn.rollback()
            return False

    # Migration methods

    def import_json_playlists(self, json_file: str, service: str) -> Tuple[int, int]:
        """Import playlists from a JSON file.

        Args:
            json_file: Path to JSON file
            service: Service name (e.g., 'spotify', 'deezer')

        Returns:
            Tuple of (success_count, error_count)
        """
        try:
            if not os.path.exists(json_file):
                logger.error(f"JSON file not found: {json_file}")
                return (0, 0)

            with open(json_file, 'r') as f:
                data = json.load(f)

            success_count = 0
            error_count = 0

            # Handle different JSON formats
            playlists = []

            if isinstance(data, dict):
                # Format: {'algorithmic': [...], 'user': [...]}
                if 'algorithmic' in data:
                    for playlist in data['algorithmic']:
                        playlist['algorithmic'] = True
                        playlists.append(playlist)

                if 'user' in data:
                    for playlist in data['user']:
                        playlist['algorithmic'] = False
                        playlists.append(playlist)

            elif isinstance(data, list):
                # Format: [{...}, {...}]
                playlists = data

            # Import playlists
            for playlist in playlists:
                if self.add_playlist(playlist, service):
                    success_count += 1
                else:
                    error_count += 1

            return (success_count, error_count)
        except Exception as e:
            logger.error(f"Error importing JSON playlists: {str(e)}")
            return (0, 0)


# Lazy-initialized global instance (thread-safe singleton pattern)
_db_instance: Optional[Database] = None
_db_lock = __import__('threading').Lock()


def get_database(db_path: str = None) -> Database:
    """Get the database instance using lazy initialization.

    This uses a thread-safe singleton pattern to avoid creating
    database connections at module import time.

    Args:
        db_path: Optional path to database file. If None, uses default.
                 Only used when creating the first instance.

    Returns:
        Database instance
    """
    global _db_instance

    if _db_instance is None:
        with _db_lock:
            # Double-check locking pattern
            if _db_instance is None:
                _db_instance = Database(db_path)

    return _db_instance


def reset_database() -> None:
    """Reset the database instance. Useful for testing.

    This closes the existing connection and clears the singleton,
    allowing a new instance to be created on next get_database() call.
    """
    global _db_instance

    with _db_lock:
        if _db_instance is not None:
            _db_instance.close()
            _db_instance = None
