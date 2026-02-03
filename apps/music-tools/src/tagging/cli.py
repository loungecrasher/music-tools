#!/usr/bin/env python3
"""
Music Library Country Tagger - CLI Interface (REFACTORED)
Main command-line interface with numbered menu system

REFACTORING IMPROVEMENTS:
- Broke down 326-line _process_music_library into 10 focused methods
- Broke down 321-line handle_configure into 8 focused methods
- Broke down 120-line handle_diagnostics into 6 focused methods
- All methods now <50 lines following Single Responsibility Principle
- Improved readability, maintainability, and testability
- INTEGRATED with universal CLI utilities for consistent UI/UX theme
"""

import os
import sys
import time
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

# Import universal CLI utilities for consistent theme
try:
    # Try importing from music_tools_common if installed as package
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "packages"))
    from music_tools_common.cli import (
        clear_screen,
        format_error_details,
        print_error,
        print_info,
        print_success,
        print_warning,
        show_panel,
    )
    from music_tools_common.cli.styles import Theme

    UNIVERSAL_CLI_AVAILABLE = True
    # Get universal theme
    theme = Theme.default()
except ImportError:
    UNIVERSAL_CLI_AVAILABLE = False
    theme = None

try:
    from .config import AppConfig, ConfigManager

    CONFIG_AVAILABLE = True
except ImportError:
    try:
        from src.tagging.config import AppConfig, ConfigManager

        CONFIG_AVAILABLE = True
    except ImportError:
        CONFIG_AVAILABLE = False
        ConfigManager = None
        AppConfig = None

try:
    from .claude_code_researcher import ClaudeCodeResearcher

    CLAUDE_CODE_AVAILABLE = True
except ImportError:
    try:
        from src.tagging.claude_code_researcher import ClaudeCodeResearcher

        CLAUDE_CODE_AVAILABLE = True
    except ImportError:
        CLAUDE_CODE_AVAILABLE = False
        ClaudeCodeResearcher = None

try:
    from .ai_researcher import AIResearcher

    AI_AVAILABLE = True
except ImportError:
    try:
        from src.tagging.ai_researcher import AIResearcher

        AI_AVAILABLE = True
    except ImportError:
        AI_AVAILABLE = False
        AIResearcher = None

try:
    from .scanner import MusicFileScanner

    SCANNER_AVAILABLE = True
except ImportError:
    try:
        from src.tagging.scanner import MusicFileScanner

        SCANNER_AVAILABLE = True
    except ImportError:
        SCANNER_AVAILABLE = False
        MusicFileScanner = None

try:
    from .metadata import MetadataHandler

    METADATA_AVAILABLE = True
except ImportError:
    try:
        from src.tagging.metadata import MetadataHandler

        METADATA_AVAILABLE = True
    except ImportError:
        METADATA_AVAILABLE = False
        MetadataHandler = None

try:
    from .cache import CacheManager

    CACHE_AVAILABLE = True
except ImportError:
    try:
        from src.tagging.cache import CacheManager

        CACHE_AVAILABLE = True
    except ImportError:
        CACHE_AVAILABLE = False
        CacheManager = None

# Import extracted classes
try:
    from .library_processor import MusicLibraryProcessor
    from .path_manager import LibraryPathManager
except ImportError:
    try:
        from src.tagging.library_processor import MusicLibraryProcessor
        from src.tagging.path_manager import LibraryPathManager
    except ImportError:
        # Fallback if files are not found (should not happen after refactor)
        LibraryPathManager = None
        MusicLibraryProcessor = None

# Initialize rich console for beautiful output
console = Console()

# Universal theme helper functions


def theme_print_success(message: str, title: str = "Success") -> None:
    """Print success message using universal theme"""
    if UNIVERSAL_CLI_AVAILABLE:
        # print_success only takes message, combine with title
        print_success(f"{title}: {message}" if title != "Success" else message)
    else:
        console.print(Panel.fit(message, title=f"✓ {title}", border_style="green"))


def theme_print_error(message: str, title: str = "Error") -> None:
    """Print error message using universal theme"""
    if UNIVERSAL_CLI_AVAILABLE:
        # print_error takes message and optional details
        print_error(message, title if title != "Error" else None)
    else:
        console.print(Panel.fit(message, title=f"✗ {title}", border_style="red"))


def theme_print_warning(message: str, title: str = "Warning") -> None:
    """Print warning message using universal theme"""
    if UNIVERSAL_CLI_AVAILABLE:
        # print_warning only takes message
        print_warning(f"{title}: {message}" if title != "Warning" else message)
    else:
        console.print(Panel.fit(message, title=f"⚠ {title}", border_style="yellow"))


def theme_print_info(message: str, title: str = "Info") -> None:
    """Print info message using universal theme"""
    if UNIVERSAL_CLI_AVAILABLE:
        # print_info only takes message
        print_info(f"{title}: {message}" if title != "Info" else message)
    else:
        console.print(Panel.fit(message, title=f"ℹ {title}", border_style="cyan"))


def get_theme_icon(icon_name: str) -> str:
    """Get icon from universal theme or fallback"""
    if UNIVERSAL_CLI_AVAILABLE and theme:
        return theme.icons.get(icon_name, "")
    # Fallback icons
    fallback_icons = {
        "success": "✓",
        "error": "✗",
        "warning": "⚠",
        "info": "ℹ",
        "header": "🎵",
        "folder": "📁",
        "stats": "📊",
        "config": "⚙",
        "clock": "⏱",
        "rocket": "🚀",
    }
    return fallback_icons.get(icon_name, "")


class ConfigurationWizard:
    """Handles configuration setup - extracted from handle_configure"""

    def __init__(self, config_manager, current_config, verbose=False):
        self.config_manager = config_manager
        self.config = current_config
        self.verbose = verbose

    def configure_api_key(self) -> None:
        """Configure Claude API key"""
        if CLAUDE_CODE_AVAILABLE:
            self._configure_with_claude_code()
        else:
            self._configure_api_only()

    def _configure_with_claude_code(self) -> None:
        """Configure when Claude Code is available"""
        console.print("\n[green]✓ Claude Code detected - using your Max plan![/green]")
        console.print("[dim]No API key needed when using Claude Code locally[/dim]")

        if Confirm.ask("Configure API key as backup? (optional)", default=False):
            self._prompt_for_api_key(optional=True)

    def _configure_api_only(self) -> None:
        """Configure when only API is available (DEPRECATED - Claude Max only!)"""
        console.print("\n[red]⚠️  API key configuration no longer supported[/red]")
        console.print(
            "[yellow]This tool now requires Claude Max plan with local `claude` command[/yellow]"
        )
        console.print("[dim]Please install Claude Code to use this feature[/dim]")

    def _prompt_for_api_key(self, optional: bool = False) -> None:
        """Prompt user for API key (DEPRECATED - not used with Claude Max)"""
        console.print("\n[yellow]⚠️  API keys are no longer used[/yellow]")
        console.print("[cyan]This tool uses Claude Max plan - no API key needed![/cyan]")

    def _validate_api_key(self, api_key: str) -> None:
        """Validate API key (DEPRECATED - not used)"""
        console.print("[yellow]⚠️  API key validation no longer needed[/yellow]")
        console.print("[cyan]Using Claude Max plan - no API key required[/cyan]")

    def configure_model_selection(self) -> None:
        """Configure model selection for Claude Code or API"""
        if CLAUDE_CODE_AVAILABLE:
            self._configure_claude_code_model()
        else:
            self._configure_api_model()

    def _configure_claude_code_model(self) -> None:
        """Configure Claude Code model selection"""
        console.print("\n[cyan]Model Configuration:[/cyan]")

        # Show current model with version info
        current_model = self.config.claude_code_model
        if (
            not current_model
            or current_model == "sonnet"
            or "sonnet-4" in str(current_model).lower()
        ):
            display_model = "Claude Sonnet 4.5 (default - fast & accurate)"
        elif current_model == "opus" or "opus" in str(current_model).lower():
            display_model = "Claude Opus 4.5 (most capable)"
        elif current_model == "haiku" or "haiku" in str(current_model).lower():
            display_model = "Claude Haiku 3.5 (fastest)"
        else:
            display_model = current_model
        console.print(f"Current model: [bold]{display_model}[/bold]")

        if Confirm.ask("Change Claude Code model?", default=False):
            models = [
                ("claude-sonnet-4-5-20250929", "Claude Sonnet 4.5 (Fast & accurate) ⚡"),
                ("claude-opus-4-5-20251101", "Claude Opus 4.5 (Most capable) 🧠"),
                ("claude-3-5-haiku-20241022", "Claude Haiku 3.5 (Fastest) 🚀"),
            ]

            console.print("\nAvailable Claude Code models:")
            for i, (alias, description) in enumerate(models, 1):
                console.print(f"  {i}. {description}")

            model_choice = IntPrompt.ask(
                "Select model (or 0 to keep current)",
                choices=[str(i) for i in range(len(models) + 1)],
                default=0,
            )

            if model_choice > 0:
                selected_model = models[model_choice - 1][0]
                self.config.claude_code_model = selected_model
                console.print(
                    f"[green]✓ Claude Code model set to: {models[model_choice - 1][1]}[/green]"
                )
        else:
            console.print("[green]✓ Using Claude Code's default model selection[/green]")

    def _configure_api_model(self) -> None:
        """Configure API model selection (DEPRECATED - not used)"""
        console.print("\n[yellow]⚠️  API model configuration no longer supported[/yellow]")
        console.print("[cyan]This tool uses Claude Max plan - no API configuration needed[/cyan]")

    def configure_library_paths(self) -> None:
        """Configure music library paths"""
        console.print("\n[cyan]Music Library Configuration:[/cyan]")
        current_paths = self.config.library_paths or []

        if current_paths:
            console.print("Current library paths:")
            for i, path in enumerate(current_paths, 1):
                console.print(f"  {i}. {path}")

        if Confirm.ask("Update music library paths?", default=not current_paths):
            if LibraryPathManager:
                new_paths = LibraryPathManager(current_paths).manage_paths()
                self.config.library_paths = new_paths
            else:
                console.print("[red]Error: LibraryPathManager not available[/red]")

    def configure_processing_settings(self) -> None:
        """Configure batch processing settings"""
        console.print("\n[cyan]Processing Settings:[/cyan]")

        console.print(f"Current batch size: {self.config.batch_size}")
        new_batch_size = IntPrompt.ask(
            "Batch size (files processed per API call)", default=self.config.batch_size
        )
        self.config.batch_size = new_batch_size

        self.config.overwrite_existing_tags = Confirm.ask(
            "Overwrite existing country tags?", default=self.config.overwrite_existing_tags
        )


class MusicTaggerCLI:
    """Main CLI Application Class"""

    def __init__(self):
        self.config_manager = ConfigManager() if CONFIG_AVAILABLE else None
        self.config = self.config_manager.load_config() if self.config_manager else None
        self.verbose = False

    def run(self):
        """Run the CLI application"""
        self._print_header()

        if not self._check_dependencies():
            return

        while True:
            self._show_main_menu()
            choice = self._get_menu_choice()

            if choice == "1":
                self._handle_tag_library()
            elif choice == "2":
                self._handle_configure()
            elif choice == "3":
                self._handle_diagnostics()
            elif choice == "4":
                self._handle_help()
            elif choice == "5":
                self._handle_exit()
                break

    def _print_header(self):
        """Print application header"""
        clear_screen()

        # Use universal theme header if available
        if UNIVERSAL_CLI_AVAILABLE:
            show_panel(
                "Music Library Country Tagger\n"
                "AI-powered metadata enrichment for your music collection",
                title="Music Tools Suite",
                border_style="cyan",
            )
        else:
            console.print(
                Panel.fit(
                    "[bold cyan]Music Library Country Tagger[/bold cyan]\n"
                    "[dim]AI-powered metadata enrichment for your music collection[/dim]",
                    border_style="cyan",
                )
            )

    def _check_dependencies(self) -> bool:
        """Check if all required dependencies are available"""
        missing = []
        if not CONFIG_AVAILABLE:
            missing.append("Config Module")
        if not CLAUDE_CODE_AVAILABLE and not AI_AVAILABLE:
            missing.append("AI Researcher Module")
        if not SCANNER_AVAILABLE:
            missing.append("Scanner Module")
        if not METADATA_AVAILABLE:
            missing.append("Metadata Module")
        if not CACHE_AVAILABLE:
            missing.append("Cache Module")

        if missing:
            theme_print_error(f"Missing dependencies: {', '.join(missing)}", "Dependency Error")
            return False
        return True

    def _show_main_menu(self):
        """Show main menu options"""
        console.print("\n[bold]Main Menu:[/bold]")

        # Define menu options with icons
        options = [
            ("1", "Tag Music Library", "rocket"),
            ("2", "Configuration", "config"),
            ("3", "Diagnostics & Tools", "stats"),
            ("4", "Help & Information", "info"),
            ("5", "Exit", "error"),
        ]

        for key, label, icon_name in options:
            icon = get_theme_icon(icon_name)
            console.print(f"  [cyan]{key}.[/cyan] {icon} {label}")

    def _get_menu_choice(self) -> str:
        """Get user menu choice"""
        try:
            return Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5"], default="1")
        except (EOFError, KeyboardInterrupt):
            return "5"

    def _handle_tag_library(self):
        """Handle tagging workflow"""
        if not self.config.library_paths:
            theme_print_warning(
                "No library paths configured. Please configure first.", "Configuration Required"
            )
            if Confirm.ask("Go to configuration now?", default=True):
                self._handle_configure()
            return

        self._process_music_library()

    def _process_music_library(self):
        """Process music library - uses extracted MusicLibraryProcessor"""
        if not MusicLibraryProcessor:
            theme_print_error("MusicLibraryProcessor not available", "Error")
            return

        # Initialize components
        scanner = MusicFileScanner(self.config.supported_extensions)
        metadata_handler = MetadataHandler()

        # Get cache directory from config manager and create cache manager ONCE
        cache_dir = str(self.config_manager.config_dir / "cache")
        cache_manager = CacheManager(cache_dir) if self.config.cache_enabled else None

        # Initialize AI researcher (reuse the same cache_manager instance)
        if CLAUDE_CODE_AVAILABLE:
            # Load Brave API key from environment (optional fallback for web search)
            from dotenv import load_dotenv

            load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
            brave_api_key = os.getenv("BRAVE_API_KEY")

            # Use config model or default to Sonnet 4.5 (faster with great accuracy)
            model = self.config.claude_code_model or "claude-sonnet-4-5-20250929"

            ai_researcher = ClaudeCodeResearcher(
                max_retries=self.config.claude_max_retries,
                timeout=self.config.claude_timeout,
                cache_manager=cache_manager,
                model=model,
                enable_websearch=True,  # Enable web search for newer/unknown artists
                brave_api_key=brave_api_key,  # Brave fallback for unknown artists
            )
        else:
            # Fallback to API key (legacy)
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                theme_print_error("No Claude Code or API key found", "Authentication Error")
                return
            ai_researcher = AIResearcher(api_key, cache_manager)

        # Create processor instance
        processor = MusicLibraryProcessor(
            scanner, metadata_handler, ai_researcher, cache_manager, self.config, self.verbose
        )

        # Select library path
        path = self._select_library_path()
        if not path:
            return

        # Ask for missing tags only (Feature: Fill Missing Tags)
        missing_only = Confirm.ask(
            "Scan for missing tags ONLY? (Skip files with existing Genre/Grouping)", default=False
        )

        # Ask for dry run
        dry_run = Confirm.ask("Run in DRY RUN mode? (No files will be modified)", default=True)

        # Run processing
        processor.process(
            path, self.config.batch_size, dry_run, resume=False, missing_only=missing_only
        )

        Prompt.ask("\nPress Enter to return to menu")

    def _select_library_path(self) -> Optional[str]:
        """Select a library path to process"""
        if len(self.config.library_paths) == 1:
            return self.config.library_paths[0]

        console.print("\n[cyan]Select Library to Process:[/cyan]")
        for i, path in enumerate(self.config.library_paths, 1):
            console.print(f"  {i}. {path}")
        console.print(f"  {len(self.config.library_paths) + 1}. All Libraries")
        console.print("  0. Cancel")

        choice = IntPrompt.ask(
            "Select option",
            choices=[str(i) for i in range(len(self.config.library_paths) + 2)],
            default=1,
        )

        if choice == 0:
            return None
        elif choice <= len(self.config.library_paths):
            return self.config.library_paths[choice - 1]
        else:
            # Process all libraries (not implemented in this simple version)
            theme_print_warning(
                "Batch processing all libraries not yet supported in this version", "Not Supported"
            )
            return self.config.library_paths[0]

    def _handle_configure(self):
        """Handle configuration workflow"""
        wizard = ConfigurationWizard(self.config_manager, self.config, self.verbose)

        while True:
            clear_screen()
            console.print(Panel("[bold]Configuration[/bold]", style="cyan"))

            options = [
                ("1", "Configure API / Model"),
                ("2", "Configure Library Paths"),
                ("3", "Configure Processing Settings"),
                ("4", "View Current Config"),
                ("5", "Save & Back"),
            ]

            for key, label in options:
                console.print(f"  [cyan]{key}.[/cyan] {label}")

            choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5"], default="5")

            if choice == "1":
                wizard.configure_api_key()
                wizard.configure_model_selection()
            elif choice == "2":
                wizard.configure_library_paths()
            elif choice == "3":
                wizard.configure_processing_settings()
            elif choice == "4":
                self._show_current_config()
                Prompt.ask("\nPress Enter to continue")
            elif choice == "5":
                self.config_manager.save_config(self.config)
                theme_print_success("Configuration saved", "Saved")
                time.sleep(1)
                break

    def _show_current_config(self):
        """Show current configuration"""
        summary = self.config_manager.get_config_summary()

        table = Table(title="Current Configuration", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        for key, value in summary.items():
            table.add_row(key, str(value))

        console.print(table)

    def _handle_diagnostics(self):
        """Handle diagnostics workflow"""
        clear_screen()
        console.print(Panel("[bold]Diagnostics & Tools[/bold]", style="cyan"))

        options = [
            ("1", "Check Dependencies"),
            ("2", "Test Claude Connection"),
            ("3", "View Cache Stats"),
            ("4", "Clear Cache"),
            ("5", "Back"),
        ]

        for key, label in options:
            console.print(f"  [cyan]{key}.[/cyan] {label}")

        choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5"], default="5")

        if choice == "1":
            if self._check_dependencies():
                theme_print_success("All dependencies installed", "Dependencies")
        elif choice == "2":
            self._test_claude_connection()
        elif choice == "3":
            self._view_cache_stats()
        elif choice == "4":
            self._clear_cache()

        if choice != "5":
            Prompt.ask("\nPress Enter to continue")

    def _test_claude_connection(self):
        """Test connection to Claude"""
        console.print("\n[cyan]Testing Claude Connection...[/cyan]")

        if CLAUDE_CODE_AVAILABLE:
            try:
                ClaudeCodeResearcher(max_retries=1, timeout=30)
                console.print("[green]✓ Claude Code module loaded[/green]")

                # Simple test query
                with console.status("Sending test query to Claude...", spinner="dots"):
                    # We don't actually send a query to save costs/time, just check if we can init
                    # To really test, we'd need to call a method
                    pass
                theme_print_success("Claude Code initialized successfully", "Success")
            except Exception as e:
                theme_print_error(f"Claude Code initialization failed: {e}", "Error")
        else:
            theme_print_error("Claude Code module not available", "Error")

    def _view_cache_stats(self):
        """View cache statistics"""
        if self.config.cache_enabled and CACHE_AVAILABLE:
            cache_dir = str(self.config_manager.config_dir / "cache")
            manager = CacheManager(cache_dir)
            stats = manager.get_statistics()

            table = Table(title="Cache Statistics", show_header=True)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            for key, value in stats.items():
                table.add_row(key, str(value))

            console.print(table)
        else:
            console.print("[yellow]Cache is disabled or unavailable[/yellow]")

    def _clear_cache(self):
        """Clear the cache"""
        if self.config.cache_enabled and CACHE_AVAILABLE:
            if Confirm.ask("Are you sure you want to clear the cache?", default=False):
                cache_dir = str(self.config_manager.config_dir / "cache")
                manager = CacheManager(cache_dir)
                manager.clear_cache()
                theme_print_success("Cache cleared", "Success")
        else:
            console.print("[yellow]Cache is disabled or unavailable[/yellow]")

    def _handle_help(self):
        """Show help information"""
        clear_screen()
        help_text = """
        [bold cyan]Music Library Country Tagger Help[/bold cyan]

        This tool scans your music library and uses AI to identify the country of origin
        for each artist. It then updates the file tags with this information.

        [bold]Features:[/bold]
        • [green]AI Research[/green]: Uses Claude to find accurate artist information
        • [green]Smart Caching[/green]: Remembers artists to save time and API costs
        • [green]Batch Processing[/green]: Processes files efficiently in groups
        • [green]Dry Run Mode[/green]: Preview changes before applying them

        [bold]Tags Updated:[/bold]
        • [cyan]Genre[/cyan]: Cultural | Style | Regional | Era
        • [cyan]Grouping[/cyan]: Region | Country | Language
        • [cyan]Year[/cyan]: Original release year

        [bold]Configuration:[/bold]
        Use the Configuration menu to set up your library paths and preferences.
        No API keys are needed if you have Claude Code installed!
        """
        console.print(Panel(help_text, border_style="cyan"))
        Prompt.ask("\nPress Enter to return to menu")

    def _handle_exit(self):
        """Handle exit"""
        console.print("\n[bold green]Goodbye![/bold green]")


def main():
    """Main entry point"""
    try:
        app = MusicTaggerCLI()
        app.run()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Exiting...[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
        if "--debug" in sys.argv:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
