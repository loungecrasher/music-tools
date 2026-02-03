"""
File handling utilities.
"""

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger("music_tools_common.utils.file")


def safe_write_json(data: Any, filepath: str) -> bool:
    """Safely write JSON data to file."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error writing JSON file: {e}")
        return False


def safe_read_json(filepath: str) -> Optional[Any]:
    """Safely read JSON data from file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading JSON file: {e}")
        return None
