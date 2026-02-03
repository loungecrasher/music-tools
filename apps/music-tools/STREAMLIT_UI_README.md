# Music Tools - Streamlit Web UI

Modern web-based interface for Music Tools as an alternative to the terminal UI.

## Overview

The Streamlit UI provides a beautiful, user-friendly web interface with four main pages:

1. **Dashboard** - Library overview with statistics and visualizations
2. **Smart Cleanup** - Interactive 8-step duplicate detection and removal workflow
3. **Library Stats** - Detailed analytics and quality breakdowns
4. **Settings** - Configuration for Spotify, Deezer, and cleanup preferences

## Installation

### Prerequisites

```bash
# Install Streamlit and Plotly (if not already installed)
pip install streamlit plotly pandas
```

### Verify Installation

```bash
# Check if Streamlit is installed
streamlit --version

# Should output something like: Streamlit, version 1.29.0
```

## Running the Application

### Quick Start

From the `music-tools` directory:

```bash
streamlit run streamlit_app.py
```

The application will automatically open in your default web browser at `http://localhost:8501`

### Advanced Options

```bash
# Run on a specific port
streamlit run streamlit_app.py --server.port 8080

# Run on a specific address (for network access)
streamlit run streamlit_app.py --server.address 0.0.0.0

# Enable auto-reload during development
streamlit run streamlit_app.py --server.runOnSave true

# Run in headless mode (no browser auto-open)
streamlit run streamlit_app.py --server.headless true
```

## Features

### 1. Dashboard Page

**Features:**
- Real-time library statistics (playlists, tracks, size, last scan)
- Interactive pie chart showing Spotify vs Deezer playlist distribution
- Line chart displaying library growth over time
- Recent playlists table with source information

**Key Metrics:**
- Total Playlists
- Total Tracks
- Library Size (GB)
- Last Scan Date

### 2. Smart Cleanup Workflow (8 Steps)

**Step 1: Library Path Selection**
- File browser interface for selecting music library
- Path validation with visual feedback
- Support for custom directory paths

**Step 2: Scan Mode Selection**
- Quick Scan (fast, metadata-based)
- Deep Scan (thorough, content hash + metadata)
- Custom Scan (user-defined parameters)
- Visual mode comparison with speed/accuracy ratings

**Step 3: Scanning Progress**
- Real-time progress bar
- Live status updates
- File grouping by metadata
- Quality analysis for duplicate groups

**Step 4: Duplicate Review**
- Side-by-side comparison in expandable groups
- Quality scores and format information
- Individual group selection with checkboxes
- Space savings calculation per group

**Step 5: Quality Distribution**
- Summary metrics (groups, files, space)
- Bar chart showing quality tier distribution
- Breakdown of Excellent/Good/Fair/Poor files

**Step 6: Confirmation**
- Safety checkpoint with warnings
- Type-to-confirm ("DELETE DUPLICATES")
- Final checkbox confirmation
- Backup location display

**Step 7: Execution**
- Dual-phase processing (backup → delete)
- Progress tracking with spinners
- Validation before execution
- Success metrics display

**Step 8: Completion**
- Celebration animation (balloons!)
- Comprehensive summary statistics
- Backup location information
- Export detailed JSON report

### 3. Library Stats Page

**Analytics:**
- Format distribution (pie chart + table)
- Bitrate distribution (bar chart)
- Quality tier breakdown (horizontal bar chart)
- Average bitrate and file count metrics

**Visualizations:**
- Interactive Plotly charts
- Color-coded quality tiers
- Percentage breakdowns
- Responsive design for all screen sizes

### 4. Settings Page

**Configuration Options:**

**Database:**
- Database path configuration
- Create new database option
- Path validation

**Spotify:**
- Client ID configuration
- Client Secret (password-protected)
- Secure storage in config files

**Deezer:**
- Email configuration
- Account linking

**Smart Cleanup Preferences:**
- Default scan mode selection
- Auto-backup toggle
- Backup retention period (1-365 days)

## Design Features

### Color Scheme

The UI uses a modern dark theme with brand colors:
- **Spotify Green:** `#1DB954`
- **Deezer Pink:** `#FF5500`
- **Background:** `#121212` (dark)
- **Cards:** `#282828` (dark gray)
- **Success:** Green
- **Warning:** Orange
- **Error:** Red
- **Info:** Cyan

### Mobile Responsive

- Fluid layouts using Streamlit columns
- Adaptive charts with `use_container_width=True`
- Touch-friendly buttons and controls
- Readable font sizes on all devices

### Error Handling

- Try-catch blocks around all database operations
- User-friendly error messages with `st.error()`
- Success confirmations with `st.success()`
- Warning alerts with `st.warning()`
- Informational messages with `st.info()`

## Configuration

### Database Path

Default: `~/.music_tools/library.db`

Change in Settings page or modify `st.session_state.db_path`

### Library Path

Default: `~/Music`

Change in Smart Cleanup Step 1 or Settings page

### Config Files

Stored in `~/.music_tools/`:
- `spotify_config.json` - Spotify API credentials
- `deezer_config.json` - Deezer account info
- `preferences.json` - UI preferences

## Troubleshooting

### Issue: Database not found

**Solution:**
1. Go to Settings page
2. Enter correct database path
3. Or check "Create new database at this path"
4. Click outside the input to save

### Issue: Charts not displaying

**Solution:**
```bash
# Ensure Plotly is installed
pip install plotly

# Update to latest version
pip install --upgrade plotly
```

### Issue: Port already in use

**Solution:**
```bash
# Use a different port
streamlit run streamlit_app.py --server.port 8502
```

### Issue: Module import errors

**Solution:**
```bash
# Ensure you're in the correct directory
cd /path/to/music-tools

# Verify Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run Streamlit
streamlit run streamlit_app.py
```

## Performance Tips

### Large Libraries

For libraries with 10,000+ files:
- Use Quick Scan mode for initial scans
- Review duplicates in batches
- Close unused expanders in Step 4
- Export reports for offline review

### Memory Management

```bash
# Increase Streamlit memory limit
streamlit run streamlit_app.py --server.maxUploadSize 500
```

### Caching

The app uses Streamlit session state for:
- Scan results (persistent across page changes)
- Confirmed groups (maintained during workflow)
- User preferences (loaded on startup)

## Development

### Local Development

```bash
# Enable auto-reload
streamlit run streamlit_app.py --server.runOnSave true

# Watch for file changes
streamlit run streamlit_app.py --server.fileWatcherType auto
```

### Custom Themes

Create `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#1DB954"
backgroundColor = "#121212"
secondaryBackgroundColor = "#282828"
textColor = "#FFFFFF"
font = "sans serif"
```

### Adding New Pages

1. Create render function: `render_new_page()`
2. Add to sidebar navigation options
3. Add conditional in `main()` function
4. Update documentation

## API Integration

### Current Integrations

- **LibraryDatabase** - SQLite-based music library
- **DuplicateChecker** - Multi-level duplicate detection
- **QualityAnalyzer** - Audio quality scoring
- **SafeDelete** - Validated file deletion with backups

### Future Integrations

- Spotify Web API (playlist management)
- Deezer API (playlist syncing)
- Last.fm (scrobbling)
- MusicBrainz (metadata enrichment)

## Security

### Best Practices

1. **Never commit credentials:**
   - API keys stored in `~/.music_tools/`
   - Password fields use `type="password"`
   - Config files in `.gitignore`

2. **Backup before deletion:**
   - Always enabled by default
   - Backups in `.cleanup_backups/`
   - Configurable retention period

3. **Validation checks:**
   - 7-point safety checklist
   - File existence verification
   - Quality comparison warnings

## Keyboard Shortcuts

Streamlit provides built-in shortcuts:
- `Ctrl+R` / `Cmd+R` - Rerun app
- `Ctrl+Shift+R` / `Cmd+Shift+R` - Clear cache and rerun
- `?` - Show keyboard shortcuts menu

## Support

### Getting Help

1. Check this README
2. Review error messages in UI
3. Check Streamlit logs in terminal
4. Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Reporting Issues

Include:
- Streamlit version (`streamlit --version`)
- Python version (`python --version`)
- Error message (full traceback)
- Steps to reproduce
- Screenshot if UI-related

## Changelog

### v1.0.0 (2026-01-08)

**Initial Release:**
- Dashboard with library statistics
- Smart Cleanup 8-step workflow
- Library Stats with detailed analytics
- Settings page for configuration
- Dark theme with Spotify/Deezer branding
- Mobile-responsive design
- Plotly charts and visualizations

## License

Copyright (c) 2026 Music Tools Dev Team

---

**Built with:**
- Streamlit 1.29+
- Plotly 5.18+
- Pandas 2.0+
- SQLite 3
- Python 3.9+

**Designed for:**
Modern music library management with quality-first duplicate detection
