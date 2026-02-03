"""
Interactive menu system.
"""
from typing import List, Callable, Optional


class InteractiveMenu:
    """Interactive menu for CLI applications."""
    
    def __init__(self, title: str):
        self.title = title
        self.options: List[tuple] = []
    
    def add_option(self, label: str, handler: Callable) -> None:
        """Add menu option."""
        self.options.append((label, handler))
    
    def display(self) -> Optional[int]:
        """Display menu and get user choice."""
        print(f"\n{self.title}")
        print("=" * len(self.title))
        
        for i, (label, _) in enumerate(self.options, 1):
            print(f"{i}. {label}")
        
        print("0. Exit")
        
        try:
            choice = int(input("\nEnter choice: "))
            if 0 <= choice <= len(self.options):
                return choice
        except ValueError:
            pass
        
        return None
    
    def run(self) -> None:
        """Run the menu loop."""
        while True:
            choice = self.display()
            
            if choice is None:
                print("Invalid choice")
                continue
            
            if choice == 0:
                break
            
            handler = self.options[choice - 1][1]
            handler()
