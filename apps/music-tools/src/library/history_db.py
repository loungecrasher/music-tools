"""
Database manager for the Candidate History feature.
Manages a separate SQLite database to track listened/vetted filenames.
"""
import sqlite3
import logging
import os
from datetime import datetime
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

class HistoryDatabase:
    """
    Manages the candidate history database.
    Tracks filenames that have been previously vetted/listened to.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the history database.
        
        Args:
            db_path: Path to the SQLite database file. 
                     If None, defaults to 'data/candidate_history.db'.
        """
        if db_path is None:
            # Default to data directory in the project root
            # Assuming this file is in apps/music-tools/src/library/
            # We want to go up 4 levels to root, then into data
            # .../apps/music-tools/src/library/history_db.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
            data_dir = os.path.join(project_root, 'data')
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, 'candidate_history.db')
        else:
            self.db_path = db_path
            
        self._initialize_database()
        
    def _initialize_database(self):
        """Create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Enable WAL mode for better concurrency
                cursor.execute("PRAGMA journal_mode=WAL")
                
                # Create history table
                # We use filename as the unique identifier as requested
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL UNIQUE,
                    added_at TIMESTAMP NOT NULL,
                    source_path TEXT
                )
                ''')
                
                # Create index on filename for fast lookups
                cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_filename ON history(filename)
                ''')
                
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize history database: {e}")
            raise

    def add_file(self, filename: str, source_path: str = "") -> bool:
        """
        Add a filename to the history.
        
        Args:
            filename: The name of the file (e.g., "Artist - Track.mp3")
            source_path: The full path where it was found (for reference)
            
        Returns:
            True if added, False if already exists
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO history (filename, added_at, source_path) VALUES (?, ?, ?)",
                    (filename, datetime.now(), source_path)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # Filename already exists
            return False
        except Exception as e:
            logger.error(f"Error adding file to history: {e}")
            return False

    def check_file(self, filename: str) -> Optional[datetime]:
        """
        Check if a filename exists in history.
        
        Args:
            filename: The name of the file to check
            
        Returns:
            datetime when it was added, or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT added_at FROM history WHERE filename = ?",
                    (filename,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Parse timestamp string back to datetime if needed
                    # SQLite stores timestamps as strings usually
                    try:
                        return datetime.fromisoformat(result[0])
                    except (ValueError, TypeError):
                        # Handle potential parsing issues or if it's already a datetime object (unlikely with standard sqlite3)
                        return result[0] 
                return None
        except Exception as e:
            logger.error(f"Error checking file in history: {e}")
            return None

    def get_stats(self) -> dict:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM history")
                count = cursor.fetchone()[0]
                
                cursor.execute("SELECT MAX(added_at) FROM history")
                last_added = cursor.fetchone()[0]
                
                return {
                    "total_files": count,
                    "last_added": last_added
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"total_files": 0, "last_added": None}
