# Performance Documentation

This directory contains all performance-related documentation, optimization guides, and benchmarking information.

## Performance Guides

### Database Performance
- [database-optimization.md](database-optimization.md) - Comprehensive database optimization guide
  - 41% average query performance improvement across all database operations
  - Composite index strategy for optimal query execution
  - PRAGMA optimizations for SQLite
  - Migration guide for existing databases

### Application Performance
- [quick-start-optimization.md](quick-start-optimization.md) - Database optimization quick start
- [batch-operations.md](batch-operations.md) - Batch operations implementation (10-50x improvement)

## Performance Achievements

- **Database queries**: 41% average improvement with composite indexes
- **Duplicate detection**: 40-60% faster with optimized hash lookups
- **Batch operations**: 10-50x speedup in library indexing and bulk operations
- **Cache TTL lookups**: 30-45% faster with composite indexes
- **Library indexing**: 800-1600 files/min (up from 100-200 files/min)

## Quick Links

- **Need faster queries?** See [Database Optimization](database-optimization.md)
- **Processing many files?** Check [Batch Operations](batch-operations.md)
- **Optimizing existing databases?** Run the [migration script](../../scripts/migrate_database_indexes.py)

[Back to Documentation Hub](../README.md)
