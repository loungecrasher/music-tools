# Architecture Plan: Merging Serato Tools into Music Tools

## Document Information
- **Version:** 1.0
- **Created:** 2026-02-03
- **Author:** System Architecture Designer
- **Status:** DRAFT

---

## Executive Summary

This document outlines a comprehensive plan for merging the Serato Tools project into the Music Tools monorepo. The merger will preserve all unique functionality from Serato Tools while integrating it seamlessly with the existing Music Tools architecture, unified menu system, and shared common library.

### Key Outcomes
- Single unified application for all music management tasks
- Serato crate management integrated into main menu
- Reuse of existing metadata extraction from `music_tools_common`
- Consistent Rich CLI interface across all features
- Backward compatibility maintained for both tools

---

## 1. Current State Analysis

### 1.1 Music Tools Architecture

```
Music Tools Dev/
├── apps/
│   └── music-tools/
│       ├── menu.py                    # Main entry point with Rich menu
│       ├── src/
│       │   ├── library/               # Library indexing, duplicate detection
│       │   ├── menu_handlers/         # Handler functions for menu options
│       │   ├── scraping/              # EDM blog scraping
│       │   ├── services/              # Spotify, Deezer integrations
│       │   └── tagging/               # AI country tagger
│       └── tests/
└── packages/
    └── common/
        └── music_tools_common/
            ├── api/                   # Spotify, Deezer API clients
            ├── auth/                  # Authentication handlers
            ├── cli/                   # CLI utilities, progress, prompts
            ├── config/                # Configuration management
            ├── database/              # SQLite database utilities
            ├── metadata/              # Audio metadata reader/writer
            ├── ui/                    # Menu system with Rich
            └── utils/                 # Retry, HTTP, validation utilities
```

**Key Features:**
- Rich CLI interface with themed menus
- Library indexing with SQLite database
- Duplicate detection with fuzzy matching
- Spotify playlist management
- EDM blog scraping
- AI-powered country tagging
- Modular handler-based menu system

### 1.2 Serato Tools Architecture

```
Serato Tools/
├── src/
│   └── csv_to_crate.py               # Single 839-line CLI tool
├── tests/
│   ├── test_api_fixes.py
│   ├── test_indexing.py
│   ├── test_directory_scan.py
│   └── test_rapidfuzz_fix.py
├── docs/
│   └── INDEXING_GUIDE.md
└── examples/
    └── sample_playlist.csv
```

**Key Features:**
- CSV to Serato crate conversion
- Fuzzy matching with RapidFuzz (configurable threshold)
- Track metadata indexing (JSON-based)
- Directory scanning for metadata extraction
- Serato crate family search
- Detailed match reporting

### 1.3 Feature Comparison Matrix

| Feature | Music Tools | Serato Tools | Overlap |
|---------|-------------|--------------|---------|
| Metadata Extraction | mutagen via MetadataReader | mutagen + filename parsing | HIGH |
| Fuzzy Matching | via duplicate_checker.py | via RapidFuzz | MEDIUM |
| Track Indexing | SQLite-based LibraryDatabase | JSON-based track_index.json | MEDIUM |
| CLI Interface | Rich Menu system | argparse CLI | LOW |
| File Scanning | LibraryIndexer | scan_directory_for_tracks | HIGH |
| Serato Integration | NONE | Full crate read/write | UNIQUE |
| CSV Processing | NONE | Full CSV import | UNIQUE |

---

## 2. Target Architecture

### 2.1 Proposed Structure

```
Music Tools Dev/
├── apps/
│   └── music-tools/
│       ├── menu.py                    # Main entry point (add Serato submenu)
│       ├── src/
│       │   ├── library/               # Existing library management
│       │   ├── menu_handlers/
│       │   │   ├── __init__.py        # Add serato_handlers exports
│       │   │   ├── library_handlers.py
│       │   │   ├── spotify_handlers.py
│       │   │   ├── external_handlers.py
│       │   │   └── serato_handlers.py # NEW: Serato menu handlers
│       │   ├── scraping/
│       │   ├── services/
│       │   │   ├── spotify_tracks.py
│       │   │   ├── deezer.py
│       │   │   └── serato/            # NEW: Serato service module
│       │   │       ├── __init__.py
│       │   │       ├── crate_manager.py
│       │   │       ├── csv_importer.py
│       │   │       ├── track_index.py
│       │   │       └── models.py
│       │   └── tagging/
│       └── tests/
│           ├── serato/                # NEW: Serato tests
│           │   ├── test_crate_manager.py
│           │   ├── test_csv_importer.py
│           │   └── test_track_index.py
│           └── database/
└── packages/
    └── common/
        └── music_tools_common/
            ├── metadata/
            │   ├── reader.py          # EXTEND: Add filename parsing
            │   └── writer.py
            └── utils/
                └── fuzzy.py           # NEW: Unified fuzzy matching utilities
```

### 2.2 Component Architecture (C4 Model - Level 2)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Music Tools CLI                              │
│                         (menu.py)                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Library Module  │  │  Spotify Module  │  │  Serato Module   │
│                  │  │                  │  │  (NEW)           │
│ - Indexer        │  │ - Playlist Mgr   │  │ - CrateManager   │
│ - DupChecker     │  │ - Date Filter    │  │ - CSVImporter    │
│ - Vetter         │  │ - Aggregator     │  │ - TrackIndex     │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    music_tools_common                                │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │   Metadata   │  │   Database   │  │     CLI      │  │  Config  │ │
│  │   Reader     │  │   Manager    │  │    Menu      │  │  Manager │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │    Auth      │  │    Utils     │  │    Fuzzy     │               │
│  │  (Spotify)   │  │   (Retry)    │  │   (NEW)      │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  External APIs   │
                    │  - serato-tools  │
                    │  - rapidfuzz     │
                    │  - mutagen       │
                    └──────────────────┘
```

---

## 3. Detailed Integration Plan

### 3.1 Phase 1: Foundation (Day 1-2)

#### Task 1.1: Add Dependencies

**File:** `/apps/music-tools/requirements.txt`

Add to requirements-core.txt:
```
# Serato integration dependencies
serato-tools>=0.1.0
rapidfuzz>=3.0.0
```

Note: `mutagen` is already a dependency in Music Tools.

#### Task 1.2: Create Fuzzy Matching Utilities

**New File:** `/packages/common/music_tools_common/utils/fuzzy.py`

```python
"""
Unified fuzzy matching utilities for Music Tools.
Consolidates fuzzy matching logic used by library vetter and Serato tools.
"""
from typing import List, Tuple, Optional, Dict, Any
from rapidfuzz import fuzz, process

def find_best_match(
    query: str,
    candidates: Dict[str, Any],
    threshold: int = 75,
    limit: int = 5
) -> Tuple[Optional[Any], List[Tuple[Any, int]], int]:
    """
    Find best matching item using fuzzy matching.

    Args:
        query: Search term
        candidates: Dict mapping search strings to objects
        threshold: Minimum match score (0-100)
        limit: Maximum number of matches to return

    Returns:
        Tuple of (best_match, all_matches, score)
    """
    # Implementation from Serato Tools
    ...
```

#### Task 1.3: Extend Metadata Reader

**File:** `/packages/common/music_tools_common/metadata/reader.py`

Add filename parsing fallback:
```python
class MetadataReader:
    @staticmethod
    def read(filepath: str, fallback_to_filename: bool = True) -> Optional[Dict[str, Any]]:
        """Read metadata from file with optional filename fallback."""
        # Existing mutagen logic
        result = cls._read_from_tags(filepath)

        if fallback_to_filename and (not result or not result.get('artist') or not result.get('title')):
            parsed = cls._parse_filename(filepath)
            if parsed:
                result = result or {}
                result.update({k: v for k, v in parsed.items() if not result.get(k)})

        return result

    @staticmethod
    def _parse_filename(filepath: str) -> Optional[Dict[str, str]]:
        """Parse artist and title from filename pattern: 'Artist - Title.ext'"""
        # Logic from Serato Tools parse_filename()
        ...
```

### 3.2 Phase 2: Service Layer (Day 3-5)

#### Task 2.1: Create Serato Service Module

**New Directory:** `/apps/music-tools/src/services/serato/`

##### File: `__init__.py`
```python
"""Serato integration services."""
from .crate_manager import CrateManager
from .csv_importer import CSVImporter
from .track_index import SeratoTrackIndex
from .models import TrackMetadata, CrateInfo

__all__ = ['CrateManager', 'CSVImporter', 'SeratoTrackIndex', 'TrackMetadata', 'CrateInfo']
```

##### File: `models.py`
```python
"""Data models for Serato integration."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class TrackMetadata:
    """Represents a track's metadata for Serato operations."""
    path: str
    artist: str
    title: str
    crate_name: str

    @property
    def search_string(self) -> str:
        return f"{self.artist} {self.title}".lower()

    def to_dict(self) -> dict:
        return {
            'path': self.path,
            'artist': self.artist,
            'title': self.title,
            'crate': self.crate_name
        }

@dataclass
class CrateInfo:
    """Information about a Serato crate."""
    name: str
    path: str
    track_count: int
    is_subcrate: bool = False
```

##### File: `crate_manager.py`
```python
"""Serato crate management operations."""
from pathlib import Path
from typing import List, Optional
from serato_tools.crate import Crate
from rich.console import Console

class CrateManager:
    """Manages Serato crate operations."""

    def __init__(self, serato_path: Optional[str] = None, console: Optional[Console] = None):
        self.serato_path = Path(serato_path or Path.home() / "Music" / "_Serato_")
        self.console = console or Console()

    def list_crate_families(self, prefix: str = "") -> List[CrateInfo]:
        """List all crate families matching prefix."""
        ...

    def create_crate(self, name: str, track_paths: List[str]) -> Path:
        """Create a new Serato crate with specified tracks."""
        ...

    def get_crate_tracks(self, crate_name: str) -> List[str]:
        """Get all track paths from a crate."""
        ...
```

##### File: `csv_importer.py`
```python
"""CSV to Serato crate import functionality."""
import csv
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass

@dataclass
class ImportResult:
    """Results of CSV import operation."""
    matched: List[Tuple[str, str, 'TrackMetadata', int]]  # (artist, title, match, score)
    not_found: List[Tuple[str, str]]  # (artist, title)
    multiple_matches: List[Tuple[str, str, List]]  # (artist, title, matches)
    crate_path: Optional[Path] = None

class CSVImporter:
    """Import CSV playlists to Serato crates."""

    def __init__(self, track_index: 'SeratoTrackIndex', console: Optional[Console] = None):
        self.track_index = track_index
        self.console = console or Console()

    def read_csv(self, csv_path: str) -> List[Tuple[str, str]]:
        """Read CSV file and extract Artist, Title pairs."""
        ...

    def import_csv_to_crate(
        self,
        csv_path: str,
        crate_name: str,
        threshold: int = 75
    ) -> ImportResult:
        """Import CSV file to a new Serato crate."""
        ...
```

##### File: `track_index.py`
```python
"""Track metadata indexing for fast crate creation."""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from rich.progress import Progress

from music_tools_common.metadata import MetadataReader

class SeratoTrackIndex:
    """Manages track metadata index for fast lookups."""

    DEFAULT_INDEX_PATH = Path.home() / ".music-tools" / "serato_track_index.json"

    def __init__(self, index_path: Optional[Path] = None):
        self.index_path = index_path or self.DEFAULT_INDEX_PATH
        self._tracks: Dict[str, TrackMetadata] = {}
        self._metadata: dict = {}

    def build_from_directory(
        self,
        directory: str,
        extensions: List[str],
        progress_callback: Optional[callable] = None
    ) -> int:
        """Build index by scanning a directory."""
        ...

    def build_from_crate_family(
        self,
        serato_path: str,
        source_crate: str,
        progress_callback: Optional[callable] = None
    ) -> int:
        """Build index from Serato crate family."""
        ...

    def save(self) -> None:
        """Save index to JSON file."""
        ...

    def load(self) -> bool:
        """Load index from JSON file."""
        ...

    def find_matches(
        self,
        artist: str,
        title: str,
        threshold: int = 75
    ) -> List[Tuple[TrackMetadata, int]]:
        """Find matching tracks using fuzzy search."""
        ...
```

### 3.3 Phase 3: Menu Integration (Day 6-7)

#### Task 3.1: Create Serato Menu Handlers

**New File:** `/apps/music-tools/src/menu_handlers/serato_handlers.py`

```python
"""Menu handlers for Serato crate operations."""
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from music_tools_common import setup_logger
from music_tools_common.cli import clear_screen, pause

from src.services.serato import CrateManager, CSVImporter, SeratoTrackIndex

logger = setup_logger('music_tools.menu.serato')
console = Console()


def run_serato_build_index() -> None:
    """Build Serato track index from directory or crate family."""
    clear_screen()

    console.print(Panel(
        "[bold green]Build Serato Track Index[/bold green]\n\n"
        "Build a searchable index of your music library for fast CSV-to-crate conversion.\n\n"
        "Options:\n"
        "  1. Scan Directory (RECOMMENDED - 8-10x faster)\n"
        "  2. Scan Serato Crate Family",
        title="[bold]Serato Track Index[/bold]",
        border_style="green"
    ))

    choice = Prompt.ask("\nSelect indexing method", choices=["1", "2"], default="1")

    if choice == "1":
        _build_index_from_directory()
    else:
        _build_index_from_crates()


def run_serato_csv_to_crate() -> None:
    """Import CSV playlist to Serato crate."""
    clear_screen()

    console.print(Panel(
        "[bold green]CSV to Serato Crate[/bold green]\n\n"
        "Import a CSV playlist file into a new Serato crate.\n\n"
        "Requirements:\n"
        "  - CSV file with 'Artist' and 'Title' columns\n"
        "  - Built track index (run 'Build Track Index' first)",
        title="[bold]CSV Import[/bold]",
        border_style="green"
    ))

    # Check if index exists
    index = SeratoTrackIndex()
    if not index.load():
        console.print("[bold red]Error:[/bold red] Track index not found.")
        console.print("Please run 'Build Track Index' first.")
        Prompt.ask("\nPress Enter to continue")
        return

    # Get CSV path
    csv_path = Prompt.ask("\nEnter path to CSV file")
    csv_path = csv_path.strip("'\"")

    if not Path(csv_path).exists():
        console.print(f"[bold red]Error:[/bold red] File not found: {csv_path}")
        Prompt.ask("\nPress Enter to continue")
        return

    # Get crate name
    crate_name = Prompt.ask("\nEnter name for new crate")

    # Get threshold
    threshold = Prompt.ask("\nFuzzy match threshold (0-100)", default="75")

    try:
        threshold_int = int(threshold)
        if not 0 <= threshold_int <= 100:
            raise ValueError()
    except ValueError:
        console.print("[yellow]Invalid threshold, using 75[/yellow]")
        threshold_int = 75

    # Perform import
    console.print("\n[bold cyan]Importing CSV to crate...[/bold cyan]")

    try:
        importer = CSVImporter(index, console=console)
        result = importer.import_csv_to_crate(csv_path, crate_name, threshold_int)

        # Display results
        _display_import_results(result)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        logger.error(f"CSV import failed: {e}", exc_info=True)

    Prompt.ask("\nPress Enter to continue")


def run_serato_list_crates() -> None:
    """List available Serato crates."""
    clear_screen()

    console.print(Panel(
        "[bold green]List Serato Crates[/bold green]\n\n"
        "View all crates in your Serato library.",
        title="[bold]Crate Browser[/bold]",
        border_style="green"
    ))

    try:
        manager = CrateManager(console=console)
        crates = manager.list_crate_families()

        if not crates:
            console.print("[yellow]No crates found in Serato library.[/yellow]")
        else:
            table = Table(title="Serato Crates")
            table.add_column("Crate Name", style="cyan")
            table.add_column("Tracks", justify="right", style="green")
            table.add_column("Type", style="yellow")

            for crate in crates:
                crate_type = "Subcrate" if crate.is_subcrate else "Main"
                table.add_row(crate.name, str(crate.track_count), crate_type)

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

    Prompt.ask("\nPress Enter to continue")


def _build_index_from_directory() -> None:
    """Build index from directory scan."""
    directory = Prompt.ask("\nEnter path to music library directory")
    directory = directory.strip("'\"")

    if not Path(directory).is_dir():
        console.print(f"[bold red]Error:[/bold red] {directory} is not a valid directory")
        Prompt.ask("\nPress Enter to continue")
        return

    extensions = Prompt.ask(
        "\nFile extensions to scan (comma-separated)",
        default=".mp3,.m4a,.flac,.wav,.aiff"
    )
    ext_list = [e.strip() for e in extensions.split(',')]

    console.print("\n[bold cyan]Building index from directory...[/bold cyan]")
    console.print(f"Directory: {directory}")
    console.print(f"Extensions: {', '.join(ext_list)}")

    try:
        index = SeratoTrackIndex()
        count = index.build_from_directory(directory, ext_list)
        index.save()

        console.print(f"\n[bold green]Index built successfully![/bold green]")
        console.print(f"Indexed {count:,} tracks")
        console.print(f"Saved to: {index.index_path}")

    except Exception as e:
        console.print(f"[bold red]Error building index:[/bold red] {str(e)}")

    Prompt.ask("\nPress Enter to continue")


def _build_index_from_crates() -> None:
    """Build index from Serato crate family."""
    source_crate = Prompt.ask("\nEnter source crate family name")

    console.print("\n[bold cyan]Building index from crate family...[/bold cyan]")
    console.print(f"Source crate: {source_crate}")

    try:
        index = SeratoTrackIndex()
        count = index.build_from_crate_family(
            str(Path.home() / "Music" / "_Serato_"),
            source_crate
        )
        index.save()

        console.print(f"\n[bold green]Index built successfully![/bold green]")
        console.print(f"Indexed {count:,} tracks")
        console.print(f"Saved to: {index.index_path}")

    except Exception as e:
        console.print(f"[bold red]Error building index:[/bold red] {str(e)}")

    Prompt.ask("\nPress Enter to continue")


def _display_import_results(result: 'ImportResult') -> None:
    """Display CSV import results."""
    # Results table
    console.print(f"\n[bold green]Matched:[/bold green] {len(result.matched)} tracks")

    if result.matched:
        table = Table(title="Matched Tracks", show_lines=False)
        table.add_column("Artist", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Match", style="green")
        table.add_column("Score", justify="right", style="yellow")

        for artist, title, match, score in result.matched[:10]:
            table.add_row(artist, title, match.title, f"{score}%")

        if len(result.matched) > 10:
            table.add_row("...", f"and {len(result.matched) - 10} more", "", "")

        console.print(table)

    if result.not_found:
        console.print(f"\n[bold red]Not Found:[/bold red] {len(result.not_found)} tracks")
        for artist, title in result.not_found[:5]:
            console.print(f"  - {artist} - {title}")
        if len(result.not_found) > 5:
            console.print(f"  ... and {len(result.not_found) - 5} more")

    if result.crate_path:
        console.print(f"\n[bold green]Crate created:[/bold green] {result.crate_path}")
```

#### Task 3.2: Update Menu Handler Exports

**File:** `/apps/music-tools/src/menu_handlers/__init__.py`

```python
"""Menu handler modules for Music Tools."""

from .library_handlers import (
    run_process_new_music,
    run_library_index,
    run_library_vet,
    run_library_stats,
    run_smart_cleanup_menu,
    run_candidate_history_add,
    run_candidate_history_check,
)
from .spotify_handlers import (
    run_spotify_playlist_manager,
    run_spotify_tracks_after_date,
    run_spotify_collect_from_folder,
    run_recent_tracks_aggregator,
)
from .external_handlers import (
    run_tool,
    run_edm_blog_scraper,
    run_music_country_tagger,
)
# NEW: Serato handlers
from .serato_handlers import (
    run_serato_build_index,
    run_serato_csv_to_crate,
    run_serato_list_crates,
)

__all__ = [
    # Library
    'run_process_new_music',
    'run_library_index',
    'run_library_vet',
    'run_library_stats',
    'run_smart_cleanup_menu',
    'run_candidate_history_add',
    'run_candidate_history_check',
    # Spotify
    'run_spotify_playlist_manager',
    'run_spotify_tracks_after_date',
    'run_spotify_collect_from_folder',
    'run_recent_tracks_aggregator',
    # External
    'run_tool',
    'run_edm_blog_scraper',
    'run_music_country_tagger',
    # Serato (NEW)
    'run_serato_build_index',
    'run_serato_csv_to_crate',
    'run_serato_list_crates',
]
```

#### Task 3.3: Update Main Menu

**File:** `/apps/music-tools/menu.py`

Add Serato submenu to main():

```python
def main() -> None:
    """Main function."""
    # ... existing setup code ...

    # Create main menu with organized categories
    main_menu = Menu("Music Tools - Main Menu")

    # Existing options
    main_menu.add_option("Process New Music Folder", run_process_new_music,
                        "Check new folder against library + history")
    main_menu.add_option("Index Library", run_library_index,
                        "Scan your main music library (one-time setup)")
    main_menu.add_option("Library Statistics", run_library_stats,
                        "View your library statistics")
    main_menu.add_option("EDM Blog Scraper", run_edm_blog_scraper,
                        "Find new music from EDM blogs")
    main_menu.add_option("Country Tagger (AI)", run_music_country_tagger,
                        "Tag files with country metadata")
    main_menu.add_option("Spotify Playlist Manager", run_spotify_playlist_manager,
                        "View, create, copy, and deduplicate playlists")
    main_menu.add_option("Spotify Tracks by Date", run_spotify_tracks_after_date,
                        "Filter playlist tracks by release date")
    main_menu.add_option("Recent Tracks Aggregator", run_recent_tracks_aggregator,
                        "Aggregate recent adds from ALL playlists into one")

    # NEW: Serato submenu
    serato_menu = main_menu.create_submenu("Serato Tools", icon="")
    serato_menu.add_option("Build Track Index", run_serato_build_index,
                          "Index music library for fast CSV import")
    serato_menu.add_option("CSV to Crate", run_serato_csv_to_crate,
                          "Import CSV playlist to Serato crate")
    serato_menu.add_option("List Crates", run_serato_list_crates,
                          "Browse your Serato crates")
    serato_menu.set_exit_option("Back to Main Menu")

    # Set exit option for main menu
    main_menu.set_exit_option("Exit")

    # Display main menu
    main_menu.display()
```

### 3.4 Phase 4: Testing and Documentation (Day 8-10)

#### Task 4.1: Create Test Suite

**New Directory:** `/apps/music-tools/tests/serato/`

##### File: `test_crate_manager.py`
```python
"""Tests for Serato crate management."""
import pytest
from pathlib import Path
import tempfile
from src.services.serato import CrateManager

class TestCrateManager:
    def test_list_crate_families(self, mock_serato_dir):
        """Test listing crate families."""
        manager = CrateManager(serato_path=mock_serato_dir)
        crates = manager.list_crate_families()
        assert len(crates) > 0

    def test_create_crate(self, mock_serato_dir, sample_tracks):
        """Test creating a new crate."""
        manager = CrateManager(serato_path=mock_serato_dir)
        crate_path = manager.create_crate("Test Crate", sample_tracks)
        assert crate_path.exists()
```

##### File: `test_csv_importer.py`
```python
"""Tests for CSV import functionality."""
import pytest
from src.services.serato import CSVImporter, SeratoTrackIndex

class TestCSVImporter:
    def test_read_csv(self, sample_csv):
        """Test reading CSV file."""
        index = SeratoTrackIndex()
        importer = CSVImporter(index)
        tracks = importer.read_csv(sample_csv)
        assert len(tracks) > 0
        assert all(isinstance(t, tuple) and len(t) == 2 for t in tracks)

    def test_import_with_matches(self, sample_csv, populated_index):
        """Test importing CSV with matching tracks."""
        importer = CSVImporter(populated_index)
        result = importer.import_csv_to_crate(sample_csv, "Test Crate")
        assert len(result.matched) > 0
```

##### File: `test_track_index.py`
```python
"""Tests for track indexing."""
import pytest
from pathlib import Path
import tempfile
from src.services.serato import SeratoTrackIndex

class TestSeratoTrackIndex:
    def test_build_from_directory(self, mock_audio_dir):
        """Test building index from directory."""
        index = SeratoTrackIndex()
        count = index.build_from_directory(mock_audio_dir, ['.mp3'])
        assert count > 0

    def test_save_and_load(self, populated_index):
        """Test saving and loading index."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            populated_index.index_path = Path(f.name)
            populated_index.save()

            new_index = SeratoTrackIndex(index_path=Path(f.name))
            assert new_index.load()
            assert len(new_index._tracks) == len(populated_index._tracks)

    def test_find_matches(self, populated_index):
        """Test fuzzy matching."""
        matches = populated_index.find_matches("The Beatles", "Hey Jude", threshold=75)
        assert len(matches) > 0
```

#### Task 4.2: Migration Test Script

**New File:** `/apps/music-tools/scripts/test_serato_migration.py`

```python
#!/usr/bin/env python3
"""
Test script to verify Serato Tools migration.
Run this after completing the merger to validate functionality.
"""
import sys
from pathlib import Path

def test_imports():
    """Test all imports work correctly."""
    print("Testing imports...")
    try:
        from src.services.serato import CrateManager, CSVImporter, SeratoTrackIndex
        from src.menu_handlers import (
            run_serato_build_index,
            run_serato_csv_to_crate,
            run_serato_list_crates
        )
        print("  All imports successful")
        return True
    except ImportError as e:
        print(f"  Import failed: {e}")
        return False

def test_index_creation():
    """Test index can be created."""
    print("\nTesting index creation...")
    try:
        from src.services.serato import SeratoTrackIndex
        index = SeratoTrackIndex()
        print(f"  Index path: {index.index_path}")
        print("  Index creation successful")
        return True
    except Exception as e:
        print(f"  Failed: {e}")
        return False

def test_crate_manager():
    """Test crate manager initialization."""
    print("\nTesting crate manager...")
    try:
        from src.services.serato import CrateManager
        manager = CrateManager()
        print(f"  Serato path: {manager.serato_path}")
        print("  Crate manager initialization successful")
        return True
    except Exception as e:
        print(f"  Failed: {e}")
        return False

def main():
    """Run all migration tests."""
    print("=" * 60)
    print("Serato Tools Migration Test")
    print("=" * 60)

    results = [
        test_imports(),
        test_index_creation(),
        test_crate_manager(),
    ]

    print("\n" + "=" * 60)
    if all(results):
        print("ALL TESTS PASSED")
        return 0
    else:
        print("SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## 4. Conflict Resolution Strategy

### 4.1 Identified Conflicts and Resolutions

| Conflict | Music Tools | Serato Tools | Resolution |
|----------|-------------|--------------|------------|
| Metadata extraction | `MetadataReader` class | `extract_metadata_from_file()` | Extend MetadataReader with filename parsing |
| Index storage | SQLite database | JSON file | Keep both; Serato uses JSON for Serato-specific index |
| Fuzzy matching | `duplicate_checker.py` | RapidFuzz direct | Create unified `fuzzy.py` utility module |
| Index location | `~/.music-tools/library_index.db` | `~/.serato-tools/track_index.json` | Move Serato index to `~/.music-tools/serato_track_index.json` |
| CLI interface | Rich Menu system | argparse | Adapt to Rich Menu with handlers |

### 4.2 Database Strategy

**Decision:** Maintain separate databases for different purposes.

| Database | Purpose | Format | Location |
|----------|---------|--------|----------|
| library_index.db | Music library indexing | SQLite | `~/.music-tools/` |
| candidate_history.db | Listening history | SQLite | `~/.music-tools/` |
| serato_track_index.json | Serato fuzzy matching | JSON | `~/.music-tools/` |

**Rationale:**
- SQLite is better for complex queries and large datasets
- JSON is simpler for the specific Serato use case (key-value lookup)
- Keeping formats allows optimal performance for each use case

---

## 5. Backward Compatibility

### 5.1 CLI Compatibility Layer (Optional)

For users who prefer CLI over menu, create a wrapper script:

**New File:** `/apps/music-tools/scripts/serato_cli.py`

```python
#!/usr/bin/env python3
"""
CLI wrapper for Serato tools functionality.
Provides backward-compatible command-line interface.
"""
import argparse
from src.services.serato import CrateManager, CSVImporter, SeratoTrackIndex

def main():
    parser = argparse.ArgumentParser(description='Serato Tools CLI')
    parser.add_argument('--build-index', action='store_true')
    parser.add_argument('--use-index', action='store_true')
    parser.add_argument('--csv', help='CSV file path')
    parser.add_argument('--crate', help='Crate name')
    parser.add_argument('--source-crate', help='Source crate family')
    parser.add_argument('--scan-directory', help='Directory to scan')
    parser.add_argument('--threshold', type=int, default=75)
    parser.add_argument('--verbose', '-v', action='store_true')

    args = parser.parse_args()

    # Route to appropriate handler
    if args.build_index:
        # Build index logic
        ...
    elif args.csv and args.crate:
        # Import CSV logic
        ...

if __name__ == "__main__":
    main()
```

### 5.2 Existing Data Migration

Users with existing Serato Tools index files can migrate:

```python
def migrate_serato_tools_index():
    """Migrate index from old location to new."""
    old_path = Path.home() / ".serato-tools" / "track_index.json"
    new_path = Path.home() / ".music-tools" / "serato_track_index.json"

    if old_path.exists() and not new_path.exists():
        shutil.copy(old_path, new_path)
        print(f"Migrated index from {old_path} to {new_path}")
```

---

## 6. Implementation Timeline

| Phase | Days | Tasks | Dependencies |
|-------|------|-------|--------------|
| 1 - Foundation | 1-2 | Dependencies, fuzzy utils, metadata extension | None |
| 2 - Service Layer | 3-5 | Serato service module (4 files) | Phase 1 |
| 3 - Menu Integration | 6-7 | Menu handlers, main menu update | Phase 2 |
| 4 - Testing | 8-10 | Test suite, documentation, migration script | Phase 3 |

**Total Estimated Time:** 10 days

---

## 7. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| serato-tools API changes | Low | Medium | Pin version, add tests |
| RapidFuzz incompatibility | Low | Low | Already tested in Serato Tools |
| Menu system conflicts | Low | Medium | Use existing Menu pattern |
| Index format issues | Medium | Low | Validate on load, rebuild option |
| Path handling differences | Medium | Medium | Use pathlib consistently |

---

## 8. Success Criteria

1. All Serato Tools functionality accessible via Music Tools menu
2. Existing Music Tools features unchanged
3. All tests pass (existing + new)
4. Index build time comparable to original (~5-15 min for 30K tracks)
5. CSV-to-crate operation completes in <5 seconds with index
6. Documentation updated with Serato features
7. Migration script successfully imports old index files

---

## 9. Files to Create Summary

| New File | Purpose |
|----------|---------|
| `packages/common/music_tools_common/utils/fuzzy.py` | Unified fuzzy matching |
| `apps/music-tools/src/services/serato/__init__.py` | Module init |
| `apps/music-tools/src/services/serato/models.py` | Data models |
| `apps/music-tools/src/services/serato/crate_manager.py` | Crate operations |
| `apps/music-tools/src/services/serato/csv_importer.py` | CSV import |
| `apps/music-tools/src/services/serato/track_index.py` | Track indexing |
| `apps/music-tools/src/menu_handlers/serato_handlers.py` | Menu handlers |
| `apps/music-tools/tests/serato/test_crate_manager.py` | Crate tests |
| `apps/music-tools/tests/serato/test_csv_importer.py` | CSV tests |
| `apps/music-tools/tests/serato/test_track_index.py` | Index tests |
| `apps/music-tools/scripts/serato_cli.py` | CLI wrapper |
| `apps/music-tools/scripts/test_serato_migration.py` | Migration tests |

## 10. Files to Modify Summary

| Existing File | Changes |
|---------------|---------|
| `requirements-core.txt` | Add serato-tools, rapidfuzz |
| `packages/common/music_tools_common/metadata/reader.py` | Add filename parsing |
| `packages/common/music_tools_common/utils/__init__.py` | Export fuzzy module |
| `apps/music-tools/src/menu_handlers/__init__.py` | Export serato handlers |
| `apps/music-tools/menu.py` | Add Serato submenu |

---

## Appendix A: Architecture Decision Record

### ADR-001: Maintain Separate Index Files

**Context:** Both Music Tools and Serato Tools use indexing for different purposes.

**Decision:** Maintain separate index files:
- Music Tools: SQLite for library management
- Serato: JSON for fuzzy matching

**Consequences:**
- Positive: Optimal format for each use case
- Negative: Two indexes to maintain
- Mitigation: Clear naming, shared metadata extraction

### ADR-002: Extend vs. Replace Metadata Reader

**Context:** Both tools extract metadata from audio files.

**Decision:** Extend existing `MetadataReader` with filename parsing fallback.

**Consequences:**
- Positive: Single source of truth for metadata
- Positive: All tools benefit from improvements
- Negative: Slight increase in complexity
- Mitigation: Clear method separation, good test coverage

### ADR-003: Menu Integration Pattern

**Context:** Serato Tools uses argparse CLI, Music Tools uses Rich Menu.

**Decision:** Create menu handlers following existing pattern, offer optional CLI wrapper.

**Consequences:**
- Positive: Consistent user experience
- Positive: Backward compatibility via CLI wrapper
- Negative: Slight code duplication in CLI wrapper
- Mitigation: CLI wrapper calls same service layer

---

**Document End**
