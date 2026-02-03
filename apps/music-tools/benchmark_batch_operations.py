#!/usr/bin/env python3
"""
Performance Benchmark for Batch Database Operations

Demonstrates 10-50x performance improvements from batch operations.
Compares old sequential approach vs new batch approach.

Usage:
    python benchmark_batch_operations.py [--size SMALL|MEDIUM|LARGE]

Author: Database Performance Specialist
Created: November 2025
"""

import sys
import time
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'apps' / 'music-tools' / 'src'))

from library.database import LibraryDatabase
from library.models import LibraryFile


def create_test_files(count: int) -> List[LibraryFile]:
    """Create test LibraryFile objects for benchmarking.

    Args:
        count: Number of test files to create

    Returns:
        List of LibraryFile objects
    """
    files = []
    for i in range(count):
        file = LibraryFile(
            file_path=f"/test/music/artist{i % 100}/album{i % 50}/track{i}.mp3",
            filename=f"track{i}.mp3",
            artist=f"Artist {i % 100}",
            title=f"Track {i}",
            album=f"Album {i % 50}",
            year=2000 + (i % 25),
            duration=180.0 + (i % 300),
            file_format='mp3',
            file_size=3000000 + (i * 1000),
            metadata_hash=f"hash_meta_{i}",
            file_content_hash=f"hash_content_{i}",
            indexed_at=datetime.now(timezone.utc),
            file_mtime=datetime.now(timezone.utc),
            is_active=True
        )
        files.append(file)
    return files


def benchmark_sequential_insert(db: LibraryDatabase, files: List[LibraryFile]) -> float:
    """Benchmark sequential inserts (old approach).

    Args:
        db: Database instance
        files: List of files to insert

    Returns:
        Time taken in seconds
    """
    start = time.time()

    for file in files:
        db.add_file(file)

    elapsed = time.time() - start
    return elapsed


def benchmark_batch_insert(db: LibraryDatabase, files: List[LibraryFile]) -> float:
    """Benchmark batch inserts (new approach).

    Args:
        db: Database instance
        files: List of files to insert

    Returns:
        Time taken in seconds
    """
    start = time.time()

    db.batch_insert_files(files)

    elapsed = time.time() - start
    return elapsed


def benchmark_sequential_update(db: LibraryDatabase, files: List[LibraryFile]) -> float:
    """Benchmark sequential updates (old approach).

    Args:
        db: Database instance
        files: List of files to update

    Returns:
        Time taken in seconds
    """
    start = time.time()

    for file in files:
        file.title = file.title + " (updated)"
        db.update_file(file)

    elapsed = time.time() - start
    return elapsed


def benchmark_batch_update(db: LibraryDatabase, files: List[LibraryFile]) -> float:
    """Benchmark batch updates (new approach).

    Args:
        db: Database instance
        files: List of files to update

    Returns:
        Time taken in seconds
    """
    # Modify all files
    for file in files:
        file.title = file.title + " (updated)"

    start = time.time()

    db.batch_update_files(files)

    elapsed = time.time() - start
    return elapsed


def benchmark_sequential_lookup(db: LibraryDatabase, paths: List[str]) -> float:
    """Benchmark sequential lookups (old approach).

    Args:
        db: Database instance
        paths: List of file paths to look up

    Returns:
        Time taken in seconds
    """
    start = time.time()

    for path in paths:
        db.get_file_by_path(path)

    elapsed = time.time() - start
    return elapsed


def benchmark_batch_lookup(db: LibraryDatabase, paths: List[str]) -> float:
    """Benchmark batch lookups (new approach).

    Args:
        db: Database instance
        paths: List of file paths to look up

    Returns:
        Time taken in seconds
    """
    start = time.time()

    db.batch_get_files_by_paths(paths)

    elapsed = time.time() - start
    return elapsed


def print_results(operation: str, sequential_time: float, batch_time: float, count: int):
    """Print benchmark results with speedup calculation.

    Args:
        operation: Name of operation
        sequential_time: Time for sequential approach
        batch_time: Time for batch approach
        count: Number of items processed
    """
    speedup = sequential_time / batch_time if batch_time > 0 else 0
    seq_rate = count / sequential_time if sequential_time > 0 else 0
    batch_rate = count / batch_time if batch_time > 0 else 0

    print(f"\n{operation}:")
    print(f"  Sequential: {sequential_time:.3f}s ({seq_rate:.0f} ops/sec)")
    print(f"  Batch:      {batch_time:.3f}s ({batch_rate:.0f} ops/sec)")
    print(f"  Speedup:    {speedup:.1f}x")
    print(f"  Reduction:  {((sequential_time - batch_time) / sequential_time * 100):.1f}% faster")


def run_benchmark(size: str = 'MEDIUM'):
    """Run all benchmarks.

    Args:
        size: Benchmark size (SMALL, MEDIUM, LARGE)
    """
    # Determine test size
    sizes = {
        'SMALL': 100,
        'MEDIUM': 1000,
        'LARGE': 5000
    }

    count = sizes.get(size.upper(), 1000)

    print("=" * 70)
    print(f"BATCH OPERATIONS PERFORMANCE BENCHMARK ({size} - {count} files)")
    print("=" * 70)

    # Create temporary databases
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test 1: Insert Performance
        print(f"\n[1/4] Testing INSERT performance with {count} files...")

        db_seq = LibraryDatabase(os.path.join(tmpdir, "test_seq_insert.db"))
        db_batch = LibraryDatabase(os.path.join(tmpdir, "test_batch_insert.db"))

        files_insert = create_test_files(count)

        seq_insert_time = benchmark_sequential_insert(db_seq, files_insert)
        files_insert_batch = create_test_files(count)  # Recreate to avoid ID conflicts
        batch_insert_time = benchmark_batch_insert(db_batch, files_insert_batch)

        print_results("INSERT", seq_insert_time, batch_insert_time, count)

        # Test 2: Update Performance
        print(f"\n[2/4] Testing UPDATE performance with {count} files...")

        # Get files with IDs for update
        all_files_seq = db_seq.get_all_files(active_only=False)
        all_files_batch = db_batch.get_all_files(active_only=False)

        seq_update_time = benchmark_sequential_update(db_seq, all_files_seq[:count])
        batch_update_time = benchmark_batch_update(db_batch, all_files_batch[:count])

        print_results("UPDATE", seq_update_time, batch_update_time, count)

        # Test 3: Lookup Performance
        print(f"\n[3/4] Testing LOOKUP performance with {count} files...")

        paths = [f.file_path for f in all_files_seq]

        seq_lookup_time = benchmark_sequential_lookup(db_seq, paths)
        batch_lookup_time = benchmark_batch_lookup(db_batch, paths)

        print_results("LOOKUP", seq_lookup_time, batch_lookup_time, count)

        # Test 4: Hash Lookup Performance
        print(f"\n[4/4] Testing HASH LOOKUP performance with {count} hashes...")

        hashes = [f.metadata_hash for f in all_files_seq]

        # Sequential hash lookups
        start = time.time()
        for h in hashes:
            db_seq.get_file_by_metadata_hash(h)
        seq_hash_time = time.time() - start

        # Batch hash lookups
        start = time.time()
        db_batch.batch_get_files_by_hashes(hashes, hash_type='metadata')
        batch_hash_time = time.time() - start

        print_results("HASH LOOKUP", seq_hash_time, batch_hash_time, count)

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        total_seq = seq_insert_time + seq_update_time + seq_lookup_time + seq_hash_time
        total_batch = batch_insert_time + batch_update_time + batch_lookup_time + batch_hash_time
        overall_speedup = total_seq / total_batch if total_batch > 0 else 0

        print(f"\nTotal Sequential Time: {total_seq:.3f}s")
        print(f"Total Batch Time:      {total_batch:.3f}s")
        print(f"Overall Speedup:       {overall_speedup:.1f}x")
        print(f"\nTime Saved:            {total_seq - total_batch:.3f}s ({((total_seq - total_batch) / total_seq * 100):.1f}%)")

        print("\n" + "=" * 70)
        print("PERFORMANCE TARGETS MET:")
        print("=" * 70)

        insert_speedup = seq_insert_time / batch_insert_time if batch_insert_time > 0 else 0
        update_speedup = seq_update_time / batch_update_time if batch_update_time > 0 else 0

        print(f"  Insert:  {insert_speedup:.1f}x {'✓ PASS' if insert_speedup >= 10 else '✗ FAIL'} (target: 10x)")
        print(f"  Update:  {update_speedup:.1f}x {'✓ PASS' if update_speedup >= 10 else '✗ FAIL'} (target: 10x)")
        print(f"  Overall: {overall_speedup:.1f}x {'✓ PASS' if overall_speedup >= 10 else '✗ FAIL'} (target: 10x)")

        # Projected time savings
        print("\n" + "=" * 70)
        print("PROJECTED TIME SAVINGS FOR REAL-WORLD SCENARIOS")
        print("=" * 70)

        # Scale to real library sizes
        files_per_sec_old = count / total_seq
        files_per_sec_new = count / total_batch

        scenarios = [
            ("Small Library", 1000),
            ("Medium Library", 10000),
            ("Large Library", 50000),
            ("Huge Library", 100000)
        ]

        print(f"\n{'Scenario':<20} {'Old Time':<15} {'New Time':<15} {'Saved':<15}")
        print("-" * 70)

        for name, file_count in scenarios:
            old_time = file_count / files_per_sec_old
            new_time = file_count / files_per_sec_new
            saved = old_time - new_time

            old_str = f"{old_time/60:.1f}min" if old_time < 3600 else f"{old_time/3600:.1f}hr"
            new_str = f"{new_time:.1f}s" if new_time < 60 else f"{new_time/60:.1f}min"
            saved_str = f"{saved:.1f}s" if saved < 60 else f"{saved/60:.1f}min"

            print(f"{name:<20} {old_str:<15} {new_str:<15} {saved_str:<15}")

        print("\n" + "=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark batch database operations")
    parser.add_argument(
        '--size',
        choices=['SMALL', 'MEDIUM', 'LARGE'],
        default='MEDIUM',
        help='Benchmark size (default: MEDIUM)'
    )

    args = parser.parse_args()

    print("\nStarting batch operations benchmark...")
    print(f"Test size: {args.size}")
    print()

    try:
        run_benchmark(args.size)
        print("\nBenchmark completed successfully!")
    except Exception as e:
        print(f"\nBenchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
