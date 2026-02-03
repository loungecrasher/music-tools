"""
CLI framework for Music Tools.
"""

from .base import BaseCLI
from .console import console
from .helpers import (
    clear_screen,
    confirm,
    create_progress_bar,
    format_error_details,
    pause,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
    prompt,
    show_panel,
    show_status,
)
from .menu import InteractiveMenu
from .progress import ProgressTracker
from .prompts import prompt_choice, prompt_user

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
