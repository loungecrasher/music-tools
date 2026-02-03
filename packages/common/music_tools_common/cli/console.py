"""Shared console instance for Music Tools.

This module provides a single shared Rich console instance to ensure
consistent output formatting across the application.
"""

from rich.console import Console

# Shared console instance
console = Console()

__all__ = ['console']