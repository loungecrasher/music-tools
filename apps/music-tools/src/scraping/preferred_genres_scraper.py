#!/usr/bin/env python3
"""
Specialized EDM Music Blog Scraper for Preferred Genres
Optimized for: House, Progressive House, Melodic, Indie Dance, Bass House,
Organic House, Drum & Bass, UK Garage, Electro Pop, Nu Disco, Funky,
Deep House, Tech House, Dance, Afro House, Brazilian, Latin, Electronica, Ambient
"""

import argparse
import json
import logging
from datetime import date, datetime
from typing import Dict, List, Optional

from tqdm import tqdm

from .music_scraper import MusicBlogScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PreferredGenresScraper(MusicBlogScraper):
    """Enhanced scraper optimized for preferred genres."""

    def __init__(self, base_url: str, output_file: str = "preferred_genres_links.txt"):
        super().__init__(base_url, output_file)

        # User's preferred genres with priority weights
        self.preferred_genres = {
            "house": 10,
            "progressive house": 10,
            "melodic": 9,
            "indie dance": 9,
            "bass house": 9,
            "organic house": 8,
            "drum and bass": 8,
            "uk garage": 8,
            "electro pop": 8,
            "nu disco": 8,
            "funky": 7,
            "deep house": 7,
            "tech house": 7,
            "dance": 7,
            "afro house": 7,
            "brazilian": 6,
            "latin": 6,
            "electronica": 6,
            "ambient": 5,
        }

        # Genre aliases and variations
        self.genre_aliases = {
            "house": ["house music", "house mix", "house track"],
            "progressive house": ["prog house", "progressive", "prog"],
            "melodic": ["melodic house", "melodic techno", "melodic trance"],
            "indie dance": ["indie", "indie electronic", "indie pop"],
            "bass house": ["basshouse", "bass house music"],
            "organic house": ["organic", "organic electronic"],
            "drum and bass": ["dnb", "drum and bass", "drum n bass"],
            "uk garage": ["ukg", "garage", "speed garage", "2-step"],
            "electro pop": ["electropop", "electronic pop", "synth pop"],
            "nu disco": ["nu-disco", "new disco", "disco house"],
            "funky": ["funk", "funky house", "funky electronic"],
            "deep house": ["deep", "deep house music"],
            "tech house": ["techhouse", "tech house music"],
            "dance": ["dance music", "electronic dance"],
            "afro house": ["afro", "african house", "afro electronic"],
            "brazilian": ["brazil", "brazilian house", "brazilian electronic"],
            "latin": ["latin house", "latin electronic", "latin music"],
            "electronica": ["electronic", "electronica music"],
            "ambient": ["ambient music", "ambient electronic"],
        }

    def extract_genres_from_text(self, text: str) -> List[str]:
        """Enhanced genre extraction with aliases and priority scoring."""
        # Handle BeautifulSoup objects
        if hasattr(text, "get_text"):
            text = text.get_text()

        if not text:
            return []

        text_lower = text.lower()
        found_genres = []

        # Check for exact matches first (higher priority)
        for genre, weight in self.preferred_genres.items():
            if genre in text_lower:
                found_genres.append(genre)

        # Check for aliases and variations
        for genre, aliases in self.genre_aliases.items():
            for alias in aliases:
                if alias in text_lower and genre not in found_genres:
                    found_genres.append(genre)
                    break

        # Also check the parent class's genre list for additional matches
        additional_genres = super().extract_genres_from_text(text)
        for genre in additional_genres:
            if genre not in found_genres:
                found_genres.append(genre)

        return found_genres

    def calculate_post_score(self, post_info: Dict) -> int:
        """Calculate a score for posts based on preferred genres and quality."""
        score = 0

        for genre in post_info["matching_genres"]:
            if genre in self.preferred_genres:
                score += self.preferred_genres[genre]

        # Bonus for multiple download links
        score += len(post_info["download_links"]) * 2

        # Bonus for FLAC quality
        flac_count = sum(
            1
            for link in post_info["download_links"]
            if any(indicator in link.lower() for indicator in ["flac", ".flac", "lossless"])
        )
        score += flac_count * 3  # Extra bonus for FLAC quality

        return score

    def filter_posts_by_genre(
        self,
        post_urls: List[str],
        target_genres: List[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict]:
        """Enhanced filtering with scoring, date range, and better organization."""
        if target_genres is None:
            target_genres = list(self.preferred_genres.keys())

        matching_posts = []

        logger.info(f"Filtering {len(post_urls)} posts for preferred genres...")
        if start_date or end_date:
            date_range = (
                f" from {start_date} to {end_date}"
                if start_date and end_date
                else f" from {start_date}" if start_date else f" until {end_date}"
            )
            logger.info(f"Date range: {date_range}")

        # Create progress bar for filtering posts
        with tqdm(total=len(post_urls), desc="Filtering preferred genres", unit="post") as pbar:
            for i, post_url in enumerate(post_urls, 1):
                logger.debug(f"Processing: {post_url}")

                soup = self.get_page_content(post_url)
                if not soup:
                    pbar.update(1)
                    continue

                # Extract post date
                post_date = self.extract_post_date(soup, post_url)

                # Check date range if specified
                if start_date or end_date:
                    if not post_date:
                        logger.debug("Could not determine post date, skipping date filter")
                    elif start_date and post_date < start_date:
                        logger.debug(f"Post date {post_date} before start date {start_date}")
                        pbar.update(1)
                        continue
                    elif end_date and post_date > end_date:
                        logger.debug(f"Post date {post_date} after end date {end_date}")
                        pbar.update(1)
                        continue
                    else:
                        logger.debug(f"Post date {post_date} within range")

                # Extract genre keywords
                post_genres = self.extract_genres_from_text(soup)

                # Check if any target genres match
                matching_genres = [
                    genre
                    for genre in target_genres
                    if genre.lower() in [g.lower() for g in post_genres]
                ]

                if matching_genres:
                    # Extract download links
                    download_links = self.extract_download_links(soup, post_url)

                    # Get post title
                    title = self.extract_post_title(soup)

                    post_info = {
                        "url": post_url,
                        "title": title,
                        "genres": post_genres,
                        "matching_genres": matching_genres,
                        "download_links": download_links,
                        "post_date": post_date,
                    }

                    # Calculate score
                    post_info["score"] = self.calculate_post_score(post_info)

                    matching_posts.append(post_info)
                    logger.info(
                        f"Found {len(download_links)} download links (Score: {post_info['score']})"
                    )
                else:
                    logger.debug("No matching genres")

                pbar.update(1)

        # Sort by score (highest first)
        matching_posts.sort(key=lambda x: x["score"], reverse=True)

        return matching_posts

    def save_results(self, matching_posts: List[Dict]):
        """Save results with enhanced organization by genre categories and automatic link extraction."""
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(
                f"Preferred Genres Music Download Links - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            f.write("=" * 80 + "\n\n")

            # Group posts by genre categories
            genre_categories = {
                "House": [
                    "house",
                    "progressive house",
                    "deep house",
                    "tech house",
                    "bass house",
                    "organic house",
                    "afro house",
                ],
                "Melodic & Progressive": ["melodic", "progressive house"],
                "Dance & Pop": ["indie dance", "dance", "electro pop", "nu disco", "funky"],
                "Bass & Garage": ["bass house", "uk garage", "drum and bass"],
                "Latin & Brazilian": ["brazilian", "latin", "afro house"],
                "Electronic": ["electronica", "ambient"],
            }

            # Create category groups
            category_posts = {}
            for category, genres in genre_categories.items():
                category_posts[category] = []
                for post in matching_posts:
                    if any(genre in post["matching_genres"] for genre in genres):
                        category_posts[category].append(post)

            # Write results by category
            for category, posts in category_posts.items():
                if posts:
                    f.write(f"\n{category.upper()}\n")
                    f.write("-" * len(category) + "\n")

                    for post in posts:
                        f.write(f"\nTitle: {post['title']}\n")
                        f.write(f"URL: {post['url']}\n")
                        if post.get("post_date"):
                            f.write(f"Date: {post['post_date']}\n")
                        f.write(f"Genres: {', '.join(post['genres'])}\n")
                        f.write(f"Matching Genres: {', '.join(post['matching_genres'])}\n")
                        f.write(f"Score: {post['score']}\n")
                        f.write("Download Links:\n")

                        if post["download_links"]:
                            for link in post["download_links"]:
                                f.write(f"  - {link}\n")
                        else:
                            f.write("  No download links found\n")

                        f.write("\n" + "-" * 40 + "\n")

            # Summary
            f.write("\n\nSUMMARY\n")
            f.write("=" * 50 + "\n")
            f.write(f"Total Posts Found: {len(matching_posts)}\n")
            f.write(
                f"Total Download Links: {sum(len(post['download_links']) for post in matching_posts)}\n"
            )

            for category, posts in category_posts.items():
                if posts:
                    total_links = sum(len(post["download_links"]) for post in posts)
                    f.write(f"{category}: {len(posts)} posts, {total_links} links\n")

        logger.info(f"Results saved to {self.output_file}")
        logger.info(f"Found {len(matching_posts)} matching posts")

        total_links = sum(len(post["download_links"]) for post in matching_posts)
        logger.info(f"Total download links found: {total_links}")

        # Log summary by category
        logger.info("Results by category:")
        for category, posts in category_posts.items():
            if posts:
                total_links = sum(len(post["download_links"]) for post in posts)
                logger.info(f"  {category}: {len(posts)} posts, {total_links} links")

        # Now automatically extract and append all unique links
        if total_links > 0:
            logger.info("Automatically extracting all unique download links...")

            # Collect all unique links with quality tracking
            all_links = set()
            quality_stats = {"flac": 0, "mp3_320": 0, "other": 0}
            genre_link_stats = {}

            for post in matching_posts:
                for link in post.get("download_links", []):
                    if link and link.strip():
                        link = link.strip()
                        all_links.add(link)

                        # Track quality stats
                        link_lower = link.lower()
                        if "flac" in link_lower or ".flac" in link_lower:
                            quality_stats["flac"] += 1
                        elif "320" in link_lower:
                            quality_stats["mp3_320"] += 1
                        else:
                            quality_stats["other"] += 1

                        # Track links per genre
                        for genre in post.get("matching_genres", []):
                            if genre not in genre_link_stats:
                                genre_link_stats[genre] = 0
                            genre_link_stats[genre] += 1

            # Sort links for consistent output
            unique_links = sorted(list(all_links))

            # Append extracted links section to the same file
            with open(self.output_file, "a", encoding="utf-8") as f:
                f.write("\n\n" + "=" * 80 + "\n")
                f.write("ALL UNIQUE DOWNLOAD LINKS (EXTRACTED)\n")
                f.write("=" * 80 + "\n\n")

                # Write enhanced statistics
                f.write("EXTRACTION STATISTICS\n")
                f.write("-" * 20 + "\n")
                f.write(f"Total posts processed: {len(matching_posts)}\n")
                f.write(f"Total unique links: {len(unique_links)}\n")
                f.write("\nQuality breakdown:\n")
                f.write(f"  FLAC/Lossless: {quality_stats['flac']}\n")
                f.write(f"  MP3 320kbps: {quality_stats['mp3_320']}\n")
                f.write(f"  Other: {quality_stats['other']}\n")

                # Genre statistics
                f.write("\nLinks per genre:\n")
                sorted_genre_stats = sorted(
                    genre_link_stats.items(), key=lambda x: x[1], reverse=True
                )
                for genre, count in sorted_genre_stats[:10]:  # Top 10 genres
                    f.write(f"  {genre}: {count} links\n")

                f.write("\n" + "=" * 80 + "\n\n")

                # Write links in groups of 20
                group_size = 20
                for i, link in enumerate(unique_links):
                    # Add group header at the start of each group
                    if i % group_size == 0:
                        group_num = (i // group_size) + 1
                        total_groups = (len(unique_links) + group_size - 1) // group_size
                        f.write(f"=== GROUP {group_num} of {total_groups} ===\n")

                    f.write(f"{link}\n")

                    # Add a blank line after every group (except the last)
                    if (i + 1) % group_size == 0 and (i + 1) < len(unique_links):
                        f.write("\n")

            logger.info(f"✅ Extracted {len(unique_links)} unique download links")
            logger.info(f"   FLAC/Lossless: {quality_stats['flac']}")
            logger.info(f"   MP3 320kbps: {quality_stats['mp3_320']}")
            logger.info(f"   Other: {quality_stats['other']}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape EDM blog for preferred genres music downloads"
    )
    parser.add_argument("url", help="Base URL of the blog site")
    parser.add_argument(
        "--genres", nargs="+", help="Specific genres to search for (default: all preferred genres)"
    )
    parser.add_argument(
        "--output",
        default="preferred_genres_links.txt",
        help="Output file name (default: preferred_genres_links.txt)",
    )
    parser.add_argument(
        "--max-pages", type=int, default=10, help="Maximum pages to search (default: 10)"
    )
    parser.add_argument(
        "--start-date", help="Start date for filtering (YYYY-MM-DD format, inclusive)"
    )
    parser.add_argument("--end-date", help="End date for filtering (YYYY-MM-DD format, inclusive)")
    parser.add_argument("--json", action="store_true", help="Also save results as JSON file")

    args = parser.parse_args()

    # Parse date arguments
    start_date = None
    end_date = None

    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid start date format. Use YYYY-MM-DD (e.g., 2024-01-15)")
            return

    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid end date format. Use YYYY-MM-DD (e.g., 2024-12-31)")
            return

    if start_date and end_date and start_date > end_date:
        logger.error("Start date cannot be after end date")
        return

    # Create specialized scraper instance
    scraper = PreferredGenresScraper(args.url, args.output)

    # Find all blog posts
    logger.info(f"Searching for blog posts on {args.url}")
    post_urls = scraper.find_blog_posts(args.max_pages)

    if not post_urls:
        logger.error("No blog posts found. Please check the URL and try again.")
        return

    # Filter posts by genre and date range
    target_genres = args.genres if args.genres else list(scraper.preferred_genres.keys())
    matching_posts = scraper.filter_posts_by_genre(post_urls, target_genres, start_date, end_date)

    # Save results
    scraper.save_results(matching_posts)

    # Save as JSON if requested
    if args.json:
        json_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_posts": len(matching_posts),
                "total_links": sum(len(post["download_links"]) for post in matching_posts),
                "genres_searched": target_genres,
                "preferred_genres": scraper.preferred_genres,
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                },
            },
            "posts": matching_posts,
        }

        json_file = args.output.replace(".txt", ".json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        logger.info(f"JSON results saved to {json_file}")


if __name__ == "__main__":
    main()
