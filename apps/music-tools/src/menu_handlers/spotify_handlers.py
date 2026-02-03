"""Menu handlers for Spotify features."""

import logging

from music_tools_common.cli import clear_screen
from rich.console import Console
from rich.prompt import Prompt

logger = logging.getLogger(__name__)
console = Console()


def _run_spotify_feature(func_name: str, label: str) -> None:
    """Generic launcher for Spotify features from spotify_tracks module."""
    clear_screen()
    try:
        import src.services.spotify_tracks as st
        func = getattr(st, func_name)
        func()
    except ImportError as e:
        console.print(f"[bold red]Error importing Spotify module:[/bold red] {e}")
        console.print("[yellow]Ensure spotipy is installed and Spotify is configured.[/yellow]")
        Prompt.ask("\nPress Enter to continue")
    except Exception as e:
        console.print(f"[bold red]Error running {label}:[/bold red] {e}")
        Prompt.ask("\nPress Enter to continue")


def run_spotify_playlist_manager() -> None:
    """Launch the Spotify Playlist Manager."""
    _run_spotify_feature("run_playlist_manager", "Spotify Playlist Manager")


def run_spotify_tracks_after_date() -> None:
    """Launch the Spotify Tracks After Date filter."""
    _run_spotify_feature("run_tracks_after_date", "Tracks After Date")


def run_spotify_collect_from_folder() -> None:
    """Launch the Collect From Playlist Folder tool."""
    _run_spotify_feature("run_collect_from_folder", "Collect From Folder")


def run_recent_tracks_aggregator() -> None:
    """Launch the Spotify Recent Tracks Aggregator."""
    _run_spotify_feature("run_recent_tracks_aggregator", "Recent Tracks Aggregator")
