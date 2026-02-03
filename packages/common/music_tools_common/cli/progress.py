"""
Progress tracking for CLI operations.
"""
from typing import Optional
from tqdm import tqdm


class ProgressTracker:
    """Progress tracker using tqdm."""
    
    def __init__(self, total: int, desc: str = "Processing"):
        self.pbar = tqdm(total=total, desc=desc)
    
    def update(self, n: int = 1):
        """Update progress."""
        self.pbar.update(n)
    
    def close(self):
        """Close progress bar."""
        self.pbar.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
