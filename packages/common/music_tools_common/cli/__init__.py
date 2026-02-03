"""
CLI framework for Music Tools.
"""

from .base import BaseCLI
from .menu import InteractiveMenu
from .prompts import prompt_user, prompt_choice
from .progress import ProgressTracker
from .console import console
from .helpers import (
    print_error,
    print_success,
    print_warning,
    print_info,
    pause,
    confirm,
    prompt,
    show_panel,
    create_progress_bar,
    show_status,
    clear_screen,
    print_header,
    format_error_details
)

__all__ = [
    'BaseCLI',
    'InteractiveMenu',
    'prompt_user',
    'prompt_choice',
    'ProgressTracker',
    'console',  # Shared console instance
    # Helpers
    'print_error',
    'print_success',
    'print_warning',
    'print_info',
    'pause',
    'confirm',
    'prompt',
    'show_panel',
    'create_progress_bar',
    'show_status',
    'clear_screen',
    'print_header',
    'format_error_details',
]
