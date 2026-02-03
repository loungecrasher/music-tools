
import sys
import os
import logging

# Add apps/music-tools/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'apps/music-tools/src')))

from scraping.music_scraper import MusicBlogScraper
from scraping.config import ScraperConfig

# Configure logging
logging.basicConfig(level=logging.INFO)

def verify_extraction():
    url = "https://sharing-db.club"
    print(f"Testing extraction on {url}...")
    
    scraper = MusicBlogScraper(url)
    
    # Fetch page content
    soup = scraper.get_page_content(url)
    if not soup:
        print("❌ Failed to fetch page content")
        return False
        
    # Extract posts
    posts = scraper.extract_posts_from_page(soup, url)
    
    print(f"Found {len(posts)} posts:")
    for post in posts[:3]:
        print(f"  - {post}")
        
    if len(posts) == 0:
        print("\n❌ Verification Failed: No posts found.")
        return False

    # Test metadata extraction on first post
    first_post_url = posts[0]
    print(f"\nTesting metadata extraction on: {first_post_url}")
    post_soup = scraper.get_page_content(first_post_url)
    
    title = scraper.extract_post_title(post_soup)
    print(f"Title: {title}")
    
    date = scraper.extract_post_date(post_soup, first_post_url)
    print(f"Date: {date}")
    
    links = scraper.extract_download_links(post_soup, first_post_url)
    print(f"Download Links: {len(links)}")
    for l in links:
        print(f"  - {l}")
        
    if title and date and len(links) > 0:
        print("\n✅ Verification Successful: All metadata found!")
        return True
    else:
        print("\n❌ Verification Failed: Missing metadata.")
        if not title: print("  - Missing Title")
        if not date: print("  - Missing Date")
        if len(links) == 0: print("  - Missing Links")
        return False

if __name__ == "__main__":
    if verify_extraction():
        sys.exit(0)
    else:
        sys.exit(1)
