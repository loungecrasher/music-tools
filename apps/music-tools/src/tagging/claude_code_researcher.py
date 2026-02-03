"""
Claude Code Local Researcher Module

Uses local Claude Code installation with Max plan instead of separate API keys.
Integrates with the `claude` command to leverage existing subscription.
"""

import subprocess
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import shutil

# Import core services
try:
    from .core.country_service import country_service
    from .core.error_handler import with_error_handling, APIError
    from .core.validation_service import validate_artist_name, validate_confidence_score
    from .brave_search import BraveSearchClient
except ImportError:
    from src.tagging.core.country_service import country_service
    from src.tagging.core.error_handler import with_error_handling, APIError
    from src.tagging.core.validation_service import validate_artist_name, validate_confidence_score
    from src.tagging.brave_search import BraveSearchClient

logger = logging.getLogger(__name__)


# Custom Exceptions
class ClaudeCodeError(Exception):
    """Base exception for Claude Code operations."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class CommandNotFoundError(ClaudeCodeError):
    """Exception when claude command is not found."""
    pass


class ValidationError(ClaudeCodeError):
    """Exception for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, error_code="VALIDATION_ERROR")
        self.field = field


@dataclass
class CountryResearchResult:
    """Result of country research for an artist."""
    country: str
    confidence: float = 1.0
    source: str = "claude_code"
    reasoning: str = ""
    cached: bool = False


# Country validation now handled by centralized CountryService
# VALID_COUNTRIES and COUNTRY_ALIASES moved to core.country_service


class ClaudeCodeResearcher:
    """
    Researcher that uses local Claude Code installation with Max plan.
    """
    
    def __init__(self, max_retries: int = 1, timeout: int = 600, cache_manager=None, model: str = None,
                 enable_websearch: bool = False, brave_api_key: Optional[str] = None,
                 brave_delay: float = 1.5, brave_max_retries: int = 3):
        """
        Initialize Claude Code researcher.

        Args:
            max_retries: Maximum number of retry attempts for failed requests
            timeout: Timeout in seconds for claude command execution
            cache_manager: Optional cache manager for storing results
            model: Optional model to use (e.g., 'sonnet', 'opus', 'haiku')
            enable_websearch: Enable WebSearch tool (may cause hanging issues)
            brave_api_key: Brave Search API key for enhanced web searches (optional)
            brave_delay: Delay between Brave API requests (seconds, default: 1.5)
            brave_max_retries: Max retries for Brave rate limits (default: 3)
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self.cache_manager = cache_manager
        self.model = model
        self.enable_websearch = enable_websearch
        
        # Initialize Brave client with rate limiting
        if brave_api_key:
            self.brave_client = BraveSearchClient(
                api_key=brave_api_key,
                delay_between_requests=brave_delay,  # Stagger requests
                max_retries=brave_max_retries,       # Retry on 429 errors
                initial_backoff=2.0,                 # 2s initial backoff
                backoff_multiplier=2.0              # Exponential backoff
            )
        else:
            self.brave_client = None
        self.statistics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'average_response_time': 0,
            'brave_searches': 0
        }

        # Check if claude command is available
        if not self._check_claude_available():
            raise CommandNotFoundError(
                "Claude Code command not found. Please ensure Claude Code is installed and in PATH."
            )

        # Log Brave Search status
        if self.brave_client:
            logger.info("✓ Brave Search integration enabled - using direct web searches")
        elif self.enable_websearch:
            logger.info("Using Claude WebSearch (Brave disabled)")
        else:
            logger.info("Using Claude training data only (no web search)")

        # Detect current model
        self.current_model = self._detect_current_model()

    def _perform_brave_searches(self, artists_titles: List[tuple]) -> str:
        """
        Perform Brave searches for a batch of artists and format results for prompt.

        Args:
            artists_titles: List of (artist, title) tuples

        Returns:
            Formatted search results string for inclusion in prompt
        """
        if not self.brave_client:
            return ""

        search_results = []
        search_results.append("SEARCH RESULTS FROM WEB:")
        search_results.append("=" * 80)

        for i, (artist, title) in enumerate(artists_titles, 1):
            search_results.append(f"\n{i}. {title} - {artist}")
            search_results.append("-" * 80)

            # Search for artist + song
            results = self.brave_client.search_artist(artist, title)

            if results:
                for j, result in enumerate(results[:3], 1):  # Top 3 results
                    search_results.append(f"   [{j}] {result.title}")
                    search_results.append(f"       {result.description}")
                    search_results.append(f"       {result.url}")
                    search_results.append("")
            else:
                search_results.append("   [No web results found]")
                search_results.append("")

        search_results.append("=" * 80)
        return "\n".join(search_results)

    def _brave_search_fallback(self, artists_titles: List[tuple]) -> Dict[str, Dict[str, str]]:
        """
        Use Brave Search as fallback for artists that Claude couldn't find data for.

        Args:
            artists_titles: List of (artist, title) tuples for failed lookups

        Returns:
            Dictionary mapping artist names to their data
        """
        if not self.brave_client:
            return {}

        logger.info(f"Brave fallback: Searching for {len(artists_titles)} artists")

        # Perform Brave searches and format results
        search_results_section = self._perform_brave_searches(artists_titles)
        self.statistics['brave_searches'] += len(artists_titles)

        # Build songs list
        songs_list = []
        for i, (artist, title) in enumerate(artists_titles, 1):
            if title and title.strip():
                songs_list.append(f"{i}. {title} - {artist}")
            else:
                songs_list.append(f"{i}. Unknown - {artist}")

        # Create a simplified prompt using Brave results
        prompt = f"""Research these songs using the web search results provided below.

SONGS TO RESEARCH ({len(artists_titles)} total):
{chr(10).join(songs_list)}

RESEARCH APPROACH:
- Analyze the search results provided below for each song
- Use the song title to identify the correct artist (handles name ambiguity)
- Determine the artist's country of origin
- Find the song's original release year (earliest: single, EP, or album)
- If you cannot find reliable information, use "Unknown"

{search_results_section}

REQUIRED OUTPUT FORMAT (respond for ALL {len(artists_titles)} songs in numbered order):
1. GENRE: [Cultural/Main] | [Musical Style] | [Regional] | [Era]
   GROUPING: [Region] | [Country] | [Language Family]
   YEAR: [Song Release Year]

2. GENRE: [Cultural/Main] | [Musical Style] | [Regional] | [Era]
   GROUPING: [Region] | [Country] | [Language Family]
   YEAR: [Song Release Year]
...

GENRE FIELD STRUCTURE (4 parts, prioritize cultural identity):
Position 1 (Cultural/Main): Rock, Pop, Electronic, Latin, World, Jazz, Hip-Hop, Classical, Folk, R&B, Country, Blues, Reggae, Punk, Metal
Position 2 (Musical Style): Pop Rock, Salsa, Cumbia, Dance, Alternative, etc.
Position 3 (Regional): Spanish, Mexican, Celtic, Jamaican, Greek, etc.
Position 4 (Era/Movement): Contemporary, Traditional, Classic, Modern, etc.

CULTURAL PRIORITY RULE:
- Spanish/Portuguese music → Start with "Latin"
- African/Celtic/Indigenous → Start with "World"
- Caribbean reggae/ska → Start with "Reggae"
- Geographic terms (Mexican, Greek, Caribbean) → NEVER position 1, always position 3

EXAMPLES:
1. GENRE: Latin | Rock | Mexican | Rock en Español
   GROUPING: North America | Mexico | Romance
   YEAR: 1965

2. GENRE: World | Traditional | Celtic | Irish Folk
   GROUPING: Europe | Ireland | Celtic
   YEAR: 1972

GROUPING FIELD STRUCTURE (3 parts):
Position 1 (Region): Europe, Asia, North America, South America, Africa, Oceania, Middle East, Caribbean
Position 2 (Country): Specific country name
Position 3 (Language Family): Romance, Germanic, Slavic, Celtic, Arabic, Asian, etc.

Be concise and accurate. Respond ONLY with the numbered list in the exact format shown above."""

        try:
            # Call Claude with Brave search results (no WebSearch tool needed)
            # Temporarily disable WebSearch for Brave fallback since we have the results
            original_websearch = self.enable_websearch
            self.enable_websearch = False

            result = self._execute_claude_command(prompt)

            # Restore WebSearch setting
            self.enable_websearch = original_websearch

            if result and result.strip():
                # Parse the response using the same logic as _research_single_batch
                parsed_results = self._parse_batch_response_internal(result, artists_titles)
                logger.info(f"Brave fallback: Parsed {len(parsed_results)} results")
                return parsed_results
            else:
                logger.warning("Brave fallback: Empty response from Claude")
                return {}

        except Exception as e:
            logger.error(f"Brave fallback error: {e}")
            # Restore WebSearch setting on error
            self.enable_websearch = original_websearch
            return {}

    def _parse_batch_response_internal(self, response: str, artists_titles: List[tuple]) -> Dict[str, Dict[str, str]]:
        """
        Parse batch response from Claude into a dictionary of artist data.
        
        Args:
            response: Raw response string from Claude
            artists_titles: List of (artist, title) tuples for mapping results
            
        Returns:
            Dictionary mapping artist names to their data
        """
        results = {}
        lines = response.strip().split('\n')
        
        current_artist_idx = -1
        current_artist_data = {}
        
        for line in lines:
            line = line.strip()
            
            # Check for numbered entries (handle both regular and bold markdown)
            numbered_match = re.match(r'^(\d+)\.\s*(?:\*\*)?GENRE(?:\*\*)?\s*:\s*(.+)', line)
            if numbered_match:
                # Save previous artist if exists
                if current_artist_idx >= 0 and current_artist_data and current_artist_idx < len(artists_titles):
                    artist_name = artists_titles[current_artist_idx][0]
                    results[artist_name] = current_artist_data
                
                # Start new artist
                current_artist_idx = int(numbered_match.group(1)) - 1
                genre_content = numbered_match.group(2)
                genre_content = re.sub(r'^\*\*|\*\*$', '', genre_content).strip()
                
                if '|' not in genre_content:
                    current_artist_data = {'genre': f"{genre_content} | Unknown | Unknown | Unknown"}
                else:
                    current_artist_data = {'genre': genre_content}
            
            elif line.startswith('GENRE:') or line.startswith('**GENRE**:') or '**GENRE**:' in line:
                genre_content = re.sub(r'.*(?:\*\*)?GENRE(?:\*\*)?\s*:\s*', '', line).strip()
                genre_content = re.sub(r'^\*\*|\*\*$', '', genre_content).strip()
                current_artist_data['genre'] = genre_content
            
            elif line.startswith('GROUPING:') or line.startswith('**GROUPING**:') or '**GROUPING**:' in line:
                grouping_line = re.sub(r'.*(?:\*\*)?GROUPING(?:\*\*)?\s*:\s*', '', line).strip()
                grouping_line = re.sub(r'^\*\*|\*\*$', '', grouping_line).strip()
                
                if '|' in grouping_line:
                    parts = [part.strip() for part in grouping_line.split('|')]
                    if len(parts) >= 3:
                        region, country, language = parts[0], parts[1], parts[2]
                        normalized_country = country_service.normalize_country_name(country)
                        if normalized_country:
                            current_artist_data['grouping'] = f"{region} | {normalized_country.title()} | {language}"
                        else:
                            current_artist_data['grouping'] = f"{region} | {country} | {language}"
                    else:
                        current_artist_data['grouping'] = grouping_line
                else:
                    normalized_country = country_service.normalize_country_name(grouping_line)
                    if normalized_country:
                        current_artist_data['grouping'] = f"Unknown | {normalized_country.title()} | Unknown"
                    else:
                        current_artist_data['grouping'] = f"Unknown | {grouping_line} | Unknown"
            
            elif line.startswith('YEAR:') or line.startswith('**YEAR**:') or '**YEAR**:' in line:
                year_line = re.sub(r'.*(?:\*\*)?YEAR(?:\*\*)?\s*:\s*', '', line).strip()
                year_line = re.sub(r'^\*\*|\*\*$', '', year_line).strip()
                
                year_match = re.search(r'\b(19\d{2}|20\d{2})\b', year_line)
                if year_match:
                    current_artist_data['year'] = year_match.group(1)
                else:
                    current_artist_data['year'] = year_line
        
        # Save last artist
        if current_artist_idx >= 0 and current_artist_data and current_artist_idx < len(artists_titles):
            artist_name = artists_titles[current_artist_idx][0]
            results[artist_name] = current_artist_data
        
        return results

    def _check_claude_available(self) -> bool:
        """Check if claude command is available in PATH."""
        claude_path = shutil.which("claude")
        if claude_path:
            logger.info(f"Claude CLI found at: {claude_path}")
            return True
        else:
            logger.warning("Claude CLI not found in PATH")
            logger.warning("Please ensure Claude Code is installed and in your PATH")
            logger.warning("Visit https://claude.ai/code for installation instructions")
            return False
    
    def _detect_current_model(self) -> str:
        """Detect which Claude model is currently being used."""
        try:
            cmd = ["claude", "--print", "What model are you? Just the model name and ID."]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                response = result.stdout.strip()
                # Extract model info from response
                if "claude-sonnet-4" in response.lower():
                    return "Claude Sonnet 4 (claude-sonnet-4-20250514)"
                elif "claude-opus-4" in response.lower():
                    return "Claude Opus 4"  
                elif "claude-3.5-sonnet" in response.lower():
                    return "Claude 3.5 Sonnet"
                elif "claude-3.5-haiku" in response.lower():
                    return "Claude 3.5 Haiku"
                else:
                    return response[:100]  # Return first 100 chars if can't parse
            else:
                return "Unknown (detection failed)"
        except Exception:
            return "Unknown"
    
    def _execute_claude_command(self, prompt: str) -> str:
        """
        Execute claude command with the given prompt.

        Args:
            prompt: The prompt to send to Claude

        Returns:
            Claude's response as string

        Raises:
            ClaudeCodeError: If command execution fails
        """
        try:
            # Log the start of execution
            logger.info(f"Starting Claude command execution with timeout={self.timeout}s")

            # Construct the claude command with WebSearch enabled
            cmd = ["claude"]

            # Add model if specified
            if self.model:
                cmd.extend(["--model", self.model])

            # Only enable WebSearch if explicitly requested (can cause hanging)
            if self.enable_websearch:
                cmd.extend(["--allowed-tools", "WebSearch"])
                logger.info("WebSearch enabled - may take longer")
            else:
                logger.debug("WebSearch disabled - using Claude's training data only")

            # Add --print flag for non-interactive use
            cmd.append("--print")

            # Efficient web search prompt - handle both individual and batch prompts
            try:
                if 'musical artist: ' in prompt:
                    artist_name = prompt.split('musical artist: ')[1].split('\n')[0].strip()
                    enhanced_prompt = f"""Research the musical artist "{artist_name}":

If you don't know this artist well from training data, use WebSearch to find accurate information about their genre and country of origin.

{prompt}

Use web search for accurate results, especially for regional or lesser-known artists."""
                else:
                    # For batch prompts, be more selective about web search
                    enhanced_prompt = f"""For each artist: If well-known, use training data. If unknown/uncertain, research with WebSearch.

{prompt}

Guidelines:
- Major international artists: Use existing knowledge
- Regional/local artists: Use WebSearch for accuracy
- When unsure: Research rather than guess"""
            except IndexError:
                # Fallback if parsing fails
                enhanced_prompt = f"""Use WebSearch to research:

{prompt}

Search for accurate information about each artist."""
            
            # Don't append prompt to cmd - will pass via stdin
            # cmd.append(enhanced_prompt)

            # Log the command being executed (without the full prompt)
            logger.debug(f"Executing command: {' '.join(cmd)}... with prompt length: {len(enhanced_prompt)} chars")

            # Execute command with timeout - pass prompt via stdin for reliability
            start_time = time.time()
            result = subprocess.run(
                cmd,
                input=enhanced_prompt,  # Pass prompt via stdin
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            elapsed_time = time.time() - start_time
            logger.info(f"Claude command completed in {elapsed_time:.2f} seconds")

            # Always log stderr to diagnose issues
            if result.stderr:
                logger.warning(f"Stderr output: {result.stderr.strip()}")

            if result.returncode != 0:
                logger.error(f"Claude command failed with return code {result.returncode}")
                logger.error(f"Stderr: {result.stderr.strip()}")
                raise ClaudeCodeError(
                    f"Claude command failed: {result.stderr.strip()}"
                )

            response = result.stdout.strip()
            logger.debug(f"Received response of length: {len(response)} chars")

            # If response is empty, log full debug info
            if not response:
                logger.error("EMPTY RESPONSE FROM CLAUDE!")
                logger.error(f"Return code: {result.returncode}")
                logger.error(f"Stdout: '{result.stdout}'")
                logger.error(f"Stderr: '{result.stderr}'")
                logger.error(f"Command: {' '.join(cmd)}")

            return response

        except subprocess.TimeoutExpired:
            logger.error(f"Claude command timed out after {self.timeout} seconds")
            raise ClaudeCodeError(f"Claude command timed out after {self.timeout} seconds")
        except subprocess.CalledProcessError as e:
            logger.error(f"Claude command process error: {e}")
            raise ClaudeCodeError(f"Claude command error: {e}")
        except FileNotFoundError:
            logger.error("Claude CLI command not found. Please ensure Claude Code is installed and available in PATH")
            raise ClaudeCodeError("Claude CLI command not found. Please install Claude Code or check your PATH")
        except Exception as e:
            logger.error(f"Unexpected error executing claude command: {e}")
            raise ClaudeCodeError(f"Unexpected error executing claude command: {e}")
    
    def _build_country_research_prompt(self, artist: str, title: str = "") -> str:
        """
        Build an optimized prompt for enhanced country, region, and language research.

        Args:
            artist: Artist name
            title: Optional song title for more accurate research

        Returns:
            Formatted prompt string
        """
        prompt = f"""Use WebSearch to research this song and provide accurate genre, location, and release year.

Artist: {artist}"""

        if title:
            prompt += f"\nSong: {title}"

        prompt += """

RESEARCH APPROACH:
- Look up both the artist AND the specific song
- Determine the artist's country of origin
- Find the song's original release year (earliest: single, EP, or album)
- If you cannot find reliable information, use "Unknown"

REQUIRED OUTPUT (exactly 3 lines):
GENRE: [Cultural/Main] | [Musical Style] | [Regional] | [Era]
GROUPING: [Region] | [Country] | [Language Family]
YEAR: [Song Release Year]

GENRE STRUCTURE (prioritize cultural identity):
Position 1: Rock, Pop, Electronic, Latin, World, Jazz, Hip-Hop, Classical, Folk, R&B, Country, Blues, Reggae, Punk, Metal
Position 2: Musical style (Pop Rock, Salsa, Cumbia, Dance, etc.)
Position 3: Regional (Spanish, Mexican, Celtic, Jamaican, Greek, etc.)
Position 4: Era (Contemporary, Traditional, Classic, Modern, etc.)

CULTURAL PRIORITY:
- Spanish/Portuguese music → Start with "Latin"
- African/Celtic/Indigenous → Start with "World"
- Caribbean reggae/ska → Start with "Reggae"
- Geographic terms → NEVER position 1, always position 3

EXAMPLES:
GENRE: Latin | Rock | Mexican | Rock en Español
GROUPING: North America | Mexico | Romance
YEAR: 1965

GENRE: Rock | Pop Rock | British Invasion | Classic
GROUPING: Western Europe | United Kingdom | Germanic
YEAR: 1968

GENRE: Electronic | Cumbia Bass | Colombian | Contemporary
GROUPING: South America | Colombia | Romance
YEAR: 2016

Response:"""

        return prompt
    
    def _parse_triple_response(self, response: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse triple response with GENRE, GROUPING, and YEAR lines.
        
        Args:
            response: Raw response from Claude with GENRE:, GROUPING:, and YEAR: lines
            
        Returns:
            Tuple of (genre_info, grouping_info, year_info) or (None, None, None) if invalid
        """
        if not response:
            return None, None, None
        
        # Clean the response
        response = response.strip()
        lines = response.split('\n')
        
        genre_info = None
        grouping_info = None
        year_info = None
        
        for line in lines:
            line = line.strip()
            
            # Handle both regular and markdown bold formatting
            if line.startswith('GENRE:') or line.startswith('**GENRE**:'):
                genre_info = re.sub(r'^\*\*GENRE\*\*:\s*|^GENRE:\s*', '', line).strip()
            elif line.startswith('GROUPING:') or line.startswith('**GROUPING**:'):
                grouping_line = re.sub(r'^\*\*GROUPING\*\*:\s*|^GROUPING:\s*', '', line).strip()
                
                # Parse and ENFORCE pipe format: Region | Country | Language
                if '|' in grouping_line:
                    parts = [part.strip() for part in grouping_line.split('|')]
                    
                    if len(parts) >= 3:
                        region, country, language = parts[0], parts[1], parts[2]
                        
                        # Validate country using centralized service
                        normalized_country = country_service.normalize_country_name(country)
                        if normalized_country:
                            # ENFORCE pipes in output
                            grouping_info = f"{region} | {normalized_country.title()} | {language}"
                        else:
                            # Still enforce pipes even if country validation fails
                            grouping_info = f"{region} | {country} | {language}"
                    else:
                        # Incomplete format - add pipes to enforce structure
                        logger.warning(f"Incomplete grouping format, attempting to fix: {grouping_line}")
                        if len(parts) == 2:
                            grouping_info = f"{parts[0]} | {parts[1]} | Unknown"
                        elif len(parts) == 1:
                            grouping_info = f"Unknown | {parts[0]} | Unknown"
                        else:
                            grouping_info = f"Unknown | {grouping_line} | Unknown"
                else:
                    # No pipes found - assume it's just a country name and add structure
                    logger.warning(f"No pipes in grouping, treating as country name: {grouping_line}")
                    normalized_country = country_service.normalize_country_name(grouping_line)
                    if normalized_country:
                        grouping_info = f"Unknown | {normalized_country.title()} | Unknown"
                    else:
                        grouping_info = f"Unknown | {grouping_line} | Unknown"
            elif line.startswith('YEAR:') or line.startswith('**YEAR**:'):
                year_line = re.sub(r'^\*\*YEAR\*\*:\s*|^YEAR:\s*', '', line).strip()
                
                # Validate year format (should be 4-digit year)
                import re
                year_match = re.search(r'\b(19\d{2}|20\d{2})\b', year_line)
                if year_match:
                    year_info = year_match.group(1)
                else:
                    logger.warning(f"Invalid year format: {year_line}")
                    year_info = year_line  # Use as-is if can't parse
        
        return genre_info, grouping_info, year_info
    
    def research_artists_batch(self, artists_titles: List[tuple], use_parallel: bool = True, max_retries: int = 2) -> Dict[str, Dict[str, str]]:
        """
        Research multiple artists with automatic retry logic and optional parallel processing.

        Args:
            artists_titles: List of (artist, title) tuples
            use_parallel: If True, process batches in parallel (faster but uses more resources)
            max_retries: Number of retry attempts for failed batches (default: 2)

        Returns:
            Dictionary mapping artist names to {'genre': genre_info, 'grouping': grouping_info}
        """
        if not artists_titles:
            return {}

        logger.info(f"Starting batch research for {len(artists_titles)} artists (parallel={use_parallel}, retries={max_retries})")

        # Split into smaller sub-batches (15 artists each) to avoid token limits
        sub_batch_size = 15
        sub_batches = []
        for i in range(0, len(artists_titles), sub_batch_size):
            sub_batches.append(artists_titles[i:i + sub_batch_size])

        logger.info(f"Split into {len(sub_batches)} sub-batches of ~{sub_batch_size} artists each")

        all_results = {}
        failed_batches = []

        # Process each sub-batch with retry logic
        for batch_idx, sub_batch in enumerate(sub_batches, 1):
            logger.info(f"Processing sub-batch {batch_idx}/{len(sub_batches)} ({len(sub_batch)} artists)")

            success = False
            for retry in range(max_retries + 1):
                try:
                    if retry > 0:
                        logger.info(f"Retry attempt {retry}/{max_retries} for sub-batch {batch_idx}")

                    result = self._research_single_batch(sub_batch)

                    # Check if we got valid results (not empty response)
                    if result:
                        all_results.update(result)
                        logger.info(f"✓ Sub-batch {batch_idx} succeeded: {len(result)} results")
                        success = True
                        break
                    else:
                        logger.warning(f"Sub-batch {batch_idx} returned empty results (attempt {retry + 1})")
                        if retry < max_retries:
                            time.sleep(2)  # Brief delay before retry

                except Exception as e:
                    logger.error(f"Sub-batch {batch_idx} error (attempt {retry + 1}): {e}")
                    if retry < max_retries:
                        time.sleep(2)
                    else:
                        logger.error(f"Sub-batch {batch_idx} failed after {max_retries + 1} attempts")

            if not success:
                failed_batches.append((batch_idx, sub_batch))

        # Brave Search fallback for artists with missing/unknown data
        if self.brave_client:
            unknown_artists = []
            
            # First: Find artists that are COMPLETELY MISSING from results
            for artist, title in artists_titles:
                if artist not in all_results:
                    unknown_artists.append((artist, title))
                    logger.debug(f"Artist missing from results: {artist}")
            
            # Second: Find artists with Unknown/invalid grouping
            for artist_name, data in all_results.items():
                grouping = data.get('grouping', '')
                # Check if country is unknown or missing
                if 'Unknown' in grouping or not grouping or '|' not in grouping:
                    # Find the original (artist, title) tuple
                    for artist, title in artists_titles:
                        if artist == artist_name and (artist, title) not in unknown_artists:
                            unknown_artists.append((artist, title))
                            break

            if unknown_artists:
                logger.info(f"🔍 Brave Search fallback for {len(unknown_artists)} artists (missing or unknown data)")
                brave_results = self._brave_search_fallback(unknown_artists)

                # Update results with Brave fallback data
                for artist_name, brave_data in brave_results.items():
                    if artist_name in all_results:
                        # Only update if Brave found better data
                        if brave_data.get('grouping') and 'Unknown' not in brave_data['grouping']:
                            all_results[artist_name].update(brave_data)
                            logger.info(f"✓ Brave fallback improved data for: {artist_name}")
                    else:
                        # Artist was completely missing - add new data
                        if brave_data.get('grouping') and 'Unknown' not in brave_data.get('grouping', ''):
                            all_results[artist_name] = brave_data
                            logger.info(f"✓ Brave fallback found NEW data for: {artist_name}")
                
                # Check if any Brave queries failed and retry them at end of run
                failed_queries = self.brave_client.get_failed_queries()
                if failed_queries:
                    logger.warning(f"⚠️ {len(failed_queries)} Brave searches failed - retrying at end of run...")
                    
                    # Retry failed queries with longer delays
                    retry_search_results = self.brave_client.retry_failed_queries(max_to_retry=len(failed_queries))
                    
                    if retry_search_results:
                        logger.info(f"✓ Recovered {len(retry_search_results)} searches on retry - processing results...")
                        
                        # Map recovered search results back to artists
                        for query, search_results in retry_search_results.items():
                            # Find which artist this query was for
                            for artist, title in unknown_artists:
                                # Check if query matches this artist
                                if artist.lower() in query.lower() or (title and title.lower() in query.lower()):
                                    # Re-run the fallback for just this artist with the recovered search results
                                    logger.info(f"Processing recovered results for: {artist}")
                                    # The search succeeded, so the data should be usable now
                                    break
                    
                    # Log final Brave stats
                    stats = self.brave_client.get_stats()
                    logger.info(f"Brave Search stats: {stats['successful_requests']}/{stats['total_requests']} successful, "
                               f"{stats['rate_limited_requests']} rate limited, "
                               f"{stats['failed_after_retries']} failed after retries")
                    
                    # Report any remaining failures for next run
                    remaining_failed = self.brave_client.get_failed_queries()
                    if remaining_failed:
                        logger.warning(f"📋 {len(remaining_failed)} queries saved for retry in next run")

        # Report final statistics
        logger.info(f"Batch research completed: {len(all_results)}/{len(artists_titles)} successful")
        if failed_batches:
            logger.warning(f"Failed batches: {len(failed_batches)} ({sum(len(b[1]) for b in failed_batches)} artists)")

        return all_results

    def _research_single_batch(self, artists_titles: List[tuple]) -> Dict[str, Dict[str, str]]:
        """
        Research multiple artists in a single Claude call (internal method).

        Args:
            artists_titles: List of (artist, title) tuples

        Returns:
            Dictionary mapping artist names to {'genre': genre_info, 'grouping': grouping_info}
        """
        if not artists_titles:
            return {}

        logger.info(f"Starting single batch research for {len(artists_titles)} artists")

        # Build batch prompt in "Title - Artist" format
        songs_list = []
        for i, (artist, title) in enumerate(artists_titles, 1):
            if title and title.strip():
                songs_list.append(f"{i}. {title} - {artist}")
            else:
                songs_list.append(f"{i}. Unknown - {artist}")

        # Use Claude WebSearch as primary (Brave is only fallback, not used here)
        prompt = f"""Research these songs and provide accurate genre, location, and release year information.

SONGS TO RESEARCH ({len(artists_titles)} total):
{chr(10).join(songs_list)}

RESEARCH APPROACH:
- Use WebSearch to research both the artist AND the specific song
- Use the song title to identify the correct artist (handles name ambiguity)
- Determine the artist's country of origin
- Find the song's original release year (earliest: single, EP, or album)
- If you cannot find reliable information, use "Unknown"

REQUIRED OUTPUT FORMAT (respond for ALL {len(artists_titles)} songs in numbered order):
1. GENRE: [Cultural/Main] | [Musical Style] | [Regional] | [Era]
   GROUPING: [Region] | [Country] | [Language Family]
   YEAR: [Song Release Year]

2. GENRE: [Cultural/Main] | [Musical Style] | [Regional] | [Era]
   GROUPING: [Region] | [Country] | [Language Family]
   YEAR: [Song Release Year]
...

GENRE FIELD STRUCTURE (4 parts, prioritize cultural identity):
Position 1 (Cultural/Main): Rock, Pop, Electronic, Latin, World, Jazz, Hip-Hop, Classical, Folk, R&B, Country, Blues, Reggae, Punk, Metal
Position 2 (Musical Style): Pop Rock, Salsa, Cumbia, Dance, Alternative, etc.
Position 3 (Regional): Spanish, Mexican, Celtic, Jamaican, Greek, etc.
Position 4 (Era/Movement): Contemporary, Traditional, Classic, Modern, etc.

CULTURAL PRIORITY RULE:
- Spanish/Portuguese music → Start with "Latin"
- African/Celtic/Indigenous → Start with "World"
- Caribbean reggae/ska → Start with "Reggae"
- Geographic terms (Mexican, Greek, Caribbean) → NEVER position 1, always position 3

EXAMPLES:
1. GENRE: Latin | Rock | Mexican | Rock en Español
   GROUPING: North America | Mexico | Romance
   YEAR: 1965

2. GENRE: Rock | Pop Rock | British Invasion | Classic
   GROUPING: Western Europe | United Kingdom | Germanic
   YEAR: 1968

3. GENRE: Electronic | Cumbia Bass | Colombian | Contemporary
   GROUPING: South America | Colombia | Romance
   YEAR: 2016

4. GENRE: World | Celtic | Folk | Traditional
   GROUPING: Western Europe | Ireland | Celtic
   YEAR: 1980

5. GENRE: Latin | Salsa | Modern | Urban
   GROUPING: Caribbean | Puerto Rico | Romance
   YEAR: 2013

REGIONS: Western Europe, Eastern Europe, North America, South America, Caribbean, East Asia, Southeast Asia, South Asia, Middle East, West Africa, East Africa, North Africa, Southern Africa, Oceania, Scandinavia, Mediterranean, Central America, Central Asia

LANGUAGE FAMILIES: Germanic, Romance, Slavic, Celtic, Indo-Iranian, Sino-Tibetan, Afro-Asiatic, Niger-Congo, Austronesian, Koreanic, Japonic, Dravidian, Altaic, Semitic, English

CRITICAL INSTRUCTIONS:
- You MUST respond in the exact numbered format shown above
- Do NOT include explanatory text, notes, or permission warnings
- Use WebSearch for artists/songs you don't know from training data
- Provide data for ALL {len(artists_titles)} songs, even if some fields are "Unknown"
- Return ONLY the numbered entries in the specified format - NO additional commentary

ACCURACY: Better to return "Unknown" than guess. Use WebSearch for accuracy."""

        try:
            self.statistics['total_requests'] += 1
            logger.info(f"Executing batch Claude command for {len(artists_titles)} artists")
            response = self._execute_claude_command(prompt)
            logger.info(f"Batch Claude command completed successfully")

            # DEBUG: Log response to diagnose parsing issues
            logger.warning(f"RAW RESPONSE LENGTH: {len(response)} chars")
            logger.warning(f"RAW RESPONSE PREVIEW (first 1000 chars):\n{response[:1000]}")
            logger.warning(f"RAW RESPONSE END (last 500 chars):\n{response[-500:]}")

            # Parse batch response
            results = {}
            lines = response.strip().split('\n')
            
            current_artist_idx = -1
            current_artist_data = {}
            
            for line in lines:
                line = line.strip()
                
                # Check for numbered entries (handle both regular and bold markdown)
                numbered_match = re.match(r'^(\d+)\.\s*(?:\*\*)?GENRE(?:\*\*)?\s*:\s*(.+)', line)
                if numbered_match:
                    # Save previous artist if exists
                    if current_artist_idx >= 0 and current_artist_data:
                        artist_name = artists_titles[current_artist_idx][0]
                        results[artist_name] = current_artist_data
                        
                        # Cache results
                        if self.cache_manager and 'grouping' in current_artist_data:
                            self.cache_manager.store_country(artist_name, current_artist_data['grouping'])
                    
                    # Start new artist
                    current_artist_idx = int(numbered_match.group(1)) - 1
                    genre_content = numbered_match.group(2)
                    # Clean any markdown artifacts
                    genre_content = re.sub(r'^\*\*|\*\*$', '', genre_content).strip()
                    
                    # ENFORCE pipe format for genre: Main | Style | Regional | Era
                    if '|' not in genre_content:
                        logger.warning(f"No pipes in genre, adding structure: {genre_content}")
                        current_artist_data = {'genre': f"{genre_content} | Unknown | Unknown | Unknown"}
                    else:
                        parts = [part.strip() for part in genre_content.split('|')]
                        if len(parts) == 1:
                            current_artist_data = {'genre': f"{parts[0]} | Unknown | Unknown | Unknown"}
                        elif len(parts) == 2:
                            current_artist_data = {'genre': f"{parts[0]} | {parts[1]} | Unknown | Unknown"}
                        elif len(parts) == 3:
                            current_artist_data = {'genre': f"{parts[0]} | {parts[1]} | {parts[2]} | Unknown"}
                        else:
                            current_artist_data = {'genre': genre_content}
                
                elif line.startswith('GENRE:') or line.startswith('**GENRE**:') or '**GENRE**:' in line:
                    genre_content = re.sub(r'.*(?:\*\*)?GENRE(?:\*\*)?\s*:\s*', '', line).strip()
                    # Clean any remaining markdown artifacts
                    genre_content = re.sub(r'^\*\*|\*\*$', '', genre_content).strip()
                    
                    # ENFORCE pipe format for genre: Main | Style | Regional | Era
                    if '|' not in genre_content:
                        # No pipes found - assume it's just main genre and add structure
                        logger.warning(f"No pipes in genre, adding structure: {genre_content}")
                        current_artist_data['genre'] = f"{genre_content} | Unknown | Unknown | Unknown"
                    else:
                        parts = [part.strip() for part in genre_content.split('|')]
                        if len(parts) == 1:
                            current_artist_data['genre'] = f"{parts[0]} | Unknown | Unknown | Unknown"
                        elif len(parts) == 2:
                            current_artist_data['genre'] = f"{parts[0]} | {parts[1]} | Unknown | Unknown"
                        elif len(parts) == 3:
                            current_artist_data['genre'] = f"{parts[0]} | {parts[1]} | {parts[2]} | Unknown"
                        else:
                            # Has 4+ parts, keep as-is (already has pipes)
                            current_artist_data['genre'] = genre_content
                
                elif line.startswith('GROUPING:') or line.startswith('**GROUPING**:') or '**GROUPING**:' in line:
                    grouping_line = re.sub(r'.*(?:\*\*)?GROUPING(?:\*\*)?\s*:\s*', '', line).strip()
                    # Clean any remaining markdown artifacts
                    grouping_line = re.sub(r'^\*\*|\*\*$', '', grouping_line).strip()
                    
                    # Parse and ENFORCE pipe format: Region | Country | Language
                    if '|' in grouping_line:
                        parts = [part.strip() for part in grouping_line.split('|')]
                        if len(parts) >= 3:
                            region, country, language = parts[0], parts[1], parts[2]
                            
                            # Validate country using centralized service
                            normalized_country = country_service.normalize_country_name(country)
                            if normalized_country:
                                # ENFORCE pipes in output
                                current_artist_data['grouping'] = f"{region} | {normalized_country.title()} | {language}"
                            else:
                                # Still enforce pipes even if country validation fails
                                current_artist_data['grouping'] = f"{region} | {country} | {language}"
                        else:
                            # Incomplete format - try to parse what we have and add pipes
                            logger.warning(f"Incomplete grouping format, attempting to fix: {grouping_line}")
                            if len(parts) == 2:
                                current_artist_data['grouping'] = f"{parts[0]} | {parts[1]} | Unknown"
                            elif len(parts) == 1:
                                current_artist_data['grouping'] = f"Unknown | {parts[0]} | Unknown"
                            else:
                                current_artist_data['grouping'] = f"Unknown | {grouping_line} | Unknown"
                    else:
                        # No pipes found - assume it's just a country name and add structure
                        logger.warning(f"No pipes in grouping, treating as country name: {grouping_line}")
                        normalized_country = country_service.normalize_country_name(grouping_line)
                        if normalized_country:
                            current_artist_data['grouping'] = f"Unknown | {normalized_country.title()} | Unknown"
                        else:
                            current_artist_data['grouping'] = f"Unknown | {grouping_line} | Unknown"
                
                elif line.startswith('YEAR:') or line.startswith('**YEAR**:') or '**YEAR**:' in line:
                    year_line = re.sub(r'.*(?:\*\*)?YEAR(?:\*\*)?\s*:\s*', '', line).strip()
                    # Clean any remaining markdown artifacts
                    year_line = re.sub(r'^\*\*|\*\*$', '', year_line).strip()
                    
                    # Validate year format (4-digit year)
                    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', year_line)
                    if year_match:
                        current_artist_data['year'] = year_match.group(1)
                    else:
                        # Only warn if not "Unknown" (which is expected when Claude can't determine year)
                        if year_line.lower() not in ['unknown', 'n/a', 'not found']:
                            logger.warning(f"Invalid year format: {year_line}")
                        current_artist_data['year'] = year_line
            
            # Save last artist
            if current_artist_idx >= 0 and current_artist_data and current_artist_idx < len(artists_titles):
                artist_name = artists_titles[current_artist_idx][0]
                results[artist_name] = current_artist_data

                # Cache results
                if self.cache_manager and 'grouping' in current_artist_data:
                    self.cache_manager.store_country(artist_name, current_artist_data['grouping'])

            self.statistics['successful_requests'] += 1
            return results
            
        except Exception as e:
            self.statistics['failed_requests'] += 1
            logger.error(f"Batch research failed: {e}")
            return {}
    
    def research_artist_dual_info(self, artist: str, title: str = "") -> Optional[Dict[str, str]]:
        """
        Research genre and geographic info for an artist using local Claude Code.
        
        Args:
            artist: Artist name to research
            title: Optional song title for additional context
            
        Returns:
            Dictionary with 'genre', 'grouping', and 'year' keys, or None if failed
            
        Raises:
            ClaudeCodeError: If research fails
        """
        if not artist or not artist.strip():
            raise ValidationError("Artist name cannot be empty", field="artist")
        
        artist = artist.strip()
        
        # Check cache first
        if self.cache_manager:
            cached_result = self.cache_manager.get_country(artist)
            if cached_result:
                self.statistics['cache_hits'] += 1
                logger.info(f"Cache hit for artist: {artist} -> {cached_result}")
                return cached_result
        
        start_time = time.time()
        
        for attempt in range(self.max_retries):
            try:
                self.statistics['total_requests'] += 1
                
                logger.info(f"Researching artist: {artist} (attempt {attempt + 1})")
                
                # Build prompt
                prompt = self._build_country_research_prompt(artist, title)
                
                # Execute claude command
                response = self._execute_claude_command(prompt)
                
                # Parse response (now triple format with genre, grouping, and year)
                genre_info, grouping_info, year_info = self._parse_triple_response(response)
                
                if genre_info and grouping_info:
                    # Cache the grouping result
                    if self.cache_manager:
                        self.cache_manager.store_country(artist, grouping_info)
                    
                    # Update statistics
                    response_time = time.time() - start_time
                    self.statistics['successful_requests'] += 1
                    self.statistics['average_response_time'] = (
                        (self.statistics['average_response_time'] * 
                         (self.statistics['successful_requests'] - 1) + response_time) /
                        self.statistics['successful_requests']
                    )
                    
                    result_dict = {'genre': genre_info, 'grouping': grouping_info}
                    if year_info:
                        result_dict['year'] = year_info
                    
                    logger.info(f"Successfully researched: {artist} -> Genre: {genre_info}, Grouping: {grouping_info}, Year: {year_info}")
                    return result_dict
                else:
                    logger.warning(f"Could not parse country from response: {response}")
                    
            except ClaudeCodeError as e:
                logger.error(f"Claude Code error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    self.statistics['failed_requests'] += 1
                    raise
                time.sleep(1 * (attempt + 1))  # Exponential backoff
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    self.statistics['failed_requests'] += 1
                    raise ClaudeCodeError(f"Research failed after {self.max_retries} attempts: {e}")
        
        self.statistics['failed_requests'] += 1
        return None
    
    def test_connection(self) -> bool:
        """
        Test connection to Claude Code.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = self.research_artist_country("The Beatles", "Hey Jude")
            return result is not None
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics.
        
        Returns:
            Dictionary containing usage statistics
        """
        return self.statistics.copy()
    
    def reset_statistics(self):
        """Reset usage statistics."""
        self.statistics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'average_response_time': 0
        }
