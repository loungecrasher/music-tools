"""
Runner for the EDM Music Blog Scraper.
Handles execution of the appropriate scraper based on configuration.
"""

import asyncio
from typing import Dict, List, Any
from datetime import datetime

from .config import ScraperSettings
from .music_scraper import MusicBlogScraper
from .preferred_genres_scraper import PreferredGenresScraper
from .async_scraper import AsyncMusicBlogScraper

class ScraperRunner:
    """Executes scraping sessions."""
    
    def __init__(self):
        self.results = []
        self.errors = []
    
    def run(self, settings: ScraperSettings) -> Dict[str, Any]:
        """
        Run the scraper with the given settings.
        
        Args:
            settings: ScraperSettings object
            
        Returns:
            Dictionary containing results and metadata
        """
        start_time = datetime.now()
        
        # Initialize the appropriate scraper
        if settings.scraper_type == "specialized":
            scraper = PreferredGenresScraper(
                base_url=settings.url,
                preferred_genres=settings.genres
            )
        else:
            scraper = MusicBlogScraper(base_url=settings.url)
            
        # Execute scraping
        try:
            self.results = scraper.scrape_website(
                max_pages=settings.max_pages,
                start_date=settings.start_date,
                end_date=settings.end_date
            )
        except Exception as e:
            self.errors.append(str(e))
            
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            'results': self.results,
            'count': len(self.results),
            'duration': duration,
            'errors': self.errors
        }

    async def run_async(self, settings: ScraperSettings) -> Dict[str, Any]:
        """
        Run the async scraper.
        
        Args:
            settings: ScraperSettings object
            
        Returns:
            Dictionary containing results and metadata
        """
        start_time = datetime.now()
        
        scraper = AsyncMusicBlogScraper(
            base_url=settings.url,
            preferred_genres=settings.genres if settings.scraper_type == "specialized" else None
        )
        
        try:
            self.results = await scraper.scrape_website(
                max_pages=settings.max_pages,
                start_date=settings.start_date,
                end_date=settings.end_date
            )
        except Exception as e:
            self.errors.append(str(e))
            
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            'results': self.results,
            'count': len(self.results),
            'duration': duration,
            'errors': self.errors
        }

    def save_results(self, settings: ScraperSettings, results: List[Dict]) -> str:
        """
        Save results to file(s).
        
        Returns:
            Summary string of saved files
        """
        saved_files = []
        
        # Save as text
        with open(settings.output_filename, 'w', encoding='utf-8') as f:
            f.write(f"Scrape Results for {settings.url}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Settings: {settings.scraper_type}, {len(results)} items found\n")
            f.write("=" * 50 + "\n\n")
            
            for item in results:
                f.write(f"Title: {item.get('title', 'N/A')}\n")
                f.write(f"URL: {item.get('url', 'N/A')}\n")
                f.write(f"Genres: {', '.join(item.get('genres', []))}\n")
                f.write(f"Matching Genres: {', '.join(item.get('matching_genres', []))}\n")
                f.write(f"Date: {item.get('post_date', 'N/A')}\n")
                
                download_links = item.get('download_links', [])
                if download_links:
                    f.write("Download Links:\n")
                    for link in download_links:
                        f.write(f"  - {link}\n")
                else:
                    f.write("Download Links: None found\n")
                    
                f.write("-" * 30 + "\n")
        
        saved_files.append(settings.output_filename)
        
        # Save as JSON if requested
        if settings.save_json:
            import json
            json_filename = settings.output_filename.rsplit('.', 1)[0] + '.json'
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4, default=str)
            saved_files.append(json_filename)
            
        # Append aggregated links to the text file
        total_links = sum(len(item.get('download_links', [])) for item in results)
        if total_links > 0:
            # Collect all unique links
            all_links = set()
            quality_stats = {'flac': 0, 'mp3_320': 0, 'other': 0}
            
            for item in results:
                for link in item.get('download_links', []):
                    # Handle different link formats
                    link_url = str(link).strip()
                    if link_url:
                        all_links.add(link_url)
                        
                        # Track quality stats
                        link_lower = link_url.lower()
                        if 'flac' in link_lower or '.flac' in link_lower:
                            quality_stats['flac'] += 1
                        elif '320' in link_lower:
                            quality_stats['mp3_320'] += 1
                        else:
                            quality_stats['other'] += 1
            
            # Sort links for consistent output
            unique_links = sorted(list(all_links))
            GROUP_SIZE = 20
            
            with open(settings.output_filename, 'a', encoding='utf-8') as f:
                f.write("\n\n" + "=" * 80 + "\n")
                f.write("ALL UNIQUE DOWNLOAD LINKS (EXTRACTED)\n")
                f.write("=" * 80 + "\n\n")
                
                # Write summary statistics
                f.write("EXTRACTION STATISTICS\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total posts processed: {len(results)}\n")
                f.write(f"Total unique links: {len(unique_links)}\n")
                f.write(f"\nQuality breakdown:\n")
                f.write(f"  FLAC/Lossless: {quality_stats['flac']}\n")
                f.write(f"  MP3 320kbps: {quality_stats['mp3_320']}\n")
                f.write(f"  Other: {quality_stats['other']}\n")
                f.write("\n" + "=" * 80 + "\n\n")
                
                # Write links in groups
                for i, link in enumerate(unique_links):
                    # Add group header at the start of each group
                    if i % GROUP_SIZE == 0:
                        group_num = (i // GROUP_SIZE) + 1
                        total_groups = (len(unique_links) + GROUP_SIZE - 1) // GROUP_SIZE
                        f.write(f"=== GROUP {group_num} of {total_groups} ===\n")
                    
                    f.write(f"{link}\n")
                    
                    # Add a blank line after every group (except the last)
                    if (i + 1) % GROUP_SIZE == 0 and (i + 1) < len(unique_links):
                        f.write("\n")
            
        return ", ".join(saved_files)
