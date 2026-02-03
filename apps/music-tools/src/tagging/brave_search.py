"""
Brave Search API Integration Module

Provides web search functionality for artist and song research using Brave Search API.
Includes rate limiting, delays, and retry logic to handle API limits.
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# Rate limiting constants - Brave Free Tier: 1 query/second, 2000 queries/month
# We use 1.1s delay to be safely under the 1 QPS limit
DEFAULT_DELAY_BETWEEN_REQUESTS = 1.1  # seconds between requests (safe margin for 1 QPS limit)
DEFAULT_MAX_RETRIES = 5  # max retries on rate limit (increased for reliability)
DEFAULT_INITIAL_BACKOFF = 2.0  # initial backoff delay in seconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0  # exponential backoff multiplier


@dataclass
class SearchResult:
    """Represents a single search result from Brave."""
    title: str
    url: str
    description: str

    def __str__(self) -> str:
        return f"{self.title}\n{self.description}\n{self.url}"


class BraveSearchClient:
    """Client for Brave Search API with rate limiting and retry logic."""

    def __init__(
        self,
        api_key: str,
        delay_between_requests: float = DEFAULT_DELAY_BETWEEN_REQUESTS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
        backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER
    ):
        """
        Initialize Brave Search client with rate limiting.

        Args:
            api_key: Brave Search API key
            delay_between_requests: Minimum delay between requests (seconds)
            max_retries: Maximum number of retries on rate limit (429) errors
            initial_backoff: Initial backoff delay for retries (seconds)
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }

        # Rate limiting configuration
        self.delay_between_requests = delay_between_requests
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.backoff_multiplier = backoff_multiplier

        # Track last request time for rate limiting
        self._last_request_time: Optional[float] = None

        # Track failed queries for potential retry
        self.failed_queries: List[str] = []

        # Persistent storage for failed queries (retry later)
        self.failed_queries_file = Path(os.path.expanduser("~/.music-tools/brave_failed_queries.json"))
        self.failed_queries_file.parent.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'rate_limited_requests': 0,
            'failed_after_retries': 0
        }

        # Load any previously failed queries from disk
        self._load_failed_queries()

    def _wait_for_rate_limit(self) -> None:
        """Wait if needed to respect rate limiting."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.delay_between_requests:
                wait_time = self.delay_between_requests - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s before next request")
                time.sleep(wait_time)

    def _make_request(self, params: dict, retry_count: int = 0) -> Optional[dict]:
        """
        Make API request with retry logic for rate limits.

        Args:
            params: Request parameters
            retry_count: Current retry attempt number

        Returns:
            Response JSON data or None on failure
        """
        try:
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params=params,
                timeout=15
            )

            # Handle rate limiting (429)
            if response.status_code == 429:
                self.stats['rate_limited_requests'] += 1
                if retry_count < self.max_retries:
                    # Calculate backoff delay - exponential: 2s, 4s, 8s, 16s, 32s
                    backoff_delay = self.initial_backoff * (self.backoff_multiplier ** retry_count)
                    logger.warning(
                        f"Brave API rate limit hit (429). "
                        f"Retry {retry_count + 1}/{self.max_retries} after {backoff_delay:.1f}s"
                    )
                    time.sleep(backoff_delay)
                    return self._make_request(params, retry_count + 1)
                else:
                    self.stats['failed_after_retries'] += 1
                    # Track the failed query and persist for later retry
                    query = params.get('q', 'unknown')
                    self.add_failed_query(query)  # Persists to disk
                    logger.error(
                        f"Brave API rate limit exceeded after {self.max_retries} retries. "
                        f"Query saved to {self.failed_queries_file} for later retry"
                    )
                    return None

            response.raise_for_status()
            return response.json()

        except requests.Timeout:
            logger.error("Brave search request timed out")
            return None
        except requests.RequestException as e:
            logger.error(f"Brave search API error: {e}")
            return None

    def search(self, query: str, count: int = 5) -> List[SearchResult]:
        """
        Perform a web search using Brave Search API with rate limiting.

        Args:
            query: Search query string
            count: Number of results to return (default: 5, max: 20)

        Returns:
            List of SearchResult objects
        """
        # Wait for rate limit if needed
        self._wait_for_rate_limit()

        params = {
            "q": query,
            "count": min(count, 20)  # Brave API max is 20
        }

        logger.debug(f"Brave search query: {query}")

        # Update stats and last request time
        self.stats['total_requests'] += 1
        self._last_request_time = time.time()

        # Make request with retry logic
        data = self._make_request(params)

        if data is not None:
            self.stats['successful_requests'] += 1

        if data is None:
            return []

        results = []
        if "web" in data and "results" in data["web"]:
            for item in data["web"]["results"]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    description=item.get("description", "")
                ))

        logger.info(f"Brave search returned {len(results)} results for: {query}")
        return results

    def search_batch_staggered(
        self,
        queries: List[str],
        count: int = 5,
        extra_delay: float = 0.5
    ) -> Dict[str, List[SearchResult]]:
        """
        Perform multiple searches with staggered delays to avoid rate limits.

        Args:
            queries: List of search queries
            count: Number of results per query
            extra_delay: Additional delay between batch queries (on top of base delay)

        Returns:
            Dictionary mapping queries to their results
        """
        results = {}
        total = len(queries)

        for i, query in enumerate(queries):
            logger.info(f"Brave batch search {i+1}/{total}: {query[:50]}...")

            # Add extra stagger delay for batches
            if i > 0:
                time.sleep(extra_delay)

            results[query] = self.search(query, count)

        return results

    def search_artist(self, artist: str, song_title: Optional[str] = None) -> List[SearchResult]:
        """
        Search for artist information.

        Args:
            artist: Artist name
            song_title: Optional song title for more specific results

        Returns:
            List of search results
        """
        if song_title:
            query = f'"{song_title}" "{artist}" artist country origin'
        else:
            query = f'"{artist}" artist country origin'

        return self.search(query, count=5)

    def search_artist_genre(self, artist: str) -> List[SearchResult]:
        """
        Search for artist genre information.

        Args:
            artist: Artist name

        Returns:
            List of search results
        """
        query = f'"{artist}" music genre style'
        return self.search(query, count=5)

    def search_song_year(self, artist: str, song_title: str) -> List[SearchResult]:
        """
        Search for song release year.

        Args:
            artist: Artist name
            song_title: Song title

        Returns:
            List of search results
        """
        query = f'"{song_title}" "{artist}" release year'
        return self.search(query, count=3)

    def get_stats(self) -> dict:
        """Get search statistics."""
        return self.stats.copy()

    def get_failed_queries(self) -> List[str]:
        """Get list of queries that failed after all retries."""
        return self.failed_queries.copy()

    def clear_failed_queries(self) -> None:
        """Clear the failed queries list (memory and disk)."""
        self.failed_queries = []
        self._save_failed_queries()  # Clear the file too

    def _load_failed_queries(self) -> None:
        """Load failed queries from persistent storage."""
        try:
            if self.failed_queries_file.exists():
                with open(self.failed_queries_file, 'r') as f:
                    data = json.load(f)
                    self.failed_queries = data.get('queries', [])
                    if self.failed_queries:
                        logger.info(f"Loaded {len(self.failed_queries)} failed queries from previous session")
        except Exception as e:
            logger.warning(f"Could not load failed queries: {e}")
            self.failed_queries = []

    def _save_failed_queries(self) -> None:
        """Save failed queries to persistent storage for later retry."""
        try:
            data = {
                'queries': self.failed_queries,
                'last_updated': datetime.now().isoformat(),
                'count': len(self.failed_queries)
            }
            with open(self.failed_queries_file, 'w') as f:
                json.dump(data, f, indent=2)
            if self.failed_queries:
                logger.info(f"Saved {len(self.failed_queries)} failed queries to {self.failed_queries_file}")
        except Exception as e:
            logger.error(f"Could not save failed queries: {e}")

    def add_failed_query(self, query: str) -> None:
        """Add a failed query and persist to disk."""
        if query not in self.failed_queries:
            self.failed_queries.append(query)
            self._save_failed_queries()

    def retry_failed_queries(self, count: int = 5, max_to_retry: int = 10) -> Dict[str, List[SearchResult]]:
        """
        Retry previously failed queries with extra delays (rotation-based).

        Retries a batch of failed queries from the persistent queue.
        Successful queries are removed, failures stay for next rotation.

        Args:
            count: Number of results per query
            max_to_retry: Maximum queries to retry in this rotation (prevents overwhelming API)

        Returns:
            Dictionary mapping queries to their results
        """
        if not self.failed_queries:
            return {}

        # Take only a subset for this rotation (FIFO queue)
        queries_to_retry = self.failed_queries[:max_to_retry]
        remaining_queries = self.failed_queries[max_to_retry:]

        logger.info(f"Retry rotation: Attempting {len(queries_to_retry)} of {len(self.failed_queries)} failed queries...")

        # Use longer delays for retry (2s to be very safe)
        original_delay = self.delay_between_requests
        self.delay_between_requests = 2.0

        results = {}
        still_failed = []

        for i, query in enumerate(queries_to_retry, 1):
            logger.info(f"Retry {i}/{len(queries_to_retry)}: {query[:50]}...")
            result = self.search(query, count)
            if result:
                results[query] = result
                logger.info(f"✓ Retry succeeded for: {query[:50]}...")
            else:
                still_failed.append(query)
                logger.warning(f"✗ Retry failed again: {query[:50]}...")

        # Restore original delay
        self.delay_between_requests = original_delay

        # Update failed queue: remaining + still failed (rotation - failed go to back)
        self.failed_queries = remaining_queries + still_failed
        self._save_failed_queries()  # Persist updated queue

        logger.info(f"Retry rotation complete: {len(results)} succeeded, {len(still_failed)} still failed")
        logger.info(f"Failed queries remaining in queue: {len(self.failed_queries)}")

        return results

    def get_failed_queries_info(self) -> Dict:
        """Get information about failed queries queue."""
        return {
            'count': len(self.failed_queries),
            'file': str(self.failed_queries_file),
            'queries': self.failed_queries[:5],  # Preview first 5
            'has_more': len(self.failed_queries) > 5
        }

    def format_results_for_prompt(self, results: List[SearchResult]) -> str:
        """
        Format search results for inclusion in Claude prompt.

        Args:
            results: List of search results

        Returns:
            Formatted string for prompt
        """
        if not results:
            return "No search results found."

        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(f"{i}. {result.title}")
            formatted.append(f"   {result.description}")
            formatted.append(f"   Source: {result.url}")
            formatted.append("")

        return "\n".join(formatted)


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python brave_search.py <API_KEY> <QUERY>")
        sys.exit(1)

    api_key = sys.argv[1]
    query = " ".join(sys.argv[2:])

    client = BraveSearchClient(api_key)
    results = client.search(query)

    print(f"\nSearch results for: {query}\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.title}")
        print(f"   {result.description}")
        print(f"   {result.url}\n")
