"""
Unified menu interface for Music Tools.
Provides access to all music-related tools through a centralized menu.
Enhanced with Rich for better visual presentation.

UI/UX Features:
- Breadcrumb navigation showing menu hierarchy
- Color-coded status indicators
- Consistent theming across all menus
"""
import sys
import time
from typing import List, Callable, Optional, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

# Import from sibling package
from ..cli import clear_screen

console = Console()

# ==========================================
# Theme Configuration
# ==========================================
THEME = {
    'primary': 'cyan',
    'secondary': 'blue',
    'success': 'green',
    'warning': 'yellow',
    'error': 'red',
    'info': 'blue',
    'muted': 'dim',
    'menu_border': 'blue',
    'menu_title': 'bold blue',
    'option_number': 'cyan',
    'option_name': 'green',
    'option_desc': 'yellow',
    'breadcrumb': 'dim cyan',
    'exit_option': 'dim',
}


def get_themed_style(key: str) -> str:
    """Get a theme style by key with fallback."""
    return THEME.get(key, '')


class MenuOption:
    """Represents a menu option."""
    
    def __init__(self, name: str, action: Callable, description: str = "", icon: str = ""):
        """Initialize a menu option.
        
        Args:
            name: Option name
            action: Function to call when option is selected
            description: Option description
            icon: Optional emoji icon for the option
        """
        self.name = name
        self.action = action
        self.description = description
        self.icon = icon


class Menu:
    """Menu system for Music Tools with enhanced UX features."""
    
    def __init__(self, title: str, icon: str = ""):
        """Initialize a menu.
        
        Args:
            title: Menu title
            icon: Optional emoji icon for the menu
        """
        self.title = title
        self.icon = icon
        self.options: List[MenuOption] = []
        self.exit_option: Optional[MenuOption] = None
        self.parent_menu: Optional[Menu] = None
    
    def add_option(self, name: str, action: Callable, description: str = "", icon: str = "") -> None:
        """Add an option to the menu.
        
        Args:
            name: Option name
            action: Function to call when option is selected
            description: Option description
            icon: Optional emoji icon for the option
        """
        self.options.append(MenuOption(name, action, description, icon))
    
    def get_breadcrumb(self) -> str:
        """Get breadcrumb trail showing menu hierarchy.
        
        Returns:
            Formatted breadcrumb string (e.g., "Main Menu > Library > Index")
        """
        breadcrumb_parts = []
        current_menu = self
        
        while current_menu is not None:
            title = current_menu.title
            if current_menu.icon:
                title = f"{current_menu.icon} {title}"
            breadcrumb_parts.insert(0, title)
            current_menu = current_menu.parent_menu
        
        return " › ".join(breadcrumb_parts)
    
    def set_exit_option(self, name: str, action: Callable = None) -> None:
        """Set the exit option for the menu.
        
        Args:
            name: Option name
            action: Function to call when option is selected (if None, returns to parent menu)
        """
        if action is None:
            # Default action is to return to parent menu or exit
            if self.parent_menu:
                action = lambda: self.parent_menu.display()
            else:
                action = lambda: sys.exit(0)
        
        self.exit_option = MenuOption(name, action)
    
    def create_submenu(self, title: str, icon: str = "") -> 'Menu':
        """Create a submenu.
        
        Args:
            title: Submenu title
            icon: Optional emoji icon for the submenu
            
        Returns:
            New submenu
        """
        submenu = Menu(title, icon)
        submenu.parent_menu = self
        
        # Add option to main menu to access submenu
        self.add_option(title, submenu.display, icon=icon)
        
        return submenu
    
    def display(self) -> None:
        """Display the menu and handle user input."""
        while True:
            # Clear screen
            clear_screen()
            
            # Display breadcrumb navigation
            breadcrumb = self.get_breadcrumb()
            console.print(f"[{get_themed_style('breadcrumb')}]{breadcrumb}[/]")
            console.print()
            
            # Create a table for the menu
            table = Table(show_header=False, expand=True, box=None, row_styles=["", "on grey15"])
            table.add_column("Number", style=get_themed_style('option_number'), justify="right", width=4)
            table.add_column("Option", style=get_themed_style('option_name'), min_width=25)
            table.add_column("Description", style=get_themed_style('option_desc'))
            
            # Add options to the table with alternating row colors
            for i, option in enumerate(self.options, 1):
                # Format option name with icon if present
                option_display = f"{option.icon} {option.name}" if option.icon else option.name
                
                if option.description:
                    table.add_row(f"[{get_themed_style('option_number')}]{i}[/]", option_display, option.description)
                else:
                    table.add_row(f"[{get_themed_style('option_number')}]{i}[/]", option_display, "")
            
            # Add separator before exit option
            if self.exit_option and self.options:
                table.add_row("", "", "")  # Empty row as separator
            
            # Add exit option if available
            if self.exit_option:
                exit_display = f"← {self.exit_option.name}" if self.parent_menu else f"⏻ {self.exit_option.name}"
                table.add_row(f"[{get_themed_style('exit_option')}]0[/]", 
                             f"[{get_themed_style('exit_option')}]{exit_display}[/]", 
                             "", style=get_themed_style('exit_option'))
            
            # Build title with icon
            title_display = f"{self.icon} {self.title}" if self.icon else self.title
            
            # Display the menu in a panel
            console.print(Panel(
                table,
                title=f"[{get_themed_style('menu_title')}]{title_display}[/]",
                border_style=get_themed_style('menu_border'),
                padding=(1, 2)
            ))
            
            # Get user input
            try:
                choice = Prompt.ask("\n[bold]Enter choice[/bold]", default="")
                
                if choice == '0' and self.exit_option:
                    self.exit_option.action()
                    return
                
                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(self.options):
                        # Call the selected option's action
                        self.options[choice_idx].action()
                    else:
                        console.print(f"[{get_themed_style('error')}]Invalid choice. Please enter a number between 0 and {len(self.options)}.[/]")
                        time.sleep(1.5)
                except ValueError:
                    if choice.strip():  # Only show error if user typed something
                        console.print(f"[{get_themed_style('error')}]Invalid input. Please enter a number.[/]")
                        time.sleep(1)
            except KeyboardInterrupt:
                console.print(f"\n[{get_themed_style('warning')}]Exiting...[/]")
                sys.exit(0)


# ==========================================
# Enhanced Error Display
# ==========================================

def show_error(message: str, context: str = "", suggestion: str = "") -> None:
    """Display a well-formatted error message with context and suggestions.
    
    Args:
        message: The main error message
        context: What operation was being attempted
        suggestion: How to fix the error
    """
    error_parts = []
    
    if context:
        error_parts.append(f"[{get_themed_style('muted')}]While: {context}[/]")
    
    error_parts.append(f"[{get_themed_style('error')}]Error: {message}[/]")
    
    if suggestion:
        error_parts.append(f"[{get_themed_style('info')}]→ {suggestion}[/]")
    
    console.print(Panel(
        "\n".join(error_parts),
        title=f"[{get_themed_style('error')}]⚠ Error[/]",
        border_style=get_themed_style('error'),
        padding=(0, 2)
    ))


def show_success(message: str, details: str = "") -> None:
    """Display a well-formatted success message.
    
    Args:
        message: The main success message
        details: Additional details about what was accomplished
    """
    success_parts = [f"[{get_themed_style('success')}]✓ {message}[/]"]
    
    if details:
        success_parts.append(f"[{get_themed_style('muted')}]{details}[/]")
    
    console.print(Panel(
        "\n".join(success_parts),
        border_style=get_themed_style('success'),
        padding=(0, 2)
    ))


def show_warning(message: str, suggestion: str = "") -> None:
    """Display a well-formatted warning message.
    
    Args:
        message: The warning message
        suggestion: Suggested action
    """
    warning_parts = [f"[{get_themed_style('warning')}]⚠ {message}[/]"]
    
    if suggestion:
        warning_parts.append(f"[{get_themed_style('info')}]→ {suggestion}[/]")
    
    console.print(Panel(
        "\n".join(warning_parts),
        border_style=get_themed_style('warning'),
        padding=(0, 2)
    ))
