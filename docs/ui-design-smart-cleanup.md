# Smart Cleanup Workflow - Rich Terminal UI/UX Design

## Design Overview

This document presents a comprehensive UI/UX design for the Smart Cleanup workflow using the Rich library, maintaining consistency with existing Music Tools patterns.

---

## 1. Color Scheme & Theme

### Quality Indicators
```python
QUALITY_COLORS = {
    'excellent': 'bright_green',    # FLAC, high-bitrate lossless
    'good': 'green',                # 320kbps MP3, AAC
    'acceptable': 'yellow',          # 192-256kbps MP3
    'poor': 'orange',               # 128-192kbps MP3
    'very_poor': 'red',             # <128kbps MP3
    'unknown': 'dim'                # Unable to determine
}

FORMAT_COLORS = {
    'FLAC': 'bright_green',
    'ALAC': 'bright_green',
    'WAV': 'green',
    'MP3': 'yellow',
    'AAC': 'yellow',
    'M4A': 'yellow',
    'OGG': 'cyan',
}

STATUS_COLORS = {
    'scanning': 'cyan',
    'analyzing': 'blue',
    'comparing': 'magenta',
    'ready': 'green',
    'processing': 'yellow',
    'complete': 'bright_green',
    'error': 'red',
}
```

### Extended Theme Configuration
```python
CLEANUP_THEME = {
    # Existing theme colors
    **THEME,

    # Cleanup-specific colors
    'duplicate_group': 'magenta',
    'keeper': 'bright_green',
    'candidate_delete': 'red',
    'quality_badge': 'bold',
    'file_size': 'cyan',
    'metadata': 'blue',
    'action_confirm': 'yellow',
    'backup_info': 'dim cyan',
    'progress_bar': 'green',
    'progress_complete': 'bright_green',
}
```

---

## 2. Screen Designs

### 2.1 Main Menu Enhancement with Library Stats

```python
# Example Rich Panel Output:
╭─────────────────────────────────────────────────────────────────────────╮
│                      🎵 Music Tools - Main Menu                         │
│                                                                         │
│  Library Status                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  📊 Total Tracks: 12,456                                         │  │
│  │  💾 Total Size: 487.3 GB                                         │  │
│  │  🎼 FLAC: 8,234 (66%)     MP3: 4,122 (33%)     Other: 100 (1%)  │  │
│  │  ⚠️  Potential Duplicates: 234 groups (468 files, ~12.3 GB)    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   #  Option                      Description                           │
│  ──────────────────────────────────────────────────────────────────    │
│   1  🧹 Smart Cleanup            Find and remove duplicate files       │
│   2  📚 Library Management       Index and organize your library       │
│   3  🎵 Spotify Tools            Playlist management and more          │
│   4  🎶 Deezer Tools             Playlist repair and tools             │
│   5  🔧 Music Tools              AI tagging and scraping               │
│   6  ⚙️  Configuration           Settings and database                 │
│                                                                         │
│   0  ⏻ Exit                                                            │
╰─────────────────────────────────────────────────────────────────────────╯
```

### 2.2 Smart Cleanup - Scan Mode Selection

```python
╭─────────────────────────────────────────────────────────────────────────╮
│              🧹 Smart Cleanup › Select Scan Mode                        │
│                                                                         │
│  Choose your scanning strategy based on your needs:                    │
│                                                                         │
│   #  Mode            Speed    Accuracy  Description                    │
│  ──────────────────────────────────────────────────────────────────    │
│   1  ⚡ Quick Scan    Fast     Good     Hash-based duplicate detection │
│                                         • Checks file size & MD5        │
│                                         • ~100-200 files/sec            │
│                                         • Best for exact duplicates     │
│                                                                         │
│   2  🔍 Deep Scan     Slow     Best     Audio fingerprint analysis     │
│                                         • Acoustic similarity matching  │
│                                         • Metadata comparison           │
│                                         • ~10-20 files/sec              │
│                                         • Finds re-encodes & variants   │
│                                                                         │
│   3  ⚙️  Custom       Varies   Custom   Configure your own settings    │
│                                         • Set similarity threshold      │
│                                         • Choose detection methods      │
│                                         • Advanced users only           │
│                                                                         │
│   0  ← Back to Main Menu                                               │
╰─────────────────────────────────────────────────────────────────────────╯

Enter choice: _
```

### 2.3 Scanning Progress Animation

```python
╭─────────────────────────────────────────────────────────────────────────╮
│              🧹 Smart Cleanup › Scanning Library                        │
╰─────────────────────────────────────────────────────────────────────────╯

  Scan Mode: ⚡ Quick Scan (Hash-based)
  Started: 2026-01-08 14:23:15

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 8,234/12,456  66% 0:02:15

  📂 Scanning: /Users/music/Albums/Artist Name/Album/track.flac

  Statistics:
  ┌────────────────────────────────────────────────────────────────────┐
  │  Scanned: 8,234 files  •  Duplicates Found: 156 groups            │
  │  Speed: 145 files/sec  •  Estimated Time: 00:00:29                │
  │  Potential Space to Recover: ~4.2 GB                              │
  └────────────────────────────────────────────────────────────────────┘

  Live Feed:
  ✓ Found duplicate: "Artist - Track.mp3" vs "Artist - Track.flac"
  ✓ Duplicate group: 3 versions of "Song Title.mp3"
  ℹ Skipped: corrupted file "damaged.mp3"

[Press Ctrl+C to cancel]
```

### 2.4 Side-by-Side Duplicate Comparison

```python
╭─────────────────────────────────────────────────────────────────────────╮
│         🧹 Smart Cleanup › Review Duplicates (Group 1 of 156)           │
╰─────────────────────────────────────────────────────────────────────────╯

  Song: "Artist Name - Track Title"
  Duplicate Type: Exact Match (99.8% similarity)

  ┌─────────────────────────────────────────────────────────────────────┐
  │                        File Comparison                              │
  ├──────────────────────────┬──────────────────────────────────────────┤
  │      File A (KEEP)       │       File B (DELETE?)                   │
  ├──────────────────────────┼──────────────────────────────────────────┤
  │ 📁 /Music/Albums/        │ 📁 /Music/Downloads/                     │
  │    Artist/Track.flac     │    Track.mp3                             │
  ├──────────────────────────┼──────────────────────────────────────────┤
  │ Quality: ★★★★★ FLAC      │ Quality: ★★★☆☆ 256kbps MP3              │
  │ Format:  FLAC            │ Format:  MP3                             │
  │ Bitrate: 1411 kbps       │ Bitrate: 256 kbps                        │
  │ Size:    47.2 MB         │ Size:    8.3 MB                          │
  │ Sample:  44.1 kHz/16bit  │ Sample:  44.1 kHz                        │
  ├──────────────────────────┼──────────────────────────────────────────┤
  │ Metadata                 │ Metadata                                 │
  │ • Title:  Track Title    │ • Title:  Track Title                    │
  │ • Artist: Artist Name    │ • Artist: Artist Name                    │
  │ • Album:  Album Name     │ • Album:  (missing)                      │
  │ • Year:   2024           │ • Year:   2024                           │
  │ • Track:  01/12          │ • Track:  (missing)                      │
  │ • Genre:  Electronic     │ • Genre:  Electronic                     │
  │                          │                                          │
  │ ✓ Complete metadata      │ ⚠️ Missing album & track number          │
  ├──────────────────────────┼──────────────────────────────────────────┤
  │ Created: 2024-01-15      │ Created: 2024-03-22                      │
  │ Modified: 2024-01-15     │ Modified: 2024-03-22                     │
  │ Last Played: Never       │ Last Played: 2024-04-10                  │
  └──────────────────────────┴──────────────────────────────────────────┘

  🤖 Recommendation: KEEP File A, DELETE File B
  Reason: Higher quality (lossless), better metadata, smaller folder structure

  Actions:
   K - Keep File A (recommended)
   D - Keep File B instead
   B - Keep both files (skip)
   P - Preview audio (play 10 sec)
   M - Show more details
   N - Next duplicate group
   Q - Finish review and process

Enter action: _
```

### 2.5 Batch Actions Menu

```python
╭─────────────────────────────────────────────────────────────────────────╮
│         🧹 Smart Cleanup › Review Summary                               │
╰─────────────────────────────────────────────────────────────────────────╯

  Review Complete: Analyzed 156 duplicate groups (312 files)

  Recommended Actions:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Action               Files     Space to Recover                    │
  ├─────────────────────────────────────────────────────────────────────┤
  │  🗑️  Delete duplicates   156       12.3 GB (26% of duplicates)      │
  │  ✓  Keep originals       156       35.4 GB                          │
  │  ⏭️  Skipped/both kept     0        0 GB                            │
  └─────────────────────────────────────────────────────────────────────┘

  Quality Distribution of Deleted Files:
  • MP3 (128-192kbps):  89 files   5.8 GB  ████████████░░░░░░░░  57%
  • MP3 (192-256kbps):  45 files   4.2 GB  ████████░░░░░░░░░░░░  29%
  • MP3 (320kbps):      22 files   2.3 GB  ████░░░░░░░░░░░░░░░░  14%

  What would you like to do?
   1. ✓ Execute cleanup (with backup)
   2. 📋 Review individual decisions
   3. 💾 Export report to file
   4. ❌ Cancel and keep everything
   0. ← Back to Main Menu

Enter choice: _
```

### 2.6 Multi-Step Confirmation with Backup Option

```python
╭─────────────────────────────────────────────────────────────────────────╮
│         🧹 Smart Cleanup › Confirmation Required                        │
╰─────────────────────────────────────────────────────────────────────────╯

  ⚠️  WARNING: You are about to delete 156 files (12.3 GB)

  Safety Measures Available:

  ┌─────────────────────────────────────────────────────────────────────┐
  │  Backup Options                                                     │
  ├─────────────────────────────────────────────────────────────────────┤
  │  1. 💾 Full Backup    Move files to backup folder before deletion   │
  │                       Location: ~/.music-tools/backups/2026-01-08/  │
  │                       Disk space required: 12.3 GB                  │
  │                       Can restore anytime                           │
  │                                                                     │
  │  2. 📋 Log Only       Just save a list of deleted files             │
  │                       Location: ~/.music-tools/logs/cleanup.log     │
  │                       Disk space: <1 MB                             │
  │                       Cannot restore files                          │
  │                                                                     │
  │  3. ⚠️  No Backup      Permanently delete files                      │
  │                       ⚠️ THIS CANNOT BE UNDONE                      │
  └─────────────────────────────────────────────────────────────────────┘

  Backup Strategy: [1-3] _

  ───────────────────────────────────────────────────────────────────────

  Final Confirmation:

  Type "DELETE 156 FILES" to proceed: _

  [Type 'cancel' to abort]
```

### 2.7 Processing Progress

```python
╭─────────────────────────────────────────────────────────────────────────╮
│         🧹 Smart Cleanup › Processing Cleanup                           │
╰─────────────────────────────────────────────────────────────────────────╯

  Phase 1: Creating Backup
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%  Complete!
  ✓ 156 files backed up to ~/.music-tools/backups/2026-01-08/

  Phase 2: Deleting Duplicate Files
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 89/156  57%  0:00:12

  Processing: /Music/Downloads/Artist - Track.mp3

  ┌─────────────────────────────────────────────────────────────────────┐
  │  Progress Details                                                   │
  ├─────────────────────────────────────────────────────────────────────┤
  │  Deleted: 89 files (7.1 GB)                                         │
  │  Remaining: 67 files (5.2 GB)                                       │
  │  Speed: 12 files/sec                                                │
  │  Errors: 0                                                          │
  └─────────────────────────────────────────────────────────────────────┘

  Recent Actions:
  ✓ Deleted: Artist - Track.mp3 (8.3 MB)
  ✓ Deleted: Another - Song.mp3 (6.1 MB)
  ✓ Deleted: Third - File.mp3 (7.8 MB)

[Do not interrupt - cleanup in progress]
```

### 2.8 Completion Summary

```python
╭─────────────────────────────────────────────────────────────────────────╮
│         🧹 Smart Cleanup › Cleanup Complete!                            │
╰─────────────────────────────────────────────────────────────────────────╯

  ✨ Success! Your library has been cleaned up.

  ┌─────────────────────────────────────────────────────────────────────┐
  │                        Cleanup Summary                              │
  ├─────────────────────────────────────────────────────────────────────┤
  │  Files Deleted:       156 files                                     │
  │  Space Recovered:     12.3 GB                                       │
  │  Files Backed Up:     156 files (in backup folder)                  │
  │  Processing Time:     00:02:34                                      │
  │  Library Size After:  475.0 GB (was 487.3 GB)                       │
  ├─────────────────────────────────────────────────────────────────────┤
  │  Quality Improvement                                                │
  │  • FLAC files: 8,234 (66% → 66%)                                    │
  │  • High-quality MP3: 3,966 (32% → 32%)                              │
  │  • Low-quality MP3: 0 (1% → 0%) ✓ Eliminated!                       │
  └─────────────────────────────────────────────────────────────────────┘

  Backup Information:
  📁 Location: ~/.music-tools/backups/2026-01-08_cleanup/
  💾 Size: 12.3 GB
  ⏰ Created: 2026-01-08 14:32:45

  To restore files: Run "restore-backup 2026-01-08_cleanup"
  To delete backup:  Run "delete-backup 2026-01-08_cleanup" (after 30 days)

  Detailed Report:
  📄 Cleanup log saved to: ~/.music-tools/logs/cleanup_2026-01-08.log
  📊 CSV export: ~/.music-tools/reports/cleanup_2026-01-08.csv

  What's next?
   1. 📊 View detailed report
   2. 📁 Open backup folder
   3. 🔄 Run another cleanup
   4. ← Return to main menu

Enter choice: _
```

---

## 3. Navigation Flow Diagram

```
Main Menu
   │
   ├─ Smart Cleanup
   │     │
   │     ├─ Select Scan Mode
   │     │     ├─ Quick Scan ──────────┐
   │     │     ├─ Deep Scan ───────────┤
   │     │     └─ Custom Settings ─────┤
   │     │                              │
   │     ├─ Scanning Progress <─────────┘
   │     │     │
   │     │     └─ [Scan Complete]
   │     │           │
   │     ├─ Review Duplicates
   │     │     │
   │     │     ├─ [For each group]
   │     │     │     ├─ Compare Files
   │     │     │     ├─ Choose Action (K/D/B/P/M)
   │     │     │     └─ Next/Previous
   │     │     │
   │     │     └─ Review Summary
   │     │           │
   │     ├─ Batch Actions Menu
   │     │     ├─ Execute Cleanup
   │     │     ├─ Review Decisions
   │     │     ├─ Export Report
   │     │     └─ Cancel
   │     │           │
   │     ├─ Confirmation Dialog
   │     │     ├─ Select Backup Strategy
   │     │     └─ Type Confirmation
   │     │           │
   │     ├─ Processing
   │     │     ├─ Backup Phase
   │     │     └─ Deletion Phase
   │     │           │
   │     └─ Completion Summary
   │           ├─ View Report
   │           ├─ Open Backup
   │           ├─ Run Again
   │           └─ Return to Menu
   │
   └─ [Other menu items...]
```

---

## 4. Keyboard Shortcut Mappings

### Global Shortcuts (All Screens)
```python
GLOBAL_SHORTCUTS = {
    'Ctrl+C': 'Cancel current operation (with confirmation)',
    'Ctrl+Q': 'Quick exit to main menu',
    'Ctrl+H': 'Show help overlay',
    'Ctrl+R': 'Refresh current screen',
    '?': 'Show keyboard shortcuts',
    'ESC': 'Go back one level',
}
```

### Scan Mode Selection
```python
SCAN_MODE_SHORTCUTS = {
    '1': 'Quick Scan',
    '2': 'Deep Scan',
    '3': 'Custom Settings',
    'Q/0': 'Quick scan with defaults',
    'D': 'Deep scan with defaults',
    '0': 'Back to main menu',
}
```

### Duplicate Review
```python
REVIEW_SHORTCUTS = {
    'K': 'Keep first file (recommended)',
    'D': 'Keep second file instead',
    'B': 'Keep both files',
    'P': 'Preview/Play audio sample',
    'M': 'Show more detailed metadata',
    'N/→': 'Next duplicate group',
    'Prev/←': 'Previous duplicate group',
    'S': 'Skip this group for now',
    'A': 'Auto-decide (use AI recommendation)',
    'J/K': 'Vim-style navigation (next/prev)',
    'Space': 'Toggle selection',
    'Enter': 'Confirm and next',
    'Q': 'Finish review session',
    '0': 'Cancel and return',
}
```

### Batch Actions
```python
BATCH_SHORTCUTS = {
    '1': 'Execute cleanup',
    '2': 'Review decisions',
    '3': 'Export report',
    '4': 'Cancel',
    'E': 'Quick execute (with backup)',
    'R': 'Review',
    'X': 'Export',
    '0': 'Back',
}
```

### Confirmation Dialog
```python
CONFIRM_SHORTCUTS = {
    '1': 'Full backup',
    '2': 'Log only',
    '3': 'No backup',
    'B': 'Quick select: Full backup',
    'L': 'Quick select: Log only',
    'Y': 'Confirm (after typing phrase)',
    'N/cancel': 'Cancel operation',
}
```

---

## 5. Example Rich Code Snippets

### 5.1 Quality Badge Component

```python
from rich.text import Text
from typing import Dict, Tuple

def get_quality_badge(format: str, bitrate: int) -> Text:
    """
    Generate a quality badge with stars and color coding.

    Args:
        format: Audio format (FLAC, MP3, etc.)
        bitrate: Bitrate in kbps

    Returns:
        Rich Text object with styled quality indicator
    """
    if format.upper() in ['FLAC', 'ALAC', 'WAV']:
        stars = '★' * 5
        color = 'bright_green'
        label = 'LOSSLESS'
    elif format.upper() == 'MP3' and bitrate >= 320:
        stars = '★' * 4 + '☆'
        color = 'green'
        label = f'{bitrate}kbps'
    elif format.upper() == 'MP3' and bitrate >= 256:
        stars = '★' * 3 + '☆' * 2
        color = 'yellow'
        label = f'{bitrate}kbps'
    elif format.upper() == 'MP3' and bitrate >= 192:
        stars = '★' * 2 + '☆' * 3
        color = 'orange'
        label = f'{bitrate}kbps'
    else:
        stars = '★' + '☆' * 4
        color = 'red'
        label = f'{bitrate}kbps'

    badge = Text()
    badge.append(f'{stars} ', style=f'bold {color}')
    badge.append(label, style=color)

    return badge


def format_file_size(bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} PB"
```

### 5.2 Duplicate Comparison Table

```python
from rich.table import Table
from rich.console import Console

def create_comparison_table(file_a: Dict, file_b: Dict,
                           recommendation: str) -> Table:
    """
    Create a side-by-side comparison table for duplicate files.

    Args:
        file_a: First file metadata
        file_b: Second file metadata
        recommendation: Which file to keep

    Returns:
        Rich Table object
    """
    table = Table(title="File Comparison", show_header=True,
                  header_style="bold cyan")

    # Highlight the recommended file
    style_a = "bright_green" if recommendation == "A" else "white"
    style_b = "bright_green" if recommendation == "B" else "white"

    table.add_column(
        "File A (KEEP)" if recommendation == "A" else "File A",
        style=style_a,
        width=40
    )
    table.add_column(
        "File B (KEEP)" if recommendation == "B" else "File B",
        style=style_b,
        width=40
    )

    # File paths
    table.add_row(
        f"📁 {file_a['path']}",
        f"📁 {file_b['path']}"
    )

    # Quality badges
    quality_a = get_quality_badge(file_a['format'], file_a['bitrate'])
    quality_b = get_quality_badge(file_b['format'], file_b['bitrate'])
    table.add_row(
        f"Quality: {quality_a}",
        f"Quality: {quality_b}"
    )

    # Technical details
    table.add_row(
        f"Format: {file_a['format']}",
        f"Format: {file_b['format']}"
    )
    table.add_row(
        f"Bitrate: {file_a['bitrate']} kbps",
        f"Bitrate: {file_b['bitrate']} kbps"
    )
    table.add_row(
        f"Size: {format_file_size(file_a['size'])}",
        f"Size: {format_file_size(file_b['size'])}"
    )
    table.add_row(
        f"Sample: {file_a['sample_rate']} Hz/{file_a['bit_depth']}bit",
        f"Sample: {file_b['sample_rate']} Hz"
    )

    # Metadata comparison
    table.add_section()
    table.add_row("Metadata", "Metadata", style="bold blue")

    metadata_fields = ['title', 'artist', 'album', 'year', 'track', 'genre']
    for field in metadata_fields:
        val_a = file_a.get(field, '(missing)')
        val_b = file_b.get(field, '(missing)')

        # Highlight missing metadata in yellow
        if val_a == '(missing)':
            val_a = f"[yellow]{val_a}[/yellow]"
        if val_b == '(missing)':
            val_b = f"[yellow]{val_b}[/yellow]"

        table.add_row(
            f"• {field.title()}: {val_a}",
            f"• {field.title()}: {val_b}"
        )

    # Completeness check
    complete_a = "✓ Complete metadata" if file_a['metadata_complete'] \
                 else "⚠️ Incomplete metadata"
    complete_b = "✓ Complete metadata" if file_b['metadata_complete'] \
                 else "⚠️ Incomplete metadata"
    table.add_row(complete_a, complete_b, style="dim")

    # File dates
    table.add_section()
    table.add_row(
        f"Created: {file_a['created']}",
        f"Created: {file_b['created']}"
    )
    table.add_row(
        f"Modified: {file_a['modified']}",
        f"Modified: {file_b['modified']}"
    )
    table.add_row(
        f"Last Played: {file_a.get('last_played', 'Never')}",
        f"Last Played: {file_b.get('last_played', 'Never')}"
    )

    return table
```

### 5.3 Multi-Phase Progress Display

```python
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn,
    TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
)
from rich.layout import Layout
from rich.panel import Panel

def create_cleanup_progress() -> Progress:
    """Create a multi-phase progress tracker for cleanup operations."""

    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(complete_style="green", finished_style="bright_green"),
        TaskProgressColumn(),
        "•",
        TimeElapsedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console,
        expand=True
    )


def display_processing_screen(phase: str, current: int, total: int,
                              current_file: str, stats: Dict):
    """
    Display the processing screen with live updates.

    Args:
        phase: Current phase name
        current: Current file index
        total: Total files to process
        current_file: Path of file being processed
        stats: Dictionary of statistics
    """
    # Create layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="progress", size=8),
        Layout(name="details", size=10),
        Layout(name="feed", size=7)
    )

    # Header
    layout["header"].update(
        Panel(
            f"🧹 Smart Cleanup › {phase}",
            style="bold cyan"
        )
    )

    # Progress bar
    with create_cleanup_progress() as progress:
        task = progress.add_task(
            f"{phase}...",
            total=total,
            completed=current
        )
        layout["progress"].update(progress)

    # Details panel
    details = Table.grid(padding=(0, 2))
    details.add_column(style="cyan")
    details.add_column(style="green")

    details.add_row("Processed:", f"{current}/{total} files")
    details.add_row("Space Recovered:", format_file_size(stats['space_freed']))
    details.add_row("Speed:", f"{stats['speed']:.1f} files/sec")
    details.add_row("Errors:", str(stats['errors']))

    layout["details"].update(
        Panel(details, title="Progress Details", border_style="blue")
    )

    # Recent actions feed
    feed_text = "\n".join(stats['recent_actions'][-5:])
    layout["feed"].update(
        Panel(
            feed_text,
            title="Recent Actions",
            border_style="dim"
        )
    )

    console.print(layout)
```

### 5.4 Interactive Confirmation with Typed Phrase

```python
from rich.prompt import Prompt, Confirm
from rich.console import Console

def get_deletion_confirmation(file_count: int, total_size: int) -> bool:
    """
    Get user confirmation for file deletion with typed phrase.

    Args:
        file_count: Number of files to delete
        total_size: Total size in bytes

    Returns:
        True if confirmed, False otherwise
    """
    console.print(
        Panel(
            f"[bold red]⚠️  WARNING[/bold red]\n\n"
            f"You are about to delete {file_count} files "
            f"({format_file_size(total_size)})",
            border_style="red"
        )
    )

    # First level: Yes/No
    if not Confirm.ask(
        "\n[yellow]Do you want to proceed with deletion?[/yellow]",
        default=False
    ):
        return False

    # Second level: Typed confirmation
    console.print(
        f"\n[yellow]To confirm, type:[/yellow] "
        f"[bold white]DELETE {file_count} FILES[/bold white]"
    )

    confirmation_phrase = f"DELETE {file_count} FILES"
    user_input = Prompt.ask("[dim]Type here[/dim]").strip()

    if user_input == confirmation_phrase:
        console.print("[green]✓ Confirmation received[/green]")
        return True
    else:
        console.print(
            f"[red]✗ Incorrect phrase. Expected:[/red] "
            f"[white]{confirmation_phrase}[/white]"
        )
        return False
```

---

## 6. Accessibility Considerations

### 6.1 Screen Reader Compatibility
```python
# Use semantic text descriptions
ACCESSIBILITY_LABELS = {
    'quality_excellent': 'Five star quality - Lossless FLAC audio',
    'quality_good': 'Four star quality - High bitrate MP3',
    'quality_acceptable': 'Three star quality - Medium bitrate MP3',
    'quality_poor': 'Two star quality - Low bitrate MP3',
    'quality_very_poor': 'One star quality - Very low bitrate MP3',
}

def get_accessible_description(file_info: Dict) -> str:
    """Generate screen-reader friendly description."""
    quality_level = determine_quality_level(file_info)

    return (
        f"{file_info['filename']}. "
        f"{ACCESSIBILITY_LABELS[quality_level]}. "
        f"Format: {file_info['format']}. "
        f"Size: {format_file_size(file_info['size'])}. "
        f"Bitrate: {file_info['bitrate']} kilobits per second."
    )
```

### 6.2 Color Blindness Support
```python
# Use patterns in addition to colors
PATTERN_INDICATORS = {
    'excellent': '▓▓▓▓▓',  # Solid blocks
    'good': '▓▓▓▓░',       # Mostly solid
    'acceptable': '▓▓▓░░',  # Half solid
    'poor': '▓▓░░░',       # Mostly hollow
    'very_poor': '▓░░░░',  # Minimal solid
}

# Use icons alongside colors
STATUS_ICONS = {
    'success': '✓',
    'error': '✗',
    'warning': '⚠',
    'info': 'ℹ',
    'processing': '⟳',
}
```

### 6.3 Keyboard-Only Navigation
- All features accessible via keyboard
- Tab/Shift+Tab for field navigation
- Arrow keys for menu navigation
- Enter to confirm, Esc to cancel
- Vim-style J/K navigation option
- Number keys for quick selection

### 6.4 Adjustable Display Settings
```python
DISPLAY_SETTINGS = {
    'use_emoji': True,           # Can disable for terminal compatibility
    'use_unicode_box': True,     # ASCII box fallback available
    'animation_speed': 'normal', # slow/normal/fast/off
    'color_mode': 'auto',        # auto/16/256/truecolor/none
    'panel_width': 'auto',       # auto or fixed width
}
```

---

## 7. Implementation Notes

### File Structure
```
packages/common/music_tools_common/
├── cli/
│   ├── cleanup_ui.py          # Smart Cleanup UI components
│   ├── quality_badges.py      # Quality indicator components
│   ├── comparison_tables.py   # File comparison displays
│   └── progress_displays.py   # Multi-phase progress tracking
└── cleanup/
    ├── scanner.py              # File scanning logic
    ├── comparator.py           # Duplicate comparison engine
    ├── actions.py              # Cleanup actions (delete, backup)
    └── models.py               # Data models
```

### Integration with Existing Code
- Extend existing `Menu` class from `ui/menu.py`
- Use existing `console` instance from `cli/output.py`
- Follow existing theme from `cli/styles.py`
- Use existing progress patterns from `cli/progress.py`

### Performance Optimizations
- Lazy loading of file metadata
- Chunked processing for large libraries
- Background scanning with live updates
- Efficient caching of audio fingerprints
- Incremental UI updates (not full screen refresh)

### Error Handling
- Graceful degradation for missing metadata
- Clear error messages in panels
- Retry mechanisms for file operations
- Validation before destructive actions
- Automatic backup on critical errors

---

## 8. Testing Scenarios

### UI/UX Testing Checklist

1. **Navigation Flow**
   - [ ] Can navigate through all menu levels
   - [ ] Breadcrumb trail shows correct hierarchy
   - [ ] Back button returns to previous screen
   - [ ] Keyboard shortcuts work correctly

2. **Scan Mode Selection**
   - [ ] All scan modes display correctly
   - [ ] Descriptions are clear and helpful
   - [ ] Performance estimates are accurate

3. **Progress Display**
   - [ ] Progress bar updates smoothly
   - [ ] Statistics are accurate and real-time
   - [ ] Live feed shows relevant events
   - [ ] Can cancel operation cleanly

4. **Duplicate Comparison**
   - [ ] Side-by-side view is clear
   - [ ] Quality indicators are accurate
   - [ ] Metadata comparison is complete
   - [ ] Recommendations make sense
   - [ ] All actions work (K/D/B/P/M)

5. **Confirmation Flow**
   - [ ] Backup options are clear
   - [ ] Typed confirmation prevents accidents
   - [ ] Can cancel at any point
   - [ ] Warning messages are prominent

6. **Processing & Completion**
   - [ ] Multi-phase progress is clear
   - [ ] Backup completes before deletion
   - [ ] Summary is accurate and detailed
   - [ ] Logs and reports are generated

---

## Conclusion

This UI/UX design provides a comprehensive, user-friendly interface for the Smart Cleanup workflow while maintaining consistency with existing Music Tools patterns. The design emphasizes:

- **Safety**: Multi-step confirmations and backup options
- **Clarity**: Clear visual hierarchy and color-coded indicators
- **Efficiency**: Keyboard shortcuts and batch operations
- **Accessibility**: Screen reader support and color-blind friendly
- **Consistency**: Matches existing Rich UI patterns throughout the project

All screens use the Rich library's advanced features while remaining accessible and performant even with large music libraries.
