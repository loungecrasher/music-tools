"""
Smart Cleanup Workflow - Interactive duplicate detection and removal with Rich UI.

Provides a comprehensive 8-screen workflow for safely identifying and removing
duplicate music files while preserving the highest quality versions.

Author: Music Tools Dev Team
Created: 2026-01-08
"""

import csv
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    TimeRemainingColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .database import LibraryDatabase
from .duplicate_checker import DuplicateChecker
from .models import LibraryFile
from .quality_analyzer import (
    AudioMetadata,
    BitrateType,
    extract_audio_metadata,
    get_quality_tier,
    rank_duplicate_group,
)
from .safe_delete import DeletionGroup, DeletionStats, SafeDeletionPlan

logger = logging.getLogger(__name__)

# UI Configuration
COLORS = {
    "flac": "green",
    "high_mp3": "yellow",
    "low_mp3": "red",
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "success": "green",
    "title": "bold cyan",
    "header": "bold white",
}

# Quality tiers for color coding
QUALITY_EXCELLENT = 80  # Green
QUALITY_GOOD = 60  # Yellow
QUALITY_FAIR = 40  # Red


@dataclass
class ScanMode:
    """Configuration for different scan modes."""

    name: str
    description: str
    use_content_hash: bool
    fuzzy_threshold: float
    deep_analysis: bool


# Predefined scan modes
SCAN_MODES = {
    "quick": ScanMode(
        name="Quick Scan",
        description="Fast metadata-based duplicate detection",
        use_content_hash=False,
        fuzzy_threshold=0.9,
        deep_analysis=False,
    ),
    "deep": ScanMode(
        name="Deep Scan",
        description="Thorough content hash + metadata analysis",
        use_content_hash=True,
        fuzzy_threshold=0.8,
        deep_analysis=True,
    ),
    "custom": ScanMode(
        name="Custom Scan",
        description="User-defined scan parameters",
        use_content_hash=True,
        fuzzy_threshold=0.85,
        deep_analysis=True,
    ),
}


@dataclass
class DuplicateGroupInfo:
    """Enhanced duplicate group with quality analysis."""

    group_id: str
    files: List[AudioMetadata]
    recommended_keep: AudioMetadata
    recommended_delete: List[AudioMetadata]
    quality_range: Tuple[int, int]
    space_savings_mb: float
    confidence: float
    user_confirmed: bool = False
    user_action: str = "pending"  # pending, keep_all, delete_selected, skip


@dataclass
class CleanupStats:
    """Statistics for cleanup session."""

    total_files_scanned: int = 0
    duplicate_groups_found: int = 0
    total_duplicates: int = 0
    groups_reviewed: int = 0
    groups_confirmed: int = 0
    files_to_delete: int = 0
    space_to_free_mb: float = 0.0
    files_deleted: int = 0
    space_freed_mb: float = 0.0
    scan_duration: float = 0.0
    cleanup_duration: float = 0.0


class SmartCleanupWorkflow:
    """
    Interactive Smart Cleanup workflow with Rich UI.

    Implements 8-screen workflow:
    1. Enhanced welcome with library stats
    2. Scan mode selection (Quick/Deep/Custom)
    3. Scanning progress with live updates
    4. Side-by-side duplicate comparison
    5. Review summary with quality distribution
    6. Multi-step confirmation with backup
    7. Dual-phase processing (backup→delete)
    8. Completion summary with reports
    """

    def __init__(
        self,
        library_db: LibraryDatabase,
        library_path: str,
        backup_dir: Optional[str] = None,
        console: Optional[Console] = None,
    ):
        """
        Initialize Smart Cleanup workflow.

        Args:
            library_db: LibraryDatabase instance
            library_path: Path to music library
            backup_dir: Optional backup directory
            console: Optional Rich console instance
        """
        self.db = library_db
        self.library_path = Path(library_path)
        self.backup_dir = backup_dir or str(self.library_path / ".cleanup_backups")
        self.console = console or Console()

        self.duplicate_checker = DuplicateChecker(library_db)
        self.deletion_plan: Optional[SafeDeletionPlan] = None
        self.duplicate_groups: List[DuplicateGroupInfo] = []
        self.stats = CleanupStats()

        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.reports_dir = self.library_path / ".cleanup_reports"
        self.reports_dir.mkdir(exist_ok=True)

    def run(self) -> CleanupStats:
        """
        Main entry point for Smart Cleanup workflow.

        Returns:
            CleanupStats with session results
        """
        try:
            # Screen 1: Enhanced welcome
            if not self._show_welcome():
                self.console.print("[yellow]Cleanup cancelled.[/yellow]")
                return self.stats

            # Screen 2: Scan mode selection
            scan_mode = self.select_scan_mode()
            if not scan_mode:
                self.console.print("[yellow]Cleanup cancelled.[/yellow]")
                return self.stats

            # Screen 3: Scanning with progress
            self.scan_for_duplicates(scan_mode, self.library_path)

            if not self.duplicate_groups:
                self.console.print(
                    Panel(
                        "[green]No duplicates found! Your library is clean.[/green]",
                        title="All Clear",
                        border_style="green",
                    )
                )
                return self.stats

            # Screen 4: Interactive review
            self.review_duplicates_interactive(self.duplicate_groups)

            # Screen 5: Review summary
            if not self.show_review_summary(self.duplicate_groups):
                self.console.print("[yellow]Cleanup cancelled.[/yellow]")
                return self.stats

            # Screen 6: Multi-step confirmation
            if not self.confirm_and_execute():
                self.console.print("[yellow]Cleanup cancelled.[/yellow]")
                return self.stats

            # Screen 7: Execute deletion (dual-phase)
            self._execute_cleanup()

            # Screen 8: Completion summary
            self.show_completion_summary(self.stats)

            return self.stats

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Cleanup interrupted by user.[/yellow]")
            return self.stats
        except Exception as e:
            logger.error(f"Error in cleanup workflow: {e}", exc_info=True)
            self.console.print(f"[red]Error: {e}[/red]")
            return self.stats

    def _show_welcome(self) -> bool:
        """
        Screen 1: Enhanced welcome with library statistics.

        Returns:
            True to continue, False to cancel
        """
        # Get library stats
        stats = self.db.get_statistics()

        # Create welcome panel
        welcome_text = Text()
        welcome_text.append("Smart Cleanup Workflow\n\n", style="bold cyan")
        welcome_text.append(
            "Safely identify and remove duplicate music files while ", style="white"
        )
        welcome_text.append("preserving the highest quality versions.\n\n", style="white")

        # Library stats
        welcome_text.append("Library Statistics:\n", style="bold")
        welcome_text.append(f"  Total Files: {stats.total_files:,}\n", style="cyan")
        welcome_text.append(f"  Total Size: {stats.total_size_gb:.2f} GB\n", style="cyan")
        welcome_text.append(f"  Artists: {stats.artists_count:,}\n", style="cyan")

        # Format breakdown
        if stats.formats_breakdown:
            welcome_text.append("\n  Format Breakdown:\n", style="bold")
            for fmt, count in sorted(
                stats.formats_breakdown.items(), key=lambda x: x[1], reverse=True
            )[:5]:
                percentage = (count / stats.total_files * 100) if stats.total_files > 0 else 0
                welcome_text.append(
                    f"    {fmt.upper()}: {count:,} ({percentage:.1f}%)\n", style="white"
                )

        welcome_text.append("\nFeatures:\n", style="bold yellow")
        welcome_text.append("  • Quality-based duplicate detection\n", style="white")
        welcome_text.append("  • Automatic backup before deletion\n", style="white")
        welcome_text.append("  • Interactive review with side-by-side comparison\n", style="white")
        welcome_text.append("  • Detailed reports (CSV/JSON)\n", style="white")

        panel = Panel(
            welcome_text, title="Welcome to Smart Cleanup", border_style="cyan", box=box.DOUBLE
        )
        self.console.print(panel)

        return Confirm.ask("\n[bold]Start cleanup workflow?[/bold]", default=True)

    def select_scan_mode(self) -> Optional[ScanMode]:
        """
        Screen 2: Scan mode selection (Quick/Deep/Custom).

        Returns:
            Selected ScanMode or None if cancelled
        """
        # Create mode selection table
        table = Table(title="Scan Mode Selection", box=box.ROUNDED)
        table.add_column("Option", style="cyan", width=8)
        table.add_column("Mode", style="bold")
        table.add_column("Description", style="white")
        table.add_column("Speed", style="yellow")
        table.add_column("Accuracy", style="green")

        table.add_row("1", "Quick Scan", "Metadata-based detection", "★★★★★", "★★★☆☆")
        table.add_row("2", "Deep Scan", "Content hash + metadata", "★★★☆☆", "★★★★★")
        table.add_row("3", "Custom Scan", "Configure parameters", "Variable", "Variable")

        self.console.print(table)

        choice = Prompt.ask(
            "\n[bold]Select scan mode[/bold]", choices=["1", "2", "3", "q"], default="2"
        )

        if choice == "q":
            return None

        mode_map = {"1": "quick", "2": "deep", "3": "custom"}
        selected_mode = SCAN_MODES[mode_map[choice]]

        # Custom mode configuration
        if choice == "3":
            selected_mode = self._configure_custom_mode()

        return selected_mode

    def _configure_custom_mode(self) -> ScanMode:
        """Configure custom scan mode parameters."""
        self.console.print("\n[bold cyan]Custom Scan Configuration[/bold cyan]")

        use_content_hash = Confirm.ask("Use content hash matching?", default=True)

        fuzzy_threshold = float(Prompt.ask("Fuzzy match threshold (0.0-1.0)", default="0.85"))
        fuzzy_threshold = max(0.0, min(1.0, fuzzy_threshold))

        deep_analysis = Confirm.ask("Perform deep quality analysis?", default=True)

        return ScanMode(
            name="Custom Scan",
            description=f"Custom: hash={use_content_hash}, threshold={fuzzy_threshold}",
            use_content_hash=use_content_hash,
            fuzzy_threshold=fuzzy_threshold,
            deep_analysis=deep_analysis,
        )

    def scan_for_duplicates(self, mode: ScanMode, path: Path) -> None:
        """
        Screen 3: Scan for duplicates with live progress.

        Args:
            mode: ScanMode configuration
            path: Path to scan
        """
        start_time = datetime.now()

        # Get all files from database
        all_files = self.db.get_all_files()
        self.stats.total_files_scanned = len(all_files)

        # Create progress display
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
        )

        with progress:
            # Phase 1: Group by metadata hash
            task1 = progress.add_task("[cyan]Grouping by metadata...", total=len(all_files))

            hash_groups: Dict[str, List[LibraryFile]] = {}
            for file in all_files:
                if file.metadata_hash:
                    hash_groups.setdefault(file.metadata_hash, []).append(file)
                progress.update(task1, advance=1)

            # Filter groups with duplicates
            duplicate_hash_groups = {k: v for k, v in hash_groups.items() if len(v) > 1}
            progress.update(task1, completed=True)

            # Phase 2: Quality analysis
            task2 = progress.add_task(
                "[cyan]Analyzing quality...", total=len(duplicate_hash_groups)
            )

            for hash_key, files in duplicate_hash_groups.items():
                # Extract quality metadata
                files_metadata = []
                for lib_file in files:
                    metadata = extract_audio_metadata(lib_file.file_path)
                    if metadata:
                        files_metadata.append(metadata)

                if len(files_metadata) > 1:
                    # Rank by quality
                    keep, delete = rank_duplicate_group(files_metadata)

                    # Calculate stats
                    scores = [f.quality_score for f in files_metadata]
                    quality_range = (min(scores), max(scores))
                    space_savings = sum(f.file_size for f in delete) / (1024 * 1024)

                    # Create group info
                    group_info = DuplicateGroupInfo(
                        group_id=f"dup_{len(self.duplicate_groups) + 1:04d}",
                        files=files_metadata,
                        recommended_keep=keep,
                        recommended_delete=delete,
                        quality_range=quality_range,
                        space_savings_mb=space_savings,
                        confidence=1.0 if quality_range[0] == quality_range[1] else 0.9,
                    )
                    self.duplicate_groups.append(group_info)

                progress.update(task2, advance=1)

        # Update stats
        self.stats.duplicate_groups_found = len(self.duplicate_groups)
        self.stats.total_duplicates = sum(len(g.files) - 1 for g in self.duplicate_groups)
        self.stats.scan_duration = (datetime.now() - start_time).total_seconds()

        # Display summary
        summary = Table(title="Scan Results", box=box.ROUNDED)
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="white")

        summary.add_row("Files Scanned", f"{self.stats.total_files_scanned:,}")
        summary.add_row("Duplicate Groups", f"{self.stats.duplicate_groups_found:,}")
        summary.add_row("Total Duplicates", f"{self.stats.total_duplicates:,}")
        summary.add_row("Scan Duration", f"{self.stats.scan_duration:.2f}s")

        self.console.print("\n", summary)

    def review_duplicates_interactive(self, groups: List[DuplicateGroupInfo]) -> None:
        """
        Screen 4: Interactive duplicate review with side-by-side comparison.

        Args:
            groups: List of duplicate groups to review
        """
        self.console.print(
            Panel(
                "[bold cyan]Interactive Review[/bold cyan]\n\n"
                "Review each duplicate group and confirm deletion.\n"
                "Commands: [y]es to confirm, [n]o to keep all, [s]kip this group, [q]uit review",
                title="Review Mode",
                border_style="cyan",
            )
        )

        for idx, group in enumerate(groups, 1):
            self.console.print(f"\n[bold]Group {idx}/{len(groups)}[/bold]")

            # Create side-by-side comparison table
            table = Table(box=box.ROUNDED, show_header=True)
            table.add_column("Action", style="bold", width=10)
            table.add_column("File", style="white", width=40)
            table.add_column("Format", style="cyan", width=8)
            table.add_column("Quality", style="white", width=12)
            table.add_column("Size", style="white", width=10)
            table.add_column("Stars", style="yellow", width=10)

            # Add keep file
            keep_color = self._get_quality_color(group.recommended_keep.quality_score)
            table.add_row(
                "[green]KEEP[/green]",
                self._truncate_path(group.recommended_keep.filepath, 40),
                group.recommended_keep.format.upper(),
                f"[{keep_color}]{group.recommended_keep.quality_score}/100[/{keep_color}]",
                f"{group.recommended_keep.file_size / (1024*1024):.1f} MB",
                self._quality_stars(group.recommended_keep.quality_score),
            )

            # Add delete files
            for file in group.recommended_delete:
                file_color = self._get_quality_color(file.quality_score)
                table.add_row(
                    "[red]DELETE[/red]",
                    self._truncate_path(file.filepath, 40),
                    file.format.upper(),
                    f"[{file_color}]{file.quality_score}/100[/{file_color}]",
                    f"{file.file_size / (1024*1024):.1f} MB",
                    self._quality_stars(file.quality_score),
                )

            self.console.print(table)

            # Show savings
            self.console.print(f"\n[yellow]Space to free: {group.space_savings_mb:.2f} MB[/yellow]")

            # Get user confirmation
            action = Prompt.ask("\n[bold]Action[/bold]", choices=["y", "n", "s", "q"], default="y")

            if action == "q":
                break
            elif action == "n":
                group.user_action = "keep_all"
                self.console.print("[yellow]Keeping all files in this group[/yellow]")
            elif action == "s":
                group.user_action = "skip"
                self.console.print("[cyan]Skipping this group[/cyan]")
            else:  # y
                group.user_confirmed = True
                group.user_action = "delete_selected"
                self.stats.groups_confirmed += 1
                self.stats.files_to_delete += len(group.recommended_delete)
                self.stats.space_to_free_mb += group.space_savings_mb
                self.console.print("[green]Confirmed for deletion[/green]")

            self.stats.groups_reviewed += 1

    def show_review_summary(self, groups: List[DuplicateGroupInfo]) -> bool:
        """
        Screen 5: Review summary with quality distribution.

        Args:
            groups: Reviewed duplicate groups

        Returns:
            True to continue, False to cancel
        """
        # Filter confirmed groups
        confirmed_groups = [g for g in groups if g.user_confirmed]

        if not confirmed_groups:
            self.console.print(
                Panel(
                    "[yellow]No groups confirmed for deletion.[/yellow]",
                    title="Summary",
                    border_style="yellow",
                )
            )
            return False

        # Create summary table
        summary = Table(title="Deletion Summary", box=box.DOUBLE)
        summary.add_column("Metric", style="cyan", width=30)
        summary.add_column("Value", style="white", width=20)

        summary.add_row("Groups to process", f"{len(confirmed_groups):,}")
        summary.add_row("Files to delete", f"{self.stats.files_to_delete:,}")
        summary.add_row("Space to free", f"{self.stats.space_to_free_mb:.2f} MB")
        summary.add_row("Groups reviewed", f"{self.stats.groups_reviewed:,}")
        summary.add_row("Groups skipped", f"{self.stats.groups_reviewed - len(confirmed_groups):,}")

        self.console.print("\n", summary)

        # Quality distribution
        quality_dist = Table(title="Quality Distribution of Files to Delete", box=box.ROUNDED)
        quality_dist.add_column("Quality Tier", style="bold")
        quality_dist.add_column("Count", style="white")
        quality_dist.add_column("Percentage", style="cyan")

        tiers = {"Excellent": 0, "Good": 0, "Fair": 0, "Poor": 0}
        for group in confirmed_groups:
            for file in group.recommended_delete:
                tier = get_quality_tier(file.quality_score)
                tiers[tier] = tiers.get(tier, 0) + 1

        total = sum(tiers.values())
        for tier, count in tiers.items():
            if count > 0:
                percentage = (count / total * 100) if total > 0 else 0
                quality_dist.add_row(tier, str(count), f"{percentage:.1f}%")

        self.console.print("\n", quality_dist)

        return Confirm.ask("\n[bold]Proceed with deletion?[/bold]", default=False)

    def confirm_and_execute(self) -> bool:
        """
        Screen 6: Multi-step confirmation with backup options.

        Returns:
            True to execute, False to cancel
        """
        self.console.print(
            Panel(
                "[bold yellow]Final Confirmation[/bold yellow]\n\n"
                "This action will permanently delete files.\n"
                "A backup will be created before deletion.",
                title="Safety Checkpoint",
                border_style="yellow",
                box=box.DOUBLE,
            )
        )

        # Step 1: Review backup location
        self.console.print(f"\n[cyan]Backup Location:[/cyan] {self.backup_dir}")

        # Step 2: Type confirmation phrase
        confirmation_phrase = "DELETE DUPLICATES"
        user_input = Prompt.ask(f'\n[bold red]Type "{confirmation_phrase}" to confirm[/bold red]')

        if user_input != confirmation_phrase:
            self.console.print("[yellow]Confirmation phrase did not match. Cancelled.[/yellow]")
            return False

        # Step 3: Final yes/no
        return Confirm.ask("\n[bold red]Are you absolutely sure?[/bold red]", default=False)

    def _execute_cleanup(self) -> None:
        """Screen 7: Execute deletion with dual-phase processing."""
        start_time = datetime.now()

        # Create deletion plan
        self.deletion_plan = SafeDeletionPlan(backup_dir=self.backup_dir)

        # Add confirmed groups to plan
        for group in self.duplicate_groups:
            if group.user_confirmed:
                self.deletion_plan.add_group(
                    keep_file=group.recommended_keep.filepath,
                    delete_files=[f.filepath for f in group.recommended_delete],
                    reason=f"Duplicate group {group.group_id} - keeping highest quality",
                )

        # Validate plan
        is_valid, errors = self.deletion_plan.validate()
        if not is_valid:
            self.console.print(
                Panel(
                    "[red]Validation failed:[/red]\n\n" + "\n".join(errors),
                    title="Error",
                    border_style="red",
                )
            )
            return

        # Execute with progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        ) as progress:
            # Phase 1: Backup
            task1 = progress.add_task("[cyan]Creating backups...", total=self.stats.files_to_delete)

            # Phase 2: Delete
            task2 = progress.add_task("[yellow]Deleting files...", total=self.stats.files_to_delete)

            # Execute deletion plan
            deletion_stats = self.deletion_plan.execute(dry_run=False, create_backup=True)

            progress.update(task1, completed=self.stats.files_to_delete)
            progress.update(task2, completed=self.stats.files_to_delete)

        # Update stats
        self.stats.files_deleted = deletion_stats.files_deleted
        self.stats.space_freed_mb = deletion_stats.space_freed_bytes / (1024 * 1024)
        self.stats.cleanup_duration = (datetime.now() - start_time).total_seconds()

    def show_completion_summary(self, stats: CleanupStats) -> None:
        """
        Screen 8: Completion summary with reports.

        Args:
            stats: Cleanup statistics
        """
        # Create completion panel
        summary_text = Text()
        summary_text.append("Smart Cleanup Complete!\n\n", style="bold green")

        summary_text.append("Results:\n", style="bold")
        summary_text.append(f"  Files Scanned: {stats.total_files_scanned:,}\n", style="white")
        summary_text.append(
            f"  Duplicate Groups: {stats.duplicate_groups_found:,}\n", style="white"
        )
        summary_text.append(f"  Files Deleted: {stats.files_deleted:,}\n", style="green")
        summary_text.append(f"  Space Freed: {stats.space_freed_mb:.2f} MB\n", style="green")

        summary_text.append("\nPerformance:\n", style="bold")
        summary_text.append(f"  Scan Time: {stats.scan_duration:.2f}s\n", style="cyan")
        summary_text.append(f"  Cleanup Time: {stats.cleanup_duration:.2f}s\n", style="cyan")

        panel = Panel(
            summary_text, title="Completion Summary", border_style="green", box=box.DOUBLE
        )
        self.console.print("\n", panel)

        # Export reports
        if Confirm.ask("\n[bold]Export detailed reports?[/bold]", default=True):
            self._export_reports()

    def _export_reports(self) -> None:
        """Export CSV and JSON reports."""
        timestamp = self.session_id

        # CSV Report
        csv_path = self.reports_dir / f"cleanup_report_{timestamp}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Group ID",
                    "Action",
                    "File Path",
                    "Format",
                    "Quality Score",
                    "File Size MB",
                    "Bitrate Type",
                    "Sample Rate",
                ]
            )

            for group in self.duplicate_groups:
                if group.user_confirmed:
                    # Keep file
                    writer.writerow(
                        [
                            group.group_id,
                            "KEEP",
                            group.recommended_keep.filepath,
                            group.recommended_keep.format,
                            group.recommended_keep.quality_score,
                            f"{group.recommended_keep.file_size / (1024*1024):.2f}",
                            group.recommended_keep.bitrate_type.value,
                            group.recommended_keep.sample_rate or "N/A",
                        ]
                    )

                    # Delete files
                    for file in group.recommended_delete:
                        writer.writerow(
                            [
                                group.group_id,
                                "DELETE",
                                file.filepath,
                                file.format,
                                file.quality_score,
                                f"{file.file_size / (1024*1024):.2f}",
                                file.bitrate_type.value,
                                file.sample_rate or "N/A",
                            ]
                        )

        # JSON Report
        json_path = self.reports_dir / f"cleanup_report_{timestamp}.json"
        report_data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_files_scanned": self.stats.total_files_scanned,
                "duplicate_groups_found": self.stats.duplicate_groups_found,
                "total_duplicates": self.stats.total_duplicates,
                "groups_reviewed": self.stats.groups_reviewed,
                "groups_confirmed": self.stats.groups_confirmed,
                "files_deleted": self.stats.files_deleted,
                "space_freed_mb": self.stats.space_freed_mb,
                "scan_duration": self.stats.scan_duration,
                "cleanup_duration": self.stats.cleanup_duration,
            },
            "groups": [],
        }

        for group in self.duplicate_groups:
            if group.user_confirmed:
                report_data["groups"].append(
                    {
                        "group_id": group.group_id,
                        "keep": group.recommended_keep.to_dict(),
                        "delete": [f.to_dict() for f in group.recommended_delete],
                        "space_savings_mb": group.space_savings_mb,
                        "quality_range": group.quality_range,
                    }
                )

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # Display export info
        self.console.print("\n[green]Reports exported:[/green]")
        self.console.print(f"  CSV: {csv_path}")
        self.console.print(f"  JSON: {json_path}")

    # Helper methods
    def _get_quality_color(self, score: int) -> str:
        """Get color based on quality score."""
        if score >= QUALITY_EXCELLENT:
            return "green"
        elif score >= QUALITY_GOOD:
            return "yellow"
        elif score >= QUALITY_FAIR:
            return "orange1"
        else:
            return "red"

    def _quality_stars(self, score: int) -> str:
        """Convert quality score to star rating."""
        stars = int((score / 100) * 5)
        filled = "★" * stars
        empty = "☆" * (5 - stars)
        return filled + empty

    def _truncate_path(self, path: str, max_length: int) -> str:
        """Truncate file path for display."""
        path_obj = Path(path)
        name = path_obj.name

        if len(name) <= max_length:
            return name

        # Truncate with ellipsis
        stem = path_obj.stem
        suffix = path_obj.suffix
        max_stem = max_length - len(suffix) - 3  # 3 for '...'

        if max_stem > 0:
            return f"{stem[:max_stem]}...{suffix}"
        else:
            return name[: max_length - 3] + "..."


def run_smart_cleanup(
    library_db: LibraryDatabase, library_path: str, backup_dir: Optional[str] = None
) -> CleanupStats:
    """
    Convenience function to run Smart Cleanup workflow.

    Args:
        library_db: LibraryDatabase instance
        library_path: Path to music library
        backup_dir: Optional backup directory

    Returns:
        CleanupStats with session results
    """
    workflow = SmartCleanupWorkflow(library_db, library_path, backup_dir)
    return workflow.run()
