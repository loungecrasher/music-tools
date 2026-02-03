"""Menu handlers for library management workflows.

Includes: process new music, indexing, vetting, statistics,
smart cleanup, and candidate history operations.
"""

import os
from pathlib import Path

from music_tools_common import setup_logger
from music_tools_common.cli import clear_screen, pause, print_error, show_panel
from music_tools_common.config import config_manager
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

logger = setup_logger('music_tools.menu.library')
console = Console()


def _get_config(service: str):
    """Get configuration for a service."""
    return config_manager.load_config(service)


def run_process_new_music() -> None:
    """Process a new music folder - unified workflow.

    Checks new folder against:
    1. Library index (finds duplicates)
    2. Candidate history (finds already-reviewed)

    Result: Categorizes as Duplicates, Reviewed, or New
    """
    from src.library.database import LibraryDatabase
    from src.library.new_music_processor import NewMusicProcessor

    clear_screen()

    console.print(Panel(
        "[bold green]Process New Music Folder[/bold green]\n\n"
        "This unified workflow will:\n"
        "  1. Check files against your library index (find duplicates)\n"
        "  2. Check files against listening history (find reviewed)\n"
        "  3. Show you only the truly NEW songs that need attention\n\n"
        "Make sure you've indexed your library first!",
        title="[bold]New Music Processor[/bold]",
        border_style="green"
    ))

    # Get folder path
    folder_path = Prompt.ask("\nEnter path to new music folder")
    folder_path = folder_path.strip("'\"")

    if not Path(folder_path).is_dir():
        console.print(f"[bold red]Error:[/bold red] {folder_path} is not a valid directory")
        Prompt.ask("\nPress Enter to continue")
        return

    # Check library database exists
    db_path = Path.home() / ".music-tools" / "library_index.db"

    if not db_path.exists():
        console.print(f"[bold red]Error:[/bold red] Library database not found at {db_path}")
        console.print("\nPlease run 'Index Library' first to create the database.")
        Prompt.ask("\nPress Enter to continue")
        return

    # Initialize processor
    try:
        library_db = LibraryDatabase(str(db_path))
        processor = NewMusicProcessor(library_db, console=console)

        # Process folder
        console.print("\n[bold cyan]Processing new music folder...[/bold cyan]")
        result = processor.process_folder(folder_path, threshold=0.8)

        # Display results
        processor.display_results(result)

        # Export new songs
        if result.truly_new:
            export_path = processor.export_new_songs(result, folder_path)
            console.print(f"\n[green]✓ New songs list exported to:[/green] {export_path}")

        # Interactive cleanup
        if result.duplicates or result.already_reviewed:
            console.print("\n[bold]Cleanup Options:[/bold]")
            if Confirm.ask("Run interactive cleanup?", default=True):
                dup_deleted, rev_deleted = processor.interactive_cleanup(result, folder_path)

                console.print("\n[bold green]Cleanup Complete![/bold green]")
                console.print(f"  Duplicates deleted: {dup_deleted}")
                console.print(f"  Reviewed deleted: {rev_deleted}")
                console.print(f"  New songs remaining: {len(result.truly_new)}")
        else:
            console.print("\n[green]✓ No cleanup needed - all files are new![/green]")

    except Exception as e:
        console.print(f"[bold red]Error processing folder:[/bold red] {str(e)}")
        logger.error(f"Error in new music processor: {e}", exc_info=True)

    Prompt.ask("\nPress Enter to continue")


def run_library_index() -> None:
    """Run Library Indexer."""
    from src.library.indexer import LibraryIndexer

    console.print(Panel(
        "[bold green]Index Your Music Library[/bold green]\n\n"
        "This will scan your main music library and create a searchable database "
        "for fast duplicate detection when vetting new imports.\n\n"
        "Supports: MP3, FLAC, M4A, WAV, OGG, OPUS, AIFF",
        title="[bold]Library Indexer[/bold]",
        border_style="green"
    ))

    library_path = Prompt.ask("\nEnter path to your main music library")
    library_path = library_path.strip("'\"")

    if not Path(library_path).is_dir():
        console.print(f"[bold red]Error:[/bold red] {library_path} is not a valid directory")
        Prompt.ask("\nPress Enter to continue")
        return

    # Use default database location
    db_path = Path.home() / ".music-tools" / "library_index.db"

    rescan = Confirm.ask("\nPerform full rescan (vs incremental)?", default=False)

    console.print("\n[bold cyan]Indexing library...[/bold cyan]")
    console.print(f"Library: {library_path}")
    console.print(f"Database: {db_path}")

    try:
        indexer = LibraryIndexer(str(db_path), console=console)
        indexer.index_library(
            str(library_path),
            rescan=rescan,
            incremental=not rescan,
            show_progress=True
        )

        console.print("\n[bold green]✓ Indexing complete![/bold green]")

    except Exception as e:
        console.print(f"[bold red]Error during indexing:[/bold red] {str(e)}")

    Prompt.ask("\nPress Enter to continue")


def run_library_vet() -> None:
    """Run Library Vetter."""
    from src.library.database import LibraryDatabase
    from src.library.vetter import ImportVetter

    console.print(Panel(
        "[bold green]Vet Import Folder Against Library[/bold green]\n\n"
        "This will check all music files in an import folder against your indexed library "
        "to identify duplicates and new songs.\n\n"
        "Make sure you've indexed your main library first!",
        title="[bold]Library Vetter[/bold]",
        border_style="green"
    ))

    import_folder = Prompt.ask("\nEnter path to import folder")
    import_folder = import_folder.strip("'\"")

    if not Path(import_folder).is_dir():
        console.print(f"[bold red]Error:[/bold red] {import_folder} is not a valid directory")
        Prompt.ask("\nPress Enter to continue")
        return

    db_path = Path.home() / ".music-tools" / "library_index.db"

    if not db_path.exists():
        console.print(f"[bold red]Error:[/bold red] Library database not found at {db_path}")
        console.print("\nPlease run 'Index Library' first to create the database.")
        Prompt.ask("\nPress Enter to continue")
        return

    threshold = Prompt.ask("\nSimilarity threshold (0.0-1.0)", default="0.8")

    try:
        threshold_float = float(threshold)
        if not 0.0 <= threshold_float <= 1.0:
            raise ValueError()
    except ValueError:
        console.print("[bold red]Invalid threshold. Using default 0.8[/bold red]")
        threshold_float = 0.8

    console.print("\n[bold cyan]Vetting import folder...[/bold cyan]")
    console.print(f"Import folder: {import_folder}")
    console.print(f"Database: {db_path}")
    console.print(f"Threshold: {threshold_float}")

    try:
        # Initialize database and vetter
        db = LibraryDatabase(str(db_path))
        vetter = ImportVetter(db, console=console)

        report = vetter.vet_folder(
            import_folder=str(import_folder),
            threshold=threshold_float,
            show_progress=True
        )

        # Display the report
        vetter.display_report(report)

        # Export new songs
        new_songs_file = str(Path(import_folder) / 'new_songs.txt')
        vetter.export_new_songs(report, new_songs_file)

        console.print("\n[bold green]✓ Vetting complete![/bold green]")
        console.print(f"\n[bold]New songs exported to:[/bold] {new_songs_file}")

        # Offer to delete duplicates
        if report.duplicate_count > 0:
            console.print()
            delete_choice = Prompt.ask(
                f"\n[bold]Delete {report.duplicate_count} duplicate files?[/bold]",
                choices=["yes", "no", "dry-run"],
                default="no"
            )

            if delete_choice == "yes":
                deleted, failed = vetter.delete_duplicates(report, confirm=True, dry_run=False)
                if deleted > 0:
                    console.print(f"\n[bold green]✓ Deleted {deleted} duplicate files[/bold green]")
                if failed > 0:
                    console.print(f"[bold red]✗ Failed to delete {failed} files[/bold red]")
            elif delete_choice == "dry-run":
                vetter.delete_duplicates(report, confirm=False, dry_run=True)
            else:
                console.print("\n[yellow]Skipped deletion. Duplicates remain in import folder.[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Error during vetting:[/bold red] {str(e)}")

    Prompt.ask("\nPress Enter to continue")


def run_library_stats() -> None:
    """Show Library Statistics."""
    from src.library.database import LibraryDatabase

    db_path = Path.home() / ".music-tools" / "library_index.db"

    if not db_path.exists():
        console.print(f"[bold red]Error:[/bold red] Library database not found at {db_path}")
        console.print("\nPlease run 'Index Library' first to create the database.")
        Prompt.ask("\nPress Enter to continue")
        return

    try:
        db = LibraryDatabase(str(db_path))
        stats = db.get_statistics()

        # Format last index time
        last_index = stats.last_index_time.strftime('%Y-%m-%d %H:%M:%S') if stats.last_index_time else 'Never'

        console.print(Panel(
            f"[bold]Total Files:[/bold] {stats.total_files:,}\n"
            f"[bold]Total Size:[/bold] {stats.total_size_gb:.2f} GB\n"
            f"[bold]Unique Artists:[/bold] {stats.artists_count:,}\n"
            f"[bold]Unique Albums:[/bold] {stats.albums_count:,}\n"
            f"[bold]Last Indexed:[/bold] {last_index}",
            title="[bold]Library Statistics[/bold]",
            border_style="cyan"
        ))

    except Exception as e:
        console.print(f"[bold red]Error retrieving stats:[/bold red] {str(e)}")

    Prompt.ask("\nPress Enter to continue")


def run_smart_cleanup_menu() -> None:
    """Run Smart Cleanup workflow with enhanced UI/UX.

    Provides an interactive 8-screen workflow for safely identifying
    and removing duplicate music files while preserving highest quality versions.
    """
    from src.library.database import LibraryDatabase
    from src.library.smart_cleanup import SmartCleanupWorkflow

    clear_screen()

    try:
        # Get library path from config or prompt
        library_config = _get_config('library')
        library_path = None

        if library_config and library_config.get('path'):
            library_path = library_config.get('path')
            console.print(f"[cyan]Using library path:[/cyan] {library_path}")
        else:
            console.print(Panel(
                "[yellow]Library path not configured.[/yellow]\n\n"
                "Please enter the path to your music library.",
                title="Configuration Required",
                border_style="yellow"
            ))
            library_path = Prompt.ask("\nEnter library path")

        if not library_path:
            console.print("[red]Library path required. Cancelled.[/red]")
            pause()
            return

        # Expand and validate path
        library_path = os.path.expanduser(library_path.strip().strip("'\""))

        if not os.path.exists(library_path):
            console.print(f"[red]Library path not found:[/red] {library_path}")
            pause()
            return

        # Initialize library database
        db_path = os.path.join(library_path, '.library.db')
        library_db = LibraryDatabase(db_path)

        # Check if database exists and has files
        with library_db:
            stats = library_db.get_statistics()
            if stats.total_files == 0:
                console.print(Panel(
                    "[yellow]Library database is empty.[/yellow]\n\n"
                    "Please run 'Index Library' first to scan your music files.",
                    title="Database Empty",
                    border_style="yellow"
                ))

                if Confirm.ask("\nReturn to Library Management menu?", default=True):
                    return
                else:
                    pause()
                    return

        # Run Smart Cleanup workflow
        workflow = SmartCleanupWorkflow(
            library_db=library_db,
            library_path=library_path,
            console=console
        )

        stats = workflow.run()

        # Show final summary
        if stats.files_deleted > 0:
            console.print(f"\n[bold green]Successfully deleted {stats.files_deleted} duplicate files![/bold green]")
            console.print(f"[green]Space freed: {stats.space_freed_mb:.2f} MB[/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Smart Cleanup cancelled by user.[/yellow]")
    except ImportError as e:
        console.print("\n[bold red]Smart Cleanup not available:[/bold red]")
        console.print(f"[yellow]{str(e)}[/yellow]")
        console.print("\n[dim]This feature requires the library module to be properly configured.[/dim]")
    except Exception as e:
        logger.error(f"Error in Smart Cleanup: {e}", exc_info=True)
        console.print("\n[bold red]Error running Smart Cleanup:[/bold red]")
        console.print(f"[red]{str(e)}[/red]")

    pause()


def run_candidate_history_add() -> None:
    """Run the Add Folder to History tool."""
    from src.library.candidate_manager import CandidateManager

    clear_screen()
    show_panel("Add files from a folder to your listening history", title="Add Folder to History", border_style="blue")

    folder_path = Prompt.ask("Enter the full path to the folder you want to add to history")

    if not folder_path:
        return

    # Strip quotes from pasted paths
    folder_path = folder_path.strip().strip("'\"")
    folder_path = os.path.expanduser(folder_path)
    if not os.path.exists(folder_path):
        print_error(f"Folder not found: {folder_path}")
        pause()
        return

    try:
        manager = CandidateManager()
        stats = manager.add_folder_to_history(folder_path)

        console.print("\n[bold green]Operation Complete![/bold green]")
        console.print(f"Total files scanned: {stats['total']}")
        console.print(f"Added to history: {stats['added']}")
        console.print(f"Skipped (already exists): {stats['skipped']}")

    except Exception as e:
        print_error(f"Error: {e}")

    pause()


def run_candidate_history_check() -> None:
    """Run the Check Folder against History tool."""
    from src.library.candidate_manager import CandidateManager

    clear_screen()
    show_panel("Check if files in a folder have been listened to before", title="Check Folder against History", border_style="blue")

    folder_path = Prompt.ask("Enter the full path to the folder you want to check")

    if not folder_path:
        return

    # Strip quotes from pasted paths
    folder_path = folder_path.strip().strip("'\"")
    folder_path = os.path.expanduser(folder_path)
    if not os.path.exists(folder_path):
        print_error(f"Folder not found: {folder_path}")
        pause()
        return

    try:
        manager = CandidateManager()
        matches = manager.check_folder(folder_path)
        manager.process_matches(matches)

    except Exception as e:
        print_error(f"Error: {e}")

    pause()
