# Library Management & Duplicate Detection

This guide explains how to use the advanced library management features to index your music, detect duplicates, and vet new imports.

## 📖 How the New Feature Works

### The Problem It Solves

As a music curator managing thousands of songs, you need to:
- **Index** your main library (25,000+ songs)
- **Vet** new import folders (thousands of new songs)
- **Identify** which songs are duplicates vs. new
- **Export** lists for automated processing

Without this feature, you'd have to manually check each song against your entire library - taking hours or days!

### The Solution: Multi-Level Duplicate Detection

The system uses **3 levels of matching** to find duplicates:

1. **Level 1: Exact Metadata Match** (100% confidence)
   - Compares MD5 hash of "artist|title"
   - Instant lookup, <1ms per file
   - Example: "The Beatles|Yesterday" → hash → exact match

2. **Level 2: File Content Match** (100% confidence)
   - Compares MD5 hash of file content (first+last 64KB)
   - Catches re-tagged files or files with different metadata
   - Example: Same audio file, different tags

3. **Level 3: Fuzzy Metadata Match** (70-95% confidence)
   - Compares normalized artist/title using similarity algorithm
   - Catches variations like "feat.", "(remix)", etc.
   - Example: "Song Name" vs "Song Name (Radio Edit)"

### Confidence Levels Explained

- **100% (Exact)** - Duplicate confirmed, safe to skip
- **70-95% (Uncertain)** - Possible duplicate, needs manual review
- **<70% (New)** - Likely a new song, safe to import

---

## 🎯 Step-by-Step Workflow

### Step 1: Index Your Main Library (One-Time Setup)

This creates a searchable database of ALL your existing music:

```bash
python3 -m music_tools_cli library index --path ~/Music
```

**What happens:**
- Scans all music files in ~/Music
- Extracts metadata (artist, title, album, year, etc.)
- Calculates hashes for duplicate detection
- Saves to database at `~/.music-tools/library_index.db`
- Takes ~5 minutes for 10,000 songs

**Example Output:**
```
Indexing library: /home/user/Music
Found 25,341 music files

Indexing files... ━━━━━━━━━━━━━━━━━━━━━━━ 100% 25341/25341

Indexing Results
┏━━━━━━━━━┳━━━━━━━┓
┃ Metric  ┃ Count ┃
┡━━━━━━━━━╇━━━━━━━┩
│ Added   │ 25341 │
│ Updated │     0 │
│ Skipped │     0 │
│ Duration│ 4.2s  │
└─────────┴───────┘
```

---

### Step 2: Vet a New Import Folder

When you download a batch of new music, vet it against your library:

```bash
python3 -m music_tools_cli library vet --folder ~/Downloads/new-music-2025-01
```

**What happens:**
- Scans all files in the import folder
- Checks each file against your indexed library (3 levels)
- Categorizes as: New, Duplicate, or Uncertain
- Shows a detailed report
- Saves results to history

**Example Output:**
```
Vetting import folder: /home/user/Downloads/new-music-2025-01
Found 1,247 music files to vet

Vetting files... ━━━━━━━━━━━━━━━━━━━━━━━ 100% 1247/1247

╭──────────── Vetting Summary ─────────────╮
│ Import Folder: /home/user/Downloads/...  │
│ Total Files: 1,247                        │
│ Threshold: 80%                            │
│ Scan Duration: 2.34s                      │
╰───────────────────────────────────────────╯

                    Results
┏━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┓
┃ Category     ┃ Count ┃ Percentage ┃
┡━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━┩
│ ✅ New Songs │   823 │     66.0%  │
│ ❌ Duplicates│   378 │     30.3%  │
│ ⚠️  Uncertain│    46 │      3.7%  │
└──────────────┴───────┴────────────┘

🔴 Duplicates Found (378):
  ├─ song1.mp3
  │  ├─ Match: Artist - Title [library/path.mp3]
  │  ├─ Confidence: 100%
  │  └─ Type: exact_metadata
  ├─ song2.mp3
  │  ├─ Match: Artist - Title [library/path2.mp3]
  │  ├─ Confidence: 100%
  │  └─ Type: exact_file
  ...

⚠️  Uncertain Matches (46):
  ├─ song3.mp3
  │  ├─ Possible Match: Artist - Title [library/path.mp3]
  │  └─ Confidence: 85%
  ...

Next Steps:
  ✅ Import 823 new songs to your library
  ❌ Skip or delete 378 duplicates
  ⚠️  Manually review 46 uncertain matches
```

---

### Step 3: Export Results for Automation

Export lists of new songs and duplicates for batch processing:

```bash
python3 -m music_tools_cli library vet \
  --folder ~/Downloads/new-music-2025-01 \
  --export-new \
  --export-duplicates \
  --export-uncertain
```

**Creates 3 Files:**
1. `new_songs.txt` - List of files safe to import
2. `duplicates.txt` - List of files to skip/delete
3. `uncertain.txt` - List of files to manually review

**Example new_songs.txt:**
```
# New Songs from /home/user/Downloads/new-music-2025-01
# Generated: 2025-01-19 14:23:45
# Total: 823

/home/user/Downloads/new-music-2025-01/Artist1 - Song1.mp3
/home/user/Downloads/new-music-2025-01/Artist2 - Song2.mp3
/home/user/Downloads/new-music-2025-01/Artist3 - Song3.mp3
...
```

**Use these files for automation:**
```bash
# Copy only new songs to your library
while IFS= read -r file; do
  [[ "$file" =~ ^# ]] && continue  # Skip comments
  cp "$file" ~/Music/
done < new_songs.txt

# Delete duplicates
while IFS= read -r file; do
  [[ "$file" =~ ^# ]] && continue
  rm "$file"
done < duplicates.txt
```

---

## 🔧 Common Commands

### View Library Statistics
```bash
python3 -m music_tools_cli library stats
```

**Shows:**
- Total files indexed
- Total library size (GB)
- Average file size
- Unique artists/albums
- Format breakdown (MP3, FLAC, etc.)

**Example Output:**
```
Library Statistics
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Metric             ┃ Value     ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Total Files        │   25,341  │
│ Total Size         │   142.3 GB│
│ Average File Size  │     5.8 MB│
│ Unique Artists     │    2,847  │
│ Unique Albums      │    4,123  │
│ Last Indexed       │ 2025-01-19│
└────────────────────┴───────────┘

Format Breakdown
┏━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┓
┃ Format ┃ Count ┃ Percentage ┃
┡━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━┩
│ MP3    │18,234 │     71.9%  │
│ FLAC   │ 6,892 │     27.2%  │
│ M4A    │   215 │      0.9%  │
└────────┴───────┴────────────┘
```

---

### View Vetting History
```bash
python3 -m music_tools_cli library history --limit 10
```

**Shows:**
- Recent vetting operations
- Dates, folders checked
- Results summary

---

### Verify Library Integrity
```bash
python3 -m music_tools_cli library verify --path ~/Music
```

**What it does:**
- Checks if indexed files still exist
- Marks missing files as inactive
- Useful after moving/deleting files

---

### Re-index After Changes
```bash
# Incremental (only new/modified files)
python3 -m music_tools_cli library index --path ~/Music

# Full rescan (force check all files)
python3 -m music_tools_cli library index --path ~/Music --rescan
```

---

## 💡 Real-World Example Workflow

### Scenario: You download 2,000 new songs weekly

**Weekly Routine (5 minutes):**

```bash
# 1. Vet the new batch (2 minutes)
python3 -m music_tools_cli library vet \
  --folder ~/Downloads/weekly-batch \
  --export-new \
  --export-duplicates

# 2. Import new songs automatically (1 minute)
while IFS= read -r file; do
  [[ "$file" =~ ^# ]] && continue
  cp "$file" ~/Music/Incoming/
done < ~/Downloads/weekly-batch/new_songs.txt

# 3. Delete duplicates (instant)
while IFS= read -r file; do
  [[ "$file" =~ ^# ]] && continue
  rm "$file"
done < ~/Downloads/weekly-batch/duplicates.txt

# 4. Update your library index (1 minute)
python3 -m music_tools_cli library index --path ~/Music

# 5. Check stats
python3 -m music_tools_cli library stats
```

**Time Saved:**
- **Without tool:** 7 hours manually checking
- **With tool:** 5 minutes automated
- **Savings:** 6 hours 55 minutes per week!

---

## 🎛️ Advanced Options

### Custom Threshold for Fuzzy Matching

```bash
# More strict (fewer uncertain matches)
python3 -m music_tools_cli library vet --folder ~/import --threshold 0.9

# More lenient (more matches considered)
python3 -m music_tools_cli library vet --folder ~/import --threshold 0.7

# Default is 0.8 (80% similarity)
```

### Custom Database Location

```bash
# Use custom database
python3 -m music_tools_cli library index \
  --path ~/Music \
  --db ~/custom-location/my-library.db

# Vet against custom database
python3 -m music_tools_cli library vet \
  --folder ~/import \
  --library-db ~/custom-location/my-library.db
```

### Multiple Libraries

```bash
# Index multiple libraries separately
python3 -m music_tools_cli library index \
  --path ~/Music/Classical \
  --db ~/databases/classical.db

python3 -m music_tools_cli library index \
  --path ~/Music/Electronic \
  --db ~/databases/electronic.db

# Vet against specific library
python3 -m music_tools_cli library vet \
  --folder ~/import \
  --library-db ~/databases/classical.db
```

---

## 🔍 Understanding the Match Types

### Exact Metadata Match (100% confidence)
```
File: Artist - Song Name.mp3
Library: Artist - Song Name.mp3
Match: ✅ Exact (artist|title hash matches)
Action: Skip - definitely a duplicate
```

### Exact File Match (100% confidence)
```
File: Unknown Artist - Track 01.mp3
Library: Real Artist - Real Title.mp3
Match: ✅ Exact (file content hash matches)
Note: Same audio, different metadata
Action: Skip - it's the same file
```

### Fuzzy Match (70-95% confidence)
```
File: Artist - Song Name (Radio Edit).mp3
Library: Artist - Song Name.mp3
Match: ⚠️ Uncertain (85% similarity)
Note: Might be same song with different version
Action: Manual review recommended
```

### No Match (<70% confidence)
```
File: New Artist - New Song.mp3
Library: No matches found
Match: ✅ New (safe to import)
Action: Import this song
```

---

## 🐛 Troubleshooting

### "No module named 'typer'" Error
```bash
# Install dependencies
pip3 install --user typer rich mutagen
```

### "Library database not found" Error
```bash
# You need to index first
python3 -m music_tools_cli library index --path ~/Music
```

### Slow Performance on Large Libraries
```bash
# Optimize database monthly
python3 -c "
from src.library.database import LibraryDatabase
db = LibraryDatabase('~/.music-tools/library_index.db')
db.optimize_database()
print('Database optimized!')
"
```

### Database Corruption
```bash
# Check integrity
python3 -c "
from src.library.database import LibraryDatabase
db = LibraryDatabase('~/.music-tools/library_index.db')
if db.verify_database_integrity():
    print('✅ Database is healthy')
else:
    print('❌ Database is corrupted - restore from backup')
"
```

---

## 💾 Backup Your Database

### Create Backup
```bash
python3 -c "
from src.library.database import LibraryDatabase
from datetime import datetime
db = LibraryDatabase('~/.music-tools/library_index.db')
backup_name = f'backup_{datetime.now():%Y%m%d_%H%M%S}.db'
db.backup_database(f'backups/{backup_name}')
print(f'Backup created: {backup_name}')
"
```

### Automated Daily Backup (Cron)
```bash
# Add to crontab
0 2 * * * cd /home/user && python3 -c "from src.library.database import LibraryDatabase; from datetime import datetime; db = LibraryDatabase('.music-tools/library_index.db'); db.backup_database(f'backups/daily_{datetime.now():%Y%m%d}.db')"
```

---

## 🎓 Key Concepts

### Database
- Located at `~/.music-tools/library_index.db`
- Contains indexed metadata for fast lookups
- ~100KB per 1,000 songs
- Thread-safe for concurrent access

### Indexing
- One-time scan of your main library
- Creates searchable database
- Update incrementally as you add music

### Vetting
- Check import folder against indexed library
- Uses 3 levels of duplicate detection
- Produces categorized results (New/Duplicate/Uncertain)

### Confidence Levels
- **100%** - Exact match, definitely a duplicate
- **70-95%** - Uncertain, manual review suggested
- **<70%** - No match, likely new

---

## 📞 Getting Help

### View Command Help
```bash
# General help
python3 -m music_tools_cli library --help

# Command-specific help
python3 -m music_tools_cli library index --help
python3 -m music_tools_cli library vet --help
```

### Check System Status
```bash
python3 -m music_tools_cli library stats
python3 -m music_tools_cli library history
```

---

## 🎉 Quick Reference Card

```bash
# SETUP (once)
pip3 install --user typer rich mutagen
python3 -m music_tools_cli library index --path ~/Music

# WEEKLY WORKFLOW
python3 -m music_tools_cli library vet --folder ~/import --export-new
# → Review results
# → Import new songs
python3 -m music_tools_cli library index --path ~/Music

# MAINTENANCE (monthly)
python3 -m music_tools_cli library verify --path ~/Music
python3 -c "from src.library.database import LibraryDatabase; LibraryDatabase('~/.music-tools/library_index.db').optimize_database()"

# MONITORING
python3 -m music_tools_cli library stats
python3 -m music_tools_cli library history
```

---

**You're now ready to use the library duplicate detection feature!** 🎵

Start with indexing your main library, then vet your next import folder. The system will save you hours of manual work!
