#!/usr/bin/env python3
"""
Example script demonstrating the new link extraction functionality
"""

from .link_extractor import LinkExtractor
import json
from datetime import datetime

def main():
    """Demonstrate link extraction features"""
    
    print("EDM Music Blog Scraper - Link Extraction Example")
    print("=" * 50)
    
    # Example 1: Extract links from a text file
    print("\nExample 1: Extracting from a text file")
    print("-" * 40)
    
    # Create a sample text file
    sample_text = """
EDM Music Download Links - Generated on 2024-01-15 14:30:25
================================================================================

Title: Amazing Deep House Mix 2024
URL: https://example-blog.com/amazing-deep-house-mix-2024
Genres: deep house, house, electronic
Matching Genres: deep house
Download Links:
  - https://mediafire.com/file/abc123/mix.zip
  - https://mega.nz/file/xyz789/mix.flac

------------------------------------------------------------

Title: Progressive House Collection
URL: https://example-blog.com/progressive-house-collection
Genres: progressive house, house, edm
Matching Genres: progressive house
Download Links:
  - https://dropbox.com/s/def456/collection_320.mp3
  - https://nfile.cc/downloads/track123.flac

------------------------------------------------------------
"""
    
    with open('sample_output.txt', 'w') as f:
        f.write(sample_text)
    
    # Extract links
    extractor = LinkExtractor()
    results = extractor.extract_and_save(
        'sample_output.txt',
        'extracted_from_text.txt',
        group_size=20,
        include_stats=True
    )
    
    print(f"✅ Extracted {results['total_links']} unique links from text file")
    print(f"   Saved to: extracted_from_text.txt")
    
    # Example 2: Extract links from a JSON file
    print("\n\nExample 2: Extracting from a JSON file")
    print("-" * 40)
    
    # Create a sample JSON file
    sample_json = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_posts": 3,
            "total_links": 5,
            "genres_searched": ["house", "progressive house", "melodic"]
        },
        "posts": [
            {
                "url": "https://example.com/post1",
                "title": "Deep House Essentials 2024",
                "genres": ["deep house", "house"],
                "matching_genres": ["house"],
                "download_links": [
                    "https://mega.nz/file/deep_house_essentials.flac",
                    "https://mediafire.com/file/deep_house_320.mp3"
                ],
                "post_date": "2024-01-15"
            },
            {
                "url": "https://example.com/post2",
                "title": "Melodic Journey Vol. 5",
                "genres": ["melodic", "progressive house"],
                "matching_genres": ["melodic", "progressive house"],
                "download_links": [
                    "https://nfile.cc/melodic_journey_flac.zip",
                    "https://dropbox.com/s/melodic_320kbps.rar"
                ],
                "post_date": "2024-01-14"
            },
            {
                "url": "https://example.com/post3",
                "title": "Bass House Bangers",
                "genres": ["bass house", "house"],
                "matching_genres": ["house"],
                "download_links": [
                    "https://soundcloud.com/bass_house_mix"
                ],
                "post_date": "2024-01-13"
            }
        ]
    }
    
    with open('sample_output.json', 'w') as f:
        json.dump(sample_json, f, indent=2)
    
    # Extract links
    results = extractor.extract_and_save(
        'sample_output.json',
        'extracted_from_json.txt',
        group_size=20,
        include_stats=True
    )
    
    print(f"✅ Extracted {results['total_links']} unique links from JSON file")
    print(f"   Saved to: extracted_from_json.txt")
    
    # Show quality statistics
    if 'quality_stats' in results:
        print("\nQuality Statistics:")
        print(f"  FLAC/Lossless: {results['quality_stats']['flac']}")
        print(f"  MP3 320kbps: {results['quality_stats']['mp3_320']}")
        print(f"  Other: {results['quality_stats']['other']}")
    
    # Show genre statistics
    if 'genre_stats' in results:
        print("\nGenre Statistics:")
        for genre, count in results['genre_stats'].items():
            print(f"  {genre}: {count} posts")
    
    print("\n✅ Example completed successfully!")
    print("\nYou can now use the CLI to extract links interactively:")
    print("  python cli_scraper.py")
    print("  Then select 'Extract Links from Existing File'")

if __name__ == "__main__":
    main()