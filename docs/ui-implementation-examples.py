#!/usr/bin/env python3
"""
Smart Cleanup UI - Implementation Examples
Rich-based terminal UI components for duplicate file detection and cleanup.

This file contains ready-to-use code snippets that implement the UI/UX design
specified in ui-design-smart-cleanup.md
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

# Initialize console
console = Console()


# ============================================================================
# COLOR SCHEMES AND THEMES
# ============================================================================

QUALITY_COLORS = {
    "excellent": "bright_green",  # FLAC, high-bitrate lossless
    "good": "green",  # 320kbps MP3, AAC
    "acceptable": "yellow",  # 192-256kbps MP3
    "poor": "orange",  # 128-192kbps MP3
    "very_poor": "red",  # <128kbps MP3
    "unknown": "dim",  # Unable to determine
}

FORMAT_COLORS = {
    "FLAC": "bright_green",
    "ALAC": "bright_green",
    "WAV": "green",
    "MP3": "yellow",
    "AAC": "yellow",
    "M4A": "yellow",
    "OGG": "cyan",
}

STATUS_COLORS = {
    "scanning": "cyan",
    "analyzing": "blue",
    "comparing": "magenta",
    "ready": "green",
    "processing": "yellow",
    "complete": "bright_green",
    "error": "red",
}

# Pattern indicators for accessibility (color-blind support)
PATTERN_INDICATORS = {
    "excellent": "▓▓▓▓▓",
    "good": "▓▓▓▓░",
    "acceptable": "▓▓▓░░",
    "poor": "▓▓░░░",
    "very_poor": "▓░░░░",
}


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class FileMetadata:
    """Metadata for an audio file."""

    path: str
    filename: str
    format: str
    bitrate: int
    sample_rate: int
    bit_depth: Optional[int]
    size: int
    created: datetime
    modified: datetime
    last_played: Optional[datetime]

    # Tag metadata
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    year: Optional[int] = None
    track: Optional[str] = None
    genre: Optional[str] = None

    @property
    def metadata_complete(self) -> bool:
        """Check if all essential metadata is present."""
        return all([self.title, self.artist, self.album, self.year])


@dataclass
class DuplicateGroup:
    """A group of duplicate files."""

    files: List[FileMetadata]
    similarity: float  # 0.0 to 1.0
    duplicate_type: str  # "exact", "re-encode", "similar"
    recommended_keep: int  # Index of file to keep
    reason: str  # Reason for recommendation


@dataclass
class ScanStats:
    """Statistics from scanning operation."""

    total_files: int = 0
    scanned_files: int = 0
    duplicate_groups: int = 0
    duplicate_files: int = 0
    space_to_recover: int = 0
    speed: float = 0.0  # files per second
    errors: int = 0
    recent_actions: List[str] = None

    def __post_init__(self):
        if self.recent_actions is None:
            self.recent_actions = []


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def format_file_size(bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration as HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def determine_quality_level(file_info: FileMetadata) -> str:
    """Determine quality level from file metadata."""
    format_upper = file_info.format.upper()

    if format_upper in ["FLAC", "ALAC", "WAV"]:
        return "excellent"
    elif format_upper == "MP3" and file_info.bitrate >= 320:
        return "good"
    elif format_upper == "MP3" and file_info.bitrate >= 256:
        return "acceptable"
    elif format_upper == "MP3" and file_info.bitrate >= 192:
        return "poor"
    else:
        return "very_poor"


# ============================================================================
# QUALITY BADGE COMPONENTS
# ============================================================================


def get_quality_badge(file_info: FileMetadata) -> Text:
    """
    Generate a quality badge with stars and color coding.

    Args:
        file_info: File metadata

    Returns:
        Rich Text object with styled quality indicator
    """
    format_upper = file_info.format.upper()
    bitrate = file_info.bitrate

    if format_upper in ["FLAC", "ALAC", "WAV"]:
        stars = "★" * 5
        color = "bright_green"
        label = "LOSSLESS"
    elif format_upper == "MP3" and bitrate >= 320:
        stars = "★" * 4 + "☆"
        color = "green"
        label = f"{bitrate}kbps"
    elif format_upper == "MP3" and bitrate >= 256:
        stars = "★" * 3 + "☆" * 2
        color = "yellow"
        label = f"{bitrate}kbps"
    elif format_upper == "MP3" and bitrate >= 192:
        stars = "★" * 2 + "☆" * 3
        color = "orange"
        label = f"{bitrate}kbps"
    else:
        stars = "★" + "☆" * 4
        color = "red"
        label = f"{bitrate}kbps"

    badge = Text()
    badge.append(f"{stars} ", style=f"bold {color}")
    badge.append(label, style=color)

    return badge


def get_format_badge(format: str) -> Text:
    """Create a colored format badge."""
    color = FORMAT_COLORS.get(format.upper(), "white")
    badge = Text(format.upper(), style=f"bold {color}")
    return badge


# ============================================================================
# SCAN MODE SELECTION SCREEN
# ============================================================================


def display_scan_mode_selection() -> str:
    """
    Display scan mode selection menu.

    Returns:
        Selected mode: 'quick', 'deep', 'custom', or 'cancel'
    """
    console.clear()

    # Create title
    title = Text("🧹 Smart Cleanup › Select Scan Mode", style="bold cyan")

    # Create table for modes
    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED, padding=(0, 2))

    table.add_column("#", style="cyan", justify="right", width=4)
    table.add_column("Mode", style="bold", width=18)
    table.add_column("Speed", justify="center", width=10)
    table.add_column("Accuracy", justify="center", width=10)
    table.add_column("Description", width=50)

    # Add scan modes
    table.add_row(
        "1",
        "⚡ Quick Scan",
        "[green]Fast[/green]",
        "[yellow]Good[/yellow]",
        "Hash-based duplicate detection\n"
        "• Checks file size & MD5\n"
        "• ~100-200 files/sec\n"
        "• Best for exact duplicates",
    )

    table.add_row(
        "2",
        "🔍 Deep Scan",
        "[yellow]Slow[/yellow]",
        "[green]Best[/green]",
        "Audio fingerprint analysis\n"
        "• Acoustic similarity matching\n"
        "• Metadata comparison\n"
        "• ~10-20 files/sec\n"
        "• Finds re-encodes & variants",
    )

    table.add_row(
        "3",
        "⚙️ Custom",
        "[cyan]Varies[/cyan]",
        "[cyan]Custom[/cyan]",
        "Configure your own settings\n"
        "• Set similarity threshold\n"
        "• Choose detection methods\n"
        "• Advanced users only",
    )

    # Add separator and exit
    table.add_row("", "", "", "", "", end_section=True)
    table.add_row("0", "← Back", "", "", "", style="dim")

    # Display in panel
    console.print(Panel(table, title=title, border_style="blue", padding=(1, 2)))

    # Get user choice
    choice = Prompt.ask("\n[bold]Enter choice[/bold]", default="1")

    mode_map = {
        "1": "quick",
        "2": "deep",
        "3": "custom",
        "0": "cancel",
        "q": "quick",
        "d": "deep",
    }

    return mode_map.get(choice.lower(), "cancel")


# ============================================================================
# SCANNING PROGRESS SCREEN
# ============================================================================


def create_scan_progress_display() -> Progress:
    """Create a progress tracker for scanning."""
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
        expand=True,
    )


def display_scanning_screen(stats: ScanStats, current_file: str, mode: str = "Quick Scan"):
    """
    Display scanning progress with live updates.

    Args:
        stats: Current scan statistics
        current_file: Path of file currently being scanned
        mode: Scan mode name
    """
    # Create layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=5),
        Layout(name="progress", size=3),
        Layout(name="current", size=3),
        Layout(name="stats", size=8),
        Layout(name="feed", size=10),
    )

    # Header
    header_text = Text()
    header_text.append("🧹 Smart Cleanup › Scanning Library\n\n", style="bold cyan")
    header_text.append(f"Scan Mode: ⚡ {mode}\n", style="cyan")
    header_text.append(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")

    layout["header"].update(Panel(header_text, border_style="cyan"))

    # Progress bar
    progress = create_scan_progress_display()
    task = progress.add_task(
        "Scanning files...", total=stats.total_files, completed=stats.scanned_files
    )
    layout["progress"].update(progress)

    # Current file
    current_text = Text()
    current_text.append("📂 Scanning: ", style="dim")
    current_text.append(current_file, style="cyan")
    layout["current"].update(Panel(current_text, border_style="dim"))

    # Statistics panel
    stats_table = Table.grid(padding=(0, 2))
    stats_table.add_column(style="cyan", justify="left")
    stats_table.add_column(style="green", justify="left")

    stats_table.add_row("Scanned:", f"{stats.scanned_files:,} files")
    stats_table.add_row("Duplicates Found:", f"{stats.duplicate_groups} groups")
    stats_table.add_row("Speed:", f"{stats.speed:.1f} files/sec")

    if stats.total_files > 0:
        remaining = stats.total_files - stats.scanned_files
        eta_seconds = remaining / stats.speed if stats.speed > 0 else 0
        stats_table.add_row("Estimated Time:", format_duration(eta_seconds))

    stats_table.add_row(
        "Potential Space to Recover:", f"~{format_file_size(stats.space_to_recover)}"
    )

    layout["stats"].update(Panel(stats_table, title="Statistics", border_style="blue"))

    # Live feed
    feed_lines = []
    for action in stats.recent_actions[-8:]:
        if action.startswith("✓"):
            style = "green"
        elif action.startswith("ℹ"):
            style = "cyan"
        elif action.startswith("⚠"):
            style = "yellow"
        else:
            style = "white"

        feed_lines.append(Text(action, style=style))

    feed_text = Text("\n").join(feed_lines) if feed_lines else Text("Scanning...", style="dim")

    layout["feed"].update(Panel(feed_text, title="Live Feed", border_style="dim"))

    # Display
    console.print(layout)


# ============================================================================
# DUPLICATE COMPARISON TABLE
# ============================================================================


def create_comparison_table(
    file_a: FileMetadata, file_b: FileMetadata, recommendation: str, reason: str
) -> Table:
    """
    Create a side-by-side comparison table for duplicate files.

    Args:
        file_a: First file metadata
        file_b: Second file metadata
        recommendation: 'A' or 'B' - which file to keep
        reason: Explanation for recommendation

    Returns:
        Rich Table object
    """
    table = Table(
        title="File Comparison",
        show_header=True,
        header_style="bold cyan",
        box=box.DOUBLE,
        padding=(0, 1),
        expand=True,
    )

    # Highlight the recommended file
    if recommendation == "A":
        header_a = "[bright_green]File A (KEEP)[/bright_green]"
        header_b = "File B (DELETE?)"
        style_a = "bright_green"
        style_b = "white"
    else:
        header_a = "File A (DELETE?)"
        header_b = "[bright_green]File B (KEEP)[/bright_green]"
        style_a = "white"
        style_b = "bright_green"

    table.add_column(header_a, style=style_a, width=40)
    table.add_column(header_b, style=style_b, width=40)

    # File paths
    table.add_row(f"📁 {file_a.path}", f"📁 {file_b.path}")

    # Add section separator
    table.add_section()

    # Quality badges
    quality_a = get_quality_badge(file_a)
    quality_b = get_quality_badge(file_b)

    table.add_row(f"Quality: {quality_a}", f"Quality: {quality_b}")

    # Technical details
    table.add_row(
        f"Format:  {get_format_badge(file_a.format)}", f"Format:  {get_format_badge(file_b.format)}"
    )

    table.add_row(f"Bitrate: {file_a.bitrate} kbps", f"Bitrate: {file_b.bitrate} kbps")

    table.add_row(
        f"Size:    {format_file_size(file_a.size)}", f"Size:    {format_file_size(file_b.size)}"
    )

    # Sample rate
    sample_a = f"{file_a.sample_rate} Hz"
    if file_a.bit_depth:
        sample_a += f"/{file_a.bit_depth}bit"

    sample_b = f"{file_b.sample_rate} Hz"
    if file_b.bit_depth:
        sample_b += f"/{file_b.bit_depth}bit"

    table.add_row(f"Sample:  {sample_a}", f"Sample:  {sample_b}")

    # Metadata comparison
    table.add_section()
    table.add_row("[bold blue]Metadata[/bold blue]", "[bold blue]Metadata[/bold blue]")

    metadata_fields = [
        ("title", "Title"),
        ("artist", "Artist"),
        ("album", "Album"),
        ("year", "Year"),
        ("track", "Track"),
        ("genre", "Genre"),
    ]

    for field, label in metadata_fields:
        val_a = getattr(file_a, field, None) or "[yellow](missing)[/yellow]"
        val_b = getattr(file_b, field, None) or "[yellow](missing)[/yellow]"

        table.add_row(f"• {label}: {val_a}", f"• {label}: {val_b}")

    # Completeness check
    complete_a = (
        "✓ Complete metadata"
        if file_a.metadata_complete
        else "[yellow]⚠️ Incomplete metadata[/yellow]"
    )
    complete_b = (
        "✓ Complete metadata"
        if file_b.metadata_complete
        else "[yellow]⚠️ Incomplete metadata[/yellow]"
    )

    table.add_row(complete_a, complete_b, style="dim")

    # File dates
    table.add_section()

    table.add_row(
        f"Created:  {file_a.created.strftime('%Y-%m-%d')}",
        f"Created:  {file_b.created.strftime('%Y-%m-%d')}",
    )

    table.add_row(
        f"Modified: {file_a.modified.strftime('%Y-%m-%d')}",
        f"Modified: {file_b.modified.strftime('%Y-%m-%d')}",
    )

    last_played_a = file_a.last_played.strftime("%Y-%m-%d") if file_a.last_played else "Never"
    last_played_b = file_b.last_played.strftime("%Y-%m-%d") if file_b.last_played else "Never"

    table.add_row(f"Last Played: {last_played_a}", f"Last Played: {last_played_b}")

    return table


def display_duplicate_review(group: DuplicateGroup, current: int, total: int):
    """
    Display duplicate review screen.

    Args:
        group: Duplicate group to review
        current: Current group number
        total: Total number of groups
    """
    console.clear()

    # Header
    title = f"🧹 Smart Cleanup › Review Duplicates (Group {current} of {total})"
    console.print(Panel(title, style="bold cyan"))

    # Song info
    file_a = group.files[0]
    console.print(f'\n  Song: [bold]"{file_a.artist} - {file_a.title}"[/bold]')
    console.print(
        f"  Duplicate Type: [cyan]{group.duplicate_type.title()}[/cyan] "
        f"({group.similarity*100:.1f}% similarity)\n"
    )

    # Comparison table
    table = create_comparison_table(
        file_a, group.files[1], "A" if group.recommended_keep == 0 else "B", group.reason
    )
    console.print(table)

    # Recommendation
    keep_letter = "A" if group.recommended_keep == 0 else "B"
    delete_letter = "B" if group.recommended_keep == 0 else "A"

    console.print(
        f"\n  🤖 Recommendation: [bright_green]KEEP File {keep_letter}[/bright_green], "
        f"[red]DELETE File {delete_letter}[/red]"
    )
    console.print(f"  Reason: [dim]{group.reason}[/dim]\n")

    # Actions
    actions_table = Table.grid(padding=(0, 2))
    actions_table.add_column(style="cyan", justify="left")
    actions_table.add_column(style="white", justify="left")

    actions_table.add_row("K", "Keep File A (recommended)")
    actions_table.add_row("D", "Keep File B instead")
    actions_table.add_row("B", "Keep both files (skip)")
    actions_table.add_row("P", "Preview audio (play 10 sec)")
    actions_table.add_row("M", "Show more details")
    actions_table.add_row("N/→", "Next duplicate group")
    actions_table.add_row("Q", "Finish review and process")

    console.print(Panel(actions_table, title="[bold]Actions[/bold]", border_style="blue"))


# ============================================================================
# REVIEW SUMMARY SCREEN
# ============================================================================


def display_review_summary(
    total_groups: int, files_to_delete: int, space_to_recover: int, quality_distribution: Dict
):
    """
    Display review summary before cleanup.

    Args:
        total_groups: Total duplicate groups reviewed
        files_to_delete: Number of files marked for deletion
        space_to_recover: Bytes to be recovered
        quality_distribution: Dict of quality level -> (count, bytes)
    """
    console.clear()

    title = Text("🧹 Smart Cleanup › Review Summary", style="bold cyan")
    console.print(Panel(title, border_style="cyan"))

    console.print(
        f"\n  Review Complete: Analyzed {total_groups} duplicate groups "
        f"({total_groups * 2} files)\n"
    )

    # Recommended actions table
    actions_table = Table(
        title="Recommended Actions", show_header=True, header_style="bold cyan", box=box.ROUNDED
    )

    actions_table.add_column("Action", style="cyan", width=25)
    actions_table.add_column("Files", justify="right", width=10)
    actions_table.add_column("Space to Recover", justify="right", width=20)

    actions_table.add_row(
        "🗑️  Delete duplicates", str(files_to_delete), f"{format_file_size(space_to_recover)} (100%)"
    )

    actions_table.add_row(
        "✓  Keep originals", str(files_to_delete), f"{format_file_size(space_to_recover * 2)}"
    )

    actions_table.add_row("⏭️  Skipped/both kept", "0", "0 GB")

    console.print(actions_table)

    # Quality distribution
    console.print("\n  Quality Distribution of Deleted Files:")

    total_size = sum(size for _, size in quality_distribution.values())

    for quality_level, (count, size) in quality_distribution.items():
        percentage = (size / total_size * 100) if total_size > 0 else 0
        bar_length = int(percentage / 5)  # Scale to 20 chars max
        bar = "█" * bar_length + "░" * (20 - bar_length)

        color = QUALITY_COLORS.get(quality_level, "white")
        console.print(
            f"  • {quality_level.replace('_', ' ').title():20} "
            f"{count:3} files   {format_file_size(size):>8}  "
            f"[{color}]{bar}[/{color}]  {percentage:>3.0f}%"
        )

    # Action menu
    console.print("\n  What would you like to do?")

    actions = Table.grid(padding=(0, 2))
    actions.add_column(style="cyan", width=5)
    actions.add_column(style="white")

    actions.add_row("1.", "✓ Execute cleanup (with backup)")
    actions.add_row("2.", "📋 Review individual decisions")
    actions.add_row("3.", "💾 Export report to file")
    actions.add_row("4.", "❌ Cancel and keep everything")
    actions.add_row("0.", "← Back to Main Menu")

    console.print(Panel(actions, border_style="blue"))


# ============================================================================
# CONFIRMATION DIALOG
# ============================================================================


def get_cleanup_confirmation(file_count: int, total_size: int) -> Tuple[bool, str]:
    """
    Get user confirmation for cleanup with backup option.

    Args:
        file_count: Number of files to delete
        total_size: Total size in bytes

    Returns:
        (confirmed, backup_mode) where backup_mode is 'full', 'log', or 'none'
    """
    console.clear()

    # Warning header
    warning_panel = Panel(
        f"[bold red]⚠️  WARNING[/bold red]\n\n"
        f"You are about to delete {file_count} files "
        f"({format_file_size(total_size)})",
        title="Confirmation Required",
        border_style="red",
        padding=(1, 2),
    )
    console.print(warning_panel)

    # Backup options
    backup_table = Table(
        title="Backup Options",
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )

    backup_table.add_column("#", style="cyan", width=5)
    backup_table.add_column("Option", style="bold", width=20)
    backup_table.add_column("Description", width=50)

    backup_table.add_row(
        "1",
        "💾 Full Backup",
        "Move files to backup folder before deletion\n"
        f"Location: ~/.music-tools/backups/{datetime.now().strftime('%Y-%m-%d')}/\n"
        f"Disk space required: {format_file_size(total_size)}\n"
        "[green]Can restore anytime[/green]",
    )

    backup_table.add_row(
        "2",
        "📋 Log Only",
        "Just save a list of deleted files\n"
        "Location: ~/.music-tools/logs/cleanup.log\n"
        "Disk space: <1 MB\n"
        "[yellow]Cannot restore files[/yellow]",
    )

    backup_table.add_row(
        "3", "⚠️  No Backup", "Permanently delete files\n" "[red]⚠️ THIS CANNOT BE UNDONE[/red]"
    )

    console.print(backup_table)

    # Get backup choice
    backup_choice = Prompt.ask(
        "\n[bold yellow]Backup Strategy[/bold yellow]", choices=["1", "2", "3"], default="1"
    )

    backup_mode_map = {"1": "full", "2": "log", "3": "none"}
    backup_mode = backup_mode_map[backup_choice]

    # Confirmation phrase
    console.print("\n" + "─" * 75)
    console.print("\n[bold yellow]Final Confirmation:[/bold yellow]\n")

    console.print(f'  Type [bold white]"DELETE {file_count} FILES"[/bold white] to proceed:\n')

    confirmation_phrase = f"DELETE {file_count} FILES"
    user_input = Prompt.ask("  [dim]Type here[/dim]").strip()

    if user_input == confirmation_phrase:
        console.print("\n  [green]✓ Confirmation received[/green]\n")
        return True, backup_mode
    else:
        console.print(
            f"\n  [red]✗ Incorrect phrase.[/red]\n"
            f"  Expected: [white]{confirmation_phrase}[/white]\n"
        )
        return False, ""


# ============================================================================
# PROCESSING PROGRESS
# ============================================================================


def display_processing_progress(
    phase: str, current: int, total: int, current_file: str, stats: Dict
):
    """
    Display processing progress with multi-phase support.

    Args:
        phase: Current phase name
        current: Current item index
        total: Total items
        current_file: Current file being processed
        stats: Statistics dictionary
    """
    console.clear()

    # Create main layout
    layout = Layout()
    layout.split_column(
        Layout(name="title", size=3),
        Layout(name="phase", size=5),
        Layout(name="current", size=3),
        Layout(name="details", size=8),
        Layout(name="feed", size=8),
    )

    # Title
    layout["title"].update(Panel("🧹 Smart Cleanup › Processing Cleanup", style="bold cyan"))

    # Phase progress
    if phase == "backup":
        phase_text = Text("Phase 1: Creating Backup\n", style="bold yellow")
    else:
        phase_text = Text("Phase 2: Deleting Duplicate Files\n", style="bold yellow")

    # Progress bar
    progress = create_scan_progress_display()
    task = progress.add_task(phase, total=total, completed=current)

    layout["phase"].update(Panel(phase_text, border_style="yellow"))

    # Current file
    current_text = Text(f"Processing: {current_file}", style="cyan")
    layout["current"].update(Panel(current_text, border_style="dim"))

    # Details
    details_table = Table.grid(padding=(0, 2))
    details_table.add_column(style="cyan", justify="left")
    details_table.add_column(style="green", justify="left")

    if phase == "backup":
        details_table.add_row("Backed up:", f"{current} files")
        details_table.add_row("Size copied:", format_file_size(stats.get("bytes_copied", 0)))
    else:
        details_table.add_row("Deleted:", f"{current} files")
        details_table.add_row("Remaining:", f"{total - current} files")
        details_table.add_row("Space freed:", format_file_size(stats.get("space_freed", 0)))

    details_table.add_row("Speed:", f"{stats.get('speed', 0):.1f} files/sec")
    details_table.add_row("Errors:", str(stats.get("errors", 0)))

    layout["details"].update(Panel(details_table, title="Progress Details", border_style="blue"))

    # Recent actions feed
    feed_text = "\n".join(stats.get("recent_actions", [])[-6:])
    layout["feed"].update(Panel(feed_text, title="Recent Actions", border_style="dim"))

    console.print(layout)


# ============================================================================
# COMPLETION SUMMARY
# ============================================================================


def display_completion_summary(
    deleted_count: int,
    space_recovered: int,
    backup_path: str,
    processing_time: float,
    library_size_before: int,
    library_size_after: int,
):
    """
    Display cleanup completion summary.

    Args:
        deleted_count: Number of files deleted
        space_recovered: Bytes recovered
        backup_path: Path to backup folder
        processing_time: Time taken in seconds
        library_size_before: Library size before cleanup
        library_size_after: Library size after cleanup
    """
    console.clear()

    # Success header
    console.print(
        Panel(
            "[bold bright_green]✨ Success! Your library has been cleaned up.[/bold bright_green]",
            title="🧹 Smart Cleanup › Cleanup Complete!",
            border_style="bright_green",
            padding=(1, 2),
        )
    )

    # Summary table
    summary_table = Table(
        title="Cleanup Summary", show_header=True, header_style="bold cyan", box=box.DOUBLE
    )

    summary_table.add_column("Metric", style="cyan", width=30)
    summary_table.add_column("Value", style="green", justify="right", width=40)

    summary_table.add_row("Files Deleted", f"{deleted_count} files")
    summary_table.add_row("Space Recovered", format_file_size(space_recovered))
    summary_table.add_row("Files Backed Up", f"{deleted_count} files (in backup folder)")
    summary_table.add_row("Processing Time", format_duration(processing_time))
    summary_table.add_row(
        "Library Size After",
        f"{format_file_size(library_size_after)} " f"(was {format_file_size(library_size_before)})",
    )

    console.print(summary_table)

    # Backup information
    console.print("\n  [bold]Backup Information:[/bold]")
    console.print(f"  📁 Location: [cyan]{backup_path}[/cyan]")
    console.print(f"  💾 Size: {format_file_size(space_recovered)}")
    console.print(f"  ⏰ Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    console.print(
        f'\n  To restore files: Run [cyan]"restore-backup ' f'{Path(backup_path).name}"[/cyan]'
    )
    console.print(
        f'  To delete backup:  Run [dim]"delete-backup '
        f'{Path(backup_path).name}"[/dim] (after 30 days)'
    )

    # Reports
    log_file = f"~/.music-tools/logs/cleanup_{datetime.now().strftime('%Y-%m-%d')}.log"
    csv_file = f"~/.music-tools/reports/cleanup_{datetime.now().strftime('%Y-%m-%d')}.csv"

    console.print("\n  [bold]Detailed Report:[/bold]")
    console.print(f"  📄 Cleanup log saved to: [cyan]{log_file}[/cyan]")
    console.print(f"  📊 CSV export: [cyan]{csv_file}[/cyan]")

    # Next steps
    next_steps = Table.grid(padding=(0, 2))
    next_steps.add_column(style="cyan", width=5)
    next_steps.add_column(style="white")

    next_steps.add_row("1.", "📊 View detailed report")
    next_steps.add_row("2.", "📁 Open backup folder")
    next_steps.add_row("3.", "🔄 Run another cleanup")
    next_steps.add_row("4.", "← Return to main menu")

    console.print(Panel(next_steps, title="[bold]What's next?[/bold]", border_style="blue"))


# ============================================================================
# DEMO / EXAMPLE USAGE
# ============================================================================


def demo():
    """Demonstrate the UI components."""
    import time

    # 1. Scan mode selection
    mode = display_scan_mode_selection()
    console.print(f"\n[green]Selected mode: {mode}[/green]")
    time.sleep(2)

    # 2. Scanning progress (simulated)
    stats = ScanStats(
        total_files=12456,
        scanned_files=8234,
        duplicate_groups=156,
        duplicate_files=312,
        space_to_recover=12_300_000_000,
        speed=145.3,
        recent_actions=[
            '✓ Found duplicate: "Artist - Track.mp3" vs "Artist - Track.flac"',
            '✓ Duplicate group: 3 versions of "Song Title.mp3"',
            'ℹ Skipped: corrupted file "damaged.mp3"',
        ],
    )

    display_scanning_screen(stats, "/Users/music/Albums/Artist Name/Album/track.flac", "Quick Scan")
    time.sleep(3)

    # 3. Review summary
    quality_dist = {
        "poor": (89, 5_800_000_000),
        "acceptable": (45, 4_200_000_000),
        "good": (22, 2_300_000_000),
    }

    display_review_summary(156, 156, 12_300_000_000, quality_dist)
    time.sleep(3)

    # 4. Confirmation
    confirmed, backup_mode = get_cleanup_confirmation(156, 12_300_000_000)

    if confirmed:
        console.print(f"\n[green]Proceeding with {backup_mode} backup mode[/green]")
    else:
        console.print("\n[yellow]Cleanup cancelled[/yellow]")


if __name__ == "__main__":
    demo()
