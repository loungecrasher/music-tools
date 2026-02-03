"""
Common CLI helper functions for Music Tools.
Provides reusable functions for console output, user input, and progress display.
"""
from typing import Optional, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.status import Status

console = Console()


def print_error(message: str, details: Optional[str] = None) -> None:
    """
    Print an error message in a consistent format.

    Args:
        message: Main error message
        details: Additional error details (optional)
    """
    if details:
        console.print(f"\n[bold red]{message}:[/bold red] {details}")
    else:
        console.print(f"\n[bold red]{message}[/bold red]")


def print_success(message: str) -> None:
    """
    Print a success message in a consistent format.

    Args:
        message: Success message
    """
    console.print(f"\n[bold green]✓ {message}[/bold green]")


def print_warning(message: str) -> None:
    """
    Print a warning message in a consistent format.

    Args:
        message: Warning message
    """
    console.print(f"\n[bold yellow]⚠ {message}[/bold yellow]")


def print_info(message: str) -> None:
    """
    Print an info message in a consistent format.

    Args:
        message: Info message
    """
    console.print(f"\n[cyan]{message}[/cyan]")


def pause(message: str = "Press Enter to continue") -> None:
    """
    Pause execution and wait for user to press Enter.

    Args:
        message: Message to display
    """
    Prompt.ask(f"\n{message}", default="")


def confirm(message: str, default: bool = False) -> bool:
    """
    Ask user for confirmation.

    Args:
        message: Confirmation message
        default: Default value if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    return Confirm.ask(message, default=default)


def prompt(message: str, default: str = "", password: bool = False) -> str:
    """
    Prompt user for input.

    Args:
        message: Prompt message
        default: Default value if user just presses Enter
        password: Whether to hide input (for passwords)

    Returns:
        User's input
    """
    return Prompt.ask(message, default=default, password=password)


def show_panel(
    content: str,
    title: Optional[str] = None,
    border_style: str = "blue",
    expand: bool = True
) -> None:
    """
    Display content in a Rich panel.

    Args:
        content: Content to display
        title: Optional panel title
        border_style: Border color/style
        expand: Whether to expand panel to full width
    """
    console.print(Panel(
        content,
        title=f"[bold]{title}[/bold]" if title else None,
        border_style=border_style,
        expand=expand,
        padding=(1, 2)
    ))


def create_progress_bar(description: str = "Processing") -> Progress:
    """
    Create a Rich progress bar with standard configuration.

    Args:
        description: Description to show next to progress bar

    Returns:
        Configured Progress instance
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    )


def show_status(message: str, spinner: str = "dots") -> Status:
    """
    Create a Rich status spinner.

    Args:
        message: Status message
        spinner: Spinner style

    Returns:
        Status instance (use with 'with' statement)

    Example:
        with show_status("Loading data..."):
            # Do work
            pass
    """
    return console.status(f"[bold green]{message}[/bold green]", spinner=spinner)


def clear_screen() -> None:
    """
    Clear the terminal screen in a cross-platform way.
    """
    import os
    # SECURITY FIX: Use os.system instead of subprocess with shell=True
    # to avoid command injection vulnerabilities
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """
    Print a formatted header.

    Args:
        title: Main title
        subtitle: Optional subtitle
    """
    from rich.text import Text

    header_text = Text(title, style="bold cyan")
    if subtitle:
        header_text.append(f"\n{subtitle}", style="dim")

    console.print(Panel(
        header_text,
        border_style="cyan",
        padding=(1, 2)
    ))


def format_error_details(exception: Exception) -> str:
    """
    Format exception details for display.

    Args:
        exception: Exception to format

    Returns:
        Formatted error string
    """
    import traceback
    return f"{type(exception).__name__}: {str(exception)}\n{traceback.format_exc()}"
