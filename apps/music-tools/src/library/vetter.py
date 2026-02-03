"""
Import vetting workflow for checking new music against library.

Provides automated duplicate detection and categorization for import folders.
"""

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from .database import LibraryDatabase
from .duplicate_checker import DuplicateChecker
from .models import DuplicateResult, VettingReport

logger = logging.getLogger(__name__)

# Constants
SUPPORTED_AUDIO_FORMATS: Set[str] = {'.mp3', '.flac', '.m4a', '.wav', '.ogg', '.opus'}
DEFAULT_FUZZY_THRESHOLD: float = 0.8
MIN_FUZZY_THRESHOLD: float = 0.0
MAX_FUZZY_THRESHOLD: float = 1.0
DEFAULT_MAX_DISPLAY: int = 10  # Default max items to display in lists
MIN_MAX_DISPLAY: int = 1
MAX_MAX_DISPLAY: int = 100


class ImportVetter:
    """Vets import folders against indexed library for duplicates."""

    SUPPORTED_FORMATS: Set[str] = SUPPORTED_AUDIO_FORMATS

    def __init__(
        self,
        library_db: LibraryDatabase,
        console: Optional[Console] = None
    ):
        """Initialize import vetter.

        Args:
            library_db: LibraryDatabase instance. Must not be None.
            console: Optional Rich console for output. If None, creates new Console.

        Raises:
            ValueError: If library_db is None.
        """
        if library_db is None:
            raise ValueError("library_db cannot be None")

        self.db = library_db
        self.checker = DuplicateChecker(library_db)
        self.console = console or Console()

    def vet_folder(
        self,
        import_folder: str,
        threshold: float = DEFAULT_FUZZY_THRESHOLD,
        use_fuzzy: bool = True,
        use_content_hash: bool = True,
        show_progress: bool = True,
        auto_skip_duplicates: bool = False
    ) -> VettingReport:
        """Vet an import folder for duplicates.

        Args:
            import_folder: Path to folder with new music. Must exist and be a directory.
            threshold: Similarity threshold for fuzzy matching.
                      Must be between 0.0 and 1.0. Default 0.8.
            use_fuzzy: If True, perform fuzzy metadata matching. Default True.
            use_content_hash: If True, check file content hash. Default True.
            show_progress: If True, show progress bar. Default True.
            auto_skip_duplicates: If True, automatically skip certain duplicates. Default False.

        Returns:
            VettingReport with categorized results. Never None.

        Raises:
            ValueError: If import_folder is None/empty or threshold is out of range.
            FileNotFoundError: If import_folder does not exist.
            NotADirectoryError: If import_folder is not a directory.
        """
        # Input validation
        if not import_folder:
            raise ValueError("import_folder cannot be None or empty")

        if not MIN_FUZZY_THRESHOLD <= threshold <= MAX_FUZZY_THRESHOLD:
            raise ValueError(
                f"threshold must be between {MIN_FUZZY_THRESHOLD} and {MAX_FUZZY_THRESHOLD}, "
                f"got {threshold}"
            )
        start_time = time.time()
        import_folder = Path(import_folder).resolve()

        if not import_folder.exists():
            raise FileNotFoundError(f"Import folder does not exist: {import_folder}")

        if not import_folder.is_dir():
            raise NotADirectoryError(f"Import folder is not a directory: {import_folder}")

        self.console.print(f"\n[bold cyan]Vetting import folder:[/bold cyan] {import_folder}")

        # Scan for music files
        music_files = self._scan_import_folder(import_folder)
        total_files = len(music_files)

        self.console.print(f"Found [bold]{total_files}[/bold] music files to vet")

        if total_files == 0:
            self.console.print("[yellow]No music files found[/yellow]")
            return VettingReport(
                import_folder=str(import_folder),
                total_files=0,
                threshold=threshold,
                duplicates=[],
                new_songs=[],
                uncertain=[]
            )

        # Check each file
        results = []

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task("Vetting files...", total=total_files)

                for file_path in music_files:
                    try:
                        result = self.checker.check_file(
                            str(file_path),
                            fuzzy_threshold=threshold,
                            use_fuzzy=use_fuzzy,
                            use_content_hash=use_content_hash
                        )
                        results.append((str(file_path), result))

                    except Exception as e:
                        self.console.print(f"[red]Error checking {file_path}: {e}[/red]")

                    progress.advance(task)
        else:
            for file_path in music_files:
                try:
                    result = self.checker.check_file(
                        str(file_path),
                        fuzzy_threshold=threshold,
                        use_fuzzy=use_fuzzy,
                        use_content_hash=use_content_hash
                    )
                    results.append((str(file_path), result))

                except Exception as e:
                    self.console.print(f"[red]Error checking {file_path}: {e}[/red]")

        # Categorize results
        duplicates, new_songs, uncertain = self._categorize_results(results, threshold)

        # Calculate duration
        duration = time.time() - start_time

        # Create report
        report = VettingReport(
            import_folder=str(import_folder),
            total_files=total_files,
            threshold=threshold,
            duplicates=duplicates,
            new_songs=new_songs,
            uncertain=uncertain,
            scan_duration=duration,
            vetted_at=datetime.now(timezone.utc)
        )

        # Display report
        self.display_report(report)

        # Save to history with error handling
        try:
            self.db.save_vetting_result(
                import_folder=str(import_folder),
                total_files=total_files,
                duplicates_found=len(duplicates),
                new_songs=len(new_songs),
                uncertain_matches=len(uncertain),
                threshold_used=threshold
            )
        except Exception as e:
            logger.error(f"Failed to save vetting result to database: {e}")
            self.console.print(f"[yellow]Warning: Could not save vetting history: {e}[/yellow]")

        return report

    def _scan_import_folder(self, folder: Path) -> List[Path]:
        """Scan import folder for music files.

        Args:
            folder: Path to import folder. Must not be None.

        Returns:
            Sorted list of music file paths with supported formats.
            Empty list if no music files found.

        Note:
            Only scans for files with extensions in SUPPORTED_FORMATS.
        """
        if folder is None:
            logger.error("_scan_import_folder called with None folder")
            return []
        music_files = []

        for root, _, files in os.walk(folder):
            for filename in files:
                file_path = Path(root) / filename

                if file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                    music_files.append(file_path)

        return sorted(music_files)

    def _categorize_results(
        self,
        results: List[Tuple[str, DuplicateResult]],
        threshold: float
    ) -> Tuple[List[Tuple[str, DuplicateResult]], List[str], List[Tuple[str, DuplicateResult]]]:
        """Categorize vetting results into duplicates, new songs, and uncertain.

        Args:
            results: List of (file_path, DuplicateResult) tuples. Must not be None.
            threshold: Similarity threshold used. Must be between 0.0 and 1.0.

        Returns:
            Tuple of (duplicates, new_songs, uncertain) lists where:
            - duplicates: List of (file_path, DuplicateResult) tuples
            - new_songs: List of file_path strings
            - uncertain: List of (file_path, DuplicateResult) tuples

        Note:
            Returns empty lists if results is None or empty.
        """
        if results is None:
            logger.warning("_categorize_results called with None results")
            return [], [], []
        duplicates = []
        new_songs = []
        uncertain = []

        for file_path, result in results:
            # Check uncertain first (has priority over duplicate)
            if result.is_uncertain:
                # Uncertain match (between 0.7 and threshold)
                uncertain.append((file_path, result))
            elif result.is_duplicate:
                # High confidence duplicate
                duplicates.append((file_path, result))
            else:
                # New song (no match or very low confidence)
                new_songs.append(file_path)

        return duplicates, new_songs, uncertain

    def display_report(self, report: VettingReport) -> None:
        """Display vetting report with Rich formatting.

        Args:
            report: VettingReport to display. Must not be None.

        Note:
            Displays summary, results table, duplicate details, uncertain matches,
            and next steps using Rich formatting.
        """
        if report is None:
            logger.error("display_report called with None report")
            return
        self.console.print()

        # Summary panel
        summary = f"""
[bold]Import Folder:[/bold] {report.import_folder}
[bold]Total Files:[/bold] {report.total_files}
[bold]Threshold:[/bold] {report.threshold:.0%}
[bold]Scan Duration:[/bold] {report.scan_duration:.2f}s
        """

        self.console.print(Panel(summary.strip(), title="Vetting Summary", border_style="cyan"))

        # Results table
        table = Table(title="Results")

        table.add_column("Category", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_column("Percentage", style="yellow", justify="right")

        table.add_row(
            "✅ New Songs",
            str(report.new_count),
            f"{report.new_percentage:.1f}%"
        )

        table.add_row(
            "❌ Duplicates",
            f"[red]{report.duplicate_count}[/red]",
            f"[red]{report.duplicate_percentage:.1f}%[/red]"
        )

        if report.uncertain_count > 0:
            # Calculate percentage safely (avoid division by zero)
            uncertain_pct = (report.uncertain_count / report.total_files * 100) if report.total_files > 0 else 0.0
            table.add_row(
                "⚠️  Uncertain",
                f"[yellow]{report.uncertain_count}[/yellow]",
                f"[yellow]{uncertain_pct:.1f}%[/yellow]"
            )

        self.console.print()
        self.console.print(table)

        # Details
        if report.duplicate_count > 0:
            self._display_duplicates(report.duplicates)

        if report.uncertain_count > 0:
            self._display_uncertain(report.uncertain)

        # Next steps
        self._display_next_steps(report)

    def _display_duplicates(
        self,
        duplicates: List[Tuple[str, DuplicateResult]],
        max_display: int = DEFAULT_MAX_DISPLAY
    ) -> None:
        """Display duplicate files.

        Args:
            duplicates: List of (file_path, DuplicateResult) tuples. Must not be None.
            max_display: Maximum number to display. Must be between 1 and 100. Default 10.

        Note:
            Displays duplicates in a Rich tree format with match details.
        """
        if duplicates is None:
            logger.error("_display_duplicates called with None duplicates")
            return

        if not MIN_MAX_DISPLAY <= max_display <= MAX_MAX_DISPLAY:
            logger.warning(
                f"max_display {max_display} out of range, using default {DEFAULT_MAX_DISPLAY}"
            )
            max_display = DEFAULT_MAX_DISPLAY
        self.console.print()
        self.console.print(f"[bold red]Duplicates Found ({len(duplicates)}):[/bold red]")

        tree = Tree("🔴 Duplicate Files")

        for i, (file_path, result) in enumerate(duplicates[:max_display]):
            file_name = Path(file_path).name
            matched_name = result.matched_file.display_name if result.matched_file else "Unknown"

            node = tree.add(f"[red]{file_name}[/red]")
            node.add(f"Match: {matched_name}")
            node.add(f"Confidence: {result.confidence:.0%}")
            node.add(f"Type: {result.match_type}")

        if len(duplicates) > max_display:
            tree.add(f"[dim]... and {len(duplicates) - max_display} more[/dim]")

        self.console.print(tree)

    def _display_uncertain(
        self,
        uncertain: List[Tuple[str, DuplicateResult]],
        max_display: int = DEFAULT_MAX_DISPLAY
    ) -> None:
        """Display uncertain matches.

        Args:
            uncertain: List of (file_path, DuplicateResult) tuples. Must not be None.
            max_display: Maximum number to display. Must be between 1 and 100. Default 10.

        Note:
            Displays uncertain matches in a Rich tree format suggesting manual review.
        """
        if uncertain is None:
            logger.error("_display_uncertain called with None uncertain")
            return

        if not MIN_MAX_DISPLAY <= max_display <= MAX_MAX_DISPLAY:
            logger.warning(
                f"max_display {max_display} out of range, using default {DEFAULT_MAX_DISPLAY}"
            )
            max_display = DEFAULT_MAX_DISPLAY
        self.console.print()
        self.console.print(f"[bold yellow]Uncertain Matches ({len(uncertain)}):[/bold yellow]")

        tree = Tree("⚠️  Uncertain Files (Manual Review Suggested)")

        for i, (file_path, result) in enumerate(uncertain[:max_display]):
            file_name = Path(file_path).name
            matched_name = result.matched_file.display_name if result.matched_file else "Unknown"

            node = tree.add(f"[yellow]{file_name}[/yellow]")
            node.add(f"Possible Match: {matched_name}")
            node.add(f"Confidence: {result.confidence:.0%}")

        if len(uncertain) > max_display:
            tree.add(f"[dim]... and {len(uncertain) - max_display} more[/dim]")

        self.console.print(tree)

    def _display_next_steps(self, report: VettingReport) -> None:
        """Display suggested next steps.

        Args:
            report: VettingReport with results. Must not be None.

        Note:
            Suggests actions based on categorized results.
        """
        if report is None:
            logger.error("_display_next_steps called with None report")
            return
        self.console.print()
        self.console.print("[bold cyan]Next Steps:[/bold cyan]")

        if report.new_count > 0:
            self.console.print(f"  ✅ Import {report.new_count} new songs to your library")

        if report.duplicate_count > 0:
            self.console.print(f"  ❌ Skip or delete {report.duplicate_count} duplicates")

        if report.uncertain_count > 0:
            self.console.print(f"  ⚠️  Manually review {report.uncertain_count} uncertain matches")

    def export_new_songs(self, report: VettingReport, output_file: str) -> None:
        """Export list of new songs to file.

        Args:
            report: VettingReport with results. Must not be None.
            output_file: Path to output file. Must not be None or empty.

        Raises:
            ValueError: If report or output_file is None/empty.
            PermissionError: If cannot write to output directory.
            IOError: If file cannot be written.
        """
        if report is None:
            raise ValueError("report cannot be None")
        if not output_file:
            raise ValueError("output_file cannot be None or empty")

        # Check write permission before attempting to write
        output_path = Path(output_file)
        if not os.access(output_path.parent, os.W_OK):
            raise PermissionError(f"Cannot write to directory: {output_path.parent}")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# New Songs from {report.import_folder}\n")
            f.write(f"# Generated: {report.vetted_at}\n")
            f.write(f"# Total: {report.new_count}\n\n")

            for file_path in report.new_songs:
                f.write(f"{file_path}\n")

        self.console.print(f"[green]Exported {report.new_count} new songs to {output_file}[/green]")

    def export_duplicates(self, report: VettingReport, output_file: str) -> None:
        """Export list of duplicates to file.

        Args:
            report: VettingReport with results. Must not be None.
            output_file: Path to output file. Must not be None or empty.

        Raises:
            ValueError: If report or output_file is None/empty.
            PermissionError: If cannot write to output directory.
            IOError: If file cannot be written.
        """
        if report is None:
            raise ValueError("report cannot be None")
        if not output_file:
            raise ValueError("output_file cannot be None or empty")

        # Check write permission before attempting to write
        output_path = Path(output_file)
        if not os.access(output_path.parent, os.W_OK):
            raise PermissionError(f"Cannot write to directory: {output_path.parent}")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Duplicates from {report.import_folder}\n")
            f.write(f"# Generated: {report.vetted_at}\n")
            f.write(f"# Total: {report.duplicate_count}\n\n")

            for file_path, result in report.duplicates:
                matched_name = result.matched_file.display_name if result.matched_file else "Unknown"
                f.write(f"{file_path}\n")
                f.write(f"  → Matches: {matched_name}\n")
                f.write(f"  → Confidence: {result.confidence:.0%}\n")
                f.write(f"  → Type: {result.match_type}\n\n")

        self.console.print(f"[green]Exported {report.duplicate_count} duplicates to {output_file}[/green]")

    def export_uncertain(self, report: VettingReport, output_file: str) -> None:
        """Export list of uncertain matches to file.

        Args:
            report: VettingReport with results. Must not be None.
            output_file: Path to output file. Must not be None or empty.

        Raises:
            ValueError: If report or output_file is None/empty.
            PermissionError: If cannot write to output directory.
            IOError: If file cannot be written.
        """
        if report is None:
            raise ValueError("report cannot be None")
        if not output_file:
            raise ValueError("output_file cannot be None or empty")

        # Check write permission before attempting to write
        output_path = Path(output_file)
        if not os.access(output_path.parent, os.W_OK):
            raise PermissionError(f"Cannot write to directory: {output_path.parent}")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Uncertain Matches from {report.import_folder}\n")
            f.write(f"# Generated: {report.vetted_at}\n")
            f.write(f"# Total: {report.uncertain_count}\n\n")

            for file_path, result in report.uncertain:
                matched_name = result.matched_file.display_name if result.matched_file else "Unknown"
                f.write(f"{file_path}\n")
                f.write(f"  → Possible Match: {matched_name}\n")
                f.write(f"  → Confidence: {result.confidence:.0%}\n\n")

        self.console.print(f"[green]Exported {report.uncertain_count} uncertain matches to {output_file}[/green]")

    def get_vetting_history(self, limit: int = 10) -> None:
        """Get recent vetting history.

        Args:
            limit: Maximum number of records to return. Must be between 1 and 1000.
                  Default 10.

        Note:
            Displays vetting history in a Rich table. Prints message if no history found.
        """
        history = self.db.get_vetting_history(limit=limit)

        if not history:
            self.console.print("[yellow]No vetting history found[/yellow]")
            return

        table = Table(title="Vetting History")

        table.add_column("Date", style="cyan")
        table.add_column("Folder", style="green")
        table.add_column("Total", justify="right")
        table.add_column("New", style="green", justify="right")
        table.add_column("Duplicates", style="red", justify="right")
        table.add_column("Uncertain", style="yellow", justify="right")

        for record in history:
            vetted_at = datetime.fromisoformat(record['vetted_at'])
            folder_name = Path(record['import_folder']).name

            table.add_row(
                vetted_at.strftime("%Y-%m-%d %H:%M"),
                folder_name,
                str(record['total_files']),
                str(record['new_songs']),
                str(record['duplicates_found']),
                str(record['uncertain_matches'])
            )

        self.console.print()
        self.console.print(table)

    def delete_duplicates(
        self,
        report: VettingReport,
        confirm: bool = True,
        dry_run: bool = False
    ) -> Tuple[int, int]:
        """Delete duplicate files identified in vetting report.

        Args:
            report: VettingReport containing duplicates to delete. Must not be None.
            confirm: If True, show confirmation prompt before deleting. Default True.
            dry_run: If True, only show what would be deleted without actually deleting. Default False.

        Returns:
            Tuple of (deleted_count, failed_count) indicating success/failure counts.

        Raises:
            ValueError: If report is None.

        Note:
            Safety features:
            - Shows list of files to be deleted before proceeding
            - Requires explicit confirmation unless confirm=False
            - Dry run mode for testing
            - Detailed error reporting for failed deletions
            - Does not delete uncertain matches (manual review required)
        """
        if report is None:
            raise ValueError("report cannot be None")

        if report.duplicate_count == 0:
            self.console.print("[yellow]No duplicates to delete[/yellow]")
            return 0, 0

        # Show what will be deleted
        self.console.print()
        self.console.print(f"[bold red]{'DRY RUN: ' if dry_run else ''}Files to be deleted:[/bold red]")
        self.console.print(f"Total: {report.duplicate_count} duplicates\n")

        tree = Tree("🗑️  Files to Delete")
        for file_path, result in report.duplicates[:10]:  # Show first 10
            file_name = Path(file_path).name
            matched_name = result.matched_file.display_name if result.matched_file else "Unknown"
            node = tree.add(f"[red]{file_name}[/red]")
            node.add(f"Duplicate of: {matched_name}")
            node.add(f"Confidence: {result.confidence:.0%}")

        if report.duplicate_count > 10:
            tree.add(f"[dim]... and {report.duplicate_count - 10} more[/dim]")

        self.console.print(tree)
        self.console.print()

        # Confirmation prompt
        if confirm and not dry_run:
            self.console.print("[bold yellow]⚠️  WARNING: This action cannot be undone![/bold yellow]")
            response = input(f"\nDelete {report.duplicate_count} duplicate files? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                self.console.print("[yellow]Deletion cancelled[/yellow]")
                return 0, 0

        # Delete files
        deleted_count = 0
        failed_count = 0
        failed_files = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(
                f"{'[DRY RUN] Simulating deletion' if dry_run else 'Deleting duplicates'}...",
                total=report.duplicate_count
            )

            for file_path, result in report.duplicates:
                try:
                    if not dry_run:
                        file_obj = Path(file_path)
                        if file_obj.exists():
                            file_obj.unlink()
                            deleted_count += 1
                        else:
                            logger.warning(f"File not found (already deleted?): {file_path}")
                            failed_count += 1
                            failed_files.append((file_path, "File not found"))
                    else:
                        # Dry run - just verify file exists
                        if Path(file_path).exists():
                            deleted_count += 1
                        else:
                            failed_count += 1
                            failed_files.append((file_path, "File not found"))

                except PermissionError as e:
                    logger.error(f"Permission denied deleting {file_path}: {e}")
                    failed_count += 1
                    failed_files.append((file_path, "Permission denied"))
                except Exception as e:
                    logger.error(f"Error deleting {file_path}: {e}")
                    failed_count += 1
                    failed_files.append((file_path, str(e)))

                progress.advance(task)

        # Display results
        self.console.print()
        if dry_run:
            self.console.print("[bold cyan]DRY RUN RESULTS:[/bold cyan]")
            self.console.print(f"  ✓ Would delete: {deleted_count} files")
            if failed_count > 0:
                self.console.print(f"  ✗ Would fail: {failed_count} files")
        else:
            if deleted_count > 0:
                self.console.print(f"[bold green]✓ Successfully deleted {deleted_count} duplicate files[/bold green]")
            if failed_count > 0:
                self.console.print(f"[bold red]✗ Failed to delete {failed_count} files[/bold red]")

        # Show failed files
        if failed_files:
            self.console.print("\n[bold red]Failed deletions:[/bold red]")
            for file_path, error in failed_files[:10]:
                self.console.print(f"  • {Path(file_path).name}: {error}")
            if len(failed_files) > 10:
                self.console.print(f"  ... and {len(failed_files) - 10} more")

        return deleted_count, failed_count
