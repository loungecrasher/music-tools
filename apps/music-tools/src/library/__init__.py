"""
Library management module for Music Tools.

Provides functionality for indexing music libraries and detecting duplicates
during import workflows.
"""

from .models import LibraryFile, VettingReport, DuplicateResult
from .database import LibraryDatabase
from .indexer import LibraryIndexer
from .duplicate_checker import DuplicateChecker
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
