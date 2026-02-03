#!/usr/bin/env python3
"""
EDM Music Blog Scraper - Interactive CLI
Refactored to use modular Config and Runner classes.
"""

import os
import sys
import asyncio
from datetime import datetime, date
from typing import List, Dict, Optional

# Import our modular components
from .config import ScraperConfig, ScraperSettings
from .runner import ScraperRunner
from .link_extractor import LinkExtractor

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class EDMScraperCLI:
    """Interactive CLI for the EDM Music Blog Scraper."""
    
    def __init__(self):
        self.runner = ScraperRunner()
    
    def print_header(self):
        """Print the application header."""
        print(f"{Colors.HEADER}{Colors.BOLD}")
        print("=" * 60)
        print("🎵 EDM Music Blog Scraper - Interactive CLI")
        print("=" * 60)
        print(f"{Colors.ENDC}")
    
    def print_menu(self, title: str, options: List[str], back_option: bool = True) -> int:
        """Display a menu and get user selection."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{title}{Colors.ENDC}")
        print("-" * len(title))
        
        for i, option in enumerate(options, 1):
            print(f"{Colors.BLUE}{i}.{Colors.ENDC} {option}")
        
        if back_option:
            print(f"{Colors.BLUE}0.{Colors.ENDC} Back/Exit")
        
        while True:
            try:
                choice = input(f"\n{Colors.YELLOW}Enter your choice: {Colors.ENDC}")
                choice_num = int(choice)
                
                if back_option and choice_num == 0:
                    return 0
                elif 1 <= choice_num <= len(options):
                    return choice_num
                else:
                    print(f"{Colors.RED}Invalid choice. Please try again.{Colors.ENDC}")
            except ValueError:
                print(f"{Colors.RED}Please enter a number.{Colors.ENDC}")

    def get_blog_url(self) -> Optional[str]:
        """Get the blog URL from user."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}Enter Blog URL{Colors.ENDC}")
        print("-" * 20)
        print(f"{Colors.YELLOW}Example URLs:{Colors.ENDC}")
        print("  • https://sharing-db.club")
        print("  • https://edmblog.com")
        
        while True:
            url = input(f"\n{Colors.YELLOW}Blog URL: {Colors.ENDC}").strip()
            if not url:
                print(f"{Colors.RED}URL cannot be empty.{Colors.ENDC}")
                continue
            
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            if ScraperConfig.validate_url(url):
                return url
            else:
                print(f"{Colors.RED}Please enter a valid URL.{Colors.ENDC}")

    def select_genres(self) -> List[str]:
        """Let user select genres."""
        selected_genres = []
        preferred = ScraperConfig.DEFAULT_GENRES
        
        while True:
            genre_options = preferred + ["All Genres", "Done"]
            choice = self.print_menu("Select Genres", genre_options)
            
            if choice == 0 or choice == len(preferred) + 2:  # Done/Back
                break
            elif choice == len(preferred) + 1:  # All Genres
                return preferred.copy()
            else:
                selected_genre = preferred[choice - 1]
                if selected_genre in selected_genres:
                    selected_genres.remove(selected_genre)
                    print(f"{Colors.YELLOW}Removed: {selected_genre}{Colors.ENDC}")
                else:
                    selected_genres.append(selected_genre)
                    print(f"{Colors.GREEN}Added: {selected_genre}{Colors.ENDC}")
            
            if selected_genres:
                print(f"\n{Colors.GREEN}Selected: {', '.join(selected_genres)}{Colors.ENDC}")
        
        return list(set(selected_genres))

    def select_date_range(self) -> tuple[Optional[date], Optional[date]]:
        """Let user select date range."""
        ranges = ScraperConfig.get_quick_date_ranges()
        options = list(ranges.keys())
        choice = self.print_menu("Select Date Range", options)
        
        if choice == 0:
            return None, None
        
        selected_key = options[choice - 1]
        start_date = ranges[selected_key]
        
        if selected_key == "Custom range":
            return self.get_custom_date_range()
        
        return start_date, datetime.now().date()

    def get_custom_date_range(self) -> tuple[Optional[date], Optional[date]]:
        """Get custom start and end dates."""
        print(f"\n{Colors.CYAN}Enter custom date range (YYYY-MM-DD){Colors.ENDC}")
        
        start_date = self._get_date_input("Start date")
        end_date = self._get_date_input("End date")
        
        valid, msg = ScraperConfig.validate_date_range(start_date, end_date)
        if not valid:
            print(f"{Colors.RED}{msg}{Colors.ENDC}")
            return None, None
            
        return start_date, end_date

    def _get_date_input(self, prompt: str) -> Optional[date]:
        """Helper to get date input."""
        while True:
            date_str = input(f"{Colors.YELLOW}{prompt} (YYYY-MM-DD, Enter to skip): {Colors.ENDC}").strip()
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                print(f"{Colors.RED}Invalid format. Use YYYY-MM-DD.{Colors.ENDC}")

    def configure_session(self) -> Optional[ScraperSettings]:
        """Configure a scraping session."""
        url = self.get_blog_url()
        if not url: return None
        
        # Scraper Type
        options = ["Standard (All genres)", "Specialized (Select genres)"]
        choice = self.print_menu("Scraper Type", options, back_option=False)
        scraper_type = "specialized" if choice == 2 else "standard"
        
        # Genres
        genres = []
        if scraper_type == "specialized":
            genres = self.select_genres()
            if not genres:
                print(f"{Colors.YELLOW}No genres selected. Using defaults.{Colors.ENDC}")
                genres = ScraperConfig.DEFAULT_GENRES[:5]
        else:
            genres = ScraperConfig.DEFAULT_GENRES
            
        # Date Range
        start_date, end_date = self.select_date_range()
        
        # Output Settings
        default_file = ScraperConfig.get_default_filename()
        filename = input(f"{Colors.YELLOW}Output filename (default: {default_file}): {Colors.ENDC}").strip() or default_file
        
        save_json = input(f"{Colors.YELLOW}Save JSON? (y/n, default: n): {Colors.ENDC}").lower().startswith('y')
        
        rec_pages = ScraperConfig.calculate_recommended_pages(start_date, end_date)
        max_pages_input = input(f"{Colors.YELLOW}Max pages (rec: {rec_pages}): {Colors.ENDC}").strip()
        max_pages = int(max_pages_input) if max_pages_input.isdigit() else rec_pages
        
        return ScraperSettings(
            url=url,
            scraper_type=scraper_type,
            genres=genres,
            start_date=start_date,
            end_date=end_date,
            output_filename=filename,
            save_json=save_json,
            max_pages=max_pages
        )

    def quick_start(self) -> Optional[ScraperSettings]:
        """Quick start configuration."""
        url = self.get_blog_url()
        if not url: return None
        
        start_date = ScraperConfig.get_quick_date_ranges()['Last 3 months']
        
        return ScraperSettings(
            url=url,
            scraper_type="specialized",
            genres=ScraperConfig.DEFAULT_GENRES,
            start_date=start_date,
            end_date=datetime.now().date(),
            output_filename=f"quick_start_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            max_pages=ScraperConfig.calculate_recommended_pages(start_date, None)
        )

    def run_scraper(self, settings: ScraperSettings, is_async: bool = False):
        """Run the scraper."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}Starting Scraper...{Colors.ENDC}")
        print(f"URL: {settings.url}")
        print(f"Type: {settings.scraper_type}")
        print(f"Output: {settings.output_filename}")
        print("=" * 50)
        
        try:
            if is_async:
                # Async execution
                result = asyncio.run(self.runner.run_async(settings))
            else:
                # Sync execution
                result = self.runner.run(settings)
            
            # Save results
            saved_files = self.runner.save_results(settings, result['results'])
            
            print(f"\n{Colors.GREEN}{Colors.BOLD}Scraping Complete!{Colors.ENDC}")
            print(f"Found {result['count']} posts in {result['duration']:.1f}s")
            print(f"Saved to: {saved_files}")
            
            if result['errors']:
                print(f"\n{Colors.RED}Errors encountered:{Colors.ENDC}")
                for err in result['errors']:
                    print(f"  - {err}")
                    
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Interrupted.{Colors.ENDC}")
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.ENDC}")

    def extract_links_session(self):
        """Extract links from existing file."""
        # Reuse existing logic or refactor? 
        # For now, let's keep a simplified version or import if it was complex.
        # The original had a lot of UI logic. Let's simplify it.
        print(f"\n{Colors.CYAN}Extract Links{Colors.ENDC}")
        
        files = [f for f in os.listdir('.') if f.endswith(('.txt', '.json'))]
        if not files:
            print(f"{Colors.RED}No files found.{Colors.ENDC}")
            return

        for i, f in enumerate(files, 1):
            print(f"{i}. {f}")
            
        try:
            choice = int(input(f"\n{Colors.YELLOW}Select file: {Colors.ENDC}"))
            if 1 <= choice <= len(files):
                input_file = files[choice-1]
                output_file = f"extracted_{input_file}"
                
                extractor = LinkExtractor()
                results = extractor.extract_and_save(input_file, output_file)
                print(f"{Colors.GREEN}Extracted {results['total_links']} links to {output_file}{Colors.ENDC}")
        except ValueError:
            pass

    def run(self):
        """Main loop."""
        self.print_header()
        while True:
            options = [
                "Start New Session",
                "Quick Start",
                "Async Session",
                "Extract Links",
                "Exit"
            ]
            choice = self.print_menu("Main Menu", options, back_option=False)
            
            if choice == 1:
                settings = self.configure_session()
                if settings: self.run_scraper(settings)
            elif choice == 2:
                settings = self.quick_start()
                if settings: self.run_scraper(settings)
            elif choice == 3:
                settings = self.configure_session()
                if settings: self.run_scraper(settings, is_async=True)
            elif choice == 4:
                self.extract_links_session()
            elif choice == 5:
                print(f"\n{Colors.GREEN}Goodbye!{Colors.ENDC}")
                break

def main():
    try:
        EDMScraperCLI().run()
    except KeyboardInterrupt:
        print("\nGoodbye!")

if __name__ == "__main__":
    main()