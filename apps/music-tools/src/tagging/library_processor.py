"""
Music Library Processor Module

Handles music library processing, metadata collection, and tagging.
Extracted from cli.py for better maintainability.

Enhanced with:
- Per-library database tracking
- Session limits (macro batches)
- Resume capability
- Rate limiting
"""

import os
import time
import re
from typing import List, Dict, Any, Tuple, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TimeRemainingColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.box import ROUNDED
from rich.panel import Panel

console = Console()

# Import tagging database (now global)
try:
    from .tagging_database import GlobalTaggingDatabase, FileStatus
    TAGGING_DB_AVAILABLE = True
except ImportError:
    try:
        from src.tagging.tagging_database import GlobalTaggingDatabase, FileStatus
        TAGGING_DB_AVAILABLE = True
    except ImportError:
        TAGGING_DB_AVAILABLE = False
        GlobalTaggingDatabase = None
        FileStatus = None
        # CRITICAL WARNING: Database tracking disabled!
        import logging
        logging.getLogger(__name__).critical(
            "⚠️  TAGGING DATABASE NOT AVAILABLE - FILE TRACKING DISABLED!\n"
            "    All files will be re-tagged on every run.\n"
            "    Fix: Run 'pip install -e .' from project root or check PYTHONPATH"
        )


class ProcessingConfig:
    """Configuration for a processing session."""
    
    def __init__(self):
        self.api_batch_size: int = 50  # Files per API call
        self.session_limit: int = 1000  # Max files per session (macro batch)
        self.delay_between_batches: float = 5.0  # Seconds between API batches
        self.delay_on_error: float = 60.0  # Seconds to wait on rate limit
        self.force_retag: bool = False  # Force re-tag completed files
        self.speed_mode: str = "normal"  # speed, normal, safe
    
    @classmethod
    def from_speed_mode(cls, mode: str) -> 'ProcessingConfig':
        """Create config from speed mode preset."""
        config = cls()
        if mode == "speed":
            config.delay_between_batches = 3.0
            config.speed_mode = "speed"
        elif mode == "safe":
            config.delay_between_batches = 10.0
            config.speed_mode = "safe"
        else:  # normal
            config.delay_between_batches = 5.0
            config.speed_mode = "normal"
        return config


class MusicLibraryProcessor:
    """Handles music library processing with database tracking."""

    def __init__(self, scanner, metadata_handler, ai_researcher, cache_manager, config, verbose=False):
        self.scanner = scanner
        self.metadata_handler = metadata_handler
        self.ai_researcher = ai_researcher
        self.cache_manager = cache_manager
        self.config = config
        self.verbose = verbose
        
        # Processing configuration
        self.processing_config = ProcessingConfig()
        
        # Database (GLOBAL - same database for all directories)
        self.tagging_db: Optional[GlobalTaggingDatabase] = None
        self.session_id: Optional[int] = None

        # Processing statistics
        self.processed_count = 0
        self.cached_count = 0
        self.error_count = 0
        self.updated_count = 0
        self.skipped_count = 0
        self.failed_files = []

    def process(self, path: str, batch_size: int, dry_run: bool, resume: bool, missing_only: bool = False) -> Dict[str, Any]:
        """Main processing entry point with database tracking."""
        try:
            # Initialize database for this library
            if TAGGING_DB_AVAILABLE:
                self._init_database(path)
            
            # Get processing configuration from user
            self._configure_session()
            
            # Ask about subdirectory selection
            selected_dirs = None
            if Confirm.ask("\nSelect specific subdirectories to process?", default=False):
                selected_dirs = self._select_subdirectories(path)
                if not selected_dirs:  # User cancelled
                    console.print("[yellow]Cancelled.[/yellow]")
                    return {}
            
            # Scan and filter files
            music_files = self._scan_and_filter_files(path, selected_dirs, missing_only)
            if not music_files:
                return {}
            
            # Start session
            if self.tagging_db:
                self.session_id = self.tagging_db.start_session()

            # Process files with session limit
            self._process_files_with_limit(music_files, dry_run)
            
            # End session
            if self.tagging_db and self.session_id:
                self.tagging_db.end_session(
                    self.session_id,
                    self.processed_count,
                    self.updated_count,
                    self.error_count
                )
            
            self._display_final_statistics(dry_run)

            if self.failed_files and not dry_run:
                self._handle_failed_files()

            return self._get_results_summary(dry_run)

        except KeyboardInterrupt:
            # Bug #12 fix: Better error recovery with proper state cleanup
            total_files = len(music_files) if 'music_files' in locals() else 0
            self._handle_interruption(total_files)

            # Save partial progress to database if available
            if hasattr(self, 'tagging_db') and self.tagging_db:
                try:
                    # Reset any stuck 'processing' status from this interrupted session
                    self.tagging_db.reset_processing_status()
                    console.print("[yellow]💾 Partial progress saved to database[/yellow]")
                except Exception as db_error:
                    console.print(f"[red]Warning: Could not save partial progress: {db_error}[/red]")

            return self._get_results_summary(dry_run=False) if 'dry_run' in locals() else {}
        except Exception as e:
            console.print(f"[red]Scan failed: {e}[/red]")
            if self.verbose:
                console.print_exception()

            # Bug #12 fix: Attempt to save any partial progress even on error
            if hasattr(self, 'tagging_db') and self.tagging_db:
                try:
                    self.tagging_db.reset_processing_status()
                    console.print("[yellow]💾 Attempted to save partial progress[/yellow]")
                except Exception:
                    pass  # Silently fail - already in error state

            return {}
    
    def _init_database(self, library_path: str):
        """Initialize the GLOBAL tagging database."""
        try:
            # Single global database - same for all directories
            self.tagging_db = GlobalTaggingDatabase()
            
            # Reset any stuck 'processing' files from interrupted sessions
            self.tagging_db.reset_processing_status()
            
            # Note: library_path is now just for reference, not for database location
        except Exception as e:
            console.print(f"[yellow]Warning: Could not initialize database: {e}[/yellow]")
            self.tagging_db = None
    
    def _select_subdirectories(self, path: str) -> List[str]:
        """Let user select which subdirectories to include for processing."""
        console.print("\n[bold cyan]📁 Subdirectory Selection[/bold cyan]")
        
        # Get immediate subdirectories
        subdirs = []
        try:
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    # Count files in subdirectory
                    file_count = sum(1 for _ in self.scanner.scan_directory(item_path))
                    subdirs.append((item, item_path, file_count))
        except Exception as e:
            console.print(f"[red]Error listing directories: {e}[/red]")
            return [path]  # Fallback to root
        
        if not subdirs:
            console.print("[dim]No subdirectories found. Processing root directory.[/dim]")
            return [path]
        
        # Display subdirectories with file counts
        console.print(f"\n[cyan]Found {len(subdirs)} subdirectories in:[/cyan]")
        console.print(f"[dim]{path}[/dim]\n")
        
        table = Table(show_header=True, box=ROUNDED)
        table.add_column("#", style="dim", justify="right", width=4)
        table.add_column("Directory", style="cyan")
        table.add_column("Files", style="green", justify="right")
        
        total_files = 0
        for i, (name, _, count) in enumerate(subdirs, 1):
            table.add_row(str(i), name, str(count))
            total_files += count
        
        console.print(table)
        console.print(f"\n[bold]Total: {total_files} files across {len(subdirs)} directories[/bold]")
        
        # Selection options
        console.print("\n[bold cyan]Selection Options:[/bold cyan]")
        console.print("  1. Process ALL subdirectories")
        console.print("  2. Select SPECIFIC subdirectories")
        console.print("  3. Process root only (no subdirectories)")
        console.print("  0. Cancel")
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3"], default="1")
        
        if choice == "0":
            return []  # Cancel
        elif choice == "1":
            # All subdirectories
            return [s[1] for s in subdirs]
        elif choice == "3":
            # Root only
            return [path]
        else:
            # Select specific subdirectories
            console.print("\n[dim]Enter directory numbers separated by commas (e.g., 1,3,5-10)[/dim]")
            selection = Prompt.ask("Select directories")
            
            # Parse selection
            selected_indices = set()
            for part in selection.split(','):
                part = part.strip()
                if '-' in part:
                    try:
                        start, end = part.split('-')
                        for i in range(int(start), int(end) + 1):
                            selected_indices.add(i)
                    except ValueError:
                        continue
                elif part.isdigit():
                    selected_indices.add(int(part))
            
            # Get selected paths
            selected_paths = []
            for idx in sorted(selected_indices):
                if 1 <= idx <= len(subdirs):
                    selected_paths.append(subdirs[idx - 1][1])
            
            if not selected_paths:
                console.print("[yellow]No valid selection. Processing all subdirectories.[/yellow]")
                return [s[1] for s in subdirs]
            
            # Show selected
            console.print(f"\n[green]Selected {len(selected_paths)} directories:[/green]")
            for p in selected_paths:
                console.print(f"  • {os.path.basename(p)}")
            
            return selected_paths
    
    def _configure_session(self):
        """Configure the processing session interactively."""
        console.print("\n[bold cyan]Processing Configuration[/bold cyan]")
        
        # Show current stats if database available
        if self.tagging_db:
            stats = self.tagging_db.get_statistics()
            if stats['total_files'] > 0:
                console.print(f"\n[cyan]Library Status:[/cyan]")
                console.print(f"  Total files tracked: {stats['total_files']}")
                console.print(f"  Completed: [green]{stats['completed']}[/green]")
                console.print(f"  Pending: [yellow]{stats['pending']}[/yellow]")
                console.print(f"  Failed: [red]{stats['failed']}[/red]")
                console.print(f"  Skipped: [dim]{stats['skipped']}[/dim]")
        
        # Session limit
        console.print(f"\n[dim]Session limit controls how many files to process before stopping.[/dim]")
        self.processing_config.session_limit = IntPrompt.ask(
            "Session limit (files per run)",
            default=1000
        )
        
        # Speed mode
        console.print("\n[dim]Processing speed affects delay between API calls:[/dim]")
        console.print("  1. Speed (3s delay) - Fast but may hit rate limits")
        console.print("  2. Normal (5s delay) - Balanced (recommended)")
        console.print("  3. Safe (10s delay) - Slow but guaranteed safe")
        
        speed_choice = Prompt.ask(
            "Select speed mode",
            choices=["1", "2", "3"],
            default="2"
        )
        
        speed_modes = {"1": "speed", "2": "normal", "3": "safe"}
        self.processing_config = ProcessingConfig.from_speed_mode(speed_modes[speed_choice])
        self.processing_config.session_limit = IntPrompt.ask(
            "Confirm session limit",
            default=1000
        ) if speed_choice != "2" else self.processing_config.session_limit
        
        # Force re-tag option
        if self.tagging_db:
            stats = self.tagging_db.get_statistics()
            if stats['completed'] > 0:
                self.processing_config.force_retag = Confirm.ask(
                    f"Force re-tag {stats['completed']} completed files?",
                    default=False
                )
                if self.processing_config.force_retag:
                    self.tagging_db.force_retag_all()
                    console.print("[yellow]All files will be re-tagged[/yellow]")
    
    def _scan_and_filter_files(self, path: str, selected_dirs: Optional[List[str]] = None, missing_only: bool = False) -> List[str]:
        """Scan directory and filter files based on database status."""
        console.print("\n[cyan]🔍 Scanning for music files...[/cyan]")
        
        # If specific directories selected, scan only those
        if selected_dirs:
            all_files = []
            for dir_path in selected_dirs:
                console.print(f"[dim]Scanning: {os.path.basename(dir_path)}[/dim]")
                all_files.extend(list(self.scanner.scan_directory(dir_path)))
        else:
            all_files = list(self.scanner.scan_directory(path))
        
        if not all_files:
            console.print("[yellow]No music files found in the specified directory[/yellow]")
            return []
        
        console.print(f"[green]Found {len(all_files)} music files[/green]")
        
        files_to_process = []
        
        if missing_only:
            console.print("\n[bold cyan]Checking for missing tags...[/bold cyan]")
            console.print("[dim]Reading metadata for all files. This may take a moment...[/dim]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Checking tags...", total=len(all_files))
                
                for file_path in all_files:
                    try:
                        metadata = self.metadata_handler.extract_metadata(file_path)
                        if metadata:
                            genre = metadata.get('genre')
                            grouping = metadata.get('grouping')
                            
                            # If either is missing/empty, we need to process it
                            if not genre or not grouping:
                                files_to_process.append(file_path)
                    except Exception:
                        pass # Skip files we can't read
                        
                    progress.advance(task)
                    
            if not files_to_process:
                console.print("[green]✓ All files have Genre and Grouping tags![/green]")
                return []
                
            console.print(f"[green]Found {len(files_to_process)} files with missing tags[/green]")

        # Filter based on database status
        elif self.tagging_db and not self.processing_config.force_retag:
            skipped_reasons = {}
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Checking file status...", total=len(all_files))
                
                for file_path in all_files:
                    should_process, reason = self.tagging_db.should_process_file(
                        file_path, force=self.processing_config.force_retag
                    )
                    
                    if should_process:
                        files_to_process.append(file_path)
                    else:
                        skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
                        self.skipped_count += 1
                    
                    progress.advance(task)
            
            # Show skip summary
            if skipped_reasons:
                console.print(f"\n[cyan]Files skipped:[/cyan]")
                for reason, count in skipped_reasons.items():
                    console.print(f"  {reason}: {count}")
            
            console.print(f"\n[green]Files to process: {len(files_to_process)}[/green]")
        else:
            files_to_process = all_files
            
        # Apply session limit
        if len(files_to_process) > self.processing_config.session_limit:
            console.print(f"[yellow]Session limit: Processing first {self.processing_config.session_limit} files[/yellow]")
            files_to_process = files_to_process[:self.processing_config.session_limit]
        
        if not files_to_process:
            console.print("[green]✓ All files already processed![/green]")
            return []
        
        # Show preview
        if not self._show_file_preview(files_to_process):
            return []
        
        return files_to_process
    
    def _process_files_with_limit(self, music_files: List[str], dry_run: bool):
        """Process files with session limit and pacing."""
        batch_size = self.processing_config.api_batch_size
        delay = self.processing_config.delay_between_batches
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            main_task = progress.add_task("Processing files...", total=len(music_files))
            batch_task = progress.add_task("Current batch...", total=batch_size, visible=False)

            batch_num = 0
            for batch_start in range(0, len(music_files), batch_size):
                batch_num += 1
                batch_end = min(batch_start + batch_size, len(music_files))
                current_batch = music_files[batch_start:batch_end]

                self._process_single_batch(
                    current_batch, batch_start, batch_size, len(music_files),
                    progress, batch_task, main_task, dry_run
                )

                progress.update(batch_task, visible=False)
                
                # Pacing delay between batches
                if batch_end < len(music_files):
                    progress.update(main_task, description=f"[dim]Waiting {delay}s before next batch...[/dim]")
                    time.sleep(delay)
                    progress.update(main_task, description="Processing files...")
                
                # Update session in database
                if self.tagging_db and self.session_id:
                    self.tagging_db.update_session(
                        self.session_id,
                        self.processed_count,
                        self.updated_count,
                        self.error_count
                    )

    # _scan_directory replaced by _scan_and_filter_files above
    
    def _show_file_preview(self, music_files: List[str]) -> bool:
        """Show preview of files before processing (UX-1)"""
        
        console.print("\n[bold cyan]📋 Preview of Files to Process[/bold cyan]\n")
        
        preview_table = Table(show_header=True, box=ROUNDED, header_style="bold blue")
        preview_table.add_column("#", style="dim", width=4)
        preview_table.add_column("File", style="cyan", width=40)
        preview_table.add_column("Artist", style="green", width=25)
        preview_table.add_column("Current Genre", style="dim", width=20)
        
        # Preview first 10 files
        preview_count = min(10, len(music_files))
        for i, file_path in enumerate(music_files[:preview_count], 1):
            file_name = os.path.basename(file_path)
            
            # Extract metadata for preview
            try:
                metadata = self.metadata_handler.extract_metadata(file_path)
                artist = metadata.get('artist', 'Unknown') if metadata else 'Unknown'
                genre = metadata.get('genre', '[empty]') if metadata else '[empty]'
                
                # Truncate long values
                if len(file_name) > 37:
                    file_name = file_name[:34] + "..."
                if len(artist) > 22:
                    artist = artist[:19] + "..."
                if len(genre) > 17:
                    genre = genre[:14] + "..."
                
                preview_table.add_row(str(i), file_name, artist, genre)
            except Exception as e:
                preview_table.add_row(str(i), file_name, "[red]Error[/red]", "[red]Can't read[/red]")
        
        console.print(preview_table)
        
        if len(music_files) > preview_count:
            console.print(f"[dim]... and {len(music_files) - preview_count} more files[/dim]\n")
        
        console.print(f"[bold]Total: {len(music_files)} files will be processed[/bold]\n")
        
        return Confirm.ask("Proceed with processing?", default=True)

    # _process_files_in_batches replaced by _process_files_with_limit above

    def _process_single_batch(self, current_batch: List[str], batch_start: int,
                             batch_size: int, total_files: int,
                             progress, batch_task, main_task, dry_run: bool) -> None:
        """Process a single batch of files with database tracking."""
        batch_num = batch_start // batch_size + 1
        total_batches = (total_files - 1) // batch_size + 1
        console.print(f"\n[cyan]Processing batch {batch_num}/{total_batches} ({len(current_batch)} files)[/cyan]")

        progress.update(batch_task, completed=0, total=len(current_batch), visible=True)

        # Phase 1: Collect metadata and check cache
        file_artist_map, artists_to_research = self._collect_metadata(
            current_batch, progress, batch_task
        )

        # Phase 2: Research artists in single batch call
        country_results = self._research_artists_batch(
            artists_to_research, progress, batch_task
        )

        # Phase 3: Update files with results
        self._update_files_with_results(
            current_batch, file_artist_map, country_results,
            progress, batch_task, main_task, dry_run
        )

    def _parse_filename(self, filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Attempt to extract Artist and Title from filename.
        Expected format: "Artist - Title.mp3"
        """
        try:
            # Remove extension
            name = os.path.splitext(filename)[0]
            
            # Common separators: " - ", " – ", "_-_"
            separators = [" - ", " – ", "_-_"]
            
            for sep in separators:
                if sep in name:
                    parts = name.split(sep, 1)
                    if len(parts) == 2:
                        return parts[0].strip(), parts[1].strip()
            
            return None, None
        except Exception:
            return None, None

    def _collect_metadata(self, current_batch: List[str], progress, batch_task) -> Tuple[Dict, List]:
        """Collect metadata and check cache for batch"""
        file_artist_map = {}
        artists_to_research = []
        artists_needing_genre = set()  # Track artists that need genre research

        for i, file_path in enumerate(current_batch):
            file_name = os.path.basename(file_path)
            progress.update(batch_task, description=f"Reading: {file_name[:30]}...", advance=1)

            try:
                metadata = self.metadata_handler.extract_metadata(file_path)
                
                # Fallback: Parse filename if metadata is missing artist
                if not metadata or not metadata.get('artist'):
                    artist, title = self._parse_filename(file_name)
                    if artist and title:
                        if not metadata: metadata = {}
                        metadata['artist'] = artist
                        metadata['title'] = title
                        # Ensure other fields exist to prevent errors
                        if 'genre' not in metadata: metadata['genre'] = ''
                        if 'grouping' not in metadata: metadata['grouping'] = ''
                        console.print(f"[dim]Inferring from filename: {artist} - {title}[/dim]")
                    else:
                        console.print(f"[yellow]Skipping {file_name}: No artist information and filename parse failed[/yellow]")
                        if self.tagging_db:
                            self.tagging_db.mark_skipped(file_path, "No artist information")
                        self.processed_count += 1
                        continue

                artist = metadata['artist']
                title = metadata.get('title', 'Unknown')
                # Mark as processing in database
                if self.tagging_db:
                    self.tagging_db.mark_processing(file_path, artist, title, metadata)
                
                file_artist_map[file_path] = (artist, title, metadata)

                # Check cache
                cached_country = None
                if self.cache_manager:
                    cached_country = self.cache_manager.get_country(artist)

                # Check if file needs genre (cache doesn't store genre)
                needs_genre = not metadata.get('genre') or self.config.overwrite_existing_tags
                
                if not cached_country and artist not in [a[0] for a in artists_to_research]:
                    # No cache - need full research
                    artists_to_research.append((artist, title))
                elif cached_country:
                    self.cached_count += 1
                    # Has cached grouping but may need genre research
                    if needs_genre and artist not in artists_needing_genre:
                        artists_needing_genre.add(artist)
                        # Add to research list to get genre data
                        if artist not in [a[0] for a in artists_to_research]:
                            artists_to_research.append((artist, title))
                            console.print(f"[dim]Will research {artist} for genre data[/dim]")

            except Exception as e:
                console.print(f"[red]Error reading {file_name}: {e}[/red]")
                if self.tagging_db:
                    self.tagging_db.mark_failed(file_path, str(e))
                self.error_count += 1
                self.processed_count += 1
                self.failed_files.append((file_path, str(e)))

        return file_artist_map, artists_to_research

    def _research_artists_batch(self, artists_to_research: List[Tuple[str, str]],
                                progress, batch_task) -> Dict[str, Any]:
        """Research all artists in single batch call"""
        if not artists_to_research:
            return {}

        progress.update(batch_task, description=f"Web searching {len(artists_to_research)} artists...")
        console.print(f"[blue]🔍 Single batch call researching ALL {len(artists_to_research)} artists...[/blue]")
        console.print("[dim]One comprehensive research call - may take 3-8 minutes...[/dim]")
        console.print("[yellow]💡 If this hangs, ensure Claude CLI is installed and working (try 'claude --version')[/yellow]")

        try:
            country_results = self.ai_researcher.research_artists_batch(artists_to_research)
            if country_results:
                console.print(f"[green]✓ Single call completed! Got results for {len(country_results)} artists[/green]")
            else:
                console.print("[yellow]⚠ No results returned. Check Claude CLI configuration.[/yellow]")
                self.error_count += len(artists_to_research)
            return country_results
        except KeyboardInterrupt:
            console.print("[red]\n❌ Processing interrupted by user[/red]")
            raise
        except Exception as e:
            console.print(f"[red]Single batch call failed: {e}[/red]")
            console.print("[yellow]💡 Tip: Check that 'claude' command works in your terminal[/yellow]")
            self.error_count += len(artists_to_research)
            return {}

    def _update_files_with_results(self, current_batch: List[str], file_artist_map: Dict,
                                   country_results: Dict, progress, batch_task,
                                   main_task, dry_run: bool) -> None:
        """Update files with research results"""
        progress.update(batch_task, description="Updating files...", completed=0, total=len(current_batch))

        for file_path in current_batch:
            if file_path not in file_artist_map:
                progress.advance(batch_task)
                progress.advance(main_task)
                continue

            artist, title, metadata = file_artist_map[file_path]
            self._update_single_file(file_path, artist, metadata, country_results, dry_run)

            self.processed_count += 1
            progress.advance(batch_task)
            progress.advance(main_task)

    def _update_single_file(self, file_path: str, artist: str, metadata: Dict,
                           country_results: Dict, dry_run: bool) -> None:
        """Update a single file with metadata"""
        file_name = os.path.basename(file_path)

        # Get info from cache or batch results
        cached_grouping = None
        if self.cache_manager:
            cached_grouping = self.cache_manager.get_country(artist)

        artist_info = country_results.get(artist)

        if not cached_grouping and not artist_info:
            console.print(f"[yellow]No information found for {artist}[/yellow]")
            return

        # Extract and clean metadata fields
        genre_info, grouping_info, year_info = self._extract_metadata_fields(
            cached_grouping, artist_info
        )

        if self.verbose:
            console.print(f"[dim]Debug {artist}: genre={genre_info}, grouping={grouping_info}, year={year_info}[/dim]")

        if dry_run:
            self._display_dry_run_update(artist, genre_info, grouping_info, year_info, metadata)
        else:
            self._apply_metadata_update(file_path, artist, metadata,
                                       genre_info, grouping_info, year_info)

    def _extract_metadata_fields(self, cached_grouping: Optional[str],
                                artist_info: Optional[Dict]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract and clean genre, grouping, and year information"""
        genre_info = None
        grouping_info = None
        year_info = None
        
        # Get grouping from cache if available
        if cached_grouping:
            grouping_info = cached_grouping
        
        # Get data from artist_info (new AI research results)
        if artist_info:
            # Get genre from AI results (not stored in cache)
            if not genre_info:
                genre_info = self._clean_field(artist_info.get('genre'))
            # Get grouping from AI results if not cached
            if not grouping_info:
                grouping_info = self._clean_field(artist_info.get('grouping'))
            # Get year from AI results (not stored in cache)
            if not year_info:
                year_info = self._clean_year_field(artist_info.get('year'))

        return genre_info, grouping_info, year_info

    def _clean_field(self, field_value: Optional[str]) -> Optional[str]:
        """Clean markdown artifacts and validate field value"""
        if not field_value:
            return None

        cleaned = re.sub(r'^\*\*|\*\*$', '', field_value).strip()

        # Filter out "Unknown" values or groupings like "Unknown | Unknown | Unknown"
        if cleaned.lower() == 'unknown':
            return None
        if 'unknown' in cleaned.lower() and '|' in cleaned:
            # Check if all parts are "Unknown"
            parts = [p.strip().lower() for p in cleaned.split('|')]
            if all(p == 'unknown' for p in parts):
                return None

        return cleaned

    def _clean_year_field(self, year_value: Optional[str]) -> Optional[str]:
        """Clean and validate year field"""
        if not year_value:
            return None

        cleaned = re.sub(r'^\*\*|\*\*$', '', year_value).strip()

        if cleaned.lower() == 'unknown' or not cleaned.isdigit():
            return None

        return cleaned

    def _display_dry_run_update(self, artist: str, genre_info: Optional[str],
                               grouping_info: Optional[str], year_info: Optional[str],
                               metadata: Dict) -> None:
        """Display what would be updated in dry run mode (UX-2: Enhanced table view)"""
        
        # Create before/after comparison table
        table = Table(
            title=f"[bold cyan]Preview Changes for: {artist}[/bold cyan]",
            show_header=True,
            box=ROUNDED,
            header_style="bold blue",
            show_lines=True
        )
        table.add_column("Field", style="cyan bold", width=12)
        table.add_column("Before", style="dim", width=35)
        table.add_column("After", style="green bold", width=35)
        table.add_column("Status", style="yellow", width=8)
        
        has_changes = False
        
        # GENRE comparison
        if genre_info:
            old_genre = metadata.get('genre', '[empty]')
            if old_genre != genre_info:
                change_icon = "✓ NEW" if old_genre == '[empty]' else "→ CHG"
                table.add_row("Genre", old_genre, genre_info, change_icon)
                has_changes = True
        
        # GROUPING comparison
        if grouping_info:
            old_grouping = metadata.get('grouping', '[empty]')
            if old_grouping != grouping_info:
                change_icon = "✓ NEW" if old_grouping == '[empty]' else "→ CHG"
                table.add_row("Grouping", old_grouping, grouping_info, change_icon)
                has_changes = True
        
        # YEAR comparison
        if year_info:
            old_year = str(metadata.get('year', '[empty]'))
            if old_year != year_info:
                change_icon = "✓ NEW" if old_year == '[empty]' else "→ CHG"
                table.add_row("Year", old_year, year_info, change_icon)
                has_changes = True
                
        if has_changes:
            console.print(table)
        else:
            console.print(f"[dim]No changes needed for {artist}[/dim]")

    def _apply_metadata_update(self, file_path: str, artist: str, metadata: Dict,
                              genre_info: Optional[str], grouping_info: Optional[str],
                              year_info: Optional[str]) -> None:
        """Apply metadata updates to file"""
        updates = {}
        
        # Always overwrite with new data when available
        # (smart overwrite - only updates if we have valid new data)
        
        if genre_info:
            # Always update genre if we have new valid data
            updates['genre'] = genre_info
        
        if grouping_info:
            # Always update grouping if we have new valid data
            updates['grouping'] = grouping_info
                
        if year_info:
            # Always update year if we have new valid data
            updates['year'] = year_info
        
        # Apply updates if any
        if updates:
            try:
                self.metadata_handler.update_metadata(file_path, updates)
                self.updated_count += 1
                
                # Mark completed in database
                if self.tagging_db:
                    self.tagging_db.mark_completed(
                        file_path,
                        genre=updates.get('genre'),
                        grouping=updates.get('grouping'),
                        year=updates.get('year'),
                        artist=artist
                    )
                
                # Show concise success message
                changes = []
                if 'genre' in updates: changes.append("Genre")
                if 'grouping' in updates: changes.append("Grouping")
                if 'year' in updates: changes.append("Year")
                
                console.print(f"[green]✓ Updated {artist}: {', '.join(changes)}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to update {os.path.basename(file_path)}: {e}[/red]")
                if self.tagging_db:
                    self.tagging_db.mark_failed(file_path, str(e))
                self.error_count += 1

    def _display_final_statistics(self, dry_run: bool) -> None:
        """Display final processing statistics with database info."""
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]         Processing Complete!          [/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]")
        
        # Create summary table
        table = Table(show_header=True, box=ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")
        
        table.add_row("Processed", str(self.processed_count))
        table.add_row("Updated", str(self.updated_count))
        table.add_row("Skipped", str(self.skipped_count))
        table.add_row("Cached (artist)", str(self.cached_count))
        table.add_row("Errors", str(self.error_count))
        
        console.print(table)
        
        if dry_run:
            console.print("\n[yellow]This was a dry run. No files were modified.[/yellow]")
        
        # Show database stats
        if self.tagging_db:
            stats = self.tagging_db.get_statistics()
            remaining = stats['pending']
            if remaining > 0:
                console.print(f"\n[cyan]Remaining to process: {remaining} files[/cyan]")
                console.print("[dim]Run again to continue processing.[/dim]")
            else:
                console.print("\n[bold green]✓ All files in library have been processed![/bold green]")

    def _get_results_summary(self, dry_run: bool) -> Dict[str, Any]:
        """Get summary of processing results"""
        return {
            'processed': self.processed_count,
            'updated': self.updated_count,
            'cached': self.cached_count,
            'errors': self.error_count,
            'dry_run': dry_run
        }

    def _handle_failed_files(self) -> None:
        """Handle files that failed processing"""
        console.print(f"\n[red]Failed Files ({len(self.failed_files)}):[/red]")
        for file_path, error in self.failed_files:
            console.print(f"  {os.path.basename(file_path)}: {error}")
            
        if Confirm.ask("Save failed files list to log?", default=True):
            try:
                log_path = os.path.join(self.config.config_dir, 'logs', f'failed_files_{int(time.time())}.log')
                with open(log_path, 'w') as f:
                    for file_path, error in self.failed_files:
                        f.write(f"{file_path}\t{error}\n")
                console.print(f"[green]Saved to {log_path}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to save log: {e}[/red]")

    def _handle_interruption(self, total_files: int) -> None:
        """
        Handle user interruption with improved state tracking.

        Bug #12 fix: Better error recovery with progress reporting.
        """
        console.print("\n[bold yellow]⚠️  Processing interrupted by user[/bold yellow]")
        console.print(f"Processed {self.processed_count}/{total_files} files before stopping")

        # Show detailed statistics
        if self.processed_count > 0:
            console.print(f"\n[cyan]Progress:[/cyan]")
            console.print(f"  ✓ Successfully tagged: {self.processed_count - self.error_count}")
            console.print(f"  ✗ Errors: {self.error_count}")
            console.print(f"  ⏭️  Skipped: {total_files - self.processed_count}")

        console.print(f"\n[yellow]💡 Progress has been saved. Re-run to continue from where you left off.[/yellow]")
