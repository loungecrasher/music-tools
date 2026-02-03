"""
Interactive Setup Example for music_tools_common.config

This example demonstrates the interactive configuration wizard.
Requires: pip install rich
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigManager


def main():
    """Demonstrate interactive configuration setup."""

    try:
        from rich.console import Console
        from rich.panel import Panel
    except ImportError:
        print("Error: This example requires the 'rich' library.")
        print("Install it with: pip install rich")
        return

    console = Console()

    console.print(
        Panel.fit(
            "[bold cyan]Music Tools Configuration Setup[/bold cyan]\n"
            "Interactive configuration wizard example",
            title="Setup Wizard",
        )
    )

    # Initialize the configuration manager
    manager = ConfigManager(app_name="music_tools_example")

    console.print("\n[bold]Configuration directory:[/bold]", manager.config_dir)
    console.print(
        "\n[yellow]Note: Sensitive data (API keys, secrets) should be stored in .env file[/yellow]"
    )
    console.print(
        "[yellow]Create a .env file in the config directory with your credentials[/yellow]\n"
    )

    # Run interactive setup for each service
    services = ["spotify", "deezer", "anthropic"]

    for service in services:
        console.print(f"\n[bold blue]Setting up {service}...[/bold blue]")

        try:
            manager.interactive_setup(service)
            console.print(f"[green]✓ {service.title()} configuration complete[/green]")
        except KeyboardInterrupt:
            console.print(f"\n[yellow]Skipped {service} setup[/yellow]")
        except Exception as e:
            console.print(f"[red]Error setting up {service}: {e}[/red]")

    console.print("\n" + "=" * 60)
    console.print("[bold green]Setup complete![/bold green]")
    console.print(f"Configuration saved to: {manager.config_dir}")
    console.print("\n[yellow]Remember to add your API keys to the .env file![/yellow]")
    console.print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
