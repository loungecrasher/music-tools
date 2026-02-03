#!/bin/bash
# Music Tools Suite Launcher
# This script helps you launch the Music Tools app from any directory

echo "🎵 Music Tools Suite Launcher"
echo "=============================="
echo ""

# Get the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$SCRIPT_DIR/apps/music-tools"

# Check if we're in the right location
if [ ! -d "$APP_DIR" ]; then
    echo "❌ Error: Cannot find apps/music-tools directory"
    echo "   Current directory: $(pwd)"
    echo "   Looking for: $APP_DIR"
    exit 1
fi

echo "📁 App directory: $APP_DIR"
echo ""
echo "Choose how to launch:"
echo "  1) Terminal Menu (Rich UI)"
echo "  2) Web UI (Streamlit)"
echo "  3) Cancel"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🚀 Launching Terminal Menu..."
        cd "$APP_DIR"
        python3 menu.py
        ;;
    2)
        echo ""
        echo "🌐 Launching Web UI..."
        cd "$APP_DIR"
        
        # Check if streamlit is installed
        if ! command -v streamlit &> /dev/null; then
            echo "⚠️  Streamlit not found. Installing..."
            pip3 install streamlit plotly pandas
        fi
        
        streamlit run streamlit_app.py
        ;;
    3)
        echo "Cancelled."
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
