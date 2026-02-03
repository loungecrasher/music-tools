#!/usr/bin/env python3
"""
Test script to debug Claude CLI integration issues.
"""

import subprocess
import sys
import time


def test_basic_claude():
    """Test basic Claude CLI functionality."""
    print("Testing basic Claude CLI...")
    try:
        cmd = ["claude", "--print", "Hello, respond with 'Hi' only"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        print(f"Return code: {result.returncode}")
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Claude command timed out after 10 seconds")
        return False
    except FileNotFoundError:
        print("❌ Claude command not found")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_claude_with_websearch():
    """Test Claude CLI with WebSearch tool."""
    print("\nTesting Claude CLI with WebSearch...")
    try:
        cmd = [
            "claude",
            "--allowed-tools",
            "WebSearch",
            "--print",
            "What year was Python released? Use web search to verify.",
        ]
        print(f"Running command: {' '.join(cmd[:5])}...")
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        elapsed = time.time() - start_time
        print(f"Completed in {elapsed:.2f} seconds")
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"Output length: {len(result.stdout)} chars")
            print(f"First 200 chars: {result.stdout[:200]}...")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Claude command with WebSearch timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_batch_research():
    """Test a small batch research similar to the app."""
    print("\nTesting batch artist research...")
    prompt = """Research these artists and provide genre and country info:
1. The Beatles
2. Bob Marley

For each artist provide:
GENRE: [genre info]
GROUPING: [country info]

Keep it brief."""

    try:
        cmd = ["claude", "--allowed-tools", "WebSearch", "--print", prompt]
        print("Running batch research for 2 artists...")
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        elapsed = time.time() - start_time
        print(f"Completed in {elapsed:.2f} seconds")
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print(f"Output received: {len(result.stdout)} chars")
            # Check if we got the expected format
            if "GENRE:" in result.stdout and "GROUPING:" in result.stdout:
                print("✅ Response format looks correct")
            else:
                print("⚠️ Response format may be incorrect")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Batch research timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Claude CLI Integration Test")
    print("=" * 50)

    # Run tests
    tests = [
        ("Basic Claude", test_basic_claude),
        ("Claude with WebSearch", test_claude_with_websearch),
        ("Batch Research", test_batch_research),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        success = test_func()
        results.append((name, success))
        print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    for name, success in results:
        print(f"{name}: {'✅ PASS' if success else '❌ FAIL'}")

    all_pass = all(success for _, success in results)
    if all_pass:
        print("\n✅ All tests passed! Claude CLI is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        print("\nPossible issues:")
        print("1. WebSearch tool may not be available in your Claude plan")
        print("2. Network issues preventing web searches")
        print("3. Claude CLI configuration issues")
        print("\nTry running: claude --allowed-tools WebSearch --print 'Test message'")

    sys.exit(0 if all_pass else 1)
