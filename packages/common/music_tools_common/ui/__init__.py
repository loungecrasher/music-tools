"""
Music Tools UI Components.

Provides unified UI components for the Music Tools suite:
- Menu system with breadcrumb navigation
- Progress bars with ETA support
- Status indicators and themed displays
- Error/success/warning message formatting
"""

from .menu import THEME, Menu, MenuOption, get_themed_style, show_error, show_success, show_warning
from .progress import (
    StatusBar,
    create_progress_bar,
    iterate_with_progress,
    progress_context,
    show_confirmation_preview,
    show_operation_summary,
    status_bar,
)

__all__ = [
    # Menu components
    "Menu",
    "MenuOption",
    "THEME",
    "get_themed_style",
    "show_error",
    "show_success",
    "show_warning",
    # Progress components
    "create_progress_bar",
    "progress_context",
    "iterate_with_progress",
    "StatusBar",
    "status_bar",
    "show_operation_summary",
    "show_confirmation_preview",
]
