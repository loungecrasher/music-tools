"""
Enhanced progress display utilities with ETA support.

Provides progress bars, spinners, and status displays with:
- Estimated time remaining (ETA)
- Throughput metrics (items/sec)
- Memory-efficient updates
"""

from contextlib import contextmanager
from typing import Any, Callable, Iterable, Iterator, Optional, TypeVar

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

from .menu import THEME, get_themed_style

console = Console()
T = TypeVar("T")


# ==========================================
# Progress Bar Configurations
# ==========================================


def create_progress_bar(
    description: str = "Processing...",
    show_eta: bool = True,
    show_speed: bool = True,
    show_percentage: bool = True,
    transient: bool = False,
) -> Progress:
    """Create a customized progress bar with optional ETA and speed.

    Args:
        description: Description text to show
        show_eta: Whether to show estimated time remaining
        show_speed: Whether to show processing speed
        show_percentage: Whether to show percentage complete
        transient: If True, progress bar disappears when done

    Returns:
        Configured Rich Progress object
    """
    columns = [
        SpinnerColumn(),
        TextColumn(f"[{get_themed_style('primary')}]{{task.description}}[/]"),
        BarColumn(bar_width=40),
    ]

    if show_percentage:
        columns.append(TaskProgressColumn())

    columns.append(MofNCompleteColumn())

    if show_eta:
        columns.append(TimeRemainingColumn())

    columns.append(TimeElapsedColumn())

    return Progress(*columns, console=console, transient=transient)


@contextmanager
def progress_context(
    total: int, description: str = "Processing...", show_eta: bool = True, unit: str = "items"
):
    """Context manager for progress tracking with ETA.

    Args:
        total: Total number of items to process
        description: Description text to show
        show_eta: Whether to show estimated time remaining
        unit: Unit name for display (e.g., "files", "tracks")

    Yields:
        Tuple of (progress, task_id) for updating progress

    Example:
        >>> with progress_context(1000, "Indexing files") as (progress, task):
        ...     for file in files:
        ...         process(file)
        ...         progress.advance(task)
    """
    progress = create_progress_bar(description, show_eta=show_eta)

    with progress:
        task = progress.add_task(description, total=total)
        yield progress, task


def iterate_with_progress(
    items: Iterable[T],
    total: Optional[int] = None,
    description: str = "Processing...",
    show_eta: bool = True,
) -> Iterator[T]:
    """Iterate over items with automatic progress tracking.

    Args:
        items: Iterable to process
        total: Total count (if known, enables ETA)
        description: Description text to show
        show_eta: Whether to show estimated time remaining

    Yields:
        Items from the iterator

    Example:
        >>> for file in iterate_with_progress(files, len(files), "Scanning"):
        ...     process(file)
    """
    # Convert to list if total not provided to get count
    if total is None:
        items = list(items)
        total = len(items)

    progress = create_progress_bar(description, show_eta=show_eta)

    with progress:
        task = progress.add_task(description, total=total)

        for item in items:
            yield item
            progress.advance(task)


# ==========================================
# Status Display
# ==========================================


class StatusBar:
    """Persistent status bar showing connection and library status."""

    def __init__(self):
        self.services: dict = {}
        self.library_stats: dict = {}

    def set_service_status(self, service: str, connected: bool, details: str = "") -> None:
        """Set connection status for a service.

        Args:
            service: Service name (e.g., "Spotify", "Deezer")
            connected: Whether service is connected
            details: Additional details (e.g., username)
        """
        self.services[service] = {"connected": connected, "details": details}

    def set_library_stats(self, total_files: int = 0, indexed: bool = False) -> None:
        """Set library statistics.

        Args:
            total_files: Total files in library
            indexed: Whether library has been indexed
        """
        self.library_stats = {"total_files": total_files, "indexed": indexed}

    def render(self) -> Panel:
        """Render the status bar as a Rich Panel.

        Returns:
            Rich Panel with status information
        """
        status_parts = []

        # Service status
        for service, status in self.services.items():
            if status["connected"]:
                icon = "✓"
                style = get_themed_style("success")
                detail = f" ({status['details']})" if status["details"] else ""
            else:
                icon = "✗"
                style = get_themed_style("error")
                detail = ""

            status_parts.append(f"[{style}]{service}: {icon}{detail}[/]")

        # Library status
        if self.library_stats:
            if self.library_stats["indexed"]:
                files = self.library_stats["total_files"]
                status_parts.append(f"[{get_themed_style('info')}]Library: {files:,} files[/]")
            else:
                status_parts.append(f"[{get_themed_style('warning')}]Library: Not indexed[/]")

        status_text = " │ ".join(status_parts) if status_parts else "No services configured"

        return Panel(status_text, border_style=get_themed_style("muted"), padding=(0, 1))

    def display(self) -> None:
        """Display the status bar."""
        console.print(self.render())


# ==========================================
# Operation Summaries
# ==========================================


def show_operation_summary(operation: str, results: dict, duration: Optional[float] = None) -> None:
    """Display a summary of an operation's results.

    Args:
        operation: Name of the operation (e.g., "Library Index")
        results: Dictionary of result metrics
        duration: Optional duration in seconds

    Example:
        >>> show_operation_summary("Library Index", {
        ...     "Added": 150,
        ...     "Updated": 30,
        ...     "Skipped": 800,
        ...     "Errors": 2
        ... }, duration=45.2)
    """
    table = Table(title=f"{operation} Results", show_header=True)
    table.add_column("Metric", style=get_themed_style("primary"))
    table.add_column("Value", style=get_themed_style("success"), justify="right")

    for metric, value in results.items():
        # Color errors differently
        if metric.lower() in ("errors", "failed", "error"):
            if value > 0:
                table.add_row(metric, f"[{get_themed_style('error')}]{value:,}[/]")
            else:
                table.add_row(metric, f"[{get_themed_style('muted')}]{value}[/]")
        elif metric.lower() in ("success", "added", "new"):
            table.add_row(metric, f"[{get_themed_style('success')}]{value:,}[/]")
        elif metric.lower() in ("warning", "skipped", "uncertain"):
            table.add_row(metric, f"[{get_themed_style('warning')}]{value:,}[/]")
        else:
            table.add_row(metric, f"{value:,}" if isinstance(value, int) else str(value))

    if duration is not None:
        # Calculate throughput if we have a total
        total = sum(v for v in results.values() if isinstance(v, (int, float)))
        if total > 0 and duration > 0:
            throughput = total / duration
            table.add_row("", "")  # Separator
            table.add_row("Duration", f"{duration:.1f}s")
            table.add_row("Throughput", f"{throughput:.1f}/sec")

    console.print()
    console.print(table)


def show_confirmation_preview(
    action: str,
    items: list,
    max_preview: int = 10,
    item_formatter: Optional[Callable[[Any], str]] = None,
) -> bool:
    """Show a preview of items and ask for confirmation.

    Args:
        action: Action to be performed (e.g., "Delete")
        items: List of items that will be affected
        max_preview: Maximum items to preview
        item_formatter: Optional function to format items for display

    Returns:
        True if user confirms, False otherwise
    """
    from rich.prompt import Confirm
    from rich.tree import Tree

    # Format action with color
    action_style = (
        get_themed_style("error") if "delete" in action.lower() else get_themed_style("warning")
    )

    console.print(f"\n[{action_style}]{action}[/] - {len(items)} items will be affected:\n")

    tree = Tree(f"📋 Items to {action.lower()}")

    for i, item in enumerate(items[:max_preview]):
        if item_formatter:
            display = item_formatter(item)
        else:
            display = str(item)
        tree.add(display)

    if len(items) > max_preview:
        tree.add(f"[{get_themed_style('muted')}]... and {len(items) - max_preview} more[/]")

    console.print(tree)
    console.print()

    return Confirm.ask(f"[{action_style}]Proceed with {action.lower()}?[/]", default=False)


# Global status bar instance
status_bar = StatusBar()
