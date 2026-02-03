"""
Utility functions for Music Tools.
Provides common functionality used across different tools.
"""
import functools
import json
import logging
import os
import random
import time
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('music_tools.utils')

# Type variables for generic functions
T = TypeVar('T')
R = TypeVar('R')


class RetryError(Exception):
    """Exception raised when maximum retry attempts are exceeded."""


def setup_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Set up a logger with the specified name and configuration.

    Args:
        name: Logger name
        log_file: Path to log file (if None, logs to console only)
        level: Logging level

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create file handler if log file specified
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    backoff: float = 2.0,
    max_delay: Optional[float] = None,
    jitter: bool = False
) -> float:
    """
    Calculate exponential backoff delay for retry attempts.

    Args:
        attempt: Current attempt number (1-indexed)
        base_delay: Initial delay in seconds
        backoff: Multiplier for exponential increase
        max_delay: Maximum delay in seconds (caps the backoff)
        jitter: If True, add random jitter to prevent thundering herd

    Returns:
        Delay in seconds

    Example:
        >>> exponential_backoff(1, base_delay=1, backoff=2)  # 1 second
        1
        >>> exponential_backoff(3, base_delay=1, backoff=2)  # 4 seconds
        4
        >>> exponential_backoff(5, base_delay=1, backoff=2, max_delay=10)  # Capped at 10
        10
    """
    if attempt <= 0:
        return 0.0

    # Calculate exponential delay: base * (backoff ^ (attempt - 1))
    delay = base_delay * (backoff ** (attempt - 1))

    # Cap at max_delay if specified
    if max_delay is not None:
        delay = min(delay, max_delay)

    # Add jitter to prevent thundering herd problem
    if jitter:
        delay = random.uniform(0, delay)

    return delay


def safe_request(func: Callable[..., T], *args, **kwargs) -> Optional[T]:
    """Execute a function with error handling.

    Args:
        func: Function to execute
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Function result or None if an error occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {str(e)}")
        logger.debug(traceback.format_exc())
        return None


def retry(
    max_attempts: int = 3,
    delay: Union[float, Callable[[int], float]] = 1.0,
    backoff: float = 2.0,
    max_delay: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
) -> Callable:
    """
    Retry decorator with exponential backoff and advanced features.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds, or callable that takes attempt number
        backoff: Backoff multiplier for exponential delay
        max_delay: Maximum delay between retries (caps exponential growth)
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback called on each retry with (attempt, exception, delay)

    Returns:
        Decorator function

    Raises:
        ValueError: If max_attempts <= 0 or delay < 0
        RetryError: If all retry attempts are exhausted

    Example:
        >>> @retry(max_attempts=3, delay=1.0, backoff=2.0)
        ... def flaky_api_call():
        ...     # May fail temporarily
        ...     return requests.get('https://api.example.com')
    """
    # Validate parameters
    if max_attempts <= 0:
        raise ValueError("max_attempts must be greater than 0")

    if isinstance(delay, (int, float)) and delay < 0:
        raise ValueError("delay must be non-negative")

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)  # Preserve function metadata
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # If this was the last attempt, raise RetryError
                    if attempt >= max_attempts:
                        raise RetryError(
                            f"Failed after {max_attempts} maximum retry attempts. "
                            f"Last error: {type(e).__name__}: {e}"
                        ) from e

                    # Calculate delay for this retry
                    if callable(delay):
                        wait_time = delay(attempt)
                    else:
                        wait_time = delay * (backoff ** (attempt - 1))
                        if max_delay is not None:
                            wait_time = min(wait_time, max_delay)

                    # Call the on_retry callback if provided
                    if on_retry:
                        on_retry(attempt, e, wait_time)

                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {str(e)}. "
                        f"Retrying in {wait_time:.2f}s..."
                    )
                    time.sleep(wait_time)

            # Should never reach here due to raise in except block
            raise RetryError(
                "Unexpected error in retry decorator"
            ) from last_exception

        return wrapper

    return decorator


def format_duration(seconds: int) -> str:
    """Format duration in seconds to MM:SS format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}:{seconds:02d}"


def format_date(date_str: str) -> str:
    """Format date string to a consistent format.

    Args:
        date_str: Date string in various formats

    Returns:
        Formatted date string (YYYY-MM-DD)
    """
    # Handle different date formats
    if len(date_str) == 4:  # Year only
        return f"{date_str}-01-01"
    elif len(date_str) == 7:  # Year-Month
        return f"{date_str}-01"
    elif len(date_str) == 10:  # Year-Month-Day
        return date_str
    else:
        try:
            # Try to parse with datetime
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            logger.warning(f"Could not parse date: {date_str}")
            return date_str


def save_json(data: Any, file_path: str) -> bool:
    """Save data to a JSON file.

    Args:
        data: Data to save
        file_path: Path to save the file

    Returns:
        True if successful, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON file: {str(e)}")
        return False


def load_json(file_path: str) -> Optional[Any]:
    """Load data from a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Loaded data or None if an error occurred
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading JSON file: {str(e)}")
        return None


def confirm_action(prompt: str, default: bool = False) -> bool:
    """Prompt the user to confirm an action.

    Args:
        prompt: Prompt message
        default: Default value if the user just presses Enter

    Returns:
        True if confirmed, False otherwise
    """
    default_str = 'Y/n' if default else 'y/N'
    response = input(f"{prompt} [{default_str}]: ").strip().lower()

    if not response:
        return default

    return response.startswith('y')


def create_directory_if_not_exists(directory: str) -> bool:
    """Create a directory if it doesn't exist.

    Args:
        directory: Directory path

    Returns:
        True if the directory exists or was created, False otherwise
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {str(e)}")
        return False


def get_file_extension(file_path: str) -> str:
    """Get the extension of a file.

    Args:
        file_path: Path to the file

    Returns:
        File extension (lowercase, without the dot)
    """
    return os.path.splitext(file_path)[1].lower().lstrip('.')


def is_valid_file(file_path: str, allowed_extensions: List[str] = None) -> bool:
    """Check if a file exists and has a valid extension.

    Args:
        file_path: Path to the file
        allowed_extensions: List of allowed extensions (without the dot)

    Returns:
        True if the file is valid, False otherwise
    """
    if not os.path.isfile(file_path):
        return False

    if allowed_extensions:
        extension = get_file_extension(file_path)
        return extension in allowed_extensions

    return True


def truncate_string(s: str, max_length: int = 50, suffix: str = '...') -> str:
    """Truncate a string to a maximum length.

    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s

    return s[:max_length - len(suffix)] + suffix


def print_table(data: List[Dict[str, Any]], columns: List[str],
                widths: Dict[str, int] = None, title: str = None) -> None:
    """Print a table of data.

    Args:
        data: List of dictionaries containing the data
        columns: List of column names to include
        widths: Dictionary mapping column names to column widths
        title: Table title
    """
    if not data:
        print("No data to display")
        return

    # Determine column widths if not provided
    if not widths:
        widths = {}
        for col in columns:
            # Width is the maximum of the column name length and the longest value
            widths[col] = max(
                len(col),
                max(len(str(item.get(col, ''))) for item in data)
            )

    # Print title if provided
    if title:
        print(f"\n{title}")
        print('=' * sum(widths.values() + len(columns) + 1))

    # Print header
    header = ' | '.join(col.ljust(widths[col]) for col in columns)
    print(header)
    print('-' * len(header))

    # Print data
    for item in data:
        row = ' | '.join(
            str(item.get(col, '')).ljust(widths[col]) for col in columns
        )
        print(row)
