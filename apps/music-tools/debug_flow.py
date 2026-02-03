#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src/tagging')

from claude_code_researcher import ClaudeCodeResearcher

# Create researcher
researcher = ClaudeCodeResearcher(max_retries=1, timeout=600, cache_manager=None)

# Test single artist
artists = [("Lancelot", "Madame")]
result = researcher.research_artists_batch(artists)

print("Result from AI:")
for artist, data in result.items():
    print(f"  {artist}:")
    print(f"    genre: {data.get('genre')}")
    print(f"    grouping: {data.get('grouping')}")
    print(f"    year: {data.get('year')}")