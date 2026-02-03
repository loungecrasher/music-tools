"""
Logging System for Music Library Country Tagger

Comprehensive logging with file rotation, structured formatting, and performance tracking.
Provides both console and file logging with configurable levels and formats.

Author: CLI & User Experience Developer
Created: September 2025
"""

import json
import logging
import logging.handlers
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler

# Global logger instances
_loggers: Dict[str, logging.Logger] = {}
_log_dir: Optional[Path] = None
_console = Console()


@dataclass
class LogConfig:
    """Configuration for logging system."""
    log_level: str = 'INFO'
    log_to_console: bool = True
    log_to_file: bool = True
    log_dir: Optional[str] = None
    max_file_size_mb: int = 10
    backup_count: int = 5
    console_format: str = "[%(levelname)8s] %(name)s: %(message)s"
    file_format: str = "%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"


class PerformanceLogger:
    """Performance tracking and logging."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._timers: Dict[str, float] = {}
        self._counters: Dict[str, int] = {}
        self._performance_log: list = []

    def start_timer(self, name: str):
        """Start a performance timer."""
        self._timers[name] = time.time()
        self.logger.debug(f"Timer started: {name}")

    def stop_timer(self, name: str, log_result: bool = True) -> float:
        """Stop a performance timer and return elapsed time."""
        if name not in self._timers:
            self.logger.warning(f"Timer '{name}' was not started")
            return 0.0

        elapsed = time.time() - self._timers[name]
        del self._timers[name]

        if log_result:
            self.logger.info(f"Timer '{name}' completed in {elapsed:.3f}s")

        # Store performance data
        self._performance_log.append({
            'timestamp': datetime.now().isoformat(),
            'timer_name': name,
            'elapsed_time': elapsed
        })

        return elapsed

    def increment_counter(self, name: str, value: int = 1):
        """Increment a performance counter."""
        self._counters[name] = self._counters.get(name, 0) + value
        self.logger.debug(f"Counter '{name}' incremented to {self._counters[name]}")

    def get_counter(self, name: str) -> int:
        """Get current counter value."""
        return self._counters.get(name, 0)

    def reset_counter(self, name: str):
        """Reset a counter to zero."""
        if name in self._counters:
            del self._counters[name]
            self.logger.debug(f"Counter '{name}' reset")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            'active_timers': list(self._timers.keys()),
            'counters': dict(self._counters),
            'recent_timings': self._performance_log[-20:] if self._performance_log else []
        }

    def log_system_info(self):
        """Log system information for debugging."""
        try:
            import platform

            import psutil

            system_info = {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'python_version': platform.python_version(),
                'cpu_count': os.cpu_count(),
                'memory_total_mb': psutil.virtual_memory().total // (1024 * 1024),
                'disk_free_gb': psutil.disk_usage('/').free // (1024 * 1024 * 1024)
            }

            self.logger.info(f"System info: {json.dumps(system_info, indent=2)}")

        except ImportError:
            self.logger.debug("psutil not available for system info logging")
        except Exception as e:
            self.logger.warning(f"Failed to log system info: {e}")


class StructuredLogFormatter(logging.Formatter):
    """Custom formatter for structured logging."""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def _sanitize_log_value(self, value: str) -> str:
        """
        Sanitize log values to prevent log injection attacks.

        Args:
            value: The log value to sanitize

        Returns:
            Sanitized log value safe for logging
        """
        # Import security module if available
        try:
            from .core.security import SecurityValidator
            return SecurityValidator.sanitize_log_message(value)
        except ImportError:
            # Fallback sanitization if security module not available
            # Remove line breaks to prevent log injection
            sanitized = str(value).replace('\n', '\\n').replace('\r', '\\r')
            # Limit length to prevent log bloat
            return sanitized[:1000] if len(sanitized) > 1000 else sanitized

    def format(self, record: logging.LogRecord) -> str:
        # Base message
        timestamp = datetime.fromtimestamp(record.created).isoformat()

        log_data = {
            'timestamp': timestamp,
            'level': record.levelname,
            'logger': record.name,
            'message': self._sanitize_log_value(record.getMessage()),
        }

        # Add location info for debug level
        if record.levelno <= logging.DEBUG:
            log_data['file'] = record.filename
            log_data['line'] = record.lineno
            log_data['function'] = record.funcName

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields if enabled
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                               'filename', 'module', 'lineno', 'funcName', 'created',
                               'msecs', 'relativeCreated', 'thread', 'threadName',
                               'processName', 'process', 'message', 'exc_info', 'exc_text',
                               'stack_info']:
                    log_data['extra'] = log_data.get('extra', {})
                    # Sanitize log values to prevent log injection
                    if isinstance(value, str):
                        value = self._sanitize_log_value(value)
                    log_data['extra'][key] = value

        return json.dumps(log_data)


def setup_logging(config: Optional[LogConfig] = None) -> Path:
    """Set up logging system with specified configuration."""
    global _log_dir

    if config is None:
        config = LogConfig()

    # Determine log directory
    if config.log_dir:
        _log_dir = Path(config.log_dir)
    else:
        _log_dir = Path.home() / '.music_tagger' / 'logs'

    # Create log directory
    _log_dir.mkdir(parents=True, exist_ok=True)

    # Set root logging level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level.upper()))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler with Rich formatting
    if config.log_to_console:
        console_handler = RichHandler(
            console=_console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=False,
            log_time_format="[%X]"
        )
        console_handler.setLevel(getattr(logging, config.log_level.upper()))

        # Use simple format for console
        console_formatter = logging.Formatter(
            fmt="%(message)s",
            datefmt=config.date_format
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if config.log_to_file:
        # Main log file
        main_log_file = _log_dir / 'music_tagger.log'
        file_handler = logging.handlers.RotatingFileHandler(
            filename=main_log_file,
            maxBytes=config.max_file_size_mb * 1024 * 1024,
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Always capture debug in files

        # Detailed format for files
        file_formatter = logging.Formatter(
            fmt=config.file_format,
            datefmt=config.date_format
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Error log file
        error_log_file = _log_dir / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            filename=error_log_file,
            maxBytes=config.max_file_size_mb * 1024 * 1024,
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.WARNING)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)

        # Performance log file (structured JSON)
        perf_log_file = _log_dir / 'performance.log'
        perf_handler = logging.handlers.RotatingFileHandler(
            filename=perf_log_file,
            maxBytes=config.max_file_size_mb * 1024 * 1024,
            backupCount=config.backup_count,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.addFilter(lambda record: hasattr(record, 'performance_data'))
        perf_handler.setFormatter(StructuredLogFormatter())
        root_logger.addHandler(perf_handler)

    # Log the setup
    setup_logger = get_logger('music_tagger.setup')
    setup_logger.info(f"Logging configured - Level: {config.log_level}, Console: {config.log_to_console}, File: {config.log_to_file}")
    setup_logger.info(f"Log directory: {_log_dir}")

    return _log_dir


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger instance."""
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    _loggers[name] = logger

    return logger


def get_performance_logger(name: str) -> PerformanceLogger:
    """Get a performance logger instance."""
    base_logger = get_logger(name)
    return PerformanceLogger(base_logger)


def log_function_call(func):
    """Decorator to log function calls with timing."""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        perf_logger = get_performance_logger(func.__module__)

        func_name = f"{func.__name__}"
        logger.debug(f"Calling {func_name} with args={len(args)}, kwargs={list(kwargs.keys())}")

        perf_logger.start_timer(func_name)
        try:
            result = func(*args, **kwargs)
            elapsed = perf_logger.stop_timer(func_name, log_result=False)
            logger.debug(f"Function {func_name} completed in {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = perf_logger.stop_timer(func_name, log_result=False)
            logger.error(f"Function {func_name} failed after {elapsed:.3f}s: {e}")
            raise

    return wrapper


def log_exception(logger: logging.Logger, exception: Exception, context: str = ""):
    """Log exception with full context."""
    import traceback

    exc_info = {
        'exception_type': type(exception).__name__,
        'exception_message': str(exception),
        'context': context,
        'timestamp': datetime.now().isoformat()
    }

    logger.error(f"Exception in {context}: {exception}", extra={'exception_data': exc_info})
    logger.debug(f"Full traceback: {traceback.format_exc()}")


def get_log_files_info() -> Dict[str, Any]:
    """Get information about log files."""
    if not _log_dir or not _log_dir.exists():
        return {}

    log_files = {}

    for log_file in _log_dir.glob('*.log*'):
        try:
            stat = log_file.stat()
            log_files[log_file.name] = {
                'path': str(log_file),
                'size_mb': stat.st_size / (1024 * 1024),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'readable': os.access(log_file, os.R_OK)
            }
        except (OSError, PermissionError):
            log_files[log_file.name] = {
                'path': str(log_file),
                'error': 'Cannot access file'
            }

    return log_files


def cleanup_old_logs(days_to_keep: int = 30) -> int:
    """Clean up log files older than specified days."""
    if not _log_dir or not _log_dir.exists():
        return 0

    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    cleaned_count = 0

    logger = get_logger('music_tagger.cleanup')

    for log_file in _log_dir.glob('*.log*'):
        try:
            # Skip current log files (without backup numbers)
            if log_file.suffix == '.log' and '.' not in log_file.stem:
                continue

            stat = log_file.stat()
            file_date = datetime.fromtimestamp(stat.st_mtime)

            if file_date < cutoff_date:
                log_file.unlink()
                cleaned_count += 1
                logger.info(f"Cleaned old log file: {log_file.name}")

        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to clean log file {log_file.name}: {e}")

    if cleaned_count > 0:
        logger.info(f"Cleaned {cleaned_count} old log files")

    return cleaned_count


def export_logs(export_path: Path, include_debug: bool = False,
                last_hours: Optional[int] = None) -> bool:
    """Export log data to a file."""
    if not _log_dir or not _log_dir.exists():
        return False

    logger = get_logger('music_tagger.export')

    try:
        exported_lines = []
        cutoff_time = None

        if last_hours:
            cutoff_time = datetime.now() - timedelta(hours=last_hours)

        # Read all log files
        for log_file in sorted(_log_dir.glob('*.log')):
            if log_file.name.startswith('.'):
                continue

            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        # Filter debug logs if not included
                        if not include_debug and ' [   DEBUG]' in line:
                            continue

                        # Filter by time if specified
                        if cutoff_time:
                            try:
                                # Extract timestamp from log line
                                if line.startswith('{'):
                                    # JSON format
                                    import json
                                    log_data = json.loads(line)
                                    log_time = datetime.fromisoformat(log_data['timestamp'])
                                else:
                                    # Standard format
                                    timestamp_end = line.find(' [')
                                    if timestamp_end > 0:
                                        timestamp_str = line[:timestamp_end]
                                        log_time = datetime.fromisoformat(timestamp_str)
                                    else:
                                        continue

                                if log_time < cutoff_time:
                                    continue

                            except (ValueError, KeyError, json.JSONDecodeError):
                                continue

                        exported_lines.append(f"[{log_file.name}] {line}")

            except (OSError, PermissionError) as e:
                logger.warning(f"Failed to read log file {log_file.name}: {e}")
                continue

        # Write exported data
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write("Music Library Country Tagger - Log Export\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Include Debug: {include_debug}\n")
            if last_hours:
                f.write(f"Last Hours: {last_hours}\n")
            f.write("=" * 80 + "\n\n")

            for line in exported_lines:
                f.write(line + "\n")

        logger.info(f"Exported {len(exported_lines)} log lines to {export_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to export logs: {e}")
        return False


# Context manager for logging operations
class LoggingContext:
    """Context manager for scoped logging operations."""

    def __init__(self, logger: logging.Logger, operation_name: str,
                 log_level: int = logging.INFO):
        self.logger = logger
        self.operation_name = operation_name
        self.log_level = log_level
        self.perf_logger = PerformanceLogger(logger)
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.log(self.log_level, f"Starting {self.operation_name}")
        self.perf_logger.start_timer(self.operation_name)
        return self.perf_logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = self.perf_logger.stop_timer(self.operation_name, log_result=False)

        if exc_type is None:
            self.logger.log(self.log_level, f"Completed {self.operation_name} in {elapsed:.3f}s")
        else:
            self.logger.error(f"Failed {self.operation_name} after {elapsed:.3f}s: {exc_val}")

        return False  # Don't suppress exceptions


# Initialize default logging on import
try:
    setup_logging()
except Exception as e:
    # Fallback to basic logging if setup fails
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    logging.getLogger(__name__).warning(f"Failed to setup advanced logging, using basic configuration: {e}")
