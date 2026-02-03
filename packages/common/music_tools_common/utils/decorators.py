"""
Common decorators for Music Tools.
Provides reusable decorators for error handling, logging, and more.
"""
import functools
import logging
from typing import Any, Callable

from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


def handle_errors(
    error_message: str = "An error occurred",
    log_error: bool = True,
    raise_error: bool = False,
    return_value: Any = None,
    error_types: tuple = (Exception,)
) -> Callable:
    """
    Decorator for standardized error handling.

    Args:
        error_message: Message to display when error occurs
        log_error: Whether to log the error
        raise_error: Whether to re-raise the error after handling
        return_value: Value to return on error (if not raising)
        error_types: Tuple of exception types to catch

    Example:
        @handle_errors("Failed to process file", return_value=False)
        def process_file(path):
            # Process file logic
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_types as e:
                if log_error:
                    logger.error(f"{error_message}: {str(e)}", exc_info=True)

                console.print(f"\n[bold red]{error_message}:[/bold red] {str(e)}")

                if raise_error:
                    raise

                return return_value
        return wrapper
    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator to retry a function on failure.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry

    Example:
        @retry(max_attempts=3, delay=1.0)
        def fetch_data(url):
            # Fetch data logic
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {str(e)}")
                        raise

                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {str(e)}. "
                        f"Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

        return wrapper
    return decorator


def log_execution(
    level: int = logging.INFO,
    include_args: bool = False,
    include_result: bool = False
) -> Callable:
    """
    Decorator to log function execution.

    Args:
        level: Logging level to use
        include_args: Whether to log function arguments
        include_result: Whether to log function result

    Example:
        @log_execution(level=logging.DEBUG, include_args=True)
        def important_function(x, y):
            return x + y
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__

            if include_args:
                logger.log(level, f"Calling {func_name} with args={args}, kwargs={kwargs}")
            else:
                logger.log(level, f"Calling {func_name}")

            result = func(*args, **kwargs)

            if include_result:
                logger.log(level, f"{func_name} returned: {result}")
            else:
                logger.log(level, f"{func_name} completed")

            return result
        return wrapper
    return decorator


def validate_args(**validators) -> Callable:
    """
    Decorator to validate function arguments.

    Args:
        **validators: Keyword arguments mapping parameter names to validator functions

    Example:
        @validate_args(
            age=lambda x: x > 0,
            name=lambda x: isinstance(x, str) and len(x) > 0
        )
        def create_user(name: str, age: int):
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Validate each argument
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if not validator(value):
                        raise ValueError(
                            f"Validation failed for parameter '{param_name}' "
                            f"with value: {value}"
                        )

            return func(*args, **kwargs)
        return wrapper
    return decorator
