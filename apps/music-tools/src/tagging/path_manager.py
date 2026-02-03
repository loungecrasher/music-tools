"""
Path Manager Module

Handles music library path management and auto-detection.
Extracted from cli.py for better maintainability.
"""

import glob
import os
from typing import List

from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt

console = Console()


class LibraryPathManager:
    """Manages music library paths."""

    def __init__(self, current_paths: List[str]):
        self.paths = list(current_paths) if current_paths else []

    def manage_paths(self) -> List[str]:
        """Interactive path management menu"""
        while True:
            self._display_current_paths()
            choice = self._get_menu_choice()

            if choice == "1":
                self._add_path()
            elif choice == "2":
                self._remove_path()
            elif choice == "3":
                self._remove_all_paths()
            elif choice == "4":
                break
            elif choice == "5":
                self._auto_detect_paths()

        return self.paths

    def _display_current_paths(self) -> None:
        """Display current paths with existence check"""
        console.print("\n[cyan]Library Path Management:[/cyan]")
        if self.paths:
            console.print("Current paths:")
            for i, path in enumerate(self.paths, 1):
                exists = "✓" if os.path.exists(path) else "✗"
                console.print(f"  [{exists}] {i}. {path}")
        else:
            console.print("[yellow]No paths configured[/yellow]")

        console.print("\n[bold]Options:[/bold]")
        console.print("  1. Add new path")
        console.print("  2. Remove specific path")
        console.print("  3. Remove all paths")
        console.print("  4. Keep current and continue")
        console.print("  5. Auto-detect common music directories")

    def _get_menu_choice(self) -> str:
        """Get user's menu choice"""
        try:
            return Prompt.ask("Select option", choices=["1", "2", "3", "4", "5"], default="4")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Path configuration cancelled[/yellow]")
            return "4"

    def _add_path(self) -> None:
        """Add a new path to the list"""
        path = input("Enter path to add (or Enter to cancel): ").strip()
        if not path:
            return

        path = path.strip("\"'")
        expanded_path = os.path.expanduser(path)

        if expanded_path in self.paths:
            console.print(f"[yellow]Path already in list: {expanded_path}[/yellow]")
            return

        if os.path.exists(expanded_path):
            self.paths.append(expanded_path)
            console.print(f"[green]✓ Added: {expanded_path}[/green]")
        else:
            console.print(f"[yellow]Warning: Path does not exist: {expanded_path}[/yellow]")
            if Confirm.ask("Add anyway?", default=False):
                self.paths.append(expanded_path)
                console.print(f"[green]✓ Added: {expanded_path}[/green]")

    def _remove_path(self) -> None:
        """Remove a specific path from the list"""
        if not self.paths:
            console.print("[yellow]No paths to remove[/yellow]")
            return

        console.print("\nSelect path to remove:")
        for i, path in enumerate(self.paths, 1):
            console.print(f"  {i}. {path}")

        try:
            remove_idx = IntPrompt.ask(
                "Path number to remove (0 to cancel)", default=0, show_default=True
            )
            if 0 < remove_idx <= len(self.paths):
                removed_path = self.paths.pop(remove_idx - 1)
                console.print(f"[red]✗ Removed: {removed_path}[/red]")
        except (ValueError, IndexError):
            console.print("[red]Invalid selection[/red]")

    def _remove_all_paths(self) -> None:
        """Remove all paths after confirmation"""
        if self.paths and Confirm.ask("Remove all paths?", default=False):
            self.paths.clear()
            console.print("[red]✗ All paths removed[/red]")

    def _auto_detect_paths(self) -> None:
        """Auto-detect common music directories"""
        console.print("\n[cyan]Checking common music directories...[/cyan]")
        common_dirs = [
            "~/Music",
            "~/Documents/Music",
            "~/Downloads/Music",
            "/Users/patrickoliver/Track Library",
            "/Users/patrickoliver/Music Library",
            "/Volumes/*/Music",
        ]

        found_dirs = self._find_existing_directories(common_dirs)

        if found_dirs:
            self._handle_found_directories(found_dirs)
        else:
            console.print("[yellow]No additional music directories found[/yellow]")

    def _find_existing_directories(self, common_dirs: List[str]) -> List[str]:
        """Find existing directories from common paths"""
        found_dirs = []
        for dir_pattern in common_dirs:
            expanded = os.path.expanduser(dir_pattern)
            if "*" in expanded:
                for path in glob.glob(expanded):
                    if os.path.isdir(path) and path not in self.paths:
                        found_dirs.append(path)
            elif os.path.isdir(expanded) and expanded not in self.paths:
                found_dirs.append(expanded)
        return found_dirs

    def _handle_found_directories(self, found_dirs: List[str]) -> None:
        """Handle found directories - add all or select specific ones"""
        console.print("\n[green]Found music directories:[/green]")
        for i, path in enumerate(found_dirs, 1):
            console.print(f"  {i}. {path}")

        if Confirm.ask("Add all found directories?", default=False):
            self.paths.extend(found_dirs)
            console.print(f"[green]✓ Added {len(found_dirs)} directories[/green]")
        else:
            self._add_selected_directories(found_dirs)

    def _add_selected_directories(self, found_dirs: List[str]) -> None:
        """Add user-selected directories"""
        selections = input("Enter numbers to add (comma-separated, or Enter for none): ").strip()
        if not selections:
            return

        try:
            indices = [int(x.strip()) - 1 for x in selections.split(",")]
            added = 0
            for idx in indices:
                if 0 <= idx < len(found_dirs):
                    self.paths.append(found_dirs[idx])
                    added += 1
            console.print(f"[green]✓ Added {added} directories[/green]")
        except (ValueError, IndexError):
            console.print("[red]Invalid selection[/red]")
