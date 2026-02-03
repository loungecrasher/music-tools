# How to Run Music Tools v2.0

## Quick Start

### Option 1: Using the Shell Script (Recommended)
```bash
cd "Music Tools Dev/apps/music-tools"
./launch_music_tools.sh
```

### Option 2: Direct Python Execution
```bash
cd "Music Tools Dev/apps/music-tools"
python3 menu.py
```

### Option 3: From Root Directory
```bash
cd "Music Tools Dev"
python3 apps/music-tools/menu.py
```

---

## Prerequisites

### Required Python Packages
Make sure you have the required dependencies installed:

```bash
# From the Music Tools Dev directory
pip install -r requirements-core.txt

# Or install individually
pip install rich python-dotenv
```

### Required for Library Features
```bash
pip install mutagen  # For audio file metadata
```

---

## First-Time Setup

### 1. Index Your Library (One-Time)
When you first run the app:
```
1. Select: "📚 Library Management"
2. Select: "Index Library"
3. Enter path to your main music library
   Example: /Users/yourname/Music/iTunes/iTunes Media/Music
4. Wait for indexing to complete
```

This creates a database at: `~/.music-tools/library_index.db`

---

## Regular Usage

### Process New Music (Your Main Workflow)
```
1. Run: python3 menu.py
2. Select: "📁 Process New Music Folder"
3. Enter path to new downloads folder
   Example: /Users/yourname/Downloads/New Music Jan 2026
4. Review results:
   - 🔴 Duplicates (already in library)
   - 🟡 Reviewed (already listened to)
   - 🟢 New (need your attention)
5. Choose cleanup option:
   - "yes" = delete all duplicates/reviewed
   - "review" = decide individually
   - "no" = keep everything
6. Find new_songs.txt in the folder with truly new songs
```

---

## Menu Structure

```
MUSIC TOOLS SUITE v2.0

1. 📁 Process New Music Folder  ← YOUR MAIN WORKFLOW
2. 📚 Library Management
   ├─ Index Library
   ├─ Library Statistics
   ├─ Smart Cleanup (Advanced)
   └─ Vet Imports (Legacy)
3. 🔧 Advanced Tools
   ├─ 🏷️ Country Tagger (AI)
   └─ 🔍 EDM Blog Scraper
4. 📝 Candidate History
   ├─ Add Folder to History
   └─ Check Folder against History
0. Exit
```

---

## Troubleshooting

### "Module not found" errors
```bash
# Install missing dependencies
pip install -r requirements-core.txt

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### "Library database not found"
```
Run "Index Library" first to create the database
```

### "Permission denied" on launch script
```bash
chmod +x launch_music_tools.sh
./launch_music_tools.sh
```

---

## Tips

### Batch Processing
Process multiple folders by running "Process New Music Folder" multiple times

### Export Lists
The `new_songs.txt` file is created in each processed folder for easy reference

### Cleanup Safety
All deleted files go to `~/.Trash` - they can be recovered if needed

### Performance
- Indexing 50,000 songs takes ~5-10 minutes (one-time)
- Processing 500 new songs takes ~30 seconds

---

## Support

For issues or questions, see:
- `REFACTORING_COMPLETE_2026-01-26.md` - Full refactoring details
- `QUICK_START.md` - Quick reference guide