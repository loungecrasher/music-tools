"""Menu handlers for external tool launching (scraper, tagger, scripts)."""

import logging
import os
import subprocess
import sys

from music_tools_common.cli import clear_screen
from music_tools_common.config import config_manager
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

logger = logging.getLogger(__name__)
console = Console()


def _get_config(service: str):
    """Get configuration for a service."""
    return config_manager.load_config(service)


def run_tool(script_path: str) -> None:
    """Execute a tool script with Python 3.

    Args:
        script_path: Path to the script to execute
    """
    try:
        # Check if script exists
        if not os.path.isfile(script_path):
            console.print(f"\n[bold red]Tool script not found:[/bold red] {script_path}")
            Prompt.ask("\nPress Enter to continue")
            return

        script_name = os.path.basename(script_path)
        script_dir = os.path.dirname(script_path)

        # Prepare environment variables for the subprocess
        env = os.environ.copy()

        # If running Spotify script, add Spotify credentials to environment
        if "Spotify Script" in script_path:
            spotify_config = _get_config('spotify')
            if spotify_config:
                env['SPOTIPY_CLIENT_ID'] = spotify_config.get('client_id', '')
                env['SPOTIPY_CLIENT_SECRET'] = spotify_config.get('client_secret', '')
                env['SPOTIPY_REDIRECT_URI'] = spotify_config.get('redirect_uri', 'http://localhost:8888/callback')
                console.print("[dim]Added Spotify credentials to environment[/dim]")

        # For interactive tools, run with direct output to console
        if (
            "Library Comparison" in script_path
            or "deezer_playlist_checker.py" in script_path
            or "main_debug.py" in script_path
            or "main_fixed.py" in script_path
            or "EDM Sharing Site Web Scrapper" in script_path
            or "music_tagger" in script_path
        ):
            console.print(f"\n[bold green]Running {script_name} directly...[/bold green]")
            process = subprocess.Popen(
                [sys.executable, script_path],
                env=env,
                cwd=script_dir or None
            )
            process.wait()
            return_code = process.returncode

            if return_code == 0:
                console.print(f"\n[bold green]✓ {script_name} completed successfully![/bold green]")
            else:
                console.print(f"\n[bold red]✗ {script_name} failed with error code: {return_code}[/bold red]")

            Prompt.ask("\nPress Enter to continue")
            return

        # For other tools, show a spinner while the tool is running
        with console.status(f"[bold green]Running {script_name}...[/bold green]", spinner="dots"):
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=script_dir or None
            )
            stdout, stderr = process.communicate()
            return_code = process.returncode

        if return_code == 0:
            console.print(f"\n[bold green]✓ {script_name} completed successfully![/bold green]")

            if stdout and stdout.strip():
                console.print(Panel(
                    stdout.strip(),
                    title="[cyan]Output[/cyan]",
                    border_style="cyan",
                    expand=False
                ))
        else:
            console.print(f"\n[bold red]✗ {script_name} failed with error code: {return_code}[/bold red]")

            if stderr and stderr.strip():
                console.print(Panel(
                    stderr.strip(),
                    title="[red]Error Output[/red]",
                    border_style="red",
                    expand=False
                ))

        Prompt.ask("\nPress Enter to continue")
    except subprocess.CalledProcessError as e:
        console.print(f"\n[bold red]Error running tool:[/bold red] {e}")
        Prompt.ask("\nPress Enter to continue")
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Tool execution interrupted.[/bold yellow]")
        Prompt.ask("\nPress Enter to continue")


def run_edm_blog_scraper() -> None:
    """Launch the EDM blog scraper tool (integrated module)."""
    clear_screen()

    try:
        from src.scraping import cli_scraper
        cli_scraper.main()
    except ImportError as e:
        console.print(f"[bold red]Error importing EDM scraper module:[/bold red] {e}")
        console.print("[yellow]The scraper module should be in src/scraping/[/yellow]")
        Prompt.ask("\nPress Enter to continue")
    except Exception as e:
        console.print(f"[bold red]Error running EDM scraper:[/bold red] {e}")
        Prompt.ask("\nPress Enter to continue")


def run_music_country_tagger() -> None:
    """Launch the Music Library Country Tagger tool (integrated module)."""
    clear_screen()

    try:
        from src.tagging import cli
        cli.main()
    except ImportError as e:
        console.print(f"[bold red]Error importing music tagger module:[/bold red] {e}")
        console.print("[yellow]The tagger module should be in src/tagging/[/yellow]")
        Prompt.ask("\nPress Enter to continue")
    except Exception as e:
        console.print(f"[bold red]Error running music tagger:[/bold red] {e}")
        Prompt.ask("\nPress Enter to continue")
