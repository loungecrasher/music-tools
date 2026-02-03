"""
Music Tools UI Components.

Provides unified UI components for the Music Tools suite:
- Menu system with breadcrumb navigation
- Progress bars with ETA support
- Status indicators and themed displays
- Error/success/warning message formatting
"""

from .menu import (
    Menu, 
    MenuOption,
    THEME,
    get_themed_style,
    show_error,
    show_success,
    show_warning,
)

from .progress import (
    create_progress_bar,
    progress_context,
    iterate_with_progress,
    StatusBar,
    status_bar,
    show_operation_summary,
    show_confirmation_preview,
)

__all__ = [
    # Menu components
    'Menu',
    'MenuOption',
    'THEME',
    'get_themed_style',
    'show_error',
    'show_success', 
    'show_warning',
    # Progress components
    'create_progress_bar',
    'progress_context',
    'iterate_with_progress',
    'StatusBar',
    'status_bar',
    'show_operation_summary',
    'show_confirmation_preview',
]
