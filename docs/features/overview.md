# Music Tools Suite

A comprehensive suite of music-related Python tools with a unified interface for managing music across different platforms (Spotify, Deezer, Soundiz).

## Features

- **Enhanced Unified Authentication**: Secure authentication for Spotify and Deezer
- **Centralized Configuration Management**: Easy configuration through menu interface
- **SQLite Database Integration**: Efficient storage and retrieval of playlists and tracks
- **Improved Menu System**: User-friendly interface with submenus and descriptions
- **Type Hints and Documentation**: Comprehensive documentation and type annotations
- **Error Handling and Logging**: Robust error handling and logging throughout

## Tools Included

1. **Deezer Playlist Availability Checker**
   - Check track availability in Deezer playlists for specific regions
   - Export available tracks to a file

2. **Soundiz File Processor**
   - Process CSV files to create formatted song lists for Soundiz
   - Support for various input formats

3. **Spotify Tracks After Date Filter**
   - Create playlists with tracks released after a specified date
   - Filter tracks from existing playlists

4. **Spotify Playlist Manager**
   - Manage Spotify playlists, especially algorithmic ones
   - Process tracks from multiple playlists
   - Database-backed playlist storage

For installation and configuration instructions, please see [Installation & Setup](../getting-started/installation.md).

## Database

The application uses SQLite to store:
- Playlists from Spotify and Deezer
- Track information
- Playlist-track relationships
- Application settings

You can manage the database through the Database menu in the application.

## Security Note

The configuration files and database contain sensitive credentials and are created with restricted permissions (600).

## Tool Descriptions

### 1. Deezer Playlist Availability Checker
Checks the availability of tracks in a Deezer playlist for a specific region. This is useful for identifying tracks that are not available in your country.

### 2. Soundiz File Processor
Processes CSV files to create formatted song lists for use with Soundiz. This helps with transferring playlists between music services.

### 3. Spotify Tracks After Date
Creates a new playlist containing tracks released after a specified date from an existing playlist. Useful for finding new music in your favorite playlists.

### 4. Spotify Playlist Manager
Comprehensive tool for managing Spotify playlists, including:
- Processing tracks from algorithmic playlists
- Managing playlist database
- Adding and validating playlists
- Creating playlists with tracks added in the last 30 days

### 5. EDM Blog Scraper
Scrapes EDM music blogs with genre filtering, download-link extraction, and configurable date ranges.

### 6. Music Country Tagger
Interactive CLI that scans local libraries and tags tracks with country-of-origin metadata using AI lookups.

### 7. CSV to Text Converter
Batch converts CSV exports (Artist, Title) into plain text lists useful for DJ tools or playlist migration.

### 8. Library Management
Comprehensive music library indexing and duplicate detection system with the following commands:
- **index**: Create a searchable database of your music library
- **vet**: Check import folders against your library for duplicates
- **verify**: Verify indexed files still exist and mark missing files
- **stats**: Display library statistics and metadata
- **history**: View recent vetting operations

## Library Commands

The library management system provides intelligent duplicate detection for your local music collection. Index your main library once, then vet new imports to identify duplicates before adding them.

### library index

Index your main music library for duplicate detection.

**Description:**
Scans your music library and creates a searchable database for fast duplicate detection. Uses both metadata (artist/title) and content hashing for accurate matching.

**Usage:**
```bash
python -m music_tools_cli library index --path ~/Music
```

**Options:**
- `--path`, `-p` (required): Path to music library to index
- `--db`: Path to database file (default: `~/.music-tools/library_index.db`)
- `--rescan`: Rescan all files even if already indexed
- `--incremental/--full`: Only scan new/modified files (default: incremental)

**Examples:**
```bash
# Index your music library (incremental mode - only new/modified files)
python -m music_tools_cli library index --path ~/Music

# Full rescan of entire library
python -m music_tools_cli library index --path ~/Music --rescan --full

# Use custom database location
python -m music_tools_cli library index --path ~/Music --db ~/my-library.db
```

**Features:**
- Supports MP3, FLAC, M4A, WAV, OGG, OPUS, and AIFF formats
- Incremental scanning for fast updates
- Progress tracking with file counts
- Metadata extraction (artist, title, album, year, duration)
- Content hash calculation for binary-level duplicate detection
- Statistics on total files, formats, artists, and albums

### library vet

Vet import folder against indexed library.

**Description:**
Checks all music files in an import folder against your indexed library to identify duplicates and new songs. Results are categorized as:
- **New Songs**: Safe to import (no matches found)
- **Duplicates**: Already in your library (high confidence match)
- **Uncertain**: Possible duplicates (manual review suggested)

**Usage:**
```bash
python -m music_tools_cli library vet --folder ~/Downloads/new-music
```

**Options:**
- `--folder`, `-f` (required): Path to import folder to vet
- `--library-db`: Path to library database (default: `~/.music-tools/library_index.db`)
- `--threshold`, `-t`: Similarity threshold for fuzzy matching (0.0-1.0, default: 0.8)
- `--export-new/--no-export-new`: Export list of new songs to file (default: enabled)
- `--export-duplicates`: Export list of duplicates to file
- `--export-uncertain`: Export list of uncertain matches to file

**Examples:**
```bash
# Basic vetting - shows results and exports new songs list
python -m music_tools_cli library vet --folder ~/Downloads/new-music

# More strict matching (fewer false positives)
python -m music_tools_cli library vet --folder ~/Downloads/new-music --threshold 0.9

# Export all categories for review
python -m music_tools_cli library vet --folder ~/Downloads/new-music \
    --export-duplicates --export-uncertain

# Use custom database
python -m music_tools_cli library vet --folder ~/Downloads/new-music \
    --library-db ~/my-library.db
```

**Matching Strategy:**
The vetting process uses multiple matching strategies:
1. **Exact Metadata Hash**: Artist + Title (normalized, case-insensitive)
2. **Content Hash**: Binary content comparison (first/last 64KB chunks)
3. **Fuzzy Matching**: Similarity scoring based on metadata fields

**Confidence Levels:**
- **Exact match** (1.0): Same metadata hash or content hash
- **High confidence** (≥ threshold): Fuzzy match above threshold
- **Uncertain** (0.7 - threshold): Possible match, manual review needed
- **No match** (< 0.7): Considered new song

**Output Files:**
When export options are enabled, files are created in the import folder:
- `new_songs.txt`: List of songs safe to import
- `duplicates.txt`: List of duplicates with match details
- `uncertain.txt`: List of uncertain matches for manual review

### library verify

Verify library index is up-to-date.

**Description:**
Checks that all indexed files still exist and marks missing files as inactive. Use this command after moving, renaming, or deleting files from your library.

**Usage:**
```bash
python -m music_tools_cli library verify --path ~/Music
```

**Options:**
- `--path`, `-p` (required): Path to music library to verify
- `--db`: Path to database file (default: `~/.music-tools/library_index.db`)

**Examples:**
```bash
# Verify library against database
python -m music_tools_cli library verify --path ~/Music

# Verify with custom database
python -m music_tools_cli library verify --path ~/Music --db ~/my-library.db
```

**What it does:**
- Scans all indexed files in the database
- Checks if each file still exists on disk
- Marks missing files as inactive (soft delete)
- Reports count of missing files and files marked inactive
- Preserves metadata for potential future recovery

### library stats

Show library index statistics.

**Description:**
Displays comprehensive statistics about your indexed music library including file counts, formats, artists, albums, total size, and last index time.

**Usage:**
```bash
python -m music_tools_cli library stats
```

**Options:**
- `--db`: Path to database file (default: `~/.music-tools/library_index.db`)

**Examples:**
```bash
# Show statistics for default library
python -m music_tools_cli library stats

# Show statistics for custom database
python -m music_tools_cli library stats --db ~/my-library.db
```

**Statistics Displayed:**
- Total files in library
- Total size (in human-readable format)
- Format breakdown (MP3, FLAC, etc.)
- Number of unique artists
- Number of unique albums
- Last index time and duration
- Average file size

### library history

Show recent vetting history.

**Description:**
Displays history of import vetting operations, showing which folders were vetted, how many duplicates were found, and how many new songs were identified.

**Usage:**
```bash
python -m music_tools_cli library history
```

**Options:**
- `--db`: Path to database file (default: `~/.music-tools/library_index.db`)
- `--limit`, `-n`: Maximum number of records to show (1-1000, default: 10)

**Examples:**
```bash
# Show last 10 vetting operations
python -m music_tools_cli library history

# Show last 50 vetting operations
python -m music_tools_cli library history --limit 50

# View history for custom database
python -m music_tools_cli library history --db ~/my-library.db --limit 20
```

**History Information:**
- Date and time of vetting
- Import folder name
- Total files scanned
- New songs found
- Duplicates found
- Uncertain matches
- Threshold used

## Typical Library Workflow

1. **Initial Setup**: Index your main music library
   ```bash
   python -m music_tools_cli library index --path ~/Music
   ```

2. **Vet New Imports**: Check new downloads for duplicates
   ```bash
   python -m music_tools_cli library vet --folder ~/Downloads/new-music
   ```

3. **Review Results**: Check the categorized results and export files
   - Import songs listed in `new_songs.txt`
   - Delete or skip files listed in `duplicates.txt`
   - Manually review files listed in `uncertain.txt`

4. **Update Library**: After importing new songs, re-index incrementally
   ```bash
   python -m music_tools_cli library index --path ~/Music
   ```

5. **Maintenance**: Periodically verify your library
   ```bash
   python -m music_tools_cli library verify --path ~/Music
   ```

6. **Monitor**: View statistics and history
   ```bash
   python -m music_tools_cli library stats
   python -m music_tools_cli library history
   ```

## Unified CLI

The new Typer-based CLI exposes each tool as a subcommand while keeping the legacy Rich menu accessible:

```bash
# Inspect available commands
python -m music_tools_cli --help

# Deezer playlist availability report
python -m music_tools_cli deezer playlist "https://www.deezer.com/us/playlist/123456789" --output-dir reports/

# Generate a Soundiiz text file from an arbitrary CSV
python -m music_tools_cli soundiz from-csv ~/exports/library.csv --title-field Name --artist-field Performer

# Filter Spotify tracks released after a date
python -m music_tools_cli spotify tracks-after-date PLAYLIST_ID 2024-01-01 --name "Fresh Finds 2024"

# Additional standalone utilities
python -m music_tools_cli extras edm-scraper
python -m music_tools_cli extras music-tagger
python -m music_tools_cli extras csv-to-text /path/to/csvs --output /path/to/output

# Launch interactive tools
python -m music_tools_cli spotify playlist-manager
python -m music_tools_cli library compare
python -m music_tools_cli menu  # Legacy Rich UI
```

The Rich-based menu now includes dedicated options for the EDM scraper, country tagger, and CSV converter alongside the original tools.

## Development

The codebase is organized into modules:
- `core/`: Core functionality (auth, config, database, utils)
- Tool-specific directories for each tool
- `music_tools_cli/`: Unified CLI application with Typer command groups
- `menu.py`: Legacy interactive user interface

## Requirements

- Python 3.8 or higher
- Dependencies listed in `requirements.txt`
