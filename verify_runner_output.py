
import sys
import os
import logging
from datetime import date

# Add apps/music-tools/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'apps/music-tools/src')))

from scraping.runner import ScraperRunner
from scraping.config import ScraperSettings

def verify_runner_output():
    print("Testing runner output formatting...")
    
    # Create dummy settings
    settings = ScraperSettings(
        url="https://example.com",
        scraper_type="standard",
        genres=[],
        output_filename="test_runner_output.txt",
        save_json=False,
        max_pages=1
    )
    
    # Create dummy results
    results = [
        {
            'title': 'Test Post 1',
            'url': 'https://example.com/post1',
            'genres': ['house', 'techno'],
            'matching_genres': ['house'],
            'post_date': date(2025, 11, 25),
            'download_links': ['https://nfile.cc/link1', 'https://novafile.org/link2']
        },
        {
            'title': 'Test Post 2',
            'url': 'https://example.com/post2',
            'genres': ['trance'],
            'matching_genres': ['trance'],
            'post_date': date(2025, 11, 24),
            'download_links': ['https://nfile.cc/link3']
        }
    ]
    
    runner = ScraperRunner()
    runner.save_results(settings, results)
    
    # Check output file
    if not os.path.exists("test_runner_output.txt"):
        print("❌ Output file not created")
        return False
        
    with open("test_runner_output.txt", "r") as f:
        content = f.read()
        
    print("\nChecking file content...")
    
    # Check for per-post details
    if "Title: Test Post 1" in content and "URL: https://example.com/post1" in content:
        print("✅ Per-post details found")
    else:
        print("❌ Per-post details missing")
        return False
        
    # Check for aggregated links section
    if "ALL UNIQUE DOWNLOAD LINKS (EXTRACTED)" in content:
        print("✅ Aggregated links section found")
    else:
        print("❌ Aggregated links section missing")
        return False
        
    # Check for specific links in aggregation
    if "https://nfile.cc/link1" in content and "https://novafile.org/link2" in content:
        print("✅ Specific links found in file")
    else:
        print("❌ Specific links missing")
        return False
        
    print("\n✅ Verification Successful!")
    return True

if __name__ == "__main__":
    if verify_runner_output():
        sys.exit(0)
    else:
        sys.exit(1)
