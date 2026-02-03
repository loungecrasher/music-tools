#!/usr/bin/env python3
"""
Unified menu interface for Music Tools.
Provides access to all music-related tools through a centralized menu.
Enhanced with Rich for better visual presentation.
"""

import os
import sys
import time
from pathlib import Path

# Load environment variables FIRST, before any other imports
from dotenv import load_dotenv

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

# Load .env from the script directory
env_file = SCRIPT_DIR / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Rich library for enhanced terminal output
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Import core modules
try:
    from music_tools_common import setup_logger
    from music_tools_common.cli import clear_screen
    from music_tools_common.ui.menu import Menu, MenuOption

    # Import all menu handlers
    from src.menu_handlers import (
        run_edm_blog_scraper,
        run_library_index,
        run_library_stats,
        run_music_country_tagger,
        run_process_new_music,
        run_recent_tracks_aggregator,
        run_serato_build_index,
        run_serato_csv_to_crate,
        run_serato_list_crates,
        run_spotify_playlist_manager,
        run_spotify_tracks_after_date,
    )
except ImportError as e:
    print(f"Error: Core modules not found. Please ensure music_tools_common is installed: {e}")
    sys.exit(1)

# Set up logging
logger = setup_logger("music_tools.menu")

# Constants
TOOLS_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(TOOLS_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize Rich console
console = Console()


def display_enhanced_welcome() -> None:
    """Display enhanced welcome screen with library statistics."""
    clear_screen()

    # App title with style
    title = Text("Music Tools Suite", style="bold cyan")

    # Get library stats if available
    db_path = Path.home() / ".music-tools" / "library_index.db"
    library_stats = None

    if db_path.exists():
        try:
            from src.library.database import LibraryDatabase

            library_db = LibraryDatabase(str(db_path))
            library_stats = library_db.get_statistics()
        except Exception as e:
            logger.debug(f"Could not fetch library stats: {e}")

    # Build welcome content
    welcome_text = Text()
    welcome_text.append("A unified interface for managing your music library.\n\n", style="white")

    # Library Status Section
    welcome_text.append("Library Status:\n", style="bold yellow")

    if library_stats and library_stats.total_files > 0:
        welcome_text.append(f"  Total Files: {library_stats.total_files:,}\n", style="green")
        welcome_text.append(f"  Total Size: {library_stats.total_size_gb:.2f} GB\n", style="green")
        welcome_text.append(f"  Artists: {library_stats.artists_count:,}\n", style="green")
        welcome_text.append(f"  Albums: {library_stats.albums_count:,}\n", style="green")
    else:
        welcome_text.append("  Library: ", style="white")
        welcome_text.append(
            "Not indexed yet - run 'Index Library' to get started\n", style="yellow"
        )

    welcome_text.append("\nMain Features:\n", style="bold cyan")
    welcome_text.append(
        "  Process New Music - Check new folders against library + history\n", style="white"
    )
    welcome_text.append(
        "  Library Management - Indexing, duplicate detection, statistics\n", style="white"
    )
    welcome_text.append("  EDM Blog Scraper - Find new music from EDM blogs\n", style="white")
    welcome_text.append("  AI Country Tagger - Tag files with country metadata\n", style="white")
    welcome_text.append(
        "  Spotify Tools - Playlist management, date filters, aggregation\n", style="white"
    )
    welcome_text.append(
        "  Serato Tools - Track indexing, CSV to crate, crate browser\n", style="white"
    )

    welcome_text.append(
        "\nUse the menu below to navigate through the available tools.\n", style="dim"
    )

    # Display welcome panel
    console.print(Panel(welcome_text, title=title, border_style="cyan", padding=(1, 2)))

    # Version and copyright
    console.print("\n[dim]Version 2.0.0 | Music Inxite | Simplified & Streamlined[/dim]")

    # Brief pause for user to read
    time.sleep(1)


def main() -> None:
    """Main function."""
    # Check if first-run setup is needed
    try:
        from setup_wizard import SetupWizard

        wizard = SetupWizard()
        if wizard.needs_setup():
            console.print("\n[bold cyan]First-time setup detected![/bold cyan]")
            if wizard.run():
                console.print("\n[green]Setup complete! Starting Music Tools...[/green]\n")
                time.sleep(2)
            else:
                console.print("\n[yellow]Setup incomplete. Some features may not work.[/yellow]")
                time.sleep(2)
    except Exception as e:
        logger.debug(f"Setup wizard check failed: {e}")

    # Display enhanced welcome screen
    display_enhanced_welcome()

    # Create main menu with organized categories
    main_menu = Menu("Music Tools - Main Menu")

    main_menu.add_option(
        "Process New Music Folder",
        run_process_new_music,
        "Check new folder against library + history",
    )
    main_menu.add_option(
        "Index Library", run_library_index, "Scan your main music library (one-time setup)"
    )
    main_menu.add_option("Library Statistics", run_library_stats, "View your library statistics")
    main_menu.add_option("EDM Blog Scraper", run_edm_blog_scraper, "Find new music from EDM blogs")
    main_menu.add_option(
        "Country Tagger (AI)", run_music_country_tagger, "Tag files with country metadata"
    )
    main_menu.add_option(
        "Spotify Playlist Manager",
        run_spotify_playlist_manager,
        "View, create, copy, and deduplicate playlists",
    )
    main_menu.add_option(
        "Spotify Tracks by Date",
        run_spotify_tracks_after_date,
        "Filter playlist tracks by release date",
    )
    main_menu.add_option(
        "Recent Tracks Aggregator",
        run_recent_tracks_aggregator,
        "Aggregate recent adds from ALL playlists into one",
    )

    # Serato Tools submenu
    serato_menu = main_menu.create_submenu("Serato Tools")
    serato_menu.add_option(
        "Build Track Index", run_serato_build_index, "Index music library for fast CSV import"
    )
    serato_menu.add_option(
        "CSV to Crate", run_serato_csv_to_crate, "Import CSV playlist to Serato crate"
    )
    serato_menu.add_option("List Crates", run_serato_list_crates, "Browse your Serato crates")
    serato_menu.set_exit_option("Back to Main Menu")

    # Set exit option for main menu
    main_menu.set_exit_option("Exit")

    # Display main menu
    main_menu.display()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting Music Tools...")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1)
