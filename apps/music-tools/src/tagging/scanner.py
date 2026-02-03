"""
Music File Scanner Module

Handles discovery and scanning of music files in directories.
Supports MP3 and FLAC formats with recursive directory traversal.
"""

import os
import logging
from typing import Generator, List, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class MusicFileScanner:
    """
    Scanner for discovering music files in directories.
    """
    
    def __init__(self, supported_extensions: Set[str] = None, skip_directories: Set[str] = None):
        """
        Initialize music file scanner with performance optimizations.

        Args:
            supported_extensions: Set of supported file extensions (default: mp3, flac, m4a, wav)
            skip_directories: Set of directory names to skip for performance
        """
        self.supported_extensions = supported_extensions or {'.mp3', '.flac', '.m4a', '.wav'}

        # Common directories to skip for performance
        self.skip_directories = skip_directories or {
            '.git', '.svn', '.hg',  # Version control
            '__pycache__', '.pyc',  # Python cache
            'node_modules', '.npm',  # Node.js
            '.DS_Store', 'Thumbs.db',  # System files
            '.cache', '.tmp', 'temp',  # Cache/temp directories
            'System Volume Information',  # Windows system
            '.Trash', '.Trashes',  # Trash folders
            'lost+found',  # Linux lost+found
            'Recovery', 'RecycleBin',  # Recovery folders
        }

        self.statistics = {
            'total_files_scanned': 0,
            'music_files_found': 0,
            'directories_scanned': 0,
            'errors': 0
        }
    
    def is_music_file(self, file_path: str) -> bool:
        """
        Check if a file is a supported music file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file is a supported music format
        """
        try:
            extension = Path(file_path).suffix.lower()
            return extension in self.supported_extensions
        except Exception as e:
            logger.warning(f"Error checking file extension for {file_path}: {e}")
            return False

    def _should_scan_directory(self, directory_name: str) -> bool:
        """
        Determine if a directory should be scanned based on filtering rules.

        Args:
            directory_name: Name of the directory to check

        Returns:
            True if directory should be scanned, False to skip
        """
        # Skip hidden directories
        if directory_name.startswith('.'):
            return False

        # Skip directories in the skip list
        if directory_name.lower() in {d.lower() for d in self.skip_directories}:
            return False

        # Skip common non-music directories by pattern
        skip_patterns = ['backup', 'archive', 'temp', 'cache', 'log']
        if any(pattern in directory_name.lower() for pattern in skip_patterns):
            return False

        return True

    def scan_directory(self, directory_path: str, recursive: bool = True) -> Generator[str, None, None]:
        """
        Scan directory for music files.
        
        Args:
            directory_path: Path to directory to scan
            recursive: Whether to scan subdirectories recursively
            
        Yields:
            Paths to music files found
        """
        if not os.path.exists(directory_path):
            logger.error(f"Directory does not exist: {directory_path}")
            return
        
        if not os.path.isdir(directory_path):
            logger.error(f"Path is not a directory: {directory_path}")
            return
        
        logger.info(f"Starting scan of directory: {directory_path} (recursive: {recursive})")
        
        try:
            if recursive:
                yield from self._scan_recursive(directory_path)
            else:
                yield from self._scan_single_directory(directory_path)
                
        except Exception as e:
            logger.error(f"Error scanning directory {directory_path}: {e}")
            self.statistics['errors'] += 1
    
    def _scan_recursive(self, directory_path: str) -> Generator[str, None, None]:
        """
        Recursively scan directory and subdirectories.
        
        Args:
            directory_path: Path to directory to scan
            
        Yields:
            Paths to music files found
        """
        try:
            for root, dirs, files in os.walk(directory_path):
                self.statistics['directories_scanned'] += 1

                # Enhanced directory filtering for performance
                dirs[:] = [d for d in dirs if self._should_scan_directory(d)]

                # Early termination if no more directories to scan
                if not dirs and not files:
                    continue
                
                for file in files:
                    self.statistics['total_files_scanned'] += 1
                    
                    # Skip hidden files
                    if file.startswith('.'):
                        continue
                    
                    file_path = os.path.join(root, file)
                    
                    if self.is_music_file(file_path):
                        self.statistics['music_files_found'] += 1
                        logger.debug(f"Found music file: {file_path}")
                        yield file_path
                        
        except PermissionError as e:
            logger.warning(f"Permission denied accessing {directory_path}: {e}")
            self.statistics['errors'] += 1
        except Exception as e:
            logger.error(f"Error in recursive scan of {directory_path}: {e}")
            self.statistics['errors'] += 1
    
    def _scan_single_directory(self, directory_path: str) -> Generator[str, None, None]:
        """
        Scan only the specified directory (non-recursive).
        
        Args:
            directory_path: Path to directory to scan
            
        Yields:
            Paths to music files found
        """
        try:
            self.statistics['directories_scanned'] += 1
            
            for file in os.listdir(directory_path):
                self.statistics['total_files_scanned'] += 1
                
                # Skip hidden files
                if file.startswith('.'):
                    continue
                
                file_path = os.path.join(directory_path, file)
                
                # Only process files, not directories
                if os.path.isfile(file_path) and self.is_music_file(file_path):
                    self.statistics['music_files_found'] += 1
                    logger.debug(f"Found music file: {file_path}")
                    yield file_path
                    
        except PermissionError as e:
            logger.warning(f"Permission denied accessing {directory_path}: {e}")
            self.statistics['errors'] += 1
        except Exception as e:
            logger.error(f"Error scanning directory {directory_path}: {e}")
            self.statistics['errors'] += 1
    
    def scan_multiple_directories(self, directory_paths: List[str], recursive: bool = True) -> Generator[str, None, None]:
        """
        Scan multiple directories for music files.
        
        Args:
            directory_paths: List of directory paths to scan
            recursive: Whether to scan subdirectories recursively
            
        Yields:
            Paths to music files found
        """
        for directory_path in directory_paths:
            logger.info(f"Scanning directory: {directory_path}")
            yield from self.scan_directory(directory_path, recursive)
    
    def get_file_count_estimate(self, directory_path: str, recursive: bool = True) -> int:
        """
        Get an estimate of music files in directory without full scan.
        
        Args:
            directory_path: Path to directory to estimate
            recursive: Whether to count subdirectories recursively
            
        Returns:
            Estimated number of music files
        """
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            return 0
        
        count = 0
        try:
            if recursive:
                for root, dirs, files in os.walk(directory_path):
                    # Skip hidden directories
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    for file in files:
                        if not file.startswith('.') and self.is_music_file(file):
                            count += 1
            else:
                for file in os.listdir(directory_path):
                    if not file.startswith('.'):
                        file_path = os.path.join(directory_path, file)
                        if os.path.isfile(file_path) and self.is_music_file(file_path):
                            count += 1
                            
        except Exception as e:
            logger.error(f"Error estimating file count for {directory_path}: {e}")
            
        return count
    
    def get_statistics(self) -> dict:
        """
        Get scanner statistics.
        
        Returns:
            Dictionary containing scanner statistics
        """
        return self.statistics.copy()
    
    def reset_statistics(self):
        """Reset scanner statistics."""
        self.statistics = {
            'total_files_scanned': 0,
            'music_files_found': 0,
            'directories_scanned': 0,
            'errors': 0
        }
    
    def validate_directory(self, directory_path: str) -> tuple[bool, str]:
        """
        Validate if directory exists and is accessible.
        
        Args:
            directory_path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not os.path.exists(directory_path):
                return False, f"Directory does not exist: {directory_path}"
            
            if not os.path.isdir(directory_path):
                return False, f"Path is not a directory: {directory_path}"
            
            if not os.access(directory_path, os.R_OK):
                return False, f"Directory is not readable: {directory_path}"
            
            # Try to list contents to check permissions
            os.listdir(directory_path)
            
            return True, ""
            
        except PermissionError:
            return False, f"Permission denied: {directory_path}"
        except Exception as e:
            return False, f"Error accessing directory: {e}"