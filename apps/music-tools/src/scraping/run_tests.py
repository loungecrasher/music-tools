#!/usr/bin/env python3
"""
Test runner for the EDM Music Blog Scraper.
"""

import sys
import subprocess
import argparse


def run_tests(args):
    """Run the test suite with specified options."""
    cmd = ["pytest"]
    
    if args.coverage:
        cmd.extend(["--cov=.", "--cov-report=term-missing", "--cov-report=html"])
    
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")
    
    if args.markers:
        cmd.extend(["-m", args.markers])
    
    if args.test:
        cmd.append(args.test)
    
    if args.failfast:
        cmd.append("-x")
    
    if args.pdb:
        cmd.append("--pdb")
    
    print(f"Running: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="Run tests for EDM Music Blog Scraper")
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Run with extra verbosity"
    )
    
    parser.add_argument(
        "-m", "--markers",
        help="Run tests matching given mark expression (e.g., 'not slow')"
    )
    
    parser.add_argument(
        "-t", "--test",
        help="Run specific test file or test case"
    )
    
    parser.add_argument(
        "-x", "--failfast",
        action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--pdb",
        action="store_true",
        help="Drop into debugger on failures"
    )
    
    args = parser.parse_args()
    
    # Run tests
    exit_code = run_tests(args)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()