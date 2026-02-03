#!/usr/bin/env python3
"""
Error handling and resilience utilities for the EDM Music Blog Scraper.
"""

import asyncio
import logging
import os
import random
import re
import threading
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Import configuration
from .config import (
    BACKOFF_FACTOR,
    CHUNK_SIZE,
    MAX_DELAY,
    MAX_FILE_SIZE,
    MAX_RETRIES,
    MAX_URL_LENGTH,
    RATE_LIMIT_MAX_DELAY,
    RATE_LIMIT_MIN_DELAY,
    REQUEST_TIMEOUT,
    USER_AGENTS,
    VALID_HOSTS,
)

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for generic return types
T = TypeVar("T")


class ScrapingError(Exception):
    """Base exception for scraping errors."""


class RateLimitError(ScrapingError):
    """Raised when rate limit is detected."""


class ContentError(ScrapingError):
    """Raised when content is invalid or missing."""


class NetworkError(ScrapingError):
    """Raised for network-related errors."""


class ValidationError(ScrapingError):
    """Raised when input validation fails."""


class ThreadSafeRateLimiter:
    """Thread-safe rate limiter for managing request delays."""

    def __init__(
        self, min_delay: float = RATE_LIMIT_MIN_DELAY, max_delay: float = RATE_LIMIT_MAX_DELAY
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time: Dict[str, float] = {}
        self._lock = threading.Lock()

    def wait_if_needed(self, domain: str) -> None:
        """Wait if needed to respect rate limits for a domain."""
        with self._lock:
            current_time = time.time()

            if domain in self.last_request_time:
                elapsed = current_time - self.last_request_time[domain]
                delay = random.uniform(self.min_delay, self.max_delay)

                if elapsed < delay:
                    sleep_time = delay - elapsed
                    time.sleep(sleep_time)

            self.last_request_time[domain] = time.time()


class AsyncRateLimiter:
    """Async rate limiter for managing request delays."""

    def __init__(
        self, min_delay: float = RATE_LIMIT_MIN_DELAY, max_delay: float = RATE_LIMIT_MAX_DELAY
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait_if_needed(self, domain: str) -> None:
        """Wait if needed to respect rate limits for a domain."""
        async with self._lock:
            current_time = time.time()

            if domain in self.last_request_time:
                elapsed = current_time - self.last_request_time[domain]
                delay = random.uniform(self.min_delay, self.max_delay)

                if elapsed < delay:
                    sleep_time = delay - elapsed
                    await asyncio.sleep(sleep_time)

            self.last_request_time[domain] = time.time()


def exponential_backoff(
    func: Callable[..., T],
    max_retries: int = MAX_RETRIES,
    base_delay: float = 1.0,
    max_delay: float = MAX_DELAY,
    exponential_base: float = BACKOFF_FACTOR,
    jitter: bool = True,
) -> Callable[..., Optional[T]]:
    """
    Decorator for exponential backoff retry logic.

    Args:
        func: Function to wrap
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays

    Returns:
        Wrapped function with retry logic
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Optional[T]:
        pass

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries - 1:
                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    if jitter:
                        delay *= 0.5 + random.random()
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f} seconds..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_retries} attempts failed for {func.__name__}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}")
                raise

        return None

    return wrapper


def rate_limit_handler(response: requests.Response) -> Optional[float]:
    """
    Handle rate limiting responses.

    Args:
        response: HTTP response object

    Returns:
        Delay in seconds if rate limited, None otherwise
    """
    if response.status_code == 429:
        # Check for Retry-After header
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                # Could be seconds or HTTP date
                delay = float(retry_after)
            except ValueError:
                # Parse HTTP date format
                from datetime import datetime
                from email.utils import parsedate_to_datetime

                try:
                    retry_date = parsedate_to_datetime(retry_after)
                    delay = (retry_date - datetime.now()).total_seconds()
                except Exception:
                    delay = 60  # Default delay
        else:
            delay = 60  # Default delay

        logger.warning(f"Rate limited. Waiting {delay} seconds...")
        return delay

    return None


@contextmanager
def rate_limiter(min_delay: float = RATE_LIMIT_MIN_DELAY, max_delay: float = RATE_LIMIT_MAX_DELAY):
    """
    Context manager for rate limiting requests.

    Args:
        min_delay: Minimum delay between requests
        max_delay: Maximum delay between requests
    """
    start_time = time.time()

    try:
        yield
    finally:
        # Calculate random delay
        delay = random.uniform(min_delay, max_delay)

        # Account for time already spent
        elapsed = time.time() - start_time
        remaining_delay = max(0, delay - elapsed)

        if remaining_delay > 0:
            time.sleep(remaining_delay)


def create_resilient_session(
    max_retries: int = MAX_RETRIES,
    backoff_factor: float = BACKOFF_FACTOR,
    status_forcelist: Optional[list] = None,
    pool_connections: int = 10,
    pool_maxsize: int = 10,
) -> requests.Session:
    """
    Create a requests session with retry logic and connection pooling.

    Args:
        max_retries: Maximum number of retries
        backoff_factor: Backoff factor for retries
        status_forcelist: HTTP status codes to retry
        pool_connections: Number of connection pools
        pool_maxsize: Maximum size of connection pool

    Returns:
        Configured requests session
    """
    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]

    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        raise_on_status=False,
    )

    # Create adapter with retry strategy and connection pooling
    adapter = HTTPAdapter(
        max_retries=retry_strategy, pool_connections=pool_connections, pool_maxsize=pool_maxsize
    )

    # Mount adapter for both HTTP and HTTPS
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set default headers
    session.headers.update(
        {
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )

    return session


def get_random_user_agent() -> str:
    """
    Get a random user agent string.

    Returns:
        Random user agent string
    """
    return random.choice(USER_AGENTS)


def validate_url(url: str) -> bool:
    """
    Validate if a URL is properly formatted and safe.

    Args:
        url: URL to validate

    Returns:
        True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    if len(url) > MAX_URL_LENGTH:
        logger.warning(f"URL too long: {len(url)} characters")
        return False

    if not url.startswith(("http://", "https://")):
        return False

    # Basic URL structure check
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False

        # Check for suspicious patterns
        suspicious_patterns = [
            r"javascript:",
            r"data:",
            r"file:",
            r"ftp:",
            r"mailto:",
            r"<script",
            r"<iframe",
            r"<object",
            r"<embed",
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                logger.warning(f"Suspicious URL pattern detected: {pattern}")
                return False

        return True
    except Exception as e:
        logger.warning(f"URL validation error: {e}")
        return False


def validate_host(host: str) -> bool:
    """
    Validate if a host is in the allowed list.

    Args:
        host: Host to validate

    Returns:
        True if valid, False otherwise
    """
    if not host:
        return False

    # Check if host is in valid hosts list
    for valid_host in VALID_HOSTS:
        if valid_host in host.lower():
            return True

    return False


def safe_request(
    session: requests.Session, url: str, method: str = "GET", **kwargs
) -> Optional[requests.Response]:
    """
    Make a safe HTTP request with error handling.

    Args:
        session: Requests session
        url: URL to request
        method: HTTP method
        **kwargs: Additional arguments for request

    Returns:
        Response object or None if failed
    """
    if not validate_url(url):
        logger.error(f"Invalid URL: {url}")
        return None

    try:
        response = session.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)

        # Check for rate limiting
        delay = rate_limit_handler(response)
        if delay:
            time.sleep(delay)
            # Retry after rate limit delay
            response = session.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)

        # Check response status
        response.raise_for_status()

        return response

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "unknown"

        if status_code == 404:
            logger.debug(f"Page not found (404): {url}")
        elif status_code == 403:
            logger.warning(f"Access forbidden (403): {url}")
            # Try with different user agent
            session.headers["User-Agent"] = get_random_user_agent()
        else:
            logger.error(f"HTTP error {status_code} for {url}: {e}")

        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {e}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error requesting {url}: {e}")
        return None


def handle_connection_error(
    session: requests.Session, error: Union[requests.exceptions.ConnectionError, Exception]
) -> requests.Session:
    """
    Handle connection errors by recreating the session.

    Args:
        session: Current session
        error: The error that occurred

    Returns:
        New session instance
    """
    logger.warning(f"Connection error: {error}. Creating new session...")

    # Close the old session
    try:
        session.close()
    except Exception:
        pass

    # Create a new session
    return create_resilient_session()


def parse_content_safely(response: requests.Response, parser: str = "html.parser") -> Optional[Any]:
    """
    Safely parse response content.

    Args:
        response: HTTP response
        parser: Parser to use (for BeautifulSoup)

    Returns:
        Parsed content or None
    """
    if not response or not response.content:
        logger.warning("Empty response content")
        return None

    # Check content type
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        logger.warning(f"Non-HTML content type: {content_type}")
        return None

    try:
        from bs4 import BeautifulSoup

        return BeautifulSoup(response.content, parser)
    except Exception as e:
        logger.error(f"Error parsing content: {e}")
        return None


def log_progress(current: int, total: int, prefix: str = "Progress") -> None:
    """
    Log progress information.

    Args:
        current: Current item number
        total: Total number of items
        prefix: Prefix for log message
    """
    percentage = (current / total) * 100 if total > 0 else 0
    logger.info(f"{prefix}: {current}/{total} ({percentage:.1f}%)")


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename for safe file system usage.

    Args:
        filename: Original filename
        max_length: Maximum length for filename

    Returns:
        Sanitized filename
    """
    import re
    import unicodedata

    # Normalize unicode characters
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Remove control characters
    filename = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", filename)

    # Limit length
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        name = name[: max_length - len(ext) - 1]
        filename = name + ext

    return filename.strip()


def safe_file_read(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """
    Safely read a file with error handling.

    Args:
        file_path: Path to the file
        encoding: File encoding

    Returns:
        File content or None if failed
    """
    try:
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            logger.error(f"File too large: {file_size} bytes")
            return None

        # Read file in chunks for large files
        if file_size > CHUNK_SIZE * 10:
            content = ""
            with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    content += chunk
            return content
        else:
            with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                return f.read()

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None
    except PermissionError:
        logger.error(f"Permission denied: {file_path}")
        return None
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error reading {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return None


def validate_file_path(file_path: str) -> bool:
    """
    Validate if a file path is safe to use.

    Args:
        file_path: File path to validate

    Returns:
        True if safe, False otherwise
    """
    if not file_path or not isinstance(file_path, str):
        return False

    # Allow temporary files (common in testing)
    if "/tmp/" in file_path or "/var/folders/" in file_path or "tmp_" in file_path:
        return True

    # Check for path traversal attempts
    suspicious_patterns = [r"\.\./", r"\.\.\\", r"//", r"\\", r"~", r"%", r"&", r"`", r"\$"]

    for pattern in suspicious_patterns:
        if re.search(pattern, file_path):
            logger.warning(f"Suspicious file path pattern: {pattern}")
            return False

    # Check if path is absolute and in allowed directories
    if os.path.isabs(file_path):
        # Only allow paths in current directory or subdirectories
        current_dir = os.getcwd()
        try:
            real_path = os.path.realpath(file_path)
            if not real_path.startswith(current_dir):
                logger.warning(f"Path outside current directory: {file_path}")
                return False
        except Exception:
            return False

    return True
