"""
Anthropic API Researcher Module

Direct API integration for artist country research using Anthropic's API.
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import Anthropic SDK
try:
    from anthropic import Anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK not installed. Install with: pip install anthropic")

# Import core services
from core.country_service import country_service
from core.error_handler import APIError, with_error_handling


@dataclass
class ResearchResult:
    """Research result for an artist."""

    artist_name: str
    country: str
    confidence: float = 1.0
    genre: Optional[str] = None
    year: Optional[str] = None


class APIResearcher:
    """
    Researcher that uses Anthropic API directly.
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_retries: int = 3,
        timeout: int = 30,
        cache_manager=None,
    ):
        """
        Initialize API researcher.

        Args:
            api_key: Anthropic API key
            model: Model to use
            max_retries: Maximum number of retry attempts
            timeout: Timeout in seconds for API calls
            cache_manager: Optional cache manager for storing results
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic SDK is required. Install with: pip install anthropic")

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key is required. Set ANTHROPIC_API_KEY environment variable or pass api_key parameter"
            )

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.cache_manager = cache_manager

        self.statistics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
        }

    def research_artists_batch(
        self, artists_titles: List[Tuple[str, str]]
    ) -> Dict[str, Dict[str, str]]:
        """
        Research multiple artists in a single API call for efficiency.

        Args:
            artists_titles: List of (artist, title) tuples

        Returns:
            Dictionary mapping artist names to {'genre': genre_info, 'grouping': grouping_info, 'year': year_info}
        """
        if not artists_titles:
            return {}

        logger.info(f"Starting batch research for {len(artists_titles)} artists via API")

        # Build batch prompt
        songs_list = []
        for i, (artist, title) in enumerate(artists_titles, 1):
            if title and title.strip():
                songs_list.append(f"{i}. {title} - {artist}")
            else:
                songs_list.append(f"{i}. Unknown - {artist}")

        prompt = f"""Research each of these songs/artists and provide genre, location, and original release date information:

Songs to analyze:
{chr(10).join(songs_list)}

For each song/artist, research and provide accurate information. ONLY provide details you are CONFIDENT about:

1. GENRE: [Main Genre] | [Sub-Genre] | [Style] | [Movement/Era] (max 4 terms)
   GROUPING: [Region] | [Country] | [Language Family]
   YEAR: [Original Release Year]

2. GENRE: [Main Genre] | [Sub-Genre] | [Style] | [Movement/Era] (max 4 terms)
   GROUPING: [Region] | [Country] | [Language Family]
   YEAR: [Original Release Year]
...

MAIN GENRE CATEGORIES (MUST use these as first term):
Rock, Pop, Electronic, Latin, World, Jazz, Hip-Hop, Classical, Folk, R&B, Country, Blues, Reggae, Punk, Metal

CRITICAL: REGIONS/COUNTRIES ARE NOT GENRES!
- Geographic terms (Caribbean, Mexican, Greek, etc.) are NEVER main genres
- Always start with one of the 15 main musical genres
- Use geographic terms as Style/Regional (3rd position) only

PROFESSIONAL MUSIC TAXONOMY:
Based on MusicBrainz/Discogs/AllMusic standards with cultural hierarchy priority.

CULTURAL HIERARCHY RULE:
When music has cultural/linguistic identity, prioritize cultural classification:
- Spanish/Portuguese language → Latin | [Musical Style] | [Regional] | [Era]
- African traditional → World | African | [Style] | [Era]
- Celtic/Irish → World | Celtic | [Style] | [Era]
- Caribbean reggae/ska → Reggae | [Style] | [Regional] | [Era]
- Asian traditional → World | [Regional] | [Style] | [Era]

EXAMPLES:
- Spanish Pop → Latin | Pop | Spanish | Contemporary
- Mexican Rock → Latin | Rock | Mexican | Rock en Español
- Celtic Folk → World | Celtic | Folk | Traditional
- Caribbean Salsa → Latin | Salsa | Caribbean | Traditional

Better to say "Unknown" than to provide incorrect information."""

        try:
            self.statistics["total_requests"] += 1
            logger.info(f"Sending API request for {len(artists_titles)} artists")

            # Make API call
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            response = message.content[0].text if message.content else ""
            logger.info(f"API response received: {len(response)} chars")

            # Parse batch response
            results = {}
            lines = response.strip().split("\n")

            current_artist_idx = -1
            current_artist_data = {}

            for line in lines:
                line = line.strip()

                # Check for numbered entries
                numbered_match = re.match(r"^(\d+)\.\s*(?:\*\*)?GENRE(?:\*\*)?\s*:\s*(.+)", line)
                if numbered_match:
                    # Save previous artist if exists
                    if (
                        current_artist_idx >= 0
                        and current_artist_idx < len(artists_titles)
                        and current_artist_data
                    ):
                        artist_name = artists_titles[current_artist_idx][0]
                        results[artist_name] = current_artist_data

                        # Cache results
                        if self.cache_manager and "grouping" in current_artist_data:
                            self.cache_manager.store_country(
                                artist_name, current_artist_data["grouping"]
                            )

                    # Start new artist
                    current_artist_idx = int(numbered_match.group(1)) - 1
                    genre_content = numbered_match.group(2)
                    genre_content = re.sub(r"^\*\*|\*\*$", "", genre_content).strip()

                    # ENFORCE pipe format for genre
                    if "|" not in genre_content:
                        logger.warning(f"No pipes in genre, adding structure: {genre_content}")
                        current_artist_data = {
                            "genre": f"{genre_content} | Unknown | Unknown | Unknown"
                        }
                    else:
                        parts = [part.strip() for part in genre_content.split("|")]
                        if len(parts) == 1:
                            current_artist_data = {
                                "genre": f"{parts[0]} | Unknown | Unknown | Unknown"
                            }
                        elif len(parts) == 2:
                            current_artist_data = {
                                "genre": f"{parts[0]} | {parts[1]} | Unknown | Unknown"
                            }
                        elif len(parts) == 3:
                            current_artist_data = {
                                "genre": f"{parts[0]} | {parts[1]} | {parts[2]} | Unknown"
                            }
                        else:
                            current_artist_data = {"genre": genre_content}

                elif line.startswith("GENRE:") or "**GENRE**:" in line:
                    genre_content = re.sub(r".*(?:\*\*)?GENRE(?:\*\*)?\s*:\s*", "", line).strip()
                    genre_content = re.sub(r"^\*\*|\*\*$", "", genre_content).strip()

                    # ENFORCE pipe format for genre
                    if "|" not in genre_content:
                        logger.warning(f"No pipes in genre, adding structure: {genre_content}")
                        current_artist_data["genre"] = (
                            f"{genre_content} | Unknown | Unknown | Unknown"
                        )
                    else:
                        parts = [part.strip() for part in genre_content.split("|")]
                        if len(parts) == 1:
                            current_artist_data["genre"] = (
                                f"{parts[0]} | Unknown | Unknown | Unknown"
                            )
                        elif len(parts) == 2:
                            current_artist_data["genre"] = (
                                f"{parts[0]} | {parts[1]} | Unknown | Unknown"
                            )
                        elif len(parts) == 3:
                            current_artist_data["genre"] = (
                                f"{parts[0]} | {parts[1]} | {parts[2]} | Unknown"
                            )
                        else:
                            current_artist_data["genre"] = genre_content

                elif line.startswith("GROUPING:") or "**GROUPING**:" in line:
                    grouping_line = re.sub(r".*(?:\*\*)?GROUPING(?:\*\*)?\s*:\s*", "", line).strip()
                    grouping_line = re.sub(r"^\*\*|\*\*$", "", grouping_line).strip()

                    # Parse and ENFORCE pipe format: Region | Country | Language
                    if "|" in grouping_line:
                        parts = [part.strip() for part in grouping_line.split("|")]
                        if len(parts) >= 3:
                            region, country, language = parts[0], parts[1], parts[2]
                            normalized_country = country_service.normalize_country_name(country)
                            if normalized_country:
                                # ENFORCE pipes in output
                                current_artist_data["grouping"] = (
                                    f"{region} | {normalized_country.title()} | {language}"
                                )
                            else:
                                # Still enforce pipes even if country validation fails
                                current_artist_data["grouping"] = (
                                    f"{region} | {country} | {language}"
                                )
                        else:
                            # Incomplete format - add pipes to enforce structure
                            logger.warning(
                                f"Incomplete grouping format, attempting to fix: {grouping_line}"
                            )
                            if len(parts) == 2:
                                current_artist_data["grouping"] = (
                                    f"{parts[0]} | {parts[1]} | Unknown"
                                )
                            elif len(parts) == 1:
                                current_artist_data["grouping"] = f"Unknown | {parts[0]} | Unknown"
                            else:
                                current_artist_data["grouping"] = (
                                    f"Unknown | {grouping_line} | Unknown"
                                )
                    else:
                        # No pipes found - assume it's just a country name and add structure
                        logger.warning(
                            f"No pipes in grouping, treating as country name: {grouping_line}"
                        )
                        normalized_country = country_service.normalize_country_name(grouping_line)
                        if normalized_country:
                            current_artist_data["grouping"] = (
                                f"Unknown | {normalized_country.title()} | Unknown"
                            )
                        else:
                            current_artist_data["grouping"] = f"Unknown | {grouping_line} | Unknown"

                elif line.startswith("YEAR:") or "**YEAR**:" in line:
                    year_line = re.sub(r".*(?:\*\*)?YEAR(?:\*\*)?\s*:\s*", "", line).strip()
                    year_line = re.sub(r"^\*\*|\*\*$", "", year_line).strip()
                    current_artist_data["year"] = year_line

            # Save last artist
            if (
                current_artist_idx >= 0
                and current_artist_idx < len(artists_titles)
                and current_artist_data
            ):
                artist_name = artists_titles[current_artist_idx][0]
                results[artist_name] = current_artist_data

                if self.cache_manager and "grouping" in current_artist_data:
                    self.cache_manager.store_country(artist_name, current_artist_data["grouping"])

            self.statistics["successful_requests"] += 1
            logger.info(f"Successfully processed {len(results)} artists")

            return results

        except Exception as e:
            self.statistics["failed_requests"] += 1
            logger.error(f"API request failed: {e}")
            raise APIError(f"Failed to research artists: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get researcher statistics."""
        return self.statistics.copy()
