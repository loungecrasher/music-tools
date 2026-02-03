"""
Configuration Management Module

Handles application configuration storage, validation, and user preferences.
Provides interactive configuration wizard and persistent settings management.

SECURITY IMPROVEMENTS:
- API keys stored only in environment variables
- Path validation to prevent directory traversal
- Secure file permissions on configuration files
- Uses pathlib for cross-platform compatibility
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def validate_file_path(file_path: Path, base_path: Optional[Path] = None) -> bool:
    """
    Validate that a file path is safe and doesn't escape the base directory.

    Args:
        file_path: Path to validate
        base_path: Base directory that path must be within (None to skip check)

    Returns:
        True if valid

    Raises:
        ValueError: If path is invalid or attempts traversal
    """
    try:
        # Resolve to absolute path
        resolved = file_path.resolve()

        # Check if within base path if provided
        if base_path:
            base_resolved = base_path.resolve()
            try:
                resolved.relative_to(base_resolved)
            except ValueError:
                raise ValueError(f"Path {file_path} is outside allowed directory {base_path}")

        return True
    except Exception as e:
        raise ValueError(f"Invalid path {file_path}: {e}")


@dataclass
class AppConfig:
    """Application configuration settings."""
    # Claude Code Configuration (uses Claude Max plan, NO API keys needed!)
    claude_code_model: str = ""  # Empty means use default (sonnet)
    claude_timeout: int = 600  # Timeout for claude command execution
    claude_max_retries: int = 1  # Retries for failed lookups

    # File Processing
    library_paths: List[str] = None
    batch_size: int = 25  # Reduced from 50 to avoid Claude output token limits
    supported_extensions: List[str] = None
    overwrite_existing_tags: bool = True

    # Caching
    cache_enabled: bool = True
    cache_ttl_days: int = 30
    auto_cleanup_cache: bool = True

    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    max_log_file_size_mb: int = 10
    log_backup_count: int = 5

    # UI Preferences
    show_progress_bars: bool = True
    show_file_names: bool = True
    show_estimated_time: bool = True
    color_output: bool = True

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.library_paths is None:
            self.library_paths = []
        if self.supported_extensions is None:
            self.supported_extensions = ['.mp3', '.flac']


class ConfigManager:
    """
    Configuration manager for the music tagger application.

    Handles loading, saving, and validating configuration settings.
    Provides interactive configuration wizard and environment variable support.
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Custom configuration directory path
        """
        # Set up configuration directory
        if config_dir:
            self.config_dir = Path(config_dir).expanduser()
        else:
            # Use environment variable if set
            env_dir = os.getenv('MUSIC_TAGGER_CONFIG_DIR')
            if env_dir:
                self.config_dir = Path(env_dir).expanduser()
            else:
                self.config_dir = Path.home() / '.music_tagger'

        # Validate config directory path
        try:
            validate_file_path(self.config_dir, base_path=Path.home())
        except ValueError as e:
            logger.warning(f"Config directory validation warning: {e}")
            # Fall back to default
            self.config_dir = Path.home() / '.music_tagger'

        self.config_dir.mkdir(exist_ok=True, parents=True)

        # Set secure permissions on config directory (owner only)
        try:
            os.chmod(self.config_dir, 0o700)
        except Exception as e:
            logger.warning(f"Could not set secure permissions: {e}")

        self.config_file = self.config_dir / 'config.json'

        # Create subdirectories with secure permissions
        for subdir in ['logs', 'cache', 'temp']:
            subdir_path = self.config_dir / subdir
            subdir_path.mkdir(exist_ok=True)
            try:
                os.chmod(subdir_path, 0o700)
            except Exception as e:
                logger.warning(f"Could not set permissions on {subdir}: {e}")

        self._config: Optional[AppConfig] = None

    def load_config(self) -> AppConfig:
        """
        Load configuration from file and environment variables.

        Returns:
            AppConfig: Loaded configuration settings
        """
        if self._config is not None:
            return self._config

        # Start with default configuration
        config_dict = {}

        # Load from file if it exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                logger.debug(f"Loaded configuration from: {self.config_file}")
            except Exception as e:
                logger.warning(f"Could not load config file: {e}")
                config_dict = {}

        # Override with environment variables
        env_config = self._load_from_environment()
        config_dict.update(env_config)

        # Remove deprecated API key fields from old config files
        deprecated_fields = [
            'anthropic_api_key', 'api_key', 'api_model',
            'api_timeout', 'api_max_retries'
        ]
        for field in deprecated_fields:
            config_dict.pop(field, None)

        # Create AppConfig instance
        try:
            self._config = AppConfig(**config_dict)
        except TypeError as e:
            logger.warning(f"Invalid configuration data: {e}")
            self._config = AppConfig()
            # Save corrected default config
            self.save_config()

        return self._config

    def save_config(self, config: Optional[AppConfig] = None) -> bool:
        """
        Save configuration to file.

        SECURITY: API keys and sensitive data are NEVER saved to the config file.
        They should only exist in environment variables.

        Args:
            config: Configuration to save. Uses current config if None.

        Returns:
            bool: True if saved successfully
        """
        if config:
            self._config = config
        elif self._config is None:
            self._config = AppConfig()

        try:
            config_dict = asdict(self._config)

            # No sensitive data to remove - Claude Max plan uses local `claude` command, not API keys!
            safe_dict = config_dict

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(safe_dict, f, indent=2, ensure_ascii=False)

            # Set secure file permissions (owner read/write only)
            try:
                os.chmod(self.config_file, 0o600)
            except Exception as e:
                logger.warning(f"Could not set secure permissions on config file: {e}")

            logger.debug(f"Saved configuration to: {self.config_file}")
            return True

        except Exception as e:
            logger.error(f"Could not save configuration: {e}")
            return False

    def run_configuration_wizard(self) -> AppConfig:
        """
        Run interactive configuration wizard.

        Returns:
            AppConfig: Updated configuration
        """
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Confirm, Prompt

        console = Console()
        console.print(Panel.fit(
            "[bold green]Music Tagger Configuration Wizard[/bold green]\n"
            "Set up your music library tagger preferences\n\n"
            "[bold cyan]ℹ️  Uses Claude Max plan through local `claude` command - NO API keys needed![/bold cyan]",
            title="Configuration"
        ))

        # Load current config as starting point
        config = self.load_config()

        # Claude Code Configuration
        console.print("\n[bold blue]Claude Code Configuration[/bold blue]")
        console.print("✓ Using Claude Max plan through local `claude` command")
        console.print("  (No API keys required!)\n")

        # Model selection (optional - default is sonnet)
        available_models = [
            ("sonnet", "Claude Sonnet (recommended, balanced)"),
            ("opus", "Claude Opus (most capable, slower)"),
            ("haiku", "Claude Haiku (fastest, less accurate)")
        ]

        console.print("Select Claude model (leave blank for default 'sonnet'):")
        for i, (model, desc) in enumerate(available_models, 1):
            marker = "✓" if model == config.claude_code_model else " "
            console.print(f"  {marker} {i}. {desc}")

        model_choice = Prompt.ask(
            "Select model",
            choices=[str(i) for i in range(1, len(available_models) + 1)],
            default="1"
        )
        config.claude_code_model = available_models[int(model_choice) - 1][0]

        # Library Paths
        console.print("\n[bold blue]Music Library Paths[/bold blue]")

        if config.library_paths:
            console.print("Current library paths:")
            for i, path in enumerate(config.library_paths, 1):
                console.print(f"  {i}. {path}")

        add_paths = Confirm.ask("Add or modify library paths?", default=True)
        if add_paths:
            new_paths = []
            while True:
                path = Prompt.ask(
                    "Enter music library path (or press Enter to finish)",
                    default=""
                )
                if not path:
                    break

                path_obj = Path(path).expanduser()
                if path_obj.exists() and path_obj.is_dir():
                    new_paths.append(str(path_obj))
                    console.print(f"✓ Added: {path_obj}")
                else:
                    console.print(f"[red]✗ Directory not found: {path}[/red]")

            if new_paths:
                config.library_paths = new_paths

        # Processing Options
        console.print("\n[bold blue]Processing Options[/bold blue]")

        config.batch_size = int(Prompt.ask(
            "Batch size (files per main batch, will be split into 15-artist sub-batches)",
            default=str(config.batch_size)
        ))

        config.overwrite_existing_tags = Confirm.ask(
            "Always overwrite existing grouping tags?",
            default=config.overwrite_existing_tags
        )

        # Caching Options
        console.print("\n[bold blue]Caching Options[/bold blue]")

        config.cache_enabled = Confirm.ask(
            "Enable artist country caching?",
            default=config.cache_enabled
        )

        if config.cache_enabled:
            config.cache_ttl_days = int(Prompt.ask(
                "Cache TTL in days",
                default=str(config.cache_ttl_days)
            ))

        # UI Preferences
        console.print("\n[bold blue]User Interface[/bold blue]")

        config.show_progress_bars = Confirm.ask(
            "Show progress bars during processing?",
            default=config.show_progress_bars
        )

        config.show_file_names = Confirm.ask(
            "Display current file being processed?",
            default=config.show_file_names
        )

        config.color_output = Confirm.ask(
            "Use colored output?",
            default=config.color_output
        )

        # Save configuration
        console.print("\n[bold green]Saving Configuration[/bold green]")
        if self.save_config(config):
            console.print("✓ Configuration saved successfully")
        else:
            console.print("[red]✗ Failed to save configuration[/red]")

        self._config = config
        return config

    def validate_config(self, config: Optional[AppConfig] = None) -> List[str]:
        """
        Validate configuration settings.

        Args:
            config: Configuration to validate. Uses current config if None.

        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        if config is None:
            config = self.load_config()

        errors = []

        # Claude Code - no API key validation needed (uses local command with Max plan)

        # Library Paths
        if not config.library_paths:
            errors.append("At least one library path must be configured")
        else:
            for path in config.library_paths:
                path_obj = Path(path)
                if not path_obj.exists():
                    errors.append(f"Library path does not exist: {path}")
                elif not path_obj.is_dir():
                    errors.append(f"Library path is not a directory: {path}")

        # Batch Size
        if config.batch_size < 1 or config.batch_size > 1000:
            errors.append("Batch size must be between 1 and 1000")

        # Cache TTL
        if config.cache_enabled and (config.cache_ttl_days < 1 or config.cache_ttl_days > 365):
            errors.append("Cache TTL must be between 1 and 365 days")

        # Log Level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if config.log_level not in valid_log_levels:
            errors.append(f"Log level must be one of: {', '.join(valid_log_levels)}")

        return errors

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration for display.

        Returns:
            Dict[str, Any]: Configuration summary
        """
        config = self.load_config()

        return {
            'claude_model': config.claude_code_model or 'sonnet (default)',
            'claude_timeout': config.claude_timeout,
            'library_paths': config.library_paths,
            'batch_size': config.batch_size,
            'cache_enabled': config.cache_enabled,
            'cache_ttl_days': config.cache_ttl_days if config.cache_enabled else 'N/A',
            'supported_extensions': config.supported_extensions,
            'overwrite_existing': config.overwrite_existing_tags,
            'config_file': str(self.config_file),
            'config_dir': str(self.config_dir),
            'note': 'Uses Claude Max plan - no API keys needed!'
        }

    def _load_from_environment(self) -> Dict[str, Any]:
        """
        Load configuration values from environment variables.

        Returns:
            Dict[str, Any]: Configuration values from environment
        """
        env_config = {}

        # Map environment variables to config keys (NO API KEYS - uses Claude Max!)
        env_mappings = {
            'MUSIC_TAGGER_MODEL': 'claude_code_model',
            'MUSIC_TAGGER_TIMEOUT': 'claude_timeout',
            'MUSIC_TAGGER_BATCH_SIZE': 'batch_size',
            'MUSIC_TAGGER_LOG_LEVEL': 'log_level',
            'MUSIC_TAGGER_CACHE_TTL': 'cache_ttl_days',
        }

        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                # Convert to appropriate type
                if config_key in ['batch_size', 'cache_ttl_days', 'claude_timeout', 'claude_max_retries']:
                    try:
                        env_config[config_key] = int(value)
                    except ValueError:
                        logger.warning(f"Invalid integer value for {env_var}: {value}")
                elif config_key in ['cache_enabled', 'overwrite_existing_tags']:
                    env_config[config_key] = value.lower() in ('true', '1', 'yes', 'on')
                else:
                    env_config[config_key] = value

        # Handle library paths from environment
        library_paths_env = os.getenv('MUSIC_TAGGER_LIBRARY_PATHS')
        if library_paths_env:
            # Split on semicolon or colon
            separator = ';' if ';' in library_paths_env else ':'
            paths = [p.strip() for p in library_paths_env.split(separator) if p.strip()]
            env_config['library_paths'] = paths

        return env_config


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config() -> AppConfig:
    """Get the current application configuration."""
    return get_config_manager().load_config()


# Example usage and testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'wizard':
        # Run configuration wizard
        manager = ConfigManager()
        config = manager.run_configuration_wizard()
        print("\nConfiguration completed!")
    else:
        # Show current configuration
        manager = ConfigManager()
        config = manager.load_config()

        print("Current Configuration:")
        print(f"  Claude Model: {config.claude_code_model or 'sonnet (default)'}")
        print(f"  Claude Timeout: {config.claude_timeout}s")
        print(f"  Library Paths: {config.library_paths}")
        print(f"  Batch Size: {config.batch_size}")
        print(f"  Cache Enabled: {config.cache_enabled}")
        print(f"  Cache TTL: {config.cache_ttl_days} days")
        print("\n  ℹ️  Uses Claude Max plan - NO API keys needed!")

        # Validate configuration
        errors = manager.validate_config()
        if errors:
            print("\nConfiguration Errors:")
            for error in errors:
                print(f"  ✗ {error}")
        else:
            print("\n✓ Configuration is valid")

        print(f"\nConfiguration file: {manager.config_file}")
        print(f"Configuration directory: {manager.config_dir}")
