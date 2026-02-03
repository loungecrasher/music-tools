"""
Candidate Manager logic.
Handles scanning folders, adding to history, and processing matches.
"""

import logging
import os
import shutil
from datetime import datetime
from typing import Dict, List

from rich.console import Console
from rich.prompt import Confirm, Prompt

from .history_db import HistoryDatabase

logger = logging.getLogger(__name__)
console = Console()


class CandidateManager:
    """
    Manages the workflow for candidate history.
    """

    def __init__(self):
        self.db = HistoryDatabase()

    def add_folder_to_history(self, folder_path: str) -> Dict[str, int]:
        """
        Scan a folder and add all files to history.

        Args:
            folder_path: Path to the folder to scan.

        Returns:
            Dictionary with stats: {'added': int, 'skipped': int, 'total': int}
        """
        stats = {"added": 0, "skipped": 0, "total": 0}

        if not os.path.exists(folder_path):
            logger.error(f"Folder not found: {folder_path}")
            return stats

        logger.info(f"Scanning folder: {folder_path}")

        for root, _, files in os.walk(folder_path):
            for file in files:
                # Skip hidden files
                if file.startswith("."):
                    continue

                # Only process audio files (optional, but good practice)
                if not file.lower().endswith((".mp3", ".flac", ".wav", ".m4a", ".aiff", ".ogg")):
                    continue

                stats["total"] += 1
                full_path = os.path.join(root, file)

                if self.db.add_file(file, full_path):
                    stats["added"] += 1
                    logger.debug(f"Added to history: {file}")
                else:
                    stats["skipped"] += 1
                    logger.debug(f"Already in history: {file}")

        return stats

    def check_folder(self, folder_path: str) -> List[Dict]:
        """
        Scan a folder and find files that are already in history.

        Args:
            folder_path: Path to the folder to check.

        Returns:
            List of matches: [{'file': str, 'path': str, 'added_at': datetime}]
        """
        matches = []

        if not os.path.exists(folder_path):
            logger.error(f"Folder not found: {folder_path}")
            return matches

        logger.info(f"Checking folder against history: {folder_path}")

        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.startswith("."):
                    continue

                added_at = self.db.check_file(file)
                if added_at:
                    matches.append(
                        {"file": file, "path": os.path.join(root, file), "added_at": added_at}
                    )

        return matches

    def process_matches(self, matches: List[Dict]) -> None:
        """
        Process found matches by prompting user to delete.

        Args:
            matches: List of match dictionaries.
        """
        if not matches:
            console.print("[green]No history matches found. Folder is clean![/green]")
            return

        console.print(f"\n[yellow]Found {len(matches)} files that are already in history:[/yellow]")

        trash_dir = os.path.expanduser("~/.Trash")
        # Ask for global action first
        console.print("\n[bold]Options:[/bold]")
        console.print("[red]d[/red]: Delete ALL found files immediately")
        console.print("[cyan]i[/cyan]: Review files individually")
        console.print("[bold]q[/bold]: Quit")

        action = Prompt.ask("Choose action", choices=["d", "i", "q"], default="i")

        if action == "q":
            console.print("[yellow]Aborted.[/yellow]")
            return

        delete_all = action == "d"

        for match in matches:
            file_name = match["file"]
            file_path = match["path"]
            added_at = match["added_at"]

            should_delete = False

            if delete_all:
                should_delete = True
                console.print(f"Deleting [bold]{file_name}[/bold]...")
            else:
                console.print(f"\n[bold]{file_name}[/bold]")
                console.print(f"  Path: {file_path}")
                console.print(f"  Previously listened on: {added_at}")

                choice = Prompt.ask(
                    f"Move '{file_name}' to Trash?", choices=["y", "n", "a", "q"], default="y"
                )

                if choice == "a":
                    delete_all = True
                    should_delete = True
                    console.print("[yellow]Deleting all remaining matches...[/yellow]")
                elif choice == "q":
                    console.print("[yellow]Aborted.[/yellow]")
                    return
                elif choice == "y":
                    should_delete = True
                else:  # 'n'
                    should_delete = False
                    console.print("[dim]Skipped[/dim]")

            if should_delete:
                try:
                    # Ensure trash exists (it should on Mac)
                    if not os.path.exists(trash_dir):
                        os.makedirs(trash_dir, exist_ok=True)

                    # Move file
                    destination = os.path.join(trash_dir, file_name)

                    # Handle duplicate names in trash
                    if os.path.exists(destination):
                        base, ext = os.path.splitext(file_name)
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        destination = os.path.join(trash_dir, f"{base}_{timestamp}{ext}")

                    shutil.move(file_path, destination)
                    console.print("[green]Moved to Trash[/green]")
                except Exception as e:
                    console.print(f"[red]Error moving file: {e}[/red]")
