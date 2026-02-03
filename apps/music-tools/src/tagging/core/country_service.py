"""
Centralized country validation and normalization service.

This module provides a single source of truth for country data and validation,
eliminating code duplication across the application.
"""

import logging
import re
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


class CountryService:
    """Service for country validation, normalization, and lookup operations."""

    # Comprehensive list of valid countries (combined and deduplicated from previous files)
    VALID_COUNTRIES: Set[str] = {
        "afghanistan", "albania", "algeria", "andorra", "angola", "argentina",
        "armenia", "australia", "austria", "azerbaijan", "bahamas", "bahrain",
        "bangladesh", "barbados", "belarus", "belgium", "belize", "benin",
        "bhutan", "bolivia", "bosnia and herzegovina", "botswana", "brazil",
        "brunei", "bulgaria", "burkina faso", "burundi", "cambodia", "cameroon",
        "canada", "cape verde", "central african republic", "chad", "chile",
        "china", "colombia", "comoros", "congo", "costa rica", "croatia",
        "cuba", "cyprus", "czech republic", "denmark", "djibouti", "dominica",
        "dominican republic", "east timor", "ecuador", "egypt", "el salvador",
        "equatorial guinea", "eritrea", "estonia", "ethiopia", "fiji", "finland",
        "france", "gabon", "gambia", "georgia", "germany", "ghana", "greece",
        "grenada", "guatemala", "guinea", "guinea-bissau", "guyana", "haiti",
        "honduras", "hungary", "iceland", "india", "indonesia", "iran", "iraq",
        "ireland", "israel", "italy", "jamaica", "japan", "jordan", "kazakhstan",
        "kenya", "kiribati", "north korea", "south korea", "kuwait", "kyrgyzstan",
        "laos", "latvia", "lebanon", "lesotho", "liberia", "libya", "liechtenstein",
        "lithuania", "luxembourg", "madagascar", "malawi", "malaysia", "maldives",
        "mali", "malta", "marshall islands", "mauritania", "mauritius", "mexico",
        "micronesia", "moldova", "monaco", "mongolia", "montenegro", "morocco",
        "mozambique", "myanmar", "namibia", "nauru", "nepal", "netherlands",
        "new zealand", "nicaragua", "niger", "nigeria", "norway", "oman",
        "pakistan", "palau", "panama", "papua new guinea", "paraguay", "peru",
        "philippines", "poland", "portugal", "puerto rico", "qatar", "romania",
        "russia", "rwanda", "saint kitts and nevis", "saint lucia",
        "saint vincent and the grenadines", "samoa", "san marino",
        "sao tome and principe", "saudi arabia", "senegal", "serbia",
        "seychelles", "sierra leone", "singapore", "slovakia", "slovenia",
        "solomon islands", "somalia", "south africa", "south sudan", "spain",
        "sri lanka", "sudan", "suriname", "swaziland", "sweden", "switzerland",
        "syria", "taiwan", "tajikistan", "tanzania", "thailand", "togo", "tonga",
        "trinidad and tobago", "tunisia", "turkey", "turkmenistan", "tuvalu",
        "uganda", "ukraine", "united arab emirates", "united kingdom",
        "united states", "uruguay", "uzbekistan", "vanuatu", "vatican city",
        "venezuela", "vietnam", "yemen", "zambia", "zimbabwe"
    }

    # Country aliases for better matching (combined from previous files)
    COUNTRY_ALIASES: Dict[str, str] = {
        "usa": "united states",
        "us": "united states",
        "america": "united states",
        "uk": "united kingdom",
        "britain": "united kingdom",
        "england": "united kingdom",
        "scotland": "united kingdom",
        "wales": "united kingdom",
        "northern ireland": "united kingdom",
        "uae": "united arab emirates",
        "czech": "czech republic",
        "drc": "congo",
        "democratic republic of congo": "congo",
        "congo republic": "congo",
    }

    def __init__(self):
        """Initialize the country service."""
        self._compiled_patterns = self._compile_country_patterns()

    def _compile_country_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for efficient country matching."""
        patterns = {}

        # Create patterns for all countries and aliases
        all_countries = set(self.VALID_COUNTRIES) | set(self.COUNTRY_ALIASES.keys())

        for country in all_countries:
            # Create pattern that matches the country name with word boundaries
            escaped_country = re.escape(country)
            pattern = re.compile(rf'\b{escaped_country}\b', re.IGNORECASE)
            patterns[country] = pattern

        return patterns

    def is_valid_country(self, country: str) -> bool:
        """
        Check if a country name is valid.

        Args:
            country: Country name to validate

        Returns:
            True if country is valid, False otherwise
        """
        if not country:
            return False

        normalized = self.normalize_country_name(country)
        return normalized in self.VALID_COUNTRIES

    def normalize_country_name(self, country: str) -> Optional[str]:
        """
        Normalize a country name to its canonical form.

        Args:
            country: Country name to normalize

        Returns:
            Normalized country name or None if invalid
        """
        if not country:
            return None

        # Clean and lowercase the input
        cleaned = country.strip().lower()

        # Check if it's a direct alias
        if cleaned in self.COUNTRY_ALIASES:
            return self.COUNTRY_ALIASES[cleaned]

        # Check if it's already a valid country
        if cleaned in self.VALID_COUNTRIES:
            return cleaned

        # Try partial matching for more flexible input
        for valid_country in self.VALID_COUNTRIES:
            if cleaned in valid_country or valid_country in cleaned:
                return valid_country

        return None

    def extract_country_from_text(self, text: str) -> Optional[str]:
        """
        Extract a country name from a text string using pattern matching.

        Args:
            text: Text to search for country names

        Returns:
            First valid country found or None
        """
        if not text:
            return None

        # First try exact matches with compiled patterns
        for country, pattern in self._compiled_patterns.items():
            if pattern.search(text):
                return self.normalize_country_name(country)

        # Fallback to word-by-word search
        words = text.lower().split()
        for word in words:
            normalized = self.normalize_country_name(word)
            if normalized:
                return normalized

        return None

    def get_country_variations(self, country: str) -> Set[str]:
        """
        Get all known variations/aliases for a country.

        Args:
            country: Country name

        Returns:
            Set of all variations including the canonical name
        """
        normalized = self.normalize_country_name(country)
        if not normalized:
            return set()

        variations = {normalized}

        # Add aliases that point to this country
        for alias, canonical in self.COUNTRY_ALIASES.items():
            if canonical == normalized:
                variations.add(alias)

        return variations

    def validate_and_normalize(self, country: str) -> tuple[bool, Optional[str]]:
        """
        Validate and normalize a country name in one operation.

        Args:
            country: Country name to validate and normalize

        Returns:
            Tuple of (is_valid, normalized_name)
        """
        normalized = self.normalize_country_name(country)
        is_valid = normalized is not None
        return is_valid, normalized

    def get_all_countries(self) -> Set[str]:
        """Get all valid country names."""
        return self.VALID_COUNTRIES.copy()

    def get_all_aliases(self) -> Dict[str, str]:
        """Get all country aliases."""
        return self.COUNTRY_ALIASES.copy()


# Global instance for easy access throughout the application
country_service = CountryService()
