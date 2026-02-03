#!/usr/bin/env python3
"""
Example usage of the EDM Music Blog Scraper
This script demonstrates how to use the scraper programmatically.
"""

import json
from datetime import datetime

from .music_scraper import MusicBlogScraper


def example_basic_usage():
    """Basic usage example."""
    print("=== Basic Usage Example ===")

    # Create scraper instance
    scraper = MusicBlogScraper("https://example-blog.com", "basic_results.txt")

    # Find blog posts (limit to 5 pages for demo)
    print("Finding blog posts...")
    post_urls = scraper.find_blog_posts(max_pages=5)

    if not post_urls:
        print("No posts found!")
        return

    # Filter by genres
    target_genres = ["house", "techno"]
    print(f"Filtering posts for genres: {target_genres}")
    matching_posts = scraper.filter_posts_by_genre(post_urls, target_genres)

    # Save results
    scraper.save_results(matching_posts)


def example_advanced_usage():
    """Advanced usage with custom configuration."""
    print("\n=== Advanced Usage Example ===")

    # Create scraper with custom output
    scraper = MusicBlogScraper("https://example-blog.com", "advanced_results.txt")

    # Define specific genres to search for
    genres = ["deep house", "progressive house", "tech house", "melodic techno", "liquid dnb"]

    print(f"Searching for genres: {genres}")

    # Find posts with more pages
    post_urls = scraper.find_blog_posts(max_pages=10)

    if not post_urls:
        print("No posts found!")
        return

    # Filter posts
    matching_posts = scraper.filter_posts_by_genre(post_urls, genres)

    # Custom processing of results
    print(f"\nFound {len(matching_posts)} matching posts")

    # Group by genre
    genre_groups = {}
    for post in matching_posts:
        for genre in post["matching_genres"]:
            if genre not in genre_groups:
                genre_groups[genre] = []
            genre_groups[genre].append(post)

    # Print summary by genre
    print("\nResults by genre:")
    for genre, posts in genre_groups.items():
        total_links = sum(len(post["download_links"]) for post in posts)
        print(f"  {genre}: {len(posts)} posts, {total_links} download links")

    # Save results
    scraper.save_results(matching_posts)


def example_json_output():
    """Example with JSON output for further processing."""
    print("\n=== JSON Output Example ===")

    scraper = MusicBlogScraper("https://example-blog.com")

    # Find and filter posts
    post_urls = scraper.find_blog_posts(max_pages=3)
    matching_posts = scraper.filter_posts_by_genre(post_urls, ["house", "techno"])

    # Save as JSON for programmatic access
    json_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_posts": len(matching_posts),
            "total_links": sum(len(post["download_links"]) for post in matching_posts),
            "genres_searched": ["house", "techno"],
        },
        "posts": matching_posts,
    }

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print("Results saved to results.json")


def example_batch_processing():
    """Example of processing multiple blogs."""
    print("\n=== Batch Processing Example ===")

    # List of blogs to process
    blogs = [
        {
            "url": "https://blog1.example.com",
            "genres": ["house", "deep house"],
            "output": "blog1_results.txt",
        },
        {
            "url": "https://blog2.example.com",
            "genres": ["techno", "trance"],
            "output": "blog2_results.txt",
        },
    ]

    for blog in blogs:
        print(f"\nProcessing {blog['url']}...")

        try:
            scraper = MusicBlogScraper(blog["url"], blog["output"])
            post_urls = scraper.find_blog_posts(max_pages=5)

            if post_urls:
                matching_posts = scraper.filter_posts_by_genre(post_urls, blog["genres"])
                scraper.save_results(matching_posts)
                print(f"  Found {len(matching_posts)} matching posts")
            else:
                print("  No posts found")

        except Exception as e:
            print(f"  Error processing {blog['url']}: {e}")


def example_custom_filtering():
    """Example with custom filtering logic."""
    print("\n=== Custom Filtering Example ===")

    scraper = MusicBlogScraper("https://example-blog.com")

    # Find all posts first
    post_urls = scraper.find_blog_posts(max_pages=5)

    if not post_urls:
        print("No posts found!")
        return

    # Custom filtering: only posts with multiple download links
    print("Filtering posts with multiple download links...")

    posts_with_multiple_links = []
    for post_url in post_urls:
        soup = scraper.get_page_content(post_url)
        if soup:
            download_links = scraper.extract_download_links(soup, post_url)

            # Only include posts with 2+ download links
            if len(download_links) >= 2:
                genres = scraper.extract_genre_keywords(soup)
                title = scraper.extract_post_title(soup)

                post_info = {
                    "url": post_url,
                    "title": title,
                    "genres": genres,
                    "download_links": download_links,
                    "link_count": len(download_links),
                }
                posts_with_multiple_links.append(post_info)

    # Sort by number of download links
    posts_with_multiple_links.sort(key=lambda x: x["link_count"], reverse=True)

    # Save results
    with open("multiple_links_results.txt", "w", encoding="utf-8") as f:
        f.write(
            f"Posts with Multiple Download Links - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        f.write("=" * 80 + "\n\n")

        for post in posts_with_multiple_links:
            f.write(f"Title: {post['title']}\n")
            f.write(f"URL: {post['url']}\n")
            f.write(f"Genres: {', '.join(post['genres'])}\n")
            f.write(f"Download Links ({post['link_count']}):\n")

            for link in post["download_links"]:
                f.write(f"  - {link}\n")

            f.write("\n" + "-" * 60 + "\n\n")

    print(f"Found {len(posts_with_multiple_links)} posts with multiple download links")
    print("Results saved to multiple_links_results.txt")


if __name__ == "__main__":
    print("EDM Music Blog Scraper - Example Usage")
    print("Note: These examples use placeholder URLs. Replace with actual blog URLs.")
    print()

    # Uncomment the examples you want to run:

    # example_basic_usage()
    # example_advanced_usage()
    # example_json_output()
    # example_batch_processing()
    # example_custom_filtering()

    print("To run examples, uncomment the function calls in the script.")
    print("Remember to replace 'https://example-blog.com' with actual blog URLs.")
