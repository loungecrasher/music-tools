#!/usr/bin/env python3
"""
Link Extractor Module for EDM Music Blog Scraper
Extracts unique download links from JSON or text files with enhanced features.
"""

import json
import re
import logging
from typing import List, Dict, Optional, Union
from pathlib import Path
from datetime import datetime

# Import configuration and error handling
from .config import (
    DOWNLOAD_PATTERNS, GROUP_SIZE, DEFAULT_ENCODING, 
    MAX_FILE_SIZE, CHUNK_SIZE
)
from .error_handling import (
    safe_file_read, validate_file_path, sanitize_filename,
    ValidationError, ScrapingError
)
from .models import LinkExtractionResult

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LinkExtractor:
    """Extract and process download links from various file formats."""
    
    def __init__(self):
        # Use pre-compiled patterns from config
        self.download_patterns = DOWNLOAD_PATTERNS
    
    def extract_from_json(self, json_file_path: str) -> Dict:
        """
        Extract all unique download links from a JSON file.
        
        Args:
            json_file_path: Path to the JSON file
            
        Returns:
            Dictionary with extraction results
        """
        try:
            # Validate file path
            if not validate_file_path(json_file_path):
                raise ValidationError(f"Invalid file path: {json_file_path}")
            
            logger.info(f"Reading JSON file: {json_file_path}")
            
            # Read file safely
            content = safe_file_read(json_file_path, DEFAULT_ENCODING)
            if not content:
                raise ScrapingError(f"Could not read file: {json_file_path}")
            
            data = json.loads(content)
            
            all_links = set()
            posts_processed = 0
            genre_stats = {}
            quality_stats = {'flac': 0, 'mp3_320': 0, 'other': 0}
            
            # Extract from posts array
            for post in data.get('posts', []):
                download_links = post.get('download_links', [])
                for link in download_links:
                    if link and link.strip():
                        all_links.add(link.strip())
                        
                        # Track quality stats
                        link_lower = link.lower()
                        if 'flac' in link_lower or '.flac' in link_lower:
                            quality_stats['flac'] += 1
                        elif '320' in link_lower:
                            quality_stats['mp3_320'] += 1
                        else:
                            quality_stats['other'] += 1
                
                # Track genre stats
                for genre in post.get('matching_genres', []):
                    genre_stats[genre] = genre_stats.get(genre, 0) + 1
                
                posts_processed += 1
            
            # Convert to sorted list
            unique_links = sorted(list(all_links))
            
            return {
                'links': unique_links,
                'total_links': len(unique_links),
                'posts_processed': posts_processed,
                'genre_stats': genre_stats,
                'quality_stats': quality_stats,
                'metadata': data.get('metadata', {})
            }
            
        except FileNotFoundError:
            logger.error(f"JSON file not found: {json_file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            raise
        except Exception as e:
            logger.error(f"Error extracting from JSON: {e}")
            raise
    
    def extract_from_text(self, text_file_path: str) -> Dict:
        """
        Extract all unique download links from a text file using streaming.
        
        Args:
            text_file_path: Path to the text file
            
        Returns:
            Dictionary with extraction results
        """
        try:
            # Validate file path
            if not validate_file_path(text_file_path):
                raise ValidationError(f"Invalid file path: {text_file_path}")
            
            logger.info(f"Reading text file: {text_file_path}")
            
            # Read file safely
            content = safe_file_read(text_file_path, DEFAULT_ENCODING)
            if not content:
                raise ScrapingError(f"Could not read file: {text_file_path}")
            
            all_links = set()
            quality_stats = {'flac': 0, 'mp3_320': 0, 'other': 0}
            
            # Find all links matching our patterns
            for pattern in self.download_patterns:
                matches = pattern.findall(content)
                for match in matches:
                    if isinstance(match, str) and match.strip():
                        link = match.strip()
                        all_links.add(link)
                        
                        # Track quality stats
                        link_lower = link.lower()
                        if 'flac' in link_lower or '.flac' in link_lower:
                            quality_stats['flac'] += 1
                        elif '320' in link_lower:
                            quality_stats['mp3_320'] += 1
                        else:
                            quality_stats['other'] += 1
            
            # Also look for lines that start with "- " (common in our output format)
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('- ') or line.startswith('• '):
                    potential_link = line[2:].strip()
                    if any(pattern.search(potential_link) for pattern in self.download_patterns):
                        all_links.add(potential_link)
            
            # Convert to sorted list
            unique_links = sorted(list(all_links))
            
            # Try to extract metadata from text file
            metadata = {}
            if 'Generated on' in content:
                date_match = re.search(r'Generated on (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', content)
                if date_match:
                    metadata['generated_at'] = date_match.group(1)
            
            return {
                'links': unique_links,
                'total_links': len(unique_links),
                'quality_stats': quality_stats,
                'metadata': metadata
            }
            
        except FileNotFoundError:
            logger.error(f"Text file not found: {text_file_path}")
            raise
        except Exception as e:
            logger.error(f"Error extracting from text: {e}")
            raise
    
    def save_links(self, links: List[str], output_file: str, group_size: int = GROUP_SIZE, 
                   include_stats: bool = True, stats: Optional[Dict] = None):
        """
        Save extracted links to a file with optional grouping and statistics.
        
        Args:
            links: List of links to save
            output_file: Output file path
            group_size: Number of links per group (0 for no grouping)
            include_stats: Whether to include statistics at the top
            stats: Additional statistics to include
        """
        try:
            # Validate output file path
            if not validate_file_path(output_file):
                raise ValidationError(f"Invalid output file path: {output_file}")
            
            # Sanitize filename
            output_file = sanitize_filename(output_file)
            
            logger.info(f"Writing {len(links)} unique links to: {output_file}")
            
            with open(output_file, 'w', encoding=DEFAULT_ENCODING) as f:
                # Write header
                f.write(f"EDM Music Download Links - Extracted on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                # Write statistics if requested
                if include_stats and stats:
                    f.write("EXTRACTION STATISTICS\n")
                    f.write("-" * 20 + "\n")
                    
                    if 'posts_processed' in stats:
                        f.write(f"Posts processed: {stats['posts_processed']}\n")
                    
                    f.write(f"Total unique links: {len(links)}\n")
                    
                    if 'quality_stats' in stats:
                        q_stats = stats['quality_stats']
                        f.write(f"\nQuality breakdown:\n")
                        f.write(f"  FLAC/Lossless: {q_stats.get('flac', 0)}\n")
                        f.write(f"  MP3 320kbps: {q_stats.get('mp3_320', 0)}\n")
                        f.write(f"  Other: {q_stats.get('other', 0)}\n")
                    
                    if 'genre_stats' in stats:
                        f.write(f"\nTop genres:\n")
                        sorted_genres = sorted(stats['genre_stats'].items(), 
                                             key=lambda x: x[1], reverse=True)[:10]
                        for genre, count in sorted_genres:
                            f.write(f"  {genre}: {count} posts\n")
                    
                    f.write("\n" + "=" * 80 + "\n\n")
                
                # Write links with optional grouping
                if group_size > 0:
                    for i, link in enumerate(links):
                        # Add group header at the start of each group
                        if i % group_size == 0:
                            group_num = (i // group_size) + 1
                            total_groups = (len(links) + group_size - 1) // group_size
                            f.write(f"=== GROUP {group_num} of {total_groups} ===\n")
                        
                        f.write(f"{link}\n")
                        
                        # Add a blank line after every group (except the last)
                        if (i + 1) % group_size == 0 and (i + 1) < len(links):
                            f.write("\n")
                else:
                    # Write all links without grouping
                    for link in links:
                        f.write(f"{link}\n")
            
            logger.info(f"✅ Successfully saved links to {output_file}")
            
        except Exception as e:
            logger.error(f"Error saving links: {e}")
            raise
    
    def extract_and_save(self, input_file: str, output_file: str = None, 
                        group_size: int = GROUP_SIZE, include_stats: bool = True) -> Dict:
        """
        Extract links from input file and save to output file.
        
        Args:
            input_file: Input file path (JSON or text)
            output_file: Output file path (auto-generated if not provided)
            group_size: Number of links per group
            include_stats: Whether to include statistics
            
        Returns:
            Extraction results dictionary
        """
        # Determine file type
        input_path = Path(input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Extract based on file type
        if input_path.suffix.lower() == '.json':
            results = self.extract_from_json(input_file)
        else:
            results = self.extract_from_text(input_file)
        
        # Generate output filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"extracted_links_{timestamp}.txt"
        
        # Save the links
        self.save_links(
            results['links'], 
            output_file, 
            group_size=group_size,
            include_stats=include_stats,
            stats=results
        )
        
        # Print summary
        logger.info(f"📊 Extraction Summary:")
        logger.info(f"   Input file: {input_file}")
        logger.info(f"   Output file: {output_file}")
        logger.info(f"   Total unique links: {results['total_links']}")
        
        return results


def main():
    """Command-line interface for link extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract download links from EDM scraper output files'
    )
    parser.add_argument('input_file', help='Input file (JSON or text)')
    parser.add_argument('-o', '--output', help='Output file (default: auto-generated)')
    parser.add_argument('-g', '--group-size', type=int, default=GROUP_SIZE,
                       help='Number of links per group (0 for no grouping)')
    parser.add_argument('--no-stats', action='store_true',
                       help='Exclude statistics from output')
    
    args = parser.parse_args()
    
    try:
        # Validate input file
        if not validate_file_path(args.input_file):
            print(f"Error: Invalid input file path: {args.input_file}")
            return 1
        
        # Validate group size
        if args.group_size < 0:
            print("Error: Group size must be non-negative")
            return 1
        
        extractor = LinkExtractor()
        results = extractor.extract_and_save(
            args.input_file,
            args.output,
            group_size=args.group_size,
            include_stats=not args.no_stats
        )
        
        print(f"\n🎉 Successfully extracted {results['total_links']} unique links!")
        
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        return 1
    except ScrapingError as e:
        print(f"❌ Scraping error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())