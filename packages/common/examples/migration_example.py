"""
Migration Example for music_tools_common.config

This example shows how to migrate from old configuration code to the new unified module.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigManager


def old_way_music_tools():
    """
    OLD WAY: From Music Tools /core/config.py
    """
    print("\nOLD WAY (Music Tools):")
    print("-" * 40)
    print("from core.config import config_manager")
    print("config = config_manager.load_config('spotify')")


def new_way_unified():
    """
    NEW WAY: Using unified config module
    """
    print("\nNEW WAY (Unified Module):")
    print("-" * 40)
    print("from music_tools_common.config import ConfigManager")
    print("manager = ConfigManager(app_name='music_tools')")
    print("config = manager.load_config('spotify')")

    # Actually demonstrate
    manager = ConfigManager(app_name='music_tools')
    config = manager.load_config('spotify')
    print(f"\nLoaded config: {list(config.keys())}")


def old_way_tag_editor():
    """
    OLD WAY: From Tag Country Origin Editor /src/config.py
    """
    print("\n\nOLD WAY (Tag Editor):")
    print("-" * 40)
    print("from src.config import ConfigManager, get_config")
    print("config_manager = ConfigManager()")
    print("config = config_manager.load_config()")
    print("# Returns: AppConfig dataclass")


def new_way_tag_editor():
    """
    NEW WAY: Using unified config module for Tag Editor
    """
    print("\nNEW WAY (Tag Editor):")
    print("-" * 40)
    print("from music_tools_common.config import ConfigManager")
    print("manager = ConfigManager(app_name='music_tagger')")
    print("anthropic_config = manager.load_config('anthropic')")
    print("# Returns: Dict with service config")

    # Actually demonstrate
    manager = ConfigManager(app_name='music_tagger')
    config = manager.load_config('anthropic')
    print(f"\nLoaded config: {list(config.keys())}")


def old_way_edm_scraper():
    """
    OLD WAY: From EDM Scraper /config.py
    """
    print("\n\nOLD WAY (EDM Scraper):")
    print("-" * 40)
    print("import config")
    print("REQUEST_TIMEOUT = config.REQUEST_TIMEOUT")
    print("MAX_PAGES = config.MAX_PAGES")


def new_way_edm_scraper():
    """
    NEW WAY: Using unified config module for EDM Scraper
    """
    print("\nNEW WAY (EDM Scraper):")
    print("-" * 40)
    print("from music_tools_common.config import ConfigManager")
    print("manager = ConfigManager(app_name='edm_scraper')")
    print("scraper_config = manager.load_config('edm_scraper')")
    print("REQUEST_TIMEOUT = scraper_config.get('request_timeout', 15)")
    print("MAX_PAGES = scraper_config.get('max_pages', 10)")


def main():
    """Run migration examples."""

    print("=" * 60)
    print("Configuration Migration Guide")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("EXAMPLE 1: Music Tools Migration")
    print("=" * 60)
    old_way_music_tools()
    new_way_unified()

    print("\n" + "=" * 60)
    print("EXAMPLE 2: Tag Country Origin Editor Migration")
    print("=" * 60)
    old_way_tag_editor()
    new_way_tag_editor()

    print("\n" + "=" * 60)
    print("EXAMPLE 3: EDM Scraper Migration")
    print("=" * 60)
    old_way_edm_scraper()
    new_way_edm_scraper()

    print("\n" + "=" * 60)
    print("Migration Benefits:")
    print("-" * 60)
    print("✓ Unified API across all projects")
    print("✓ Better security (automatic sensitive data stripping)")
    print("✓ Environment variable support out of the box")
    print("✓ Pydantic validation for type safety")
    print("✓ Interactive setup wizard")
    print("✓ Configuration caching for performance")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
