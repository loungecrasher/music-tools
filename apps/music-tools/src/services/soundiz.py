"""Wrapper around the Soundiiz processor."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
from types import ModuleType

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

_MODULE: ModuleType | None = None

console = Console()


def _load_module() -> ModuleType:
    global _MODULE
    if _MODULE is None:
        module_path = Path(__file__).resolve().parents[2] / "Soundiz File Maker" / "process_music.py"
        spec = importlib.util.spec_from_file_location("soundiz_processor", module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load Soundiz processor from {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        _MODULE = module
    return _MODULE


def process_soundiz_csv(*args, **kwargs):  # type: ignore[no-untyped-def]
    return getattr(_load_module(), "process_soundiz_csv")(*args, **kwargs)


def SoundizResult():  # pragma: no cover - helper for type hints
    return getattr(_load_module(), "SoundizResult")


def run_soundiz_processor():
    """Interactive wrapper for Soundiiz CSV processor."""
    console.print(Panel(
        "[bold green]Soundiiz File Processor[/bold green]\n\n"
        "Generate a Soundiiz-ready text file from a CSV export.\n"
        "The tool will extract track titles and artists from your CSV\n"
        "and format them for import into Soundiiz.",
        title="[bold]Soundiiz CSV Processor[/bold]",
        border_style="green"
    ))

    input_path = Prompt.ask("\nEnter path to CSV file")
    input_path = input_path.strip("'\"")

    if not Path(input_path).is_file():
        console.print(f"[bold red]Error:[/bold red] {input_path} is not a valid file")
        Prompt.ask("\nPress Enter to continue")
        return

    output_path_str = Prompt.ask("Enter output file path (or press Enter for default)", default="")
    output_path = Path(output_path_str) if output_path_str else None

    title_field = Prompt.ask("Enter title column name", default="Title")
    artist_field = Prompt.ask("Enter artist column name", default="Artist")
    delimiter = Prompt.ask("Enter CSV delimiter", default=",")
    encoding = Prompt.ask("Enter CSV encoding", default="utf-8")

    console.print("\n[bold cyan]Processing CSV file...[/bold cyan]")
    console.print(f"Input: {input_path}")
    console.print(f"Title column: {title_field}")
    console.print(f"Artist column: {artist_field}")

    try:
        result = process_soundiz_csv(
            Path(input_path),
            output_path,
            title_field=title_field,
            artist_field=artist_field,
            delimiter=delimiter,
            encoding=encoding
        )

        console.print("\n[bold green]✓ Processing complete![/bold green]")
        console.print(f"Rows processed: {result.total_rows}")
        console.print(f"Rows written: {result.written_rows}")
        console.print(f"Output file: {result.output_path}")

    except Exception as e:
        console.print(f"[bold red]Error processing CSV:[/bold red] {str(e)}")

    Prompt.ask("\nPress Enter to continue")
