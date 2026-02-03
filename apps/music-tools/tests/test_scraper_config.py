"""
Tests for ScraperConfig and ScraperSettings.
"""

import pytest
from datetime import date, timedelta
from src.scraping.config import ScraperConfig, ScraperSettings

class TestScraperConfig:
    """Test ScraperConfig functionality."""
    
    def test_validate_url(self):
        """Test URL validation."""
        assert ScraperConfig.validate_url("https://example.com") is True
        assert ScraperConfig.validate_url("http://example.com") is True
        assert ScraperConfig.validate_url("ftp://example.com") is False
        assert ScraperConfig.validate_url("example.com") is False
        assert ScraperConfig.validate_url("") is False
        
    def test_validate_date_range(self):
        """Test date range validation."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Valid range
        valid, msg = ScraperConfig.validate_date_range(today, tomorrow)
        assert valid is True
        assert msg == ""
        
        # Invalid range
        valid, msg = ScraperConfig.validate_date_range(tomorrow, today)
        assert valid is False
        assert "cannot be after" in msg
        
        # None values are valid (open range)
        valid, msg = ScraperConfig.validate_date_range(None, today)
        assert valid is True
        
    def test_calculate_recommended_pages(self):
        """Test page recommendation logic."""
        today = date.today()
        
        # 1 week -> ~3 pages
        start = today - timedelta(days=7)
        assert ScraperConfig.calculate_recommended_pages(start, today) == 3
        
        # 1 month -> ~10 pages
        start = today - timedelta(days=30)
        assert ScraperConfig.calculate_recommended_pages(start, today) == 10
        
        # No start date -> default
        assert ScraperConfig.calculate_recommended_pages(None, None) == 10

class TestScraperSettings:
    """Test ScraperSettings dataclass."""
    
    def test_is_valid(self):
        """Test validity check."""
        settings = ScraperSettings()
        assert settings.is_valid is False
        
        settings.url = "https://example.com"
        assert settings.is_valid is False  # Needs filename
        
        settings.output_filename = "out.txt"
        assert settings.is_valid is True
