# Music Tools Common

Shared library for the Music Tools ecosystem, providing unified configuration, database management, authentication, and utilities for all Music Tools projects.

## Features

- **Configuration Management**: Unified config handling with secure credential storage
- **Database Management**: SQLite database interface with caching support
- **Authentication**: Spotify and Deezer authentication managers
- **CLI Framework**: Base classes and utilities for building CLI applications
- **Metadata Handling**: Read and write music file metadata
- **API Clients**: Base API client implementations
- **Utilities**: Retry logic, validation, file handling, HTTP utilities

## Installation

### From PyPI (when published)

```bash
pip install music-tools-common
```

### From Source

```bash
git clone https://github.com/musictools/music-tools-common.git
cd music-tools-common
pip install -e .
```

### For Development

```bash
pip install -e ".[dev]"
```

## Quick Start

### Configuration

```python
from music_tools_common.config import config_manager

# Load Spotify configuration
spotify_config = config_manager.load_config('spotify')

# Save configuration
config_manager.save_config('spotify', {
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret'
})

# Validate configuration
errors = config_manager.validate_config('spotify')
if errors:
    print(f"Configuration errors: {errors}")
```

### Database

```python
from music_tools_common.database import get_database

# Get database instance
db = get_database()

# Add a playlist
playlist = {
    'id': 'abc123',
    'name': 'My Playlist',
    'url': 'https://open.spotify.com/playlist/abc123',
    'owner': 'user',
    'tracks': 50
}
db.add_playlist(playlist, 'spotify')

# Get playlists
playlists = db.get_playlists(service='spotify')
```

### Authentication

```python
from music_tools_common.auth import get_spotify_client, get_deezer_client

# Get authenticated Spotify client
sp = get_spotify_client()
user = sp.me()
print(f"Authenticated as: {user['id']}")

# Get authenticated Deezer client
deezer = get_deezer_client()
```

### Cache

```python
from music_tools_common.database import get_cache

cache = get_cache(ttl=3600)  # 1 hour TTL

# Set value
cache.set('my_key', {'data': 'value'})

# Get value
value = cache.get('my_key', default={})
```

### CLI Framework

```python
from music_tools_common.cli import BaseCLI, InteractiveMenu

class MyApp(BaseCLI):
    def run(self) -> int:
        menu = InteractiveMenu("My Application")
        menu.add_option("Process data", self.process_data)
        menu.add_option("Export results", self.export_results)
        menu.run()
        return 0
    
    def process_data(self):
        self.info("Processing data...")
    
    def export_results(self):
        self.info("Exporting results...")

if __name__ == "__main__":
    app = MyApp("my-app", "1.0.0")
    exit(app.run())
```

### Utilities

```python
from music_tools_common.utils import retry, safe_request, validate_email

# Retry decorator
@retry(max_attempts=3, delay=1.0)
def fetch_data():
    return requests.get('https://api.example.com/data')

# Safe request execution
result = safe_request(fetch_data)

# Validation
if validate_email('user@example.com'):
    print("Valid email")
```

## Configuration

Music Tools Common uses environment variables for sensitive credentials. Create a `.env` file:

```env
# Spotify
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback

# Deezer
DEEZER_EMAIL=your_deezer_email

# Paths (optional)
MUSIC_TOOLS_CONFIG_DIR=~/.music_tools/config

# Note: Country Tagger works via Claude Max plan (no API key needed)
```

## Project Structure

```
music_tools_common/
├── __init__.py              # Package exports
├── config/                  # Configuration module
│   ├── __init__.py
│   ├── manager.py           # ConfigManager
│   ├── schema.py            # Pydantic schemas
│   └── validation.py        # Validators
├── database/                # Database module
│   ├── __init__.py
│   ├── manager.py           # DatabaseManager
│   ├── cache.py             # CacheManager
│   └── models.py            # Data models
├── cli/                     # CLI framework
│   ├── __init__.py
│   ├── base.py              # BaseCLI
│   ├── menu.py              # InteractiveMenu
│   ├── prompts.py           # User prompts
│   └── progress.py          # ProgressTracker
├── utils/                   # Utilities
│   ├── __init__.py
│   ├── retry.py             # Retry logic
│   ├── validation.py        # Validators
│   ├── file.py              # File utilities
│   └── http.py              # HTTP utilities
├── auth/                    # Authentication
│   ├── __init__.py
│   ├── base.py              # Base auth
│   ├── spotify.py           # Spotify auth
│   └── deezer.py            # Deezer auth
├── metadata/                # Metadata handling
│   ├── __init__.py
│   ├── reader.py            # MetadataReader
│   └── writer.py            # MetadataWriter
└── api/                     # API clients
    ├── __init__.py
    ├── base.py              # BaseAPIClient
    ├── spotify.py           # SpotifyClient
    └── deezer.py            # DeezerClient
```

## Security

- **Never commit API keys or secrets** - use environment variables
- **Use `.env` files** for local development
- **Config files** should only contain non-sensitive settings
- **File permissions** are automatically secured (600/700)

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
isort .
```

### Type Checking

```bash
mypy music_tools_common
```

### Building Package

```bash
python -m build
```

## Dependencies

Core dependencies:
- requests >= 2.31.0
- pydantic >= 2.12.0
- python-dotenv >= 1.0.0
- click >= 8.3.0
- rich >= 14.2.0
- mutagen >= 1.47.0
- spotipy >= 2.25.0

See `requirements.txt` for full list.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://music-tools-common.readthedocs.io
- Issues: https://github.com/musictools/music-tools-common/issues
- Discussions: https://github.com/musictools/music-tools-common/discussions
