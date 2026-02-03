"""
Library management module for Music Tools.

Provides functionality for indexing music libraries and detecting duplicates
during import workflows.
"""

from .database import LibraryDatabase
from .duplicate_checker import DuplicateChecker
from .indexer import LibraryIndexer
from .models import DuplicateResult, LibraryFile, VettingReport
from .vetter import ImportVetter

__all__ = [
    'LibraryFile',
    'VettingReport',
    'DuplicateResult',
    'LibraryDatabase',
    'LibraryIndexer',
    'DuplicateChecker',
    'ImportVetter',
]
