# 🚀 Music Tools Suite - Quick Start Guide

## How to Launch

You are currently in: `Music Tools Dev/`

### Option 1: Use the Launcher Script (Easiest)
```bash
./launch_music_tools.sh
```
This will give you a menu to choose Terminal or Web UI.

### Option 2: Navigate to App Directory First
```bash
cd apps/music-tools
```

Then choose:

**For Terminal UI:**
```bash
python3 menu.py
```

**For Web UI:**
```bash
streamlit run streamlit_app.py
# OR
./run_streamlit.sh
```

### Option 3: Launch Directly
```bash
# Terminal UI
python3 apps/music-tools/menu.py

# Web UI  
cd apps/music-tools && streamlit run streamlit_app.py
```

## First Time Setup

If Streamlit is not installed:
```bash
pip3 install streamlit plotly pandas
```

## Troubleshooting

**Problem:** `zsh: no such file or directory`
- **Solution:** You need to `cd apps/music-tools` first

**Problem:** `streamlit: command not found`  
- **Solution:** `pip3 install streamlit plotly pandas`

**Problem:** `No module named 'src.library'`
- **Solution:** Make sure you're in the `apps/music-tools` directory

## What's Where

```
Music Tools Dev/                    ← YOU ARE HERE
├── launch_music_tools.sh           ← NEW: Easy launcher
├── apps/music-tools/               ← APP DIRECTORY
│   ├── menu.py                     ← Terminal UI entry point
│   ├── streamlit_app.py            ← Web UI entry point
│   ├── run_streamlit.sh            ← Web UI launcher
│   └── src/library/                ← New Smart Cleanup modules
│       ├── quality_analyzer.py
│       ├── safe_delete.py
│       ├── quality_models.py
│       └── smart_cleanup.py
└── QUICK_START.md                  ← This file
```

## Next Steps

1. Launch the app using one of the methods above
2. Navigate to: **Library Management** → **Smart Cleanup**
3. Enter your music library path (e.g., `~/Music`)
4. Choose scan mode and let it analyze your collection!

---

**Need help?** Check `docs/guides/user/smart-cleanup.md` for detailed instructions.
