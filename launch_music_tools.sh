#!/bin/bash
# Music Tools Suite Launcher
# Run this from the "Music Tools Dev" directory

echo "🎵 Music Tools Suite Launcher"
echo "=============================="
echo ""

# Check if we're in the right location
if [ ! -d "apps/music-tools" ]; then
    echo "❌ Error: Cannot find apps/music-tools directory"
    echo "   Current directory: $(pwd)"
    echo "   Please run this script from the 'Music Tools Dev' directory"
    exit 1
fi

echo "📁 Found app directory: apps/music-tools"
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
        cd apps/music-tools
        python3 menu.py
        ;;
    2)
        echo ""
        echo "🌐 Launching Web UI..."
        cd apps/music-tools

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
