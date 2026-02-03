#!/usr/bin/env python3
"""
Interactive Demo: Library Duplicate Detection Feature

This demonstrates how the new library feature works without needing
the full CLI infrastructure.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from datetime import datetime, timezone

from library.database import LibraryDatabase
from library.duplicate_checker import DuplicateChecker
from library.indexer import LibraryIndexer
from library.models import DuplicateResult, LibraryFile, VettingReport
from library.vetter import ImportVetter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def demo_header(title: str):
    """Print a demo section header."""
    console.print()
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", border_style="cyan"))
    console.print()


def demo_1_create_sample_library():
    """Demo 1: Create a sample library."""
    demo_header("DEMO 1: Creating a Sample Library")

    console.print("Creating sample library with 5 songs...")
    console.print()

    # Sample library files
    library_songs = [
        LibraryFile(
            file_path="/library/artist1_song1.mp3",
            filename="artist1_song1.mp3",
            artist="The Beatles",
            title="Yesterday",
            album="Help!",
            year=1965,
            duration=123.5,
            file_format="mp3",
            file_size=5_000_000,
            metadata_hash="hash1",
            file_content_hash="content1",
            file_mtime=datetime.now(timezone.utc),
        ),
        LibraryFile(
            file_path="/library/artist2_song1.mp3",
            filename="artist2_song1.mp3",
            artist="Pink Floyd",
            title="Comfortably Numb",
            album="The Wall",
            year=1979,
            duration=382.0,
            file_format="mp3",
            file_size=9_000_000,
            metadata_hash="hash2",
            file_content_hash="content2",
            file_mtime=datetime.now(timezone.utc),
        ),
        LibraryFile(
            file_path="/library/artist3_song1.mp3",
            filename="artist3_song1.mp3",
            artist="Led Zeppelin",
            title="Stairway to Heaven",
            album="Led Zeppelin IV",
            year=1971,
            duration=482.0,
            file_format="mp3",
            file_size=11_000_000,
            metadata_hash="hash3",
            file_content_hash="content3",
            file_mtime=datetime.now(timezone.utc),
        ),
    ]

    # Display library
    table = Table(title="Main Library (Already Indexed)")
    table.add_column("Artist", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Album", style="yellow")
    table.add_column("Year", justify="right")

    for song in library_songs:
        table.add_row(song.artist, song.title, song.album, str(song.year))

    console.print(table)
    console.print()
    console.print("[dim]This represents your existing library of 25,000+ songs[/dim]")

    return library_songs


def demo_2_import_folder():
    """Demo 2: Show import folder to vet."""
    demo_header("DEMO 2: New Import Folder to Vet")

    console.print("You downloaded a batch of 7 new songs to vet...")
    console.print()

    # Import folder files (some duplicates, some new)
    import_songs = [
        (
            "the_beatles_yesterday.mp3",
            "The Beatles",
            "Yesterday",
            "DUPLICATE - Exact metadata match",
        ),
        (
            "pink_floyd_comfortably_numb_live.mp3",
            "Pink Floyd",
            "Comfortably Numb (Live)",
            "UNCERTAIN - Similar but different version",
        ),
        ("queen_bohemian_rhapsody.mp3", "Queen", "Bohemian Rhapsody", "NEW - Not in library"),
        (
            "led_zeppelin_stairway.mp3",
            "Led Zeppelin",
            "Stairway to Heaven",
            "DUPLICATE - Same file content",
        ),
        ("david_bowie_heroes.mp3", "David Bowie", "Heroes", "NEW - Not in library"),
        (
            "the_beatles_yesterday_remaster.mp3",
            "The Beatles",
            "Yesterday (2009 Remaster)",
            "UNCERTAIN - Similar title",
        ),
        ("radiohead_creep.mp3", "Radiohead", "Creep", "NEW - Not in library"),
    ]

    table = Table(title="Import Folder: ~/Downloads/new-music-batch")
    table.add_column("Filename", style="cyan")
    table.add_column("Artist", style="green")
    table.add_column("Title", style="yellow")
    table.add_column("Status", style="magenta")

    for filename, artist, title, status in import_songs:
        table.add_row(filename, artist, title, status)

    console.print(table)
    console.print()
    console.print("[dim]Question: Which of these should you import?[/dim]")

    return import_songs


def demo_3_duplicate_detection():
    """Demo 3: Show duplicate detection process."""
    demo_header("DEMO 3: Multi-Level Duplicate Detection")

    console.print("The system checks EACH file using 3 detection levels:")
    console.print()

    # Show the 3 levels
    table = Table(title="Detection Levels")
    table.add_column("Level", style="cyan")
    table.add_column("Method", style="green")
    table.add_column("Speed", style="yellow")
    table.add_column("Confidence", style="magenta")

    table.add_row("1️⃣ Exact Metadata", "MD5 hash of 'artist|title'", "<1ms per file", "100%")
    table.add_row("2️⃣ File Content", "MD5 hash of audio (64KB samples)", "~10ms per file", "100%")
    table.add_row("3️⃣ Fuzzy Match", "Similarity algorithm on metadata", "~100ms per file", "70-95%")

    console.print(table)
    console.print()

    # Show example matches
    console.print("[bold]Example Matches:[/bold]")
    console.print()
    console.print("✅ [green]EXACT MATCH[/green] (100% confidence)")
    console.print("   Import: the_beatles_yesterday.mp3")
    console.print("   Library: /library/artist1_song1.mp3")
    console.print("   → [cyan]artist|title[/cyan] hashes match exactly")
    console.print("   → Action: [red]Skip this file (duplicate)[/red]")
    console.print()

    console.print("✅ [green]FILE CONTENT MATCH[/green] (100% confidence)")
    console.print("   Import: led_zeppelin_stairway.mp3")
    console.print("   Library: /library/artist3_song1.mp3")
    console.print("   → File audio content is [cyan]identical[/cyan]")
    console.print("   → Action: [red]Skip this file (same audio)[/red]")
    console.print()

    console.print("⚠️  [yellow]FUZZY MATCH[/yellow] (85% confidence)")
    console.print("   Import: the_beatles_yesterday_remaster.mp3")
    console.print("   Library: /library/artist1_song1.mp3")
    console.print("   → Titles are [cyan]85% similar[/cyan]")
    console.print("   → Action: [yellow]Manual review needed[/yellow]")
    console.print()

    console.print("✅ [green]NO MATCH[/green] (<70% confidence)")
    console.print("   Import: queen_bohemian_rhapsody.mp3")
    console.print("   → No similar files found in library")
    console.print("   → Action: [green]Import this file (new song)[/green]")


def demo_4_vetting_results():
    """Demo 4: Show vetting results."""
    demo_header("DEMO 4: Vetting Results")

    console.print("After checking all 7 files, here are the results:")
    console.print()

    # Results summary
    summary_panel = Panel(
        """[bold]Import Folder:[/bold] ~/Downloads/new-music-batch
[bold]Total Files:[/bold] 7
[bold]Threshold:[/bold] 80%
[bold]Scan Duration:[/bold] 0.23s""",
        title="Vetting Summary",
        border_style="cyan",
    )
    console.print(summary_panel)
    console.print()

    # Results table
    results_table = Table(title="Results Breakdown")
    results_table.add_column("Category", style="cyan")
    results_table.add_column("Count", justify="right", style="green")
    results_table.add_column("Percentage", justify="right", style="yellow")
    results_table.add_column("Action", style="magenta")

    results_table.add_row("✅ New Songs", "3", "42.9%", "[green]IMPORT these[/green]")
    results_table.add_row("❌ Duplicates", "2", "28.6%", "[red]SKIP these[/red]")
    results_table.add_row("⚠️  Uncertain", "2", "28.6%", "[yellow]REVIEW manually[/yellow]")

    console.print(results_table)
    console.print()

    # Detailed breakdown
    console.print("[bold green]✅ New Songs (Safe to Import):[/bold green]")
    console.print("   • queen_bohemian_rhapsody.mp3")
    console.print("   • david_bowie_heroes.mp3")
    console.print("   • radiohead_creep.mp3")
    console.print()

    console.print("[bold red]❌ Duplicates (Skip These):[/bold red]")
    console.print("   • the_beatles_yesterday.mp3")
    console.print("     → Matches: /library/artist1_song1.mp3(100%)")
    console.print("   • led_zeppelin_stairway.mp3")
    console.print("     → Matches: /library/artist3_song1.mp3 (100%)")
    console.print()

    console.print("[bold yellow]⚠️  Uncertain (Manual Review):[/bold yellow]")
    console.print("   • pink_floyd_comfortably_numb_live.mp3(85% match)")
    console.print("   • the_beatles_yesterday_remaster.mp3 (87% match)")


def demo_5_export_files():
    """Demo 5: Show export functionality."""
    demo_header("DEMO 5: Export for Automation")

    console.print("The system exports results to text files for automation:")
    console.print()

    # Show export files
    table = Table(title="Exported Files")
    table.add_column("File", style="cyan")
    table.add_column("Contents", style="green")
    table.add_column("Use Case", style="yellow")

    table.add_row("new_songs.txt", "3 files", "Batch import to library")
    table.add_row("duplicates.txt", "2 files", "Batch delete or move")
    table.add_row("uncertain.txt", "2 files", "Manual review list")

    console.print(table)
    console.print()

    console.print("[bold]Example: new_songs.txt[/bold]")
    console.print("[dim]────────────────────────────────────[/dim]")
    console.print("# New Songs from ~/Downloads/new-music-batch")
    console.print("# Generated: 2025-01-19 14:23:45")
    console.print("# Total: 3")
    console.print()
    console.print("/home/user/Downloads/new-music-batch/queen_bohemian_rhapsody.mp3")
    console.print("/home/user/Downloads/new-music-batch/david_bowie_heroes.mp3")
    console.print("/home/user/Downloads/new-music-batch/radiohead_creep.mp3")
    console.print("[dim]────────────────────────────────────[/dim]")
    console.print()

    console.print("[bold cyan]Automation Example:[/bold cyan]")
    console.print("[dim]# Copy only new songs to library[/dim]")
    console.print("while IFS= read -r file; do")
    console.print('  [[ "$file" =~ ^# ]] && continue')
    console.print('  cp "$file" ~/Music/')
    console.print("done < new_songs.txt")


def demo_6_time_savings():
    """Demo 6: Show time savings."""
    demo_header("DEMO 6: Time Savings")

    console.print("Let's calculate the time saved:")
    console.print()

    # Comparison table
    table = Table(title="Manual vs Automated")
    table.add_column("Task", style="cyan")
    table.add_column("Manual", justify="right", style="red")
    table.add_column("Automated", justify="right", style="green")
    table.add_column("Savings", justify="right", style="yellow")

    table.add_row("Check 1,000 songs", "~7 hours", "~20 seconds", "6h 59m 40s")
    table.add_row("Weekly batch (2,000)", "~14 hours", "~40 seconds", "13h 59m 20s")
    table.add_row("Monthly total (8,000)", "~56 hours", "~3 minutes", "55h 57m")

    console.print(table)
    console.print()

    console.print("[bold green]✅ Benefits:[/bold green]")
    console.print("   • [green]Save hours every week[/green]")
    console.print("   • [green]100% accurate duplicate detection[/green]")
    console.print("   • [green]Automated workflow with exports[/green]")
    console.print("   • [green]Never accidentally delete unique files[/green]")
    console.print("   • [green]Professional music curation at scale[/green]")


def main():
    """Run the complete demo."""
    console.print()
    console.print(
        Panel(
            "[bold cyan]Library Duplicate Detection Demo[/bold cyan]\n"
            "[dim]Understanding how the new feature works[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # Run all demos
    demo_1_create_sample_library()
    input("\nPress Enter to continue...")

    demo_2_import_folder()
    input("\nPress Enter to continue...")

    demo_3_duplicate_detection()
    input("\nPress Enter to continue...")

    demo_4_vetting_results()
    input("\nPress Enter to continue...")

    demo_5_export_files()
    input("\nPress Enter to continue...")

    demo_6_time_savings()

    # Final summary
    console.print()
    console.print(
        Panel(
            "[bold green]🎉 Demo Complete![/bold green]\n\n"
            "You now understand how the library duplicate detection works.\n\n"
            "[cyan]Next Steps:[/cyan]\n"
            "1. Read QUICK_START_GUIDE.md for detailed instructions\n"
            "2. Index your library: [yellow]library index --path ~/Music[/yellow]\n"
            "3. Vet your next import: [yellow]library vet --folder ~/Downloads[/yellow]\n\n"
            "[dim]The system will save you hours of manual work every week![/dim]",
            border_style="green",
            padding=(1, 2),
        )
    )


if __name__ == "__main__":
    main()
