
import sys
import os
from unittest.mock import MagicMock, patch

# Add the app directory to path so imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, "apps/music-tools"))

from src.library.candidate_manager import CandidateManager

def test_delete_all_logic():
    print("Testing Delete All Logic...")
    
    # Mock data
    matches = [
        {'file': 'file1.mp3', 'path': '/tmp/file1.mp3', 'added_at': '2023-01-01'},
        {'file': 'file2.mp3', 'path': '/tmp/file2.mp3', 'added_at': '2023-01-01'},
        {'file': 'file3.mp3', 'path': '/tmp/file3.mp3', 'added_at': '2023-01-01'},
    ]
    
    manager = CandidateManager()
    
    # Patch dependencies
    with patch('src.library.candidate_manager.Prompt.ask') as mock_ask, \
         patch('src.library.candidate_manager.shutil.move') as mock_move, \
         patch('src.library.candidate_manager.os.path.exists') as mock_exists, \
         patch('src.library.candidate_manager.console.print') as mock_print:
         
        # Setup mocks
        mock_exists.return_value = True # Pretend files exist
        
        # Simulate user typing 'a' on the first prompt
        mock_ask.side_effect = ['a'] 
        
        # Run
        manager.process_matches(matches)
        
        # Verification
        print(f"\nPrompt asked {mock_ask.call_count} times (Expected: 1)")
        print(f"Move called {mock_move.call_count} times (Expected: 3)")
        
        if mock_ask.call_count == 1 and mock_move.call_count == 3:
            print("\nSUCCESS: 'a' input triggered batch deletion for all items!")
        else:
            print("\nFAILURE: Logic did not loop correctly.")

if __name__ == "__main__":
    test_delete_all_logic()
