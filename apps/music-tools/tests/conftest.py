import sys
from pathlib import Path

# Add apps/music-tools to sys.path to allow importing from src
# This assumes the test file is in apps/music-tools/tests/
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
