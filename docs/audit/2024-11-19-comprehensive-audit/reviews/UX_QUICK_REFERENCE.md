# Music Tools - UI/UX Quick Reference Guide

**For:** Development Team
**Purpose:** Quick lookup for implementing UX improvements
**See Also:** UX_IMPROVEMENT_PROPOSAL.md (full details)

---

## Document Index

1. **UX_REVIEW_EXECUTIVE_SUMMARY.md** - Start here (management overview)
2. **UX_IMPROVEMENT_PROPOSAL.md** - Complete proposal (60+ pages)
3. **UX_VISUAL_EXAMPLES.md** - Before/after mockups
4. **UX_QUICK_REFERENCE.md** - This file (developer guide)

---

## Quick Wins (Implement Today)

Each task: < 4 hours

### 1. Add Examples to Prompts
**Location:** `menu.py` - All `Prompt.ask()` calls

```python
# Before
url = Prompt.ask("Playlist URL")

# After
console.print("[dim]Example: https://www.deezer.com/playlist/123456[/dim]")
url = Prompt.ask("Playlist URL")
```

**Files to update:**
- `menu.py`: Lines 762, 365, 421
- `music_tools_cli/commands/deezer.py`
- `music_tools_cli/commands/spotify.py`

---

### 2. Show CLI Equivalents
**Location:** `menu.py` - After each operation

```python
def show_cli_hint(operation: str, command: str):
    """Show CLI equivalent after interactive operation."""
    console.print(f"\n[dim]💡 CLI equivalent:[/dim]")
    console.print(f"[dim cyan]{command}[/dim cyan]")
    if Confirm.ask("Copy to clipboard?", default=False):
        import pyperclip
        pyperclip.copy(command)
        console.print("[green]✓ Copied![/green]")

# Usage after Deezer check
show_cli_hint(
    "Deezer Check",
    f"music-tools deezer playlist {url} --output-dir {output_dir}"
)
```

**Files to update:**
- `menu.py`: Add after operations in functions like `run_deezer_playlist_checker()`

---

### 3. Add Recent Items
**Location:** `menu.py` - New module

```python
# history.py (new file)
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

class OperationHistory:
    """Track recent operations."""

    def __init__(self, history_file: Path = None):
        self.history_file = history_file or Path(DATA_DIR) / "history.json"
        self.history = self._load()

    def _load(self) -> List[Dict]:
        if self.history_file.exists():
            with open(self.history_file) as f:
                return json.load(f)
        return []

    def _save(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def add(self, operation: str, details: Dict):
        """Add operation to history."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'details': details
        }
        self.history.insert(0, entry)  # Most recent first
        self.history = self.history[:50]  # Keep last 50
        self._save()

    def get_recent(self, operation: str = None, limit: int = 5) -> List[Dict]:
        """Get recent operations."""
        if operation:
            filtered = [h for h in self.history if h['operation'] == operation]
            return filtered[:limit]
        return self.history[:limit]

# Usage in menu.py
history = OperationHistory()

# After Deezer check
history.add('deezer_check', {
    'url': playlist_url,
    'total': total_tracks,
    'available': available_count
})

# Show in menu
recent = history.get_recent('deezer_check', limit=3)
if recent:
    console.print("\n[cyan]Recent checks:[/cyan]")
    for check in recent:
        console.print(f"  • {check['details']['url']} - {check['timestamp']}")
```

**New file:** `music_tools_cli/services/history.py`

---

### 4. Add "What's Next" After Operations
**Location:** `menu.py` - After each operation completes

```python
def show_next_actions(context: str, actions: List[tuple]):
    """Show suggested next actions.

    Args:
        context: Current operation context
        actions: List of (description, function) tuples
    """
    console.print(f"\n[cyan]What would you like to do next?[/cyan]")

    for i, (description, _) in enumerate(actions, 1):
        console.print(f"  {i}. {description}")

    choice = Prompt.ask("Choice", choices=[str(i) for i in range(len(actions) + 1)], default=str(len(actions)))

    if choice != str(len(actions)):  # Not "return to menu"
        idx = int(choice) - 1
        actions[idx][1]()  # Call the function

# Usage after Deezer check
show_next_actions("Deezer Check", [
    ("View detailed report", lambda: view_report(report_file)),
    ("Export to Soundiz format", lambda: export_to_soundiz(results)),
    ("Check another playlist", run_deezer_playlist_checker),
    ("Return to main menu", lambda: None)
])
```

---

## Design System

### Color Scheme
**Location:** Create `music_tools_cli/ui/colors.py`

```python
"""Centralized color definitions."""

from dataclasses import dataclass

@dataclass
class ColorScheme:
    """Application color scheme."""
    primary: str = "cyan"
    secondary: str = "blue"
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    info: str = "blue"
    muted: str = "dim"

THEME = ColorScheme()

# Status icons
ICONS = {
    'success': '✓',
    'error': '✗',
    'warning': '⚠',
    'info': 'ℹ',
    'loading': '⏳',
}

def success(msg: str) -> str:
    return f"[{THEME.success}]{ICONS['success']} {msg}[/{THEME.success}]"

def error(msg: str) -> str:
    return f"[{THEME.error}]{ICONS['error']} {msg}[/{THEME.error}]"

def warning(msg: str) -> str:
    return f"[{THEME.warning}]{ICONS['warning']} {msg}[/{THEME.warning}]"

def info(msg: str) -> str:
    return f"[{THEME.info}]{ICONS['info']} {msg}[/{THEME.info}]"
```

**Usage:**
```python
from music_tools_cli.ui.colors import success, error, warning

console.print(success("Configuration saved!"))
console.print(error("Connection failed"))
console.print(warning("No API key found"))
```

---

### Panel Templates
**Location:** Create `music_tools_cli/ui/panels.py`

```python
"""Reusable panel templates."""

from rich.panel import Panel
from .colors import THEME

def info_panel(content: str, title: str = "Info") -> Panel:
    return Panel(
        content,
        title=f"[bold {THEME.info}]{title}[/bold {THEME.info}]",
        border_style=THEME.info,
        padding=(1, 2)
    )

def success_panel(content: str, title: str = "Success") -> Panel:
    return Panel(
        content,
        title=f"[bold {THEME.success}]{title}[/bold {THEME.success}]",
        border_style=THEME.success,
        padding=(1, 2)
    )

def error_panel(content: str, title: str = "Error") -> Panel:
    return Panel(
        content,
        title=f"[bold {THEME.error}]{title}[/bold {THEME.error}]",
        border_style=THEME.error,
        padding=(1, 2)
    )

def warning_panel(content: str, title: str = "Warning") -> Panel:
    return Panel(
        content,
        title=f"[bold {THEME.warning}]{title}[/bold {THEME.warning}]",
        border_style=THEME.warning,
        padding=(1, 2)
    )
```

---

## Critical Fixes

### 1. First-Run Detection
**Location:** `menu.py` - `main()` function

```python
def is_first_run() -> bool:
    """Detect if this is the first run."""
    config_file = Path(config_manager.config_dir) / "config.json"
    return not config_file.exists()

def run_setup_wizard() -> bool:
    """Run first-time setup wizard."""
    console.clear()

    console.print(Panel.fit(
        "[bold cyan]🎵 Welcome to Music Tools![/bold cyan]\n\n"
        "Let's get you set up. This will take about 5 minutes.\n\n"
        "[dim]You can always skip and configure later.[/dim]",
        border_style="cyan"
    ))

    if not Confirm.ask("Start setup wizard?", default=True):
        return False

    # Step 1: Service Selection
    console.print("\n[bold]Step 1: Which services do you use?[/bold]")
    use_spotify = Confirm.ask("  Spotify?", default=True)
    use_deezer = Confirm.ask("  Deezer?", default=False)

    # Step 2: Configure selected services
    if use_spotify:
        console.print("\n[bold]Step 2a: Configure Spotify[/bold]")
        configure_spotify()

    if use_deezer:
        console.print(f"\n[bold]Step 2{'b' if use_spotify else 'a'}: Configure Deezer[/bold]")
        configure_deezer()

    # Step 3: Test connections
    console.print("\n[bold]Step 3: Testing connections...[/bold]")
    if use_spotify:
        test_spotify_connection()
    if use_deezer:
        test_deezer_connection()

    # Complete
    console.print(Panel(
        "[green]✓ Setup complete![/green]\n\n"
        "You're ready to use Music Tools.\n"
        "Press Enter to see the main menu.",
        border_style="green"
    ))
    input()

    return True

# In main()
def main():
    if is_first_run():
        if run_setup_wizard():
            show_quick_start_guide()

    display_welcome_screen()
    main_menu.display()
```

---

### 2. Menu Categorization
**Location:** `menu.py` - Reorganize main menu

```python
def create_categorized_menu() -> Menu:
    """Create categorized main menu."""
    main_menu = Menu("Music Tools Suite")

    # Quick Actions Section
    console.print("\n[bold cyan]⚡ QUICK ACTIONS[/bold cyan]")
    main_menu.add_option(
        "Check Playlist Availability (Deezer)",
        run_deezer_playlist_checker,
        "Check which tracks are available in your region"
    )
    main_menu.add_option(
        "Filter Tracks by Date (Spotify)",
        run_spotify_tracks_after_date,
        "Create playlist with tracks after specific date"
    )
    main_menu.add_option(
        "Tag Library with Countries",
        run_music_country_tagger,
        "AI-powered country tagging for local files"
    )

    # Streaming Platforms Section
    console.print("\n[bold cyan]🎵 STREAMING PLATFORMS[/bold cyan]")
    spotify_menu = main_menu.create_submenu("Spotify Toolkit")
    spotify_menu.add_option("Playlist Manager", run_spotify_playlist_manager)
    spotify_menu.add_option("Filter by Date", run_spotify_tracks_after_date)
    spotify_menu.add_option("Remove CSV Tracks", run_csv_remover)

    deezer_menu = main_menu.create_submenu("Deezer Tools")
    deezer_menu.add_option("Availability Checker", run_deezer_playlist_checker)

    main_menu.add_option("Soundiz Converter", run_soundiz_file_processor)

    # Local Library Section
    console.print("\n[bold cyan]💿 LOCAL LIBRARY[/bold cyan]")
    library_menu = main_menu.create_submenu("Library Tools")
    library_menu.add_option("Compare & Deduplicate", run_library_comparison)
    library_menu.add_option("File Deduplicator", run_duplicate_remover)
    library_menu.add_option("Country Tagger", run_music_country_tagger)

    # Advanced Tools Section
    console.print("\n[bold cyan]🔧 ADVANCED TOOLS[/bold cyan]")
    main_menu.add_option("EDM Blog Scraper", run_edm_blog_scraper)
    main_menu.add_option("CSV Text Export", run_csv_batch_converter)

    # System Section
    config_menu = main_menu.create_submenu("Configuration")
    # ... existing config options ...

    db_menu = main_menu.create_submenu("Database")
    # ... existing db options ...

    return main_menu
```

---

### 3. Keyboard Shortcuts
**Location:** `menu.py` - Update `Menu.display()`

```python
SHORTCUTS = {
    'c': 'configuration',
    'd': 'database',
    'h': 'help',
    'q': 'quit',
    '?': 'help',
    '!': 'show_cli',
    '/': 'search',
    'r': 'refresh'
}

def handle_shortcut(shortcut: str):
    """Handle keyboard shortcut."""
    action = SHORTCUTS.get(shortcut.lower())

    if action == 'configuration':
        configure_services()
    elif action == 'database':
        show_database_info()
    elif action == 'help':
        show_help()
    elif action == 'quit':
        sys.exit(0)
    elif action == 'show_cli':
        show_cli_reference()
    elif action == 'search':
        search_features()
    elif action == 'refresh':
        # Just redisplay menu
        pass

# In Menu.display()
def display(self):
    while True:
        # ... existing display code ...

        # Show shortcuts hint
        console.print("\n[dim]Shortcuts: [C]onfig [D]atabase [H]elp [Q]uit [/]Search[/dim]")

        choice = Prompt.ask("\nEnter choice or shortcut", default="")

        # Check if it's a shortcut
        if choice.lower() in SHORTCUTS:
            handle_shortcut(choice)
            continue

        # ... existing choice handling ...
```

---

## Enhanced Error Messages

### Error Template
**Location:** Create `music_tools_cli/ui/errors.py`

```python
"""Enhanced error handling."""

from typing import Dict, List, Optional
from rich.panel import Panel
from rich.prompt import Confirm
from .colors import THEME

class ErrorHandler:
    """Centralized error handling with solutions."""

    ERRORS = {
        'spotify_not_configured': {
            'title': 'Spotify Not Configured',
            'message': 'Spotify features require API credentials.',
            'causes': [
                'You haven\'t set up Spotify credentials yet',
                'Configuration file is missing or corrupted'
            ],
            'solutions': [
                'Configure Spotify now (takes ~3 minutes)',
                'Skip and use other features'
            ],
            'actions': {
                'Configure Now': 'configure_spotify',
                'Show Guide': 'show_spotify_guide',
                'Cancel': None
            },
            'help_link': 'https://docs.../spotify-setup'
        },
        'connection_failed': {
            'title': 'Connection Failed',
            'message': 'Could not connect to {service} API.',
            'causes': [
                'No internet connection',
                '{service} API is down',
                'Firewall blocking request'
            ],
            'solutions': [
                'Check your internet connection',
                'Try again in a few minutes',
                'Check {service} status page'
            ],
            'actions': {
                'Retry Now': 'retry',
                'Test Connection': 'test_connection',
                'Cancel': None
            }
        }
    }

    def show_error(self, error_code: str, context: Dict = None) -> Optional[str]:
        """Show error with solutions.

        Returns:
            Action to take, or None
        """
        error = self.ERRORS.get(error_code)
        if not error:
            # Generic error
            console.print(f"[red]Error: {error_code}[/red]")
            return None

        # Format with context
        context = context or {}
        message = error['message'].format(**context)
        causes = [c.format(**context) for c in error['causes']]
        solutions = [s.format(**context) for s in error['solutions']]

        # Build error panel
        content = f"""[red]❌ {message}[/red]

[yellow]Possible causes:[/yellow]
{chr(10).join(f"• {c}" for c in causes)}

[green]How to fix:[/green]
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(solutions))}

[dim]More help: {error.get('help_link', 'N/A')}[/dim]
"""

        console.print(Panel(
            content,
            title=f"[bold red]{error['title']}[/bold red]",
            border_style="red"
        ))

        # Show action buttons
        console.print("\nActions:")
        for i, (label, action) in enumerate(error['actions'].items(), 1):
            console.print(f"  {i}. {label}")

        choice = Prompt.ask("Select action", choices=[str(i) for i in range(1, len(error['actions']) + 1)])
        action_list = list(error['actions'].values())
        return action_list[int(choice) - 1]

# Usage
error_handler = ErrorHandler()

# In code
if not check_service_config('spotify'):
    action = error_handler.show_error('spotify_not_configured')
    if action == 'configure_spotify':
        configure_spotify()
```

---

## Progress Indicators

### Multi-Level Progress
**Location:** Create `music_tools_cli/ui/progress.py`

```python
"""Enhanced progress indicators."""

from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn,
    MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn
)
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

class MultiLevelProgress:
    """Multi-level progress tracking."""

    def __init__(self, console):
        self.console = console
        self.progress = None

    def __enter__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
        self.progress.start()
        return self

    def __exit__(self, *args):
        self.progress.stop()

    def add_task(self, description: str, total: int):
        """Add a task."""
        return self.progress.add_task(description, total=total)

    def update(self, task_id, **kwargs):
        """Update task progress."""
        self.progress.update(task_id, **kwargs)

    def advance(self, task_id, amount: float = 1):
        """Advance task progress."""
        self.progress.advance(task_id, amount)

# Usage
with MultiLevelProgress(console) as progress:
    main_task = progress.add_task("Processing files...", total=500)
    batch_task = progress.add_task("Current batch...", total=25)

    for batch in batches:
        progress.update(batch_task, completed=0, total=len(batch))

        for file in batch:
            # Process file
            progress.advance(batch_task)
            progress.advance(main_task)
```

---

## File Locations

### New Files to Create
```
music_tools_cli/
  ui/
    __init__.py
    colors.py         # Color scheme and formatting
    panels.py         # Reusable panel templates
    errors.py         # Error handling with solutions
    progress.py       # Enhanced progress indicators
    help.py           # Help system
  services/
    history.py        # Operation history tracking
```

### Files to Modify
```
menu.py              # Main menu reorganization
  - Add first-run detection
  - Categorize menu
  - Add keyboard shortcuts
  - Integrate history

music_tools_cli/
  cli.py             # Unified entry point
  commands/
    *.py             # Add examples to prompts
  services/
    *.py             # Use new UI components
```

---

## Testing Checklist

### Before Each Change
- [ ] Read current code
- [ ] Understand user flow
- [ ] Identify pain point
- [ ] Design improvement
- [ ] Implement with tests
- [ ] Manual testing
- [ ] Documentation

### After Implementation
- [ ] First-run experience works
- [ ] All menu options accessible
- [ ] Shortcuts work
- [ ] Errors show solutions
- [ ] Progress is clear
- [ ] Help is contextual
- [ ] CLI hints displayed
- [ ] History persists

---

## Common Patterns

### Pattern 1: Confirming Before Destructive Operations
```python
if Confirm.ask(f"This will delete {count} items. Continue?", default=False):
    # Do destructive operation
    console.print(success("Operation completed"))
else:
    console.print(info("Operation cancelled"))
```

### Pattern 2: Showing Options with Descriptions
```python
options = [
    ("Option 1", "Description of option 1", handler1),
    ("Option 2", "Description of option 2", handler2),
]

table = Table(show_header=False)
table.add_column("Option", style="cyan")
table.add_column("Description", style="yellow")

for i, (name, desc, _) in enumerate(options, 1):
    table.add_row(f"{i}. {name}", desc)

console.print(table)
choice = Prompt.ask("Select", choices=[str(i) for i in range(1, len(options) + 1)])
options[int(choice) - 1][2]()  # Call handler
```

### Pattern 3: Progress with Context
```python
with console.status(f"[bold green]Processing {filename}...[/bold green]", spinner="dots"):
    result = long_operation(filename)

console.print(success(f"Processed {filename}: {result}"))
```

---

## Migration Guide

### Phase 1: Quick Wins (Week 1)
1. Add examples to all prompts (2 hours)
2. Add CLI hints after operations (2 hours)
3. Create history module (3 hours)
4. Add "What's next" prompts (2 hours)

### Phase 2: Design System (Week 2)
1. Create `ui/` module (4 hours)
2. Migrate to color scheme (2 hours)
3. Update all panels (3 hours)
4. Implement error templates (4 hours)

### Phase 3: Critical Fixes (Week 3-4)
1. First-run wizard (8 hours)
2. Menu categorization (6 hours)
3. Keyboard shortcuts (4 hours)
4. Help system (6 hours)

---

## Support

Questions? Check:
1. **UX_IMPROVEMENT_PROPOSAL.md** - Full details
2. **UX_VISUAL_EXAMPLES.md** - Before/after mockups
3. **UX_REVIEW_EXECUTIVE_SUMMARY.md** - Management overview

For implementation questions, refer to the Rich library docs:
- https://rich.readthedocs.io/en/stable/

---

**Last Updated:** November 15, 2025
**Status:** Ready for Implementation
