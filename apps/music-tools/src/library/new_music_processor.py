"""
New Music Processor - Unified workflow for processing new music folders.

Combines duplicate checking against library and candidate history checking
into a single, streamlined workflow.

Author: Music Tools Dev Team
Created: 2026-01-26
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .candidate_manager import CandidateManager
from .database import LibraryDatabase
from .vetter import ImportVetter

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Results from processing a new music folder."""

    total_files: int = 0
    duplicates: List[str] = None  # Files already in library
    already_reviewed: List[str] = None  # Files in history
    truly_new: List[str] = None  # Files that need attention

    def __post_init__(self):
        if self.duplicates is None:
            self.duplicates = []
        if self.already_reviewed is None:
            self.already_reviewed = []
        if self.truly_new is None:
            self.truly_new = []


class NewMusicProcessor:
    """
    Unified processor for new music folders.

    Combines library duplicate checking and candidate history checking
    into a single workflow with clear categorization.
    """

    def __init__(self, library_db: LibraryDatabase, console: Console = None):
        """
        Initialize the processor.

        Args:
            library_db: LibraryDatabase instance for duplicate checking
            console: Optional Rich console for output
        """
        self.library_db = library_db
        self.console = console or Console()
        self.vetter = ImportVetter(library_db, console=console)
        self.candidate_manager = CandidateManager()

    def process_folder(self, folder_path: str, threshold: float = 0.8) -> ProcessingResult:
        """
        Process a new music folder against library and history.

        Args:
            folder_path: Path to folder containing new music
            threshold: Similarity threshold for duplicate detection (0.0-1.0)

        Returns:
            ProcessingResult with categorized files
        """
        result = ProcessingResult()

        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        # Step 1: Check against library
        self.console.print("\n[cyan]Step 1/2: Checking against library index...[/cyan]")
        vet_report = self.vetter.vet_folder(
            import_folder=str(folder), threshold=threshold, show_progress=True
        )

        # Step 2: Check against history
        self.console.print("\n[cyan]Step 2/2: Checking against listening history...[/cyan]")
        history_matches = self.candidate_manager.check_folder(str(folder))

        # Categorize files
        result.total_files = vet_report.total_files

        # Duplicates (already in library)
        for file_path, dup_result in vet_report.duplicates:
            result.duplicates.append(file_path)

        # Already reviewed (in history but not necessarily in library)
        history_files = {match["path"] for match in history_matches}
        duplicate_files = set(result.duplicates)

        for hist_file in history_files:
            if hist_file not in duplicate_files:
                result.already_reviewed.append(hist_file)

        # Truly new (not in library AND not in history)
        for new_song in vet_report.new_songs:
            if new_song not in history_files:
                result.truly_new.append(new_song)

        return result

    def display_results(self, result: ProcessingResult) -> None:
        """
        Display processing results in a clear, actionable format.

        Args:
            result: ProcessingResult to display
        """
        # Create summary table
        summary = Table(title="Processing Results", show_header=True)
        summary.add_column("Category", style="bold", width=20)
        summary.add_column("Count", style="cyan", justify="right", width=10)
        summary.add_column("Description", style="white", width=50)

        summary.add_row("📊 Total Files", str(result.total_files), "Total audio files scanned")
        summary.add_row("🔴 Duplicates", str(len(result.duplicates)), "Already in your library")
        summary.add_row(
            "🟡 Reviewed", str(len(result.already_reviewed)), "You've listened to before"
        )
        summary.add_row("🟢 New", str(len(result.truly_new)), "Require your attention")

        self.console.print("\n", summary)

        # Show percentages
        if result.total_files > 0:
            dup_pct = (len(result.duplicates) / result.total_files) * 100
            rev_pct = (len(result.already_reviewed) / result.total_files) * 100
            new_pct = (len(result.truly_new) / result.total_files) * 100

            self.console.print(
                f"\n[dim]Breakdown: {dup_pct:.1f}% duplicates | "
                f"{rev_pct:.1f}% reviewed | {new_pct:.1f}% new[/dim]"
            )

    def export_new_songs(self, result: ProcessingResult, folder_path: str) -> str:
        """
        Export list of truly new songs to a text file.

        Args:
            result: ProcessingResult with new songs
            folder_path: Folder where the export file will be saved

        Returns:
            Path to the exported file
        """
        export_path = Path(folder_path) / "new_songs.txt"

        with open(export_path, "w", encoding="utf-8") as f:
            f.write(f"New Songs to Review ({len(result.truly_new)} files)\n")
            f.write("=" * 60 + "\n\n")

            for song_path in sorted(result.truly_new):
                song_name = Path(song_path).name
                f.write(f"{song_name}\n")

        return str(export_path)

    def interactive_cleanup(self, result: ProcessingResult, folder_path: str) -> Tuple[int, int]:
        """
        Interactive cleanup workflow for duplicates and reviewed files.

        Args:
            result: ProcessingResult with categorized files
            folder_path: Base folder path

        Returns:
            Tuple of (duplicates_deleted, reviewed_deleted)
        """

        duplicates_deleted = 0
        reviewed_deleted = 0
        trash_dir = Path.home() / ".Trash"

        # Handle duplicates
        if result.duplicates:
            self.console.print(f"\n[yellow]Found {len(result.duplicates)} duplicate files[/yellow]")
            action = Prompt.ask(
                "Delete duplicates?", choices=["yes", "no", "review"], default="review"
            )

            if action == "yes":
                for dup_file in result.duplicates:
                    try:
                        self._move_to_trash(dup_file, trash_dir)
                        duplicates_deleted += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {dup_file}: {e}")

                self.console.print(f"[green]✓ Deleted {duplicates_deleted} duplicates[/green]")

            elif action == "review":
                for dup_file in result.duplicates:
                    self.console.print(f"\n[bold]{Path(dup_file).name}[/bold]")
                    if Confirm.ask("Delete this file?", default=False):
                        try:
                            self._move_to_trash(dup_file, trash_dir)
                            duplicates_deleted += 1
                        except Exception as e:
                            logger.error(f"Failed to delete {dup_file}: {e}")

        # Handle already reviewed
        if result.already_reviewed:
            self.console.print(
                f"\n[yellow]Found {len(result.already_reviewed)} previously reviewed files[/yellow]"
            )
            action = Prompt.ask(
                "Delete reviewed files?", choices=["yes", "no", "review"], default="no"
            )

            if action == "yes":
                for rev_file in result.already_reviewed:
                    try:
                        self._move_to_trash(rev_file, trash_dir)
                        reviewed_deleted += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {rev_file}: {e}")

                self.console.print(f"[green]✓ Deleted {reviewed_deleted} reviewed files[/green]")

            elif action == "review":
                for rev_file in result.already_reviewed:
                    self.console.print(f"\n[bold]{Path(rev_file).name}[/bold]")
                    if Confirm.ask("Delete this file?", default=False):
                        try:
                            self._move_to_trash(rev_file, trash_dir)
                            reviewed_deleted += 1
                        except Exception as e:
                            logger.error(f"Failed to delete {rev_file}: {e}")

        return duplicates_deleted, reviewed_deleted

    def _move_to_trash(self, file_path: str, trash_dir: Path) -> None:
        """
        Move a file to the trash.

        Args:
            file_path: Path to file to delete
            trash_dir: Trash directory path
        """
        import shutil
        from datetime import datetime

        trash_dir.mkdir(exist_ok=True)

        source = Path(file_path)
        destination = trash_dir / source.name

        # Handle duplicate names in trash
        if destination.exists():
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            destination = trash_dir / f"{source.stem}_{timestamp}{source.suffix}"

        shutil.move(str(source), str(destination))
