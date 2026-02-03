#!/bin/bash
# Music Tools - Streamlit UI Launcher
# Quick start script for the web interface

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Music Tools - Streamlit UI         ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo ""

# Check if Streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo -e "${YELLOW}Streamlit not found. Installing...${NC}"
    pip install streamlit plotly pandas
else
    echo -e "${GREEN}✓ Streamlit found${NC}"
fi

# Check if in correct directory
if [ ! -f "streamlit_app.py" ]; then
    echo -e "${YELLOW}Warning: streamlit_app.py not found in current directory${NC}"
    echo "Please run this script from the music-tools directory"
    exit 1
fi

echo -e "${GREEN}✓ Application file found${NC}"
echo ""

# Display options
echo -e "${BLUE}Starting Streamlit UI...${NC}"
echo ""
echo "Application will open at: http://localhost:8501"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Launch Streamlit
streamlit run streamlit_app.py \
    --server.port 8501 \
    --server.headless false \
    --browser.gatherUsageStats false \
    --theme.base "dark" \
    --theme.primaryColor "#1DB954" \
    --theme.backgroundColor "#121212" \
    --theme.secondaryBackgroundColor "#282828" \
    --theme.textColor "#FFFFFF"
