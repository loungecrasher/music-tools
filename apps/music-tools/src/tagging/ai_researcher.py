"""
AI Researcher Module

Handles Claude AI integration for researching artist country of origin.
Provides optimized prompts, retry logic, response parsing, and comprehensive
error handling for robust music metadata enrichment.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Dict, Optional

# Import core services
from core.country_service import country_service
from core.error_handler import APIError, with_error_handling, with_retry
from core.validation_service import validate_artist_name, validate_confidence_score

try:
    import anthropic
    from anthropic import APIError as AnthropicAPIError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None
    AnthropicAPIError = Exception

try:
    from .cache import CacheManager
    CACHE_AVAILABLE = True
except ImportError:
    # Fallback for when running standalone
    try:
        from cache import CacheManager
        CACHE_AVAILABLE = True
    except ImportError:
        CACHE_AVAILABLE = False
        CacheManager = None

logger = logging.getLogger(__name__)


# Custom Exceptions
class ResearchError(Exception):
    """Base exception for research operations."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class APIError(ResearchError):  # noqa: F811
    """Exception for API-related errors."""

    def __init__(self, message: str, status_code: Optional[int] = None,
                 retry_after: Optional[int] = None):
        super().__init__(message, error_code="API_ERROR")
        self.status_code = status_code
        self.retry_after = retry_after


class ValidationError(ResearchError):
    """Exception for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, error_code="VALIDATION_ERROR")
        self.field = field


@dataclass
class CountryResearchResult:
    """Result of country research for an artist."""
    country: str
    confidence: float = 1.0
    source: str = "unknown"
    reasoning: str = ""
    cached: bool = False


# Country validation now handled by centralized CountryService
# VALID_COUNTRIES and COUNTRY_ALIASES moved to core.country_service


def validate_country_name(country: Optional[str]) -> bool:
    """
    Validate if a string is a recognized country name using centralized CountryService.

    Args:
        country: Country name to validate

    Returns:
        bool: True if country name is valid
    """
    if not country or not isinstance(country, str):
        return False

    country_lower = country.lower().strip()

    # Check against known invalid responses
    invalid_responses = {"unknown", "unclear", "not found", "n/a", "none", ""}
    if country_lower in invalid_responses:
        return False

    # Use centralized country service for validation
    return country_service.is_valid_country(country)


def parse_country_response(response: str) -> Optional[str]:
    """
    Parse country from AI response text.

    Handles various response formats and extracts the most likely country name.

    Args:
        response: Raw response text from AI

    Returns:
        str: Parsed country name or None if not found
    """
    if not response or not isinstance(response, str):
        return None

    response = response.strip()

    # Direct country name (simple case)
    if validate_country_name(response):
        normalized = country_service.normalize_country_name(response)
        return normalized.title() if normalized else response

    # Look for patterns like "Country: X" or "The country is X"
    patterns = [
        r"(?:country|nation)(?:\s*is|\s*:)\s*([^.,:;]+)",
        r"(?:from|in|of)\s+([^.,:;]+)",
        r"(?:originates?\s+from|comes\s+from)\s+([^.,:;]+)",
        r"(?:artist\s+is\s+from)\s+([^.,:;]+)",
        r"primary artist is from\s+([^.,:;]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, response.lower())
        if match:
            candidate = match.group(1).strip()
            if validate_country_name(candidate):
                normalized = country_service.normalize_country_name(candidate)
                return normalized.title() if normalized else candidate.title()

    # Use centralized service to extract country from text
    extracted_country = country_service.extract_country_from_text(response)
    if extracted_country:
        return extracted_country.title()

    return None


def build_research_prompt(artist: str, title: Optional[str] = None) -> str:
    """
    Build optimized prompt for country research.

    Args:
        artist: Artist name
        title: Optional song title

    Returns:
        str: Formatted prompt for AI research
    """
    base_prompt = f"""Research the country of origin for the musical artist: {artist}"""

    if title and title.strip():
        base_prompt += f"""
Song title: {title}"""

    base_prompt += """

Return ONLY the country name. If uncertain, return the most likely country.
If the artist is a collaboration between artists from different countries, return the country of the primary or most prominent artist.
If the artist is a band, return the country where the band was formed or is primarily based.

Examples of good responses:
- "United States"
- "United Kingdom"
- "Canada"
- "Germany"

Do not include explanations, just the country name."""

    return base_prompt


class AIResearcher:
    """
    Claude AI integration for artist country research.

    Provides robust country research with caching, retry logic,
    and comprehensive error handling.
    """

    def __init__(
        self,
        api_key: str,
        cache_manager: Optional[CacheManager] = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        timeout: int = 30
    ):
        """
        Initialize the AI researcher.

        Args:
            api_key: Anthropic API key
            cache_manager: Optional cache manager instance
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            timeout: Request timeout in seconds
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout

        # Initialize Anthropic client
        if ANTHROPIC_AVAILABLE:
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            # For testing purposes when anthropic is not available
            self.client = None
            logger.warning("Anthropic library not available - API calls will fail")

        # Initialize cache manager
        if cache_manager is not None:
            self.cache_manager = cache_manager
        elif CACHE_AVAILABLE:
            try:
                self.cache_manager = CacheManager()
            except Exception as e:
                logger.warning(f"Could not initialize cache manager: {e}")
                self.cache_manager = None
        else:
            self.cache_manager = None
            logger.warning("Cache manager not available - no caching will be performed")

        # Statistics
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'successful_researches': 0,
            'failed_researches': 0
        }

    async def research_artist_country(
        self,
        artist: str,
        title: Optional[str] = None
    ) -> CountryResearchResult:
        """
        Research the country of origin for an artist.

        Args:
            artist: Artist name
            title: Optional song title for context

        Returns:
            CountryResearchResult: Research result with country and metadata

        Raises:
            APIError: If API calls fail after retries
            ValidationError: If input validation fails
        """
        if not artist or not artist.strip():
            raise ValidationError("Artist name cannot be empty", field="artist")

        artist = artist.strip()
        self.stats['total_requests'] += 1

        # Check cache first
        if self.cache_manager:
            cached_country = self.cache_manager.get_country(artist)
            if cached_country:
                self.stats['cache_hits'] += 1
                logger.debug(f"Cache hit for artist: {artist} -> {cached_country}")
                return CountryResearchResult(
                    country=cached_country,
                    confidence=0.9,  # Cached results have high confidence
                    source="cache",
                    cached=True
                )

        # Perform API research
        try:
            country = await self._perform_api_research(artist, title)

            # Store in cache
            if self.cache_manager and country:
                self.cache_manager.store_country(artist, country, confidence=0.95)

            self.stats['successful_researches'] += 1

            return CountryResearchResult(
                country=country,
                confidence=0.95,
                source="Claude API",
                reasoning=f"API research for artist: {artist}",
                cached=False
            )

        except Exception as e:
            self.stats['failed_researches'] += 1
            logger.error(f"Failed to research artist {artist}: {e}")
            raise

    async def _perform_api_research(
        self,
        artist: str,
        title: Optional[str] = None
    ) -> str:
        """
        Perform the actual API research with retry logic.

        Args:
            artist: Artist name
            title: Optional song title

        Returns:
            str: Researched country name

        Raises:
            APIError: If API calls fail after retries
        """
        if not self.client:
            raise APIError("Anthropic client not available - library may not be installed")

        prompt = build_research_prompt(artist, title)

        for attempt in range(self.max_retries):
            try:
                self.stats['api_calls'] += 1

                logger.debug(f"API call attempt {attempt + 1} for artist: {artist}")

                response = await self.client.messages.create(
                    model="claude-3-haiku-20240307",  # Fast and cost-effective
                    max_tokens=50,  # Short responses expected
                    temperature=0.1,  # Low temperature for consistent results
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                # Extract text from response
                if response.content and len(response.content) > 0:
                    raw_response = response.content[0].text
                    country = parse_country_response(raw_response)

                    if country and validate_country_name(country):
                        logger.debug(f"Successfully researched: {artist} -> {country}")
                        return country
                    else:
                        logger.warning(f"Invalid country response for {artist}: {raw_response}")
                        if attempt == self.max_retries - 1:
                            raise ValidationError(f"Could not parse valid country from response: {raw_response}")
                else:
                    logger.warning(f"Empty response for artist: {artist}")
                    if attempt == self.max_retries - 1:
                        raise APIError("Empty response from API")

            except AnthropicAPIError as e:
                logger.warning(f"Anthropic API error (attempt {attempt + 1}): {e}")

                # Check for rate limiting
                if hasattr(e, 'status_code') and e.status_code == 429:
                    retry_after = getattr(e, 'retry_after', self.base_delay * (2 ** attempt))
                    if attempt < self.max_retries - 1:
                        logger.info(f"Rate limited, waiting {retry_after}s before retry")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        raise APIError(f"Rate limited after {self.max_retries} attempts",
                                       status_code=429, retry_after=retry_after)

                # For other API errors, wait with exponential backoff
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.info(f"API error, waiting {delay}s before retry")
                    await asyncio.sleep(delay)
                else:
                    raise APIError(f"API error after {self.max_retries} attempts: {e}")

            except Exception as e:
                logger.error(f"Unexpected error during API call: {e}")
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    raise APIError(f"Unexpected error after {self.max_retries} attempts: {e}")

        raise APIError(f"Failed to research country after {self.max_retries} attempts")

    def research_artist_country_sync(
        self,
        artist: str,
        title: Optional[str] = None
    ) -> CountryResearchResult:
        """
        Synchronous wrapper for async research method.

        Args:
            artist: Artist name
            title: Optional song title

        Returns:
            CountryResearchResult: Research result
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.research_artist_country(artist, title))

    def get_stats(self) -> Dict[str, int]:
        """
        Get research statistics.

        Returns:
            dict: Dictionary of statistics
        """
        return self.stats.copy()

    def clear_stats(self) -> None:
        """Clear research statistics."""
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'api_calls': 0,
            'successful_researches': 0,
            'failed_researches': 0
        }


# Convenience functions
def create_researcher(
    api_key: str,
    use_cache: bool = True,
    cache_path: Optional[str] = None
) -> AIResearcher:
    """
    Create an AI researcher with default settings.

    Args:
        api_key: Anthropic API key
        use_cache: Whether to enable caching
        cache_path: Optional custom cache path

    Returns:
        AIResearcher: Configured researcher instance
    """
    cache_manager = None
    if use_cache and CACHE_AVAILABLE:
        cache_manager = CacheManager(database_path=cache_path)

    return AIResearcher(
        api_key=api_key,
        cache_manager=cache_manager,
        max_retries=3,
        base_delay=1.0,
        timeout=30
    )


async def research_country(
    artist: str,
    title: Optional[str] = None,
    api_key: Optional[str] = None
) -> Optional[str]:
    """
    Simple async function to research artist country.

    Args:
        artist: Artist name
        title: Optional song title
        api_key: API key (required if not set in environment)

    Returns:
        str: Country name or None if research fails
    """
    if not api_key:
        import os
        api_key = os.getenv('ANTHROPIC_API_KEY')

    if not api_key:
        raise ValueError("API key must be provided or set in ANTHROPIC_API_KEY environment variable")

    try:
        researcher = create_researcher(api_key)
        result = await researcher.research_artist_country(artist, title)
        return result.country
    except Exception as e:
        logger.error(f"Failed to research country for {artist}: {e}")
        return None


# Example usage and testing
if __name__ == "__main__":
    import os
    import sys

    from dotenv import load_dotenv

    load_dotenv()

    async def main():
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("Please set ANTHROPIC_API_KEY environment variable")
            return

        if len(sys.argv) < 2:
            print("Usage: python ai_researcher.py <artist> [title]")
            return

        artist = sys.argv[1]
        title = sys.argv[2] if len(sys.argv) > 2 else None

        print(f"Researching country for: {artist}")
        if title:
            print(f"Song: {title}")

        researcher = create_researcher(api_key)

        try:
            result = await researcher.research_artist_country(artist, title)
            print("\nResult:")
            print(f"  Country: {result.country}")
            print(f"  Confidence: {result.confidence}")
            print(f"  Source: {result.source}")
            print(f"  Cached: {result.cached}")

            # Show stats
            stats = researcher.get_stats()
            print("\nStatistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        except Exception as e:
            print(f"Error: {e}")

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
