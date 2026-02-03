#!/usr/bin/env python3
"""
Test batch research functionality
"""

import sys

sys.path.insert(0, '/Users/patrickoliver/Music Inxite/Office/Tech/Local Development/Music Tools/Tag Country Origin Editor/Codebase/music_tagger/src')

from .claude_code_researcher import ClaudeCodeResearcher

# Initialize researcher
researcher = ClaudeCodeResearcher(timeout=60)

# Test with a small batch
test_artists = [
    ("The Beatles", "Hey Jude"),
    ("Bob Marley", "No Woman No Cry")
]

print("Testing batch research with 2 artists...")
print("-" * 40)

try:
    results = researcher.research_artists_batch(test_artists)
    print(f"✅ Success! Got results for {len(results)} artists:")
    for artist, info in results.items():
        print(f"\n{artist}:")
        print(f"  Genre: {info.get('genre', 'N/A')}")
        print(f"  Grouping: {info.get('grouping', 'N/A')}")
        print(f"  Year: {info.get('year', 'N/A')}")
except Exception as e:
    print(f"❌ Error: {e}")
