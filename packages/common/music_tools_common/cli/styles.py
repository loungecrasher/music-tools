"""
Color schemes and themes for CLI applications.

Provides consistent styling across all Music Tools CLIs.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Colors:
    """ANSI color codes for terminal output."""

    # Basic colors
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'

    # Compound styles
    SUCCESS = '\033[92m\033[1m'  # Bold Green
    ERROR = '\033[91m\033[1m'    # Bold Red
    WARNING = '\033[93m\033[1m'  # Bold Yellow
    INFO = '\033[96m\033[1m'     # Bold Cyan

    @classmethod
    def wrap(cls, text: str, color: str) -> str:
        """
        Wrap text in color codes.

        Args:
            text: Text to colorize
            color: Color code

        Returns:
            Colorized text
        """
        return f"{color}{text}{cls.ENDC}"

    @classmethod
    def success(cls, text: str) -> str:
        """Wrap text in success color."""
        return cls.wrap(text, cls.SUCCESS)

    @classmethod
    def error(cls, text: str) -> str:
        """Wrap text in error color."""
        return cls.wrap(text, cls.ERROR)

    @classmethod
    def warning(cls, text: str) -> str:
        """Wrap text in warning color."""
        return cls.wrap(text, cls.WARNING)

    @classmethod
    def info(cls, text: str) -> str:
        """Wrap text in info color."""
        return cls.wrap(text, cls.INFO)


@dataclass
class Styles:
    """Rich markup styles for consistent formatting."""

    # Status styles
    SUCCESS = "bold green"
    ERROR = "bold red"
    WARNING = "bold yellow"
    INFO = "bold cyan"

    # Text styles
    HEADER = "bold blue"
    SUBTITLE = "dim"
    EMPHASIS = "bold"
    DIM_TEXT = "dim"

    # Data styles
    KEY = "cyan"
    VALUE = "green"
    NUMBER = "magenta"
    PATH = "yellow"

    # UI element styles
    BORDER = "blue"
    MENU_OPTION = "green"
    MENU_NUMBER = "cyan"
    MENU_DESCRIPTION = "yellow"


@dataclass
class Theme:
    """
    A complete theme for CLI applications.

    Includes colors, styles, and icons for consistent UI.
    """

    name: str
    primary_color: str
    secondary_color: str
    accent_color: str
    success_color: str
    error_color: str
    warning_color: str
    info_color: str
    header_style: str
    subtitle_style: str
    icons: Dict[str, str]

    @classmethod
    def default(cls) -> "Theme":
        """Get the default theme."""
        return cls(
            name="default",
            primary_color="blue",
            secondary_color="cyan",
            accent_color="magenta",
            success_color="green",
            error_color="red",
            warning_color="yellow",
            info_color="cyan",
            header_style="bold blue",
            subtitle_style="dim",
            icons={
                "success": "✓",
                "error": "✗",
                "warning": "⚠",
                "info": "ℹ",
                "header": "🎵",
                "folder": "📁",
                "file": "📄",
                "link": "🔗",
                "config": "⚙",
                "stats": "📊",
                "clock": "⏱",
                "rocket": "🚀",
            },
        )

    @classmethod
    def dark(cls) -> "Theme":
        """Get a dark theme optimized for dark terminals."""
        return cls(
            name="dark",
            primary_color="bright_blue",
            secondary_color="bright_cyan",
            accent_color="bright_magenta",
            success_color="bright_green",
            error_color="bright_red",
            warning_color="bright_yellow",
            info_color="bright_cyan",
            header_style="bold bright_blue",
            subtitle_style="bright_black",
            icons=Theme.default().icons,
        )

    @classmethod
    def light(cls) -> "Theme":
        """Get a light theme optimized for light terminals."""
        return cls(
            name="light",
            primary_color="blue",
            secondary_color="cyan",
            accent_color="magenta",
            success_color="green",
            error_color="red",
            warning_color="yellow",
            info_color="blue",
            header_style="bold blue",
            subtitle_style="dim black",
            icons=Theme.default().icons,
        )

    @classmethod
    def minimal(cls) -> "Theme":
        """Get a minimal theme without icons."""
        return cls(
            name="minimal",
            primary_color="white",
            secondary_color="white",
            accent_color="white",
            success_color="green",
            error_color="red",
            warning_color="yellow",
            info_color="cyan",
            header_style="bold white",
            subtitle_style="dim",
            icons={key: "" for key in Theme.default().icons},
        )


# Global theme registry
_THEMES: Dict[str, Theme] = {
    "default": Theme.default(),
    "dark": Theme.dark(),
    "light": Theme.light(),
    "minimal": Theme.minimal(),
}

_CURRENT_THEME: Theme = Theme.default()


def register_theme(theme: Theme) -> None:
    """
    Register a custom theme.

    Args:
        theme: Theme to register
    """
    _THEMES[theme.name] = theme


def get_theme(name: Optional[str] = None) -> Theme:
    """
    Get a theme by name.

    Args:
        name: Theme name (default, dark, light, minimal)

    Returns:
        Theme object
    """
    if name is None:
        return _CURRENT_THEME

    return _THEMES.get(name, Theme.default())


def set_theme(name: str) -> None:
    """
    Set the global theme.

    Args:
        name: Theme name
    """
    global _CURRENT_THEME
    _CURRENT_THEME = get_theme(name)


def list_themes() -> list[str]:
    """
    Get list of available theme names.

    Returns:
        List of theme names
    """
    return list(_THEMES.keys())
