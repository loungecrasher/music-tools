"""
Formatted output utilities for CLI applications.
"""

from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


console = Console()


def print_table(
    data: List[Dict[str, Any]],
    title: Optional[str] = None,
    columns: Optional[List[str]] = None,
) -> None:
    """
    Print data as a formatted table.

    Args:
        data: List of dictionaries with table data
        title: Optional table title
        columns: Column names (defaults to data keys)
    """
    if not data:
        console.print("[yellow]No data to display[/yellow]")
        return

    # Get columns from first row if not provided
    if columns is None:
        columns = list(data[0].keys())

    # Create table
    table = Table(title=title, show_header=True, header_style="bold cyan")

    # Add columns
    for col in columns:
        table.add_column(col, style="green")

    # Add rows
    for row in data:
        table.add_row(*[str(row.get(col, "")) for col in columns])

    console.print(table)


def print_panel(
    content: str,
    title: Optional[str] = None,
    style: str = "blue",
) -> None:
    """
    Print content in a panel.

    Args:
        content: Content to display
        title: Optional panel title
        style: Border style color
    """
    panel = Panel(
        content,
        title=title,
        border_style=style,
        padding=(1, 2),
    )
    console.print(panel)


def print_success(message: str, title: str = "Success") -> None:
    """Print success message."""
    print_panel(message, title=f"✓ {title}", style="green")


def print_error(message: str, title: str = "Error") -> None:
    """Print error message."""
    print_panel(message, title=f"✗ {title}", style="red")


def print_warning(message: str, title: str = "Warning") -> None:
    """Print warning message."""
    print_panel(message, title=f"⚠ {title}", style="yellow")


def print_info(message: str, title: str = "Info") -> None:
    """Print info message."""
    print_panel(message, title=f"ℹ {title}", style="cyan")


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


def format_rate(count: int, seconds: float, unit: str = "items") -> str:
    """
    Format processing rate.

    Args:
        count: Number of items processed
        seconds: Time elapsed
        unit: Unit name for items

    Returns:
        Formatted rate string
    """
    if seconds > 0:
        rate = count / seconds
        return f"{rate:.1f} {unit}/s"
    return f"0 {unit}/s"
