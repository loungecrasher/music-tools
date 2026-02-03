"""
HTTP session management and request utilities.

This module provides utilities for creating resilient HTTP sessions,
making safe requests, and handling rate limiting and retries.
"""

import logging
import random
import time
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# Default user agents for web scraping
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
]


def get_random_user_agent(user_agents: Optional[List[str]] = None) -> str:
    """
    Get a random user agent string.

    Args:
        user_agents: List of user agents to choose from (default: DEFAULT_USER_AGENTS)

    Returns:
        Random user agent string

    Example:
        >>> agent = get_random_user_agent()
        >>> print(agent[:20])
        'Mozilla/5.0 (Windows'
    """
    if user_agents is None:
        user_agents = DEFAULT_USER_AGENTS

    return random.choice(user_agents)


def create_resilient_session(
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    status_forcelist: Optional[List[int]] = None,
    pool_connections: int = 10,
    pool_maxsize: int = 10,
    timeout: int = 30,
    user_agent: Optional[str] = None,
) -> requests.Session:
    """
    Create a requests session with retry logic and connection pooling.

    Configures automatic retries for transient failures, connection pooling
    for efficiency, and appropriate headers for web requests.

    Args:
        max_retries: Maximum number of retries (default: 3)
        backoff_factor: Backoff factor for retries (default: 1.0)
        status_forcelist: HTTP status codes to retry (default: [429, 500, 502, 503, 504])
        pool_connections: Number of connection pools (default: 10)
        pool_maxsize: Maximum size of connection pool (default: 10)
        timeout: Default timeout for requests in seconds (default: 30)
        user_agent: User agent string (default: random from DEFAULT_USER_AGENTS)

    Returns:
        Configured requests session

    Example:
        >>> session = create_resilient_session(max_retries=5, timeout=60)
        >>> response = session.get('https://api.example.com/data')
    """
    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]

    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
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
    if user_agent is None:
        user_agent = get_random_user_agent()

    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )

    return session


def _safe_request_with_session(
    session: requests.Session, url: str, method: str = "GET", timeout: int = 30, **kwargs
) -> Optional[requests.Response]:
    """
    Make a safe HTTP request with error handling and rate limit handling (internal).

    Args:
        session: Requests session to use
        url: URL to request
        method: HTTP method (default: 'GET')
        timeout: Request timeout in seconds (default: 30)
        **kwargs: Additional arguments for request

    Returns:
        Response object or None if failed

    Example:
        >>> session = create_resilient_session()
        >>> response = _safe_request_with_session(session, 'https://api.example.com/data')
        >>> if response:
        ...     print(f"Status: {response.status_code}")
    """
    try:
        response = session.request(method, url, timeout=timeout, **kwargs)

        # Check for rate limiting
        if response.status_code == 429:
            delay = handle_rate_limit(response)
            if delay:
                logger.info(f"Rate limited. Waiting {delay}s before retry...")
                time.sleep(delay)
                # Retry after rate limit delay
                response = session.request(method, url, timeout=timeout, **kwargs)

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

    except requests.exceptions.Timeout:
        logger.error(f"Request timeout for {url}")
        return None

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error for {url}: {e}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {e}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error requesting {url}: {e}")
        return None


def handle_rate_limit(response: requests.Response) -> Optional[float]:
    """
    Handle rate limiting responses and return retry delay.

    Checks for Retry-After header and returns appropriate delay time.

    Args:
        response: HTTP response object

    Returns:
        Delay in seconds if rate limited, None otherwise

    Example:
        >>> delay = handle_rate_limit(response)
        >>> if delay:
        ...     time.sleep(delay)
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

        logger.warning(f"Rate limited. Retry after {delay} seconds")
        return delay

    return None


def get_json(
    session: requests.Session, url: str, timeout: int = 30, **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Make a GET request and parse JSON response.

    Args:
        session: Requests session to use
        url: URL to request
        timeout: Request timeout in seconds (default: 30)
        **kwargs: Additional arguments for request

    Returns:
        Parsed JSON dict or None if failed

    Example:
        >>> session = create_resilient_session()
        >>> data = get_json(session, 'https://api.example.com/data')
        >>> if data:
        ...     print(f"Received {len(data)} items")
    """
    response = _safe_request_with_session(session, url, method="GET", timeout=timeout, **kwargs)

    if not response:
        return None

    try:
        result: Dict[str, Any] = response.json()
        return result
    except ValueError as e:
        logger.error(f"Invalid JSON response from {url}: {e}")
        return None


def post_json(
    session: requests.Session, url: str, data: Dict[str, Any], timeout: int = 30, **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Make a POST request with JSON data and parse JSON response.

    Args:
        session: Requests session to use
        url: URL to request
        data: Dictionary to send as JSON
        timeout: Request timeout in seconds (default: 30)
        **kwargs: Additional arguments for request

    Returns:
        Parsed JSON dict or None if failed

    Example:
        >>> session = create_resilient_session()
        >>> payload = {'name': 'Daft Punk', 'genre': 'Electronic'}
        >>> response = post_json(session, 'https://api.example.com/artists', payload)
    """
    # Set content-type header for JSON
    if "headers" not in kwargs:
        kwargs["headers"] = {}
    kwargs["headers"]["Content-Type"] = "application/json"

    response = _safe_request_with_session(
        session, url, method="POST", json=data, timeout=timeout, **kwargs
    )

    if not response:
        return None

    try:
        result: Dict[str, Any] = response.json()
        return result
    except ValueError as e:
        logger.error(f"Invalid JSON response from {url}: {e}")
        return None


def check_url_accessible(url: str, timeout: int = 10) -> bool:
    """
    Check if a URL is accessible (returns 2xx status).

    Args:
        url: URL to check
        timeout: Request timeout in seconds (default: 10)

    Returns:
        True if URL is accessible, False otherwise

    Example:
        >>> if check_url_accessible('https://api.example.com'):
        ...     print("API is online")
    """
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return 200 <= response.status_code < 300
    except Exception:
        return False


def get_domain_from_url(url: str) -> Optional[str]:
    """
    Extract domain from URL.

    Args:
        url: URL to extract domain from

    Returns:
        Domain string or None if parsing fails

    Example:
        >>> get_domain_from_url('https://api.example.com/path/to/resource')
        'api.example.com'
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception as e:
        logger.warning(f"Could not parse domain from {url}: {e}")
        return None


# Token bucket rate limiter
class RateLimiter:
    """
    Token bucket rate limiter for API requests.

    Tracks request timestamps and allows a maximum number of calls within
    a rolling time window.

    Attributes:
        max_calls: Maximum number of calls allowed within time_window
        time_window: Time window in seconds
        calls: List of timestamps for recent calls

    Example:
        >>> limiter = RateLimiter(max_calls=10, time_window=60)
        >>> if limiter.acquire():
        ...     # Make API call
        ...     response = requests.get('https://api.example.com')
    """

    def __init__(self, max_calls: int, time_window: int):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: List[float] = []

    def acquire(self) -> bool:
        """
        Attempt to acquire a token for making a request.

        Cleans up old call timestamps and checks if we're within the rate limit.

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()

        # Clean up calls outside the time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]

        # Check if we can make another call
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True

        return False

    def wait_if_needed(self) -> None:
        """
        Wait if necessary to respect rate limit (blocking).

        This method blocks until a token is available.
        """
        while not self.acquire():
            time.sleep(0.1)  # Check every 100ms


def make_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict] = None,
    data: Optional[Dict] = None,
    timeout: int = 30,
) -> Optional[requests.Response]:
    """Make HTTP request with error handling (legacy compatibility)."""
    try:
        response = requests.request(
            method=method, url=url, headers=headers, json=data, timeout=timeout
        )
        response.raise_for_status()
        return response
    except Exception as e:
        logger.error(f"HTTP request failed: {e}")
        return None


# Convenience aliases and standalone functions for testing/simple use cases
def setup_session(
    max_retries: int = 3,
    headers: Optional[Dict[str, str]] = None,
    pool_connections: int = 10,
    pool_maxsize: int = 20,
    timeout: int = 30,
    backoff_factor: float = 1.0,
) -> requests.Session:
    """
    Setup HTTP session with retry logic (convenience wrapper).

    This is an alias/wrapper around create_resilient_session() for compatibility
    with test expectations and simpler API.

    Args:
        max_retries: Maximum number of retry attempts
        headers: Custom headers to add to session
        pool_connections: Number of connection pools
        pool_maxsize: Maximum size of connection pool
        timeout: Default timeout for requests
        backoff_factor: Backoff factor for retries

    Returns:
        Configured requests session

    Example:
        >>> session = setup_session(max_retries=5)
        >>> response = session.get('https://api.example.com')
    """
    session = create_resilient_session(
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        pool_connections=pool_connections,
        pool_maxsize=pool_maxsize,
        timeout=timeout,
    )

    # Add custom headers if provided
    if headers:
        session.headers.update(headers)

    return session


# Standalone safe_request function for testing/simple use cases
def safe_request(
    url: str,
    method: str = "GET",
    max_retries: int = 3,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None,
    json: Optional[Dict] = None,
    data: Optional[Dict] = None,
    backoff_factor: float = 1.0,
    **kwargs,
) -> Optional[requests.Response]:
    """
    Make a safe HTTP request with automatic retry logic (standalone version).

    This is the primary safe_request function that works without requiring
    a session object. It creates and manages its own session internally.

    Args:
        url: URL to request
        method: HTTP method (GET, POST, etc.)
        max_retries: Maximum number of retry attempts
        timeout: Request timeout in seconds
        headers: Custom headers dictionary
        json: JSON data for POST/PUT requests
        data: Form data for POST/PUT requests
        backoff_factor: Exponential backoff factor for retries
        **kwargs: Additional arguments passed to requests

    Returns:
        Response object or None if request failed

    Example:
        >>> response = safe_request('https://api.example.com/data')
        >>> if response and response.status_code == 200:
        ...     data = response.json()
        ...     print(f"Received {len(data)} items")
    """
    # Use the method directly with requests module (for test mocking compatibility)
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Prepare request kwargs
            request_kwargs: Dict[str, Any] = {"timeout": timeout}
            if headers:
                request_kwargs["headers"] = headers
            if json is not None:
                request_kwargs["json"] = json
            if data is not None:
                request_kwargs["data"] = data
            request_kwargs.update(kwargs)

            # Make the request using requests module directly
            if method.upper() == "GET":
                response = requests.get(url, **request_kwargs)
            elif method.upper() == "POST":
                response = requests.post(url, **request_kwargs)
            elif method.upper() == "PUT":
                response = requests.put(url, **request_kwargs)
            elif method.upper() == "DELETE":
                response = requests.delete(url, **request_kwargs)
            elif method.upper() == "PATCH":
                response = requests.patch(url, **request_kwargs)
            elif method.upper() == "HEAD":
                response = requests.head(url, **request_kwargs)
            else:
                response = requests.request(method, url, **request_kwargs)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        delay = 1.0
                else:
                    delay = 1.0

                logger.warning(f"Rate limited (429). Waiting {delay}s...")
                time.sleep(delay)
                retry_count += 1
                continue

            # Don't retry on client errors (4xx except 429)
            if 400 <= response.status_code < 500 and response.status_code != 429:
                return response

            # Retry on server errors (5xx)
            if response.status_code >= 500:
                retry_count += 1
                if retry_count < max_retries:
                    delay = backoff_factor * (2 ** (retry_count - 1))
                    logger.warning(
                        f"Server error {response.status_code}. "
                        f"Retrying in {delay}s... (attempt {retry_count}/{max_retries})"
                    )
                    time.sleep(delay)
                    continue
                else:
                    return response

            # Success
            return response

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            retry_count += 1

            if retry_count < max_retries:
                delay = backoff_factor * (2 ** (retry_count - 1))
                logger.warning(
                    f"{type(e).__name__}: {e}. "
                    f"Retrying in {delay}s... (attempt {retry_count}/{max_retries})"
                )
                time.sleep(delay)
            else:
                logger.error(f"Request failed after {max_retries} attempts: {e}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error during request: {e}")
            return None

    logger.error(f"Request failed after {max_retries} attempts")
    return None
