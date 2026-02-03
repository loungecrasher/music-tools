"""
Tests for DatabaseManager
"""

import pytest
import sqlite3
import tempfile
import threading
from pathlib import Path

from music_tools_common.database import DatabaseManager, DatabaseError


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield db_path


@pytest.fixture
def db(temp_db):
    """Create DatabaseManager instance."""
    db = DatabaseManager(temp_db, wal_mode=True)
    yield db
    db.close()


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    def test_initialization(self, temp_db):
        """Test database initialization."""
        db = DatabaseManager(temp_db, wal_mode=True)
        assert db.db_path == temp_db
        assert db.wal_mode is True
        assert temp_db.exists()
        db.close()

    def test_create_table(self, db):
        """Test table creation."""
        db.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''', commit=True)

        assert db.table_exists('test_table')

    def test_insert_and_fetch(self, db):
        """Test insert and fetch operations."""
        db.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''', commit=True)

        # Insert
        db.execute(
            'INSERT INTO test_table (id, name) VALUES (?, ?)',
            (1, 'Test Name'),
            commit=True
        )

        # Fetch one
        result = db.fetch_one('SELECT * FROM test_table WHERE id = ?', (1,))
        assert result is not None
        assert result['id'] == 1
        assert result['name'] == 'Test Name'

        # Fetch all
        results = db.fetch_all('SELECT * FROM test_table')
        assert len(results) == 1

        # Fetch value
        name = db.fetch_value('SELECT name FROM test_table WHERE id = ?', (1,))
        assert name == 'Test Name'

    def test_batch_operations(self, db):
        """Test batch insert operations."""
        db.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''', commit=True)

        # Batch insert
        data = [(i, f'Name {i}') for i in range(100)]
        count = db.execute_many(
            'INSERT INTO test_table (id, name) VALUES (?, ?)',
            data
        )

        assert count == 100

        # Verify
        results = db.fetch_all('SELECT * FROM test_table')
        assert len(results) == 100

    def test_transactions(self, db):
        """Test transaction support."""
        db.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''', commit=True)

        # Successful transaction
        with db.transaction():
            db.execute('INSERT INTO test_table (id, name) VALUES (?, ?)', (1, 'Name 1'))
            db.execute('INSERT INTO test_table (id, name) VALUES (?, ?)', (2, 'Name 2'))

        results = db.fetch_all('SELECT * FROM test_table')
        assert len(results) == 2

        # Failed transaction (should rollback)
        try:
            with db.transaction():
                db.execute('INSERT INTO test_table (id, name) VALUES (?, ?)', (3, 'Name 3'))
                raise Exception("Test error")
        except:
            pass

        results = db.fetch_all('SELECT * FROM test_table')
        assert len(results) == 2  # Should still be 2

    def test_statistics(self, db):
        """Test statistics tracking."""
        db.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''', commit=True)

        # Execute operations
        db.execute('INSERT INTO test_table (id, name) VALUES (?, ?)', (1, 'Name'), commit=True)
        db.execute('UPDATE test_table SET name = ? WHERE id = ?', ('Updated', 1), commit=True)
        db.execute('DELETE FROM test_table WHERE id = ?', (1,), commit=True)

        stats = db.get_statistics()
        assert stats['inserts'] >= 1
        assert stats['updates'] >= 1
        assert stats['deletes'] >= 1
        assert stats['queries_executed'] >= 4

    def test_table_operations(self, db):
        """Test table utility methods."""
        db.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value INTEGER DEFAULT 0
            )
        ''', commit=True)

        # Table exists
        assert db.table_exists('test_table')
        assert not db.table_exists('nonexistent_table')

        # Table info
        info = db.get_table_info('test_table')
        assert len(info) == 3
        column_names = [col['name'] for col in info]
        assert 'id' in column_names
        assert 'name' in column_names
        assert 'value' in column_names

    def test_optimize_operations(self, db):
        """Test VACUUM and ANALYZE."""
        db.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''', commit=True)

        # Insert and delete data
        data = [(i, f'Name {i}') for i in range(100)]
        db.execute_many('INSERT INTO test_table VALUES (?, ?)', data)
        db.execute('DELETE FROM test_table WHERE id < 50', commit=True)

        # Should not raise errors
        db.vacuum()
        db.analyze()
        db.optimize()

    def test_context_manager(self, temp_db):
        """Test context manager functionality."""
        with DatabaseManager(temp_db) as db:
            db.execute('''
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT
                )
            ''', commit=True)

            db.execute('INSERT INTO test_table VALUES (1, "Test")', commit=True)

        # Verify connection was closed
        assert not hasattr(db._local, 'connection') or db._local.connection is None

    def test_thread_safety(self, db):
        """Test thread-safe operations."""
        db.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                value INTEGER
            )
        ''', commit=True)

        results = []
        errors = []

        def worker(thread_id):
            try:
                for i in range(10):
                    db.execute(
                        'INSERT INTO test_table (value) VALUES (?)',
                        (thread_id * 100 + i,),
                        commit=True
                    )
                results.append(thread_id)
            except Exception as e:
                errors.append(str(e))

        # Run multiple threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify all threads completed
        assert len(results) == 5
        assert len(errors) == 0

        # Verify all inserts
        count = db.fetch_value('SELECT COUNT(*) FROM test_table')
        assert count == 50

    def test_wal_mode(self, temp_db):
        """Test WAL mode configuration."""
        db = DatabaseManager(temp_db, wal_mode=True)

        # Check journal mode
        mode = db.fetch_value('PRAGMA journal_mode')
        assert mode.lower() == 'wal'

        db.close()

    def test_error_handling(self, db):
        """Test error handling."""
        # Invalid query should raise DatabaseError
        with pytest.raises(DatabaseError):
            db.execute('INVALID SQL QUERY')

        # Non-existent table
        with pytest.raises(DatabaseError):
            db.execute('SELECT * FROM nonexistent_table')


class TestDatabaseStatistics:
    """Test database statistics."""

    def test_statistics_tracking(self, db):
        """Test comprehensive statistics tracking."""
        db.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        ''', commit=True)

        # Perform various operations
        db.execute('INSERT INTO test_table VALUES (1, "Test")', commit=True)
        db.execute('UPDATE test_table SET name = "Updated" WHERE id = 1', commit=True)
        db.fetch_all('SELECT * FROM test_table')
        db.execute('DELETE FROM test_table WHERE id = 1', commit=True)

        stats = db.get_statistics()

        assert 'queries_executed' in stats
        assert 'inserts' in stats
        assert 'updates' in stats
        assert 'deletes' in stats
        assert 'database_size_bytes' in stats
        assert 'database_size_mb' in stats

        assert stats['inserts'] >= 1
        assert stats['updates'] >= 1
        assert stats['deletes'] >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
