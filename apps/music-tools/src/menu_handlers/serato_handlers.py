"""Menu handlers for Serato crate operations.

Includes: build track index, CSV to crate import, and crate listing.
"""

from pathlib import Path

from music_tools_common import setup_logger
from music_tools_common.cli import clear_screen
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

logger = setup_logger('music_tools.menu.serato')
console = Console()


def run_serato_build_index() -> None:
    """Build Serato track index from directory or crate family.

    Presents the user with two indexing strategies:
      1. Scan a directory tree for audio files (fast, recommended).
      2. Scan a Serato crate family (reads crate metadata directly).

    The resulting index is saved to ``~/.music-tools/serato_track_index.json``
    and is required by the CSV-to-crate import feature.
    """
    clear_screen()

    console.print(Panel(
        "[bold green]Build Serato Track Index[/bold green]\n\n"
        "Build a searchable index of your music library for fast CSV-to-crate\n"
        "conversion. The index stores artist/title metadata extracted from your\n"
        "audio files so that CSV playlists can be matched quickly.\n\n"
        "Indexing methods:\n"
        "  [cyan]1.[/cyan] Scan Directory  [dim](recommended -- 8-10x faster)[/dim]\n"
        "  [cyan]2.[/cyan] Scan Serato Crate Family",
        title="[bold]Serato Track Index[/bold]",
        border_style="green"
    ))

    choice = Prompt.ask(
        "\nSelect indexing method",
        choices=["1", "2"],
        default="1",
    )

    if choice == "1":
        _build_index_from_directory()
    else:
        _build_index_from_crates()


def run_serato_csv_to_crate() -> None:
    """Import a CSV playlist into a new Serato crate.

    Requires a pre-built track index (see ``run_serato_build_index``).
    The CSV file must contain ``Artist`` and ``Title`` columns.
    """
    from src.services.serato import CSVImporter, SeratoTrackIndex

    clear_screen()

    console.print(Panel(
        "[bold green]CSV to Serato Crate[/bold green]\n\n"
        "Import a CSV playlist file into a new Serato crate.\n\n"
        "Requirements:\n"
        "  - CSV file with 'Artist' and 'Title' columns\n"
        "  - Built track index (run 'Build Track Index' first)",
        title="[bold]CSV Import[/bold]",
        border_style="green"
    ))

    # Load existing index
    try:
        index = SeratoTrackIndex()
        count = index.load()
        if count == 0:
            console.print(
                "[bold yellow]Warning:[/bold yellow] Track index is empty "
                f"({index.index_path})"
            )
            console.print(
                "You may want to rebuild it with [cyan]'Build Track Index'[/cyan]."
            )
    except FileNotFoundError:
        console.print(
            "[bold red]Error:[/bold red] Track index not found."
        )
        console.print(
            "\nPlease run [cyan]'Build Track Index'[/cyan] first to "
            "create the index."
        )
        Prompt.ask("\nPress Enter to continue")
        return
    except Exception as e:
        console.print(f"[bold red]Error loading index:[/bold red] {e}")
        logger.error("Failed to load Serato track index: %s", e, exc_info=True)
        Prompt.ask("\nPress Enter to continue")
        return

    # Get CSV file path
    csv_path = Prompt.ask("\nEnter path to CSV file")
    csv_path = csv_path.strip().strip("'\"")

    if not Path(csv_path).is_file():
        console.print(f"[bold red]Error:[/bold red] File not found: {csv_path}")
        Prompt.ask("\nPress Enter to continue")
        return

    # Get crate name
    crate_name = Prompt.ask("\nEnter name for new Serato crate")
    if not crate_name.strip():
        console.print("[bold red]Error:[/bold red] Crate name cannot be empty.")
        Prompt.ask("\nPress Enter to continue")
        return

    # Get threshold
    threshold_str = Prompt.ask(
        "\nFuzzy match threshold (0-100)",
        default="75",
    )

    try:
        threshold = int(threshold_str)
        if not 0 <= threshold <= 100:
            raise ValueError("out of range")
    except ValueError:
        console.print("[yellow]Invalid threshold. Using default 75.[/yellow]")
        threshold = 75

    # Perform import
    console.print("\n[bold cyan]Importing CSV to crate...[/bold cyan]")
    console.print(f"CSV file:  {csv_path}")
    console.print(f"Crate:     {crate_name}")
    console.print(f"Threshold: {threshold}")

    try:
        importer = CSVImporter(index)
        result = importer.import_csv_to_crate(csv_path, crate_name, threshold)
        _display_import_results(result)
    except Exception as e:
        console.print(f"[bold red]Error during CSV import:[/bold red] {e}")
        logger.error("CSV import failed: %s", e, exc_info=True)

    Prompt.ask("\nPress Enter to continue")


def run_serato_list_crates() -> None:
    """List all Serato crates found in the default Serato library."""
    from src.services.serato import CrateManager

    clear_screen()

    console.print(Panel(
        "[bold green]List Serato Crates[/bold green]\n\n"
        "View all crate files found in your Serato library.\n"
        "Reads from the default Serato data folder at\n"
        "[dim]~/Music/_Serato_/Subcrates/[/dim]",
        title="[bold]Crate Browser[/bold]",
        border_style="green"
    ))

    try:
        manager = CrateManager()
        crates = manager.list_crate_families()

        if not crates:
            console.print(
                "\n[yellow]No crates found in Serato library.[/yellow]"
            )
            console.print(
                "[dim]Expected location: ~/Music/_Serato_/Subcrates/[/dim]"
            )
        else:
            table = Table(title="Serato Crates", show_lines=False)
            table.add_column("Crate Name", style="cyan", no_wrap=False)
            table.add_column("Tracks", justify="right", style="green")
            table.add_column("Type", style="yellow")

            total_tracks = 0
            for crate in crates:
                crate_type = "Subcrate" if crate.is_subcrate else "Main"
                table.add_row(
                    crate.name,
                    str(crate.track_count),
                    crate_type,
                )
                total_tracks += crate.track_count

            console.print()
            console.print(table)
            console.print(
                f"\n[bold]Total:[/bold] {len(crates)} crate(s), "
                f"{total_tracks:,} track(s)"
            )
    except Exception as e:
        console.print(f"[bold red]Error listing crates:[/bold red] {e}")
        logger.error("Failed to list Serato crates: %s", e, exc_info=True)

    Prompt.ask("\nPress Enter to continue")


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _build_index_from_directory() -> None:
    """Prompt for directory details and build the track index."""
    from src.services.serato import SeratoTrackIndex

    directory = Prompt.ask("\nEnter path to music library directory")
    directory = directory.strip().strip("'\"")

    if not Path(directory).is_dir():
        console.print(
            f"[bold red]Error:[/bold red] {directory} is not a valid directory"
        )
        Prompt.ask("\nPress Enter to continue")
        return

    extensions_str = Prompt.ask(
        "\nFile extensions to scan (comma-separated)",
        default=".mp3,.m4a,.flac,.wav,.aiff",
    )
    ext_list = [ext.strip() for ext in extensions_str.split(",") if ext.strip()]

    console.print("\n[bold cyan]Building index from directory...[/bold cyan]")
    console.print(f"Directory:  {directory}")
    console.print(f"Extensions: {', '.join(ext_list)}")

    try:
        index = SeratoTrackIndex()
        count = index.build_from_directory(directory, ext_list)
        index.save()

        console.print("\n[bold green]Index built successfully![/bold green]")
        console.print(f"Indexed [bold]{count:,}[/bold] tracks")
        console.print(f"Saved to: {index.index_path}")
    except Exception as e:
        console.print(f"[bold red]Error building index:[/bold red] {e}")
        logger.error("Index build from directory failed: %s", e, exc_info=True)

    Prompt.ask("\nPress Enter to continue")


def _build_index_from_crates() -> None:
    """Prompt for crate family name and build the track index."""
    from src.services.serato import SeratoTrackIndex

    source_crate = Prompt.ask("\nEnter source crate family name")
    if not source_crate.strip():
        console.print("[bold red]Error:[/bold red] Crate name cannot be empty.")
        Prompt.ask("\nPress Enter to continue")
        return

    console.print("\n[bold cyan]Building index from crate family...[/bold cyan]")
    console.print(f"Source crate: {source_crate}")

    try:
        index = SeratoTrackIndex()
        count = index.build_from_crate_family(
            str(Path.home() / "Music" / "_Serato_"),
            source_crate,
        )
        index.save()

        console.print("\n[bold green]Index built successfully![/bold green]")
        console.print(f"Indexed [bold]{count:,}[/bold] tracks")
        console.print(f"Saved to: {index.index_path}")
    except Exception as e:
        console.print(f"[bold red]Error building index:[/bold red] {e}")
        logger.error(
            "Index build from crate family failed: %s", e, exc_info=True
        )

    Prompt.ask("\nPress Enter to continue")


def _display_import_results(result) -> None:
    """Display results from a CSV import operation.

    Parameters
    ----------
    result : ImportResult
        The import result containing matched, not_found, and
        multiple_matches lists.
    """
    # Summary line
    console.print(
        f"\n[bold green]Matched:[/bold green] {len(result.matched)} tracks"
    )

    # Matched tracks table
    if result.matched:
        table = Table(title="Matched Tracks", show_lines=False)
        table.add_column("Artist", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Matched To", style="green")
        table.add_column("Score", justify="right", style="yellow")

        display_limit = 20
        for artist, title, match, score in result.matched[:display_limit]:
            match_label = str(match) if not hasattr(match, 'title') else match.title
            table.add_row(artist, title, match_label, f"{score}%")

        if len(result.matched) > display_limit:
            table.add_row(
                "...",
                f"and {len(result.matched) - display_limit} more",
                "",
                "",
            )

        console.print(table)

    # Not found
    if result.not_found:
        console.print(
            f"\n[bold red]Not Found:[/bold red] {len(result.not_found)} tracks"
        )
        display_limit = 10
        for artist, title in result.not_found[:display_limit]:
            console.print(f"  [dim]-[/dim] {artist} - {title}")
        if len(result.not_found) > display_limit:
            console.print(
                f"  [dim]... and {len(result.not_found) - display_limit} "
                f"more[/dim]"
            )

    # Multiple matches
    if result.multiple_matches:
        console.print(
            f"\n[bold yellow]Multiple Matches:[/bold yellow] "
            f"{len(result.multiple_matches)} tracks"
        )
        display_limit = 5
        for artist, title, matches in result.multiple_matches[:display_limit]:
            console.print(f"  [dim]-[/dim] {artist} - {title} ({len(matches)} candidates)")
        if len(result.multiple_matches) > display_limit:
            console.print(
                f"  [dim]... and "
                f"{len(result.multiple_matches) - display_limit} more[/dim]"
            )

    # Crate creation result
    if result.crate_path:
        console.print(
            f"\n[bold green]Crate created:[/bold green] {result.crate_path}"
        )
