"""
User Interface Components for Music Library Country Tagger

Rich terminal UI with progress bars, statistics dashboards, and elegant formatting.
Provides comprehensive visual feedback for all operations.

Author: CLI & User Experience Developer
Created: September 2025
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich import print as rprint
from rich.align import Align
from rich.box import HEAVY, ROUNDED, SIMPLE
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.status import Status
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

console = Console()


@dataclass
class ProgressData:
    """Container for progress tracking data."""

    current_file: str = ""
    files_processed: int = 0
    files_total: int = 0
    countries_found: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    start_time: float = 0.0
    current_speed: float = 0.0  # files per second


class ProgressTracker:
    """Advanced progress tracking with multiple progress bars."""

    def __init__(self, main_title: str = "Processing"):
        self.main_title = main_title
        self.progress = None
        self.main_task = None
        self.file_task = None
        self.data = ProgressData()
        self.data.start_time = time.time()

        # Thread-safe updates
        self._lock = threading.Lock()
        self._running = False

    def start(self, total_files: int):
        """Initialize progress tracking."""
        self.data.files_total = total_files

        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}", justify="right"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),
            "•",
            MofNCompleteColumn(),
            "•",
            TimeElapsedColumn(),
            "•",
            TimeRemainingColumn(),
            console=console,
            refresh_per_second=4,
        )

        self.progress.start()

        # Main progress task
        self.main_task = self.progress.add_task(f"[bold blue]{self.main_title}", total=total_files)

        # Current file task
        self.file_task = self.progress.add_task("[dim]Preparing...", total=None)

        self._running = True

    def update_file(self, filename: str, progress: float = None):
        """Update current file being processed."""
        with self._lock:
            self.data.current_file = filename

            if self.progress and self.file_task is not None:
                # Show the filename with extension, smart truncation
                display_name = Path(filename).name
                if len(display_name) > 60:
                    # Keep extension visible
                    name_parts = display_name.rsplit(".", 1)
                    if len(name_parts) == 2:
                        base_name, ext = name_parts
                        max_base = 55 - len(ext)
                        display_name = f"{base_name[:max_base]}...{ext}"
                    else:
                        display_name = display_name[:57] + "..."

                task_desc = f"[cyan]{display_name}[/cyan]"

                if progress is not None:
                    self.progress.update(
                        self.file_task, description=task_desc, completed=progress, total=100
                    )
                else:
                    self.progress.update(self.file_task, description=task_desc)

    def increment(self, countries_found: int = 0, cache_hit: bool = False, error: bool = False):
        """Increment progress counters."""
        with self._lock:
            self.data.files_processed += 1

            if countries_found > 0:
                self.data.countries_found += countries_found

            if cache_hit:
                self.data.cache_hits += 1
            else:
                self.data.cache_misses += 1

            if error:
                self.data.errors += 1

            # Calculate speed
            elapsed = time.time() - self.data.start_time
            if elapsed > 0:
                self.data.current_speed = self.data.files_processed / elapsed

            # Update main progress
            if self.progress and self.main_task is not None:
                self.progress.update(self.main_task, completed=self.data.files_processed)

                # Calculate overall progress percentage
                progress_percent = (
                    (self.data.files_processed / self.data.files_total * 100)
                    if self.data.files_total > 0
                    else 0
                )

                # Update main task description with stats
                stats_text = f"[bold green]{progress_percent:.1f}%[/bold green]"
                stats_text += f" • [green]{self.data.countries_found} countries[/green]"
                if self.data.cache_hits > 0:
                    cache_percent = (
                        self.data.cache_hits / (self.data.cache_hits + self.data.cache_misses)
                    ) * 100
                    stats_text += f" • [blue]{cache_percent:.1f}% cached[/blue]"

                if self.data.errors > 0:
                    stats_text += f" • [red]{self.data.errors} errors[/red]"

                # Calculate ETA
                if self.data.current_speed > 0:
                    remaining_files = self.data.files_total - self.data.files_processed
                    eta_seconds = remaining_files / self.data.current_speed
                    if eta_seconds < 60:
                        eta_text = f"{int(eta_seconds)}s"
                    elif eta_seconds < 3600:
                        eta_text = f"{int(eta_seconds/60)}m {int(eta_seconds % 60)}s"
                    else:
                        eta_text = f"{int(eta_seconds/3600)}h {int((eta_seconds % 3600)/60)}m"
                    speed_text = f"[dim]{self.data.current_speed:.1f}/s • ETA: {eta_text}[/dim]"
                else:
                    speed_text = "[dim]calculating speed...[/dim]"

                self.progress.update(
                    self.main_task,
                    description=f"[bold blue]{self.main_title}[/bold blue] • {stats_text} • {speed_text}",
                )

    def finish(self):
        """Complete progress tracking."""
        with self._lock:
            if self.progress:
                # Update final file task
                if self.file_task is not None:
                    self.progress.update(self.file_task, description="[green]✓ Complete[/green]")

                self.progress.stop()
                self.progress = None

            self._running = False

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        with self._lock:
            elapsed = time.time() - self.data.start_time
            return {
                "files_processed": self.data.files_processed,
                "files_total": self.data.files_total,
                "countries_found": self.data.countries_found,
                "cache_hits": self.data.cache_hits,
                "cache_misses": self.data.cache_misses,
                "errors": self.data.errors,
                "elapsed_time": elapsed,
                "current_speed": self.data.current_speed,
                "current_file": self.data.current_file,
            }


class UIManager:
    """Main UI manager for all visual components."""

    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors
        self.console = Console(color_system="auto" if use_colors else None)

    @contextmanager
    def status(self, message: str, spinner: str = "dots"):
        """Context manager for status messages."""
        with Status(message, spinner=spinner, console=self.console) as status:
            yield status

    def show_configuration_wizard(self, config_manager):
        """Display configuration wizard UI."""
        # Header
        header = Panel.fit(
            "[bold blue]🎵 Music Library Country Tagger[/bold blue]\n"
            "[dim]Configuration Wizard[/dim]\n\n"
            "Let's set up your music tagging preferences step by step.",
            border_style="blue",
            padding=(1, 2),
        )
        self.console.print(header)
        self.console.print()

        # Run interactive configuration
        config_manager.interactive_configuration()

    def show_scan_summary(self, results: Dict[str, Any]):
        """Display scan completion summary."""
        # Create summary panel
        summary = Table(show_header=False, box=None, padding=(0, 2))

        # Results
        summary.add_row("📁 Files Processed:", f"[bold]{results.get('total_processed', 0)}[/bold]")
        summary.add_row(
            "🏷️ Files Tagged:", f"[bold green]{results.get('total_tagged', 0)}[/bold green]"
        )

        if results.get("total_errors", 0) > 0:
            summary.add_row("❌ Errors:", f"[bold red]{results['total_errors']}[/bold red]")

        # Timing
        elapsed = results.get("elapsed_time", 0)
        if elapsed > 0:
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours > 0:
                time_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            elif minutes > 0:
                time_str = f"{int(minutes)}m {int(seconds)}s"
            else:
                time_str = f"{seconds:.1f}s"

            summary.add_row("⏱️ Time Elapsed:", f"[dim]{time_str}[/dim]")

            # Speed
            if results.get("total_processed", 0) > 0:
                speed = results["total_processed"] / elapsed
                summary.add_row("🚀 Processing Speed:", f"[dim]{speed:.1f} files/second[/dim]")

        # Status
        status_style = "green"
        status_text = "✓ Scan Completed Successfully"

        if results.get("interrupted", False):
            status_style = "yellow"
            status_text = "⚠️ Scan Interrupted (Progress Saved)"
        elif results.get("total_errors", 0) > 0:
            status_style = "yellow"
            status_text = "⚠️ Scan Completed with Errors"

        if results.get("dry_run", False):
            status_text += " [dim](Dry Run)[/dim]"

        # Final panel
        title = Text()
        title.append("Scan Summary", style="bold")

        panel = Panel(
            summary, title=title, title_align="left", border_style=status_style, padding=(1, 2)
        )

        self.console.print()
        self.console.print(panel)
        self.console.print(f"\n[{status_style}]{status_text}[/{status_style}]")

    def show_statistics(self, stats_data: Dict[str, Any], detailed: bool = False):
        """Display comprehensive statistics."""
        # Main statistics table
        stats_table = Table(title="Library Statistics", show_header=True, header_style="bold blue")
        stats_table.add_column("Metric", style="cyan", width=25)
        stats_table.add_column("Value", style="white", width=15)
        stats_table.add_column("Details", style="dim", width=30)

        # File processing stats
        stats_table.add_section()
        total_files = stats_data.get("total_files_scanned", 0)
        tagged_files = stats_data.get("total_files_tagged", 0)

        stats_table.add_row("Files Scanned", f"{total_files:,}", "Total music files processed")
        stats_table.add_row("Files Tagged", f"{tagged_files:,}", "Files with country information")

        if total_files > 0:
            tag_percent = (tagged_files / total_files) * 100
            stats_table.add_row("Tag Coverage", f"{tag_percent:.1f}%", "Percentage of files tagged")

        # Country statistics
        stats_table.add_section()
        countries_found = stats_data.get("unique_countries", 0)
        stats_table.add_row("Countries Found", str(countries_found), "Unique countries of origin")

        # Performance stats
        stats_table.add_section()
        cache_hits = stats_data.get("cache_hits", 0)
        cache_misses = stats_data.get("cache_misses", 0)
        total_requests = cache_hits + cache_misses

        if total_requests > 0:
            cache_percent = (cache_hits / total_requests) * 100
            stats_table.add_row(
                "Cache Hit Rate", f"{cache_percent:.1f}%", "API requests served from cache"
            )

        avg_speed = stats_data.get("average_processing_speed", 0)
        if avg_speed > 0:
            stats_table.add_row(
                "Processing Speed", f"{avg_speed:.1f}/s", "Average files per second"
            )

        self.console.print(stats_table)

        # Country distribution if detailed
        if detailed and "country_distribution" in stats_data:
            self.console.print()
            self._show_country_distribution(stats_data["country_distribution"])

        # Recent activity if available
        if "recent_activity" in stats_data:
            self.console.print()
            self._show_recent_activity(stats_data["recent_activity"])

    def _show_country_distribution(self, distribution: Dict[str, int]):
        """Show country distribution chart."""
        if not distribution:
            return

        # Sort by count
        sorted_countries = sorted(distribution.items(), key=lambda x: x[1], reverse=True)

        # Create distribution table
        dist_table = Table(
            title="Country Distribution (Top 20)", show_header=True, header_style="bold green"
        )
        dist_table.add_column("Rank", style="dim", width=6)
        dist_table.add_column("Country", style="cyan", width=20)
        dist_table.add_column("Files", style="white", width=10)
        dist_table.add_column("Percentage", style="green", width=12)
        dist_table.add_column("Bar", style="blue", width=30)

        total_files = sum(distribution.values())
        max_count = max(distribution.values()) if distribution else 1

        for i, (country, count) in enumerate(sorted_countries[:20], 1):
            percentage = (count / total_files) * 100
            bar_length = int((count / max_count) * 25)
            bar = "█" * bar_length + "░" * (25 - bar_length)

            dist_table.add_row(str(i), country, f"{count:,}", f"{percentage:.1f}%", bar)

        self.console.print(dist_table)

    def _show_recent_activity(self, activity: List[Dict[str, Any]]):
        """Show recent processing activity."""
        if not activity:
            return

        activity_table = Table(
            title="Recent Activity", show_header=True, header_style="bold yellow"
        )
        activity_table.add_column("Time", style="dim", width=12)
        activity_table.add_column("Operation", style="cyan", width=15)
        activity_table.add_column("Files", style="white", width=8)
        activity_table.add_column("Status", style="green", width=10)

        for entry in activity[-10:]:  # Show last 10 entries
            timestamp = datetime.fromisoformat(entry["timestamp"])
            time_str = timestamp.strftime("%H:%M:%S")

            status_style = "green" if entry.get("success", True) else "red"
            status_text = "Success" if entry.get("success", True) else "Failed"

            activity_table.add_row(
                time_str,
                entry.get("operation", "Unknown"),
                str(entry.get("files_count", 0)),
                f"[{status_style}]{status_text}[/{status_style}]",
            )

        self.console.print(activity_table)

    def show_topic_help(self, topic: str):
        """Show help for specific topics."""
        help_content = {
            "config": {
                "title": "⚙️ Configuration Help",
                "content": [
                    "The configuration system manages all settings for the music tagger.",
                    "",
                    "[bold]Key Configuration Options:[/bold]",
                    "• [cyan]Library Paths[/cyan]: Directories containing your music files",
                    "• [cyan]API Key[/cyan]: MusicBrainz API key for higher rate limits",
                    "• [cyan]Batch Size[/cyan]: Number of files processed per batch (default: 50)",
                    "• [cyan]Log Level[/cyan]: Logging verbosity (DEBUG, INFO, WARNING, ERROR)",
                    "",
                    "[bold]Configuration Commands:[/bold]",
                    "• [green]music-tagger configure[/green] - Interactive configuration wizard",
                    "• [green]music-tagger configure --library-path /path/to/music[/green] - Set library path",
                    "• [green]music-tagger configure --api-key YOUR_KEY[/green] - Set API key",
                    "",
                    "[bold]Configuration File:[/bold]",
                    f"• Location: [dim]{Path.home() / '.music_tagger' / 'config.json'}[/dim]",
                    "• Format: JSON with validation",
                    "• Automatic backup before changes",
                ],
            },
            "scan": {
                "title": "🎵 Scanning Help",
                "content": [
                    "The scan command processes your music library and adds country tags.",
                    "",
                    "[bold]Basic Usage:[/bold]",
                    "• [green]music-tagger scan /path/to/music[/green] - Scan single directory",
                    "• [green]music-tagger scan /path1 /path2[/green] - Scan multiple directories",
                    "",
                    "[bold]Scan Options:[/bold]",
                    "• [cyan]--recursive[/cyan]: Include subdirectories (default: enabled)",
                    "• [cyan]--dry-run[/cyan]: Preview changes without modifying files",
                    "• [cyan]--resume[/cyan]: Continue interrupted scan",
                    "• [cyan]--force[/cyan]: Re-process previously scanned files",
                    "• [cyan]--file-types[/cyan]: Specify audio formats (default: mp3,flac,m4a,ogg,wav)",
                    "",
                    "[bold]Scan Process:[/bold]",
                    "1. Discovers audio files in specified directories",
                    "2. Extracts artist information from metadata",
                    "3. Queries MusicBrainz API for artist origin",
                    "4. Updates file tags with country information",
                    "5. Maintains progress database for resume capability",
                ],
            },
            "stats": {
                "title": "📊 Statistics Help",
                "content": [
                    "View comprehensive statistics about your tagged music library.",
                    "",
                    "[bold]Statistics Commands:[/bold]",
                    "• [green]music-tagger stats[/green] - Show basic statistics",
                    "• [green]music-tagger stats --detailed[/green] - Show detailed breakdown",
                    "• [green]music-tagger stats --export results.csv[/green] - Export to CSV",
                    "",
                    "[bold]Available Statistics:[/bold]",
                    "• [cyan]File Processing[/cyan]: Total files scanned and tagged",
                    "• [cyan]Country Distribution[/cyan]: Most common countries in your library",
                    "• [cyan]Performance Metrics[/cyan]: Processing speed and cache efficiency",
                    "• [cyan]Recent Activity[/cyan]: Latest tagging operations",
                    "",
                    "[bold]Understanding Cache Metrics:[/bold]",
                    "• High cache hit rate means fewer API calls and faster processing",
                    "• Low cache hit rate might indicate diverse music library",
                    "• Cache automatically expires after configured duration",
                ],
            },
            "troubleshooting": {
                "title": "🔧 Troubleshooting Help",
                "content": [
                    "Common issues and solutions for the music tagger.",
                    "",
                    "[bold]Configuration Issues:[/bold]",
                    "• [cyan]'No configuration found'[/cyan]: Run [green]music-tagger configure[/green]",
                    "• [cyan]'Invalid library path'[/cyan]: Check path exists and is readable",
                    "• [cyan]'API key invalid'[/cyan]: Verify MusicBrainz API key",
                    "",
                    "[bold]Scanning Issues:[/bold]",
                    "• [cyan]'No files found'[/cyan]: Check file types and directory structure",
                    "• [cyan]'API rate limit'[/cyan]: Reduce batch size or add API key",
                    "• [cyan]'Permission denied'[/cyan]: Ensure read/write access to music files",
                    "",
                    "[bold]Performance Issues:[/bold]",
                    "• [cyan]Slow processing[/cyan]: Increase batch size, reduce concurrent requests",
                    "• [cyan]High memory usage[/cyan]: Reduce batch size, clear cache",
                    "• [cyan]Network timeouts[/cyan]: Increase request delay",
                    "",
                    "[bold]Getting Help:[/bold]",
                    "• Check log files in [dim]~/.music_tagger/logs/[/dim]",
                    "• Use [green]--log-level DEBUG[/green] for detailed information",
                    "• Run [green]music-tagger stats[/green] to check system status",
                ],
            },
        }

        if topic not in help_content:
            self.console.print(f"[red]Unknown help topic: {topic}[/red]")
            return

        help_data = help_content[topic]

        # Create help panel
        help_text = Text()
        for line in help_data["content"]:
            help_text.append(line + "\n")

        panel = Panel(
            help_text.rstrip(), title=help_data["title"], border_style="blue", padding=(1, 2)
        )

        self.console.print(panel)

    def show_search_help(self, query: str):
        """Show help search results."""
        # Simple help search implementation
        self.console.print(f"[yellow]Searching help for: '{query}'[/yellow]")
        self.console.print()

        # For now, show comprehensive help
        self.show_comprehensive_help()

    def show_comprehensive_help(self):
        """Show complete help documentation."""
        help_sections = [
            {
                "title": "🎵 Music Library Country Tagger",
                "content": [
                    "Automatically tag your music files with country of origin information.",
                    "Uses MusicBrainz database for accurate artist geographic data.",
                ],
            },
            {
                "title": "🚀 Quick Start",
                "content": [
                    "1. [green]music-tagger configure[/green] - Set up your preferences",
                    "2. [green]music-tagger scan ~/Music[/green] - Scan your music library",
                    "3. [green]music-tagger stats[/green] - View results and statistics",
                ],
            },
            {
                "title": "📋 Available Commands",
                "content": [
                    "[bold]configure[/bold] - Set up library paths and preferences",
                    "[bold]scan[/bold] - Process music files and add country tags",
                    "[bold]stats[/bold] - Display library statistics and metrics",
                    "[bold]clear-cache[/bold] - Clear cached data and progress",
                    "[bold]help[/bold] - Show detailed help for specific topics",
                ],
            },
        ]

        for section in help_sections:
            # Create section panel
            content_text = Text()
            for line in section["content"]:
                content_text.append(line + "\n")

            panel = Panel(
                content_text.rstrip(), title=section["title"], border_style="blue", padding=(1, 2)
            )

            self.console.print(panel)
            self.console.print()

        # Footer
        footer = Text()
        footer.append("For detailed help on specific topics:\n", style="dim")
        footer.append("music-tagger help --topic config\n", style="green")
        footer.append("music-tagger help --topic scan\n", style="green")
        footer.append("music-tagger help --topic troubleshooting", style="green")

        footer_panel = Panel(
            Align.center(footer), title="Need More Help?", border_style="yellow", padding=(1, 2)
        )

        self.console.print(footer_panel)

    def confirm_action(self, message: str, default: bool = True) -> bool:
        """Show confirmation prompt."""
        return Confirm.ask(message, default=default, console=self.console)

    def show_error(self, title: str, message: str, details: Optional[str] = None):
        """Show formatted error message."""
        error_text = Text()
        error_text.append(message, style="red")

        if details:
            error_text.append("\n\n")
            error_text.append("Details:", style="bold")
            error_text.append(f"\n{details}", style="dim")

        panel = Panel(
            error_text, title=f"❌ {title}", title_align="left", border_style="red", padding=(1, 2)
        )

        self.console.print(panel)

    def show_warning(self, title: str, message: str):
        """Show formatted warning message."""
        warning_text = Text(message, style="yellow")

        panel = Panel(
            warning_text,
            title=f"⚠️ {title}",
            title_align="left",
            border_style="yellow",
            padding=(1, 2),
        )

        self.console.print(panel)

    def show_success(self, title: str, message: str):
        """Show formatted success message."""
        success_text = Text(message, style="green")

        panel = Panel(
            success_text,
            title=f"✓ {title}",
            title_align="left",
            border_style="green",
            padding=(1, 2),
        )

        self.console.print(panel)
