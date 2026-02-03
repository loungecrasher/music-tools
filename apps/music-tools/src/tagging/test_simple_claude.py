#!/usr/bin/env python3
"""
Simple test to see what's happening with Claude CLI calls.
"""

import subprocess

# Test 1: Simple test without WebSearch
print("Test 1: Simple claude --print command")
print("-" * 40)
cmd = ["claude", "--print", "Say just 'Hello' and nothing else"]
print(f"Running: {' '.join(cmd)}")

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(f"Return code: {result.returncode}")
    print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Stderr: {result.stderr}")
except subprocess.TimeoutExpired:
    print("ERROR: Command timed out after 30 seconds")
    print("\nThis suggests claude --print is hanging.")
    print("Possible fixes:")
    print("1. Run 'claude' interactively first to ensure it's authenticated")
    print("2. Check if there's a workspace trust prompt blocking execution")
    print("3. Try: claude --print --dangerously-skip-permissions 'test'")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 50)
print("\nTest 2: With --dangerously-skip-permissions flag")
print("-" * 40)
cmd = ["claude", "--print", "--dangerously-skip-permissions", "Say just 'Hello' and nothing else"]
print(f"Running: {' '.join(cmd)}")

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(f"Return code: {result.returncode}")
    print(f"Output: {result.stdout}")
    if result.stderr:
        print(f"Stderr: {result.stderr}")
except subprocess.TimeoutExpired:
    print("ERROR: Still timed out even with --dangerously-skip-permissions")
except Exception as e:
    print(f"ERROR: {e}")
