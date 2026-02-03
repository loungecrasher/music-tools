#!/usr/bin/env python3
"""
First-Run Setup Wizard for Music Tools.
Guides users through initial configuration in <10 minutes.
"""
import os
import sys
from pathlib import Path

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'packages'))

from music_tools_common.config import config_manager

console = Console()


class SetupWizard:
    """First-run setup wizard."""

    def __init__(self):
        self.config_dir = Path.home() / '.music_tools'
        self.env_file = Path(__file__).parent / '.env'
        self.env_example = Path(__file__).parent / '.env.example'
        self.setup_complete_marker = self.config_dir / '.setup_complete'

    def needs_setup(self) -> bool:
        """Check if first-run setup is needed."""
        return not self.setup_complete_marker.exists()

    def run(self) -> bool:
        """Run the setup wizard. Returns True if setup completed successfully."""
        console.clear()

        # Welcome screen
        self.show_welcome()

        if not Confirm.ask("\n[bold cyan]Would you like to run the setup wizard?[/bold cyan]", default=True):
            console.print("\n[yellow]You can run setup later with:[/yellow] python3 setup_wizard.py")
            return False

        # Step 1: Create config directory
        if not self.setup_config_directory():
            return False

        # Step 2: Spotify configuration
        spotify_configured = self.configure_spotify()

        # Step 3: Deezer configuration (optional)
        deezer_configured = self.configure_deezer()

        # Step 4: Summary
        self.show_summary(spotify_configured, deezer_configured)

        # Mark setup as complete
        self.setup_complete_marker.touch()

        return True

    def show_welcome(self):
        """Display welcome screen."""
        welcome_text = """
[bold cyan]Welcome to Music Tools![/bold cyan]

This wizard will help you configure your music management suite in less than 10 minutes.

[bold]What you'll configure:[/bold]
• [green]✓[/green] Spotify integration (required for most features)
• [yellow]○[/yellow] Deezer integration (optional)
• [green]✓[/green] Application settings

[bold]What you'll need:[/bold]
• Spotify Developer credentials (get free at https://developer.spotify.com/dashboard)
• Optional: Deezer account email

[dim]This wizard only needs to run once. You can reconfigure later if needed.[/dim]
"""
        console.print(Panel(welcome_text, title="[bold]Setup Wizard[/bold]", border_style="cyan"))

    def setup_config_directory(self) -> bool:
        """Create configuration directory."""
        console.print("\n[bold]Step 1:[/bold] Creating configuration directory...")

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]✓[/green] Created: {self.config_dir}")
            return True
        except Exception as e:
            console.print(f"[bold red]✗ Error creating config directory:[/bold red] {e}")
            return False

    def configure_spotify(self) -> bool:
        """Configure Spotify integration."""
        console.print("\n[bold]Step 2:[/bold] Spotify Configuration")
        console.print("[dim]Spotify is required for most music management features.[/dim]\n")

        if not Confirm.ask("Configure Spotify now?", default=True):
            console.print("[yellow]⚠ Skipped - You can configure Spotify later from the Configuration menu[/yellow]")
            return False

        # Show instructions
        instructions = """
[bold]How to get Spotify credentials:[/bold]

1. Go to: [link]https://developer.spotify.com/dashboard[/link]
2. Click "Create app"
3. Fill in:
   • App name: "Music Tools"
   • App description: "Personal music management"
   • Redirect URI: [bold cyan]http://127.0.0.1:8888/callback[/bold cyan] [bold red]← IMPORTANT![/bold red]
4. Copy your Client ID and Client Secret

[bold red]NOTE:[/bold red] Must use [bold]127.0.0.1[/bold] (not localhost) as of Nov 27, 2025!
"""
        console.print(Panel(instructions, border_style="blue"))

        if not Confirm.ask("\nReady to enter your Spotify credentials?", default=True):
            return False

        # Get credentials
        client_id = Prompt.ask("\nSpotify Client ID", default="")
        if not client_id:
            console.print("[yellow]⚠ Skipped Spotify configuration[/yellow]")
            return False

        client_secret = Prompt.ask("Spotify Client Secret", password=True)
        if not client_secret:
            console.print("[yellow]⚠ Skipped Spotify configuration[/yellow]")
            return False

        redirect_uri = Prompt.ask(
            "Spotify Redirect URI",
            default="http://127.0.0.1:8888/callback"
        )

        # Save configuration
        try:
            config = {
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri
            }
            config_manager.save_config('spotify', config)
            console.print("[green]✓ Spotify configured successfully![/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]✗ Error saving Spotify config:[/bold red] {e}")
            return False

    def configure_deezer(self) -> bool:
        """Configure Deezer integration (optional)."""
        console.print("\n[bold]Step 3:[/bold] Deezer Configuration (Optional)")
        console.print("[dim]Deezer is used for playlist repair and cross-platform features.[/dim]\n")

        if not Confirm.ask("Configure Deezer now?", default=False):
            console.print("[dim]○ Skipped - You can configure Deezer later if needed[/dim]")
            return False

        email = Prompt.ask("\nDeezer account email", default="")
        if not email:
            console.print("[dim]○ Skipped Deezer configuration[/dim]")
            return False

        try:
            config = {'email': email}
            config_manager.save_config('deezer', config)
            console.print("[green]✓ Deezer configured successfully![/green]")
            return True
        except Exception as e:
            console.print(f"[bold red]✗ Error saving Deezer config:[/bold red] {e}")
            return False

    def show_summary(self, spotify: bool, deezer: bool):
        """Show setup summary."""
        console.print("\n" + "="*70)
        console.print("[bold cyan]Setup Complete![/bold cyan]\n")

        # Create summary table
        table = Table(title="Configuration Summary", show_header=True)
        table.add_column("Feature", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Available Features")

        table.add_row(
            "Spotify",
            "[green]✓ Configured[/green]" if spotify else "[yellow]⚠ Not configured[/yellow]",
            "Playlists, Library, Tracks" if spotify else "[dim]Configure to enable[/dim]"
        )

        table.add_row(
            "Deezer",
            "[green]✓ Configured[/green]" if deezer else "[dim]○ Not configured[/dim]",
            "Playlist repair, Cross-platform" if deezer else "[dim]Optional[/dim]"
        )

        console.print(table)

        # Next steps
        next_steps = """
[bold]Next Steps:[/bold]

1. Run the application:
   [cyan]python3 menu.py[/cyan]

2. Start with Spotify features (if configured)
3. Explore the menu to discover all 9 features

[bold]Need help?[/bold]
• Documentation: See docs/guides/HOW_TO_RUN.md
• Reconfigure: Run Configuration menu option
• Support: Check docs/reviews/ for detailed guides

[green]You're all set! Enjoy Music Tools![/green]
"""
        console.print(Panel(next_steps, border_style="green"))


def main():
    """Main entry point for setup wizard."""
    wizard = SetupWizard()

    if not wizard.needs_setup():
        console.print("\n[yellow]Setup has already been completed.[/yellow]")
        if Confirm.ask("Run setup again?", default=False):
            wizard.setup_complete_marker.unlink()
        else:
            console.print("\nTo reconfigure, use the Configuration menu in the main application.")
            return

    success = wizard.run()

    if success:
        console.print("\n[bold green]✓ Setup completed successfully![/bold green]")
        console.print("\nRun: [cyan]python3 menu.py[/cyan] to start using Music Tools\n")
    else:
        console.print("\n[yellow]Setup was not completed. You can run it again anytime.[/yellow]\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Setup cancelled by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Setup error:[/bold red] {e}")
        sys.exit(1)
