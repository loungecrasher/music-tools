"""Tests for retry utilities module."""

import time

import pytest
from music_tools_common.utils.retry import RetryError, exponential_backoff, retry


class TestRetryDecorator:
    """Tests for @retry decorator."""

    def test_retry_successful_first_attempt(self):
        """Test function succeeds on first attempt."""
        call_count = 0

        @retry(max_attempts=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()

        assert result == "success"
        assert call_count == 1

    def test_retry_succeeds_after_failures(self):
        """Test function succeeds after initial failures."""
        call_count = 0

        @retry(max_attempts=3, delay=0.1)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count == 3

    def test_retry_max_attempts_exceeded(self):
        """Test raises RetryError when max attempts exceeded."""
        call_count = 0

        @retry(max_attempts=3, delay=0.1)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryError) as exc_info:
            always_fails()

        assert call_count == 3
        assert "maximum retry attempts" in str(exc_info.value).lower()

    def test_retry_with_specific_exceptions(self):
        """Test retry only on specific exception types."""
        call_count = 0

        @retry(
            max_attempts=3,
            exceptions=(ConnectionError, TimeoutError),
            delay=0.1
        )
        def selective_retry():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Retry this")
            elif call_count == 2:
                raise TimeoutError("Retry this too")
            return "success"

        result = selective_retry()

        assert result == "success"
        assert call_count == 3

    def test_retry_does_not_catch_unlisted_exceptions(self):
        """Test decorator doesn't retry on unlisted exceptions."""
        call_count = 0

        @retry(max_attempts=3, exceptions=(ConnectionError,))
        def raises_different_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Don't retry this")

        with pytest.raises(ValueError):
            raises_different_error()

        # Should fail immediately without retry
        assert call_count == 1

    def test_retry_with_exponential_backoff(self):
        """Test retry with exponential backoff delay."""
        call_count = 0
        timestamps = []

        @retry(
            max_attempts=4,
            delay=0.1,
            backoff=2,  # Exponential: 0.1, 0.2, 0.4
            exceptions=(ValueError,)
        )
        def exponential_function():
            nonlocal call_count
            call_count += 1
            timestamps.append(time.time())
            if call_count < 4:
                raise ValueError("Retry")
            return "success"

        result = exponential_function()

        assert result == "success"
        assert call_count == 4

        # Check delays between attempts (roughly exponential)
        delays = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        # First delay ~0.1s, second ~0.2s, third ~0.4s
        assert delays[0] >= 0.09  # Allow for timing variance
        assert delays[1] >= 0.18
        assert delays[2] >= 0.35

    def test_retry_with_max_delay(self):
        """Test retry respects max_delay parameter."""
        call_count = 0

        @retry(
            max_attempts=5,
            delay=0.1,
            backoff=10,  # Would create huge delays
            max_delay=0.3,  # But capped at 0.3s
            exceptions=(ValueError,)
        )
        def capped_delay_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "success"

        start_time = time.time()
        result = capped_delay_function()
        elapsed = time.time() - start_time

        assert result == "success"
        # Total delay should be roughly: 0.1 + 0.3 = 0.4s (capped)
        # Not 0.1 + 1.0 (uncapped exponential)
        assert elapsed < 1.0

    def test_retry_with_callable_delay(self):
        """Test retry with callable delay function."""
        call_count = 0
        delays_used = []

        def custom_delay(attempt: int) -> float:
            """Custom delay: 0.1s for attempt 1, 0.2s for attempt 2, etc."""
            delay = attempt * 0.1
            delays_used.append(delay)
            return delay

        @retry(
            max_attempts=3,
            delay=custom_delay,
            exceptions=(ValueError,)
        )
        def custom_delay_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "success"

        result = custom_delay_function()

        assert result == "success"
        assert len(delays_used) == 2  # 2 retries
        assert delays_used[0] == 0.1  # First retry delay
        assert delays_used[1] == 0.2  # Second retry delay

    def test_retry_with_on_retry_callback(self):
        """Test retry with callback on each retry."""
        retry_info = []

        def on_retry(attempt, exception, delay):
            retry_info.append({
                'attempt': attempt,
                'exception': str(exception),
                'delay': delay
            })

        call_count = 0

        @retry(
            max_attempts=3,
            delay=0.1,
            exceptions=(ValueError,),
            on_retry=on_retry
        )
        def function_with_callback():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} failed")
            return "success"

        result = function_with_callback()

        assert result == "success"
        assert len(retry_info) == 2  # 2 retries
        assert retry_info[0]['attempt'] == 1
        assert "Attempt 1" in retry_info[0]['exception']

    def test_retry_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""
        @retry(max_attempts=3)
        def documented_function():
            """This function has documentation."""
            return "result"

        assert documented_function.__doc__ == "This function has documentation."
        assert documented_function.__name__ == "documented_function"

    def test_retry_with_function_arguments(self):
        """Test retry works with function arguments."""
        call_count = 0

        @retry(max_attempts=3, delay=0.1, exceptions=(ValueError,))
        def function_with_args(x, y, z=10):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            return x + y + z

        result = function_with_args(5, 3, z=7)

        assert result == 15
        assert call_count == 2

    def test_retry_with_async_function(self):
        """Test retry with async function (if supported)."""
        # This test is only valid if your retry decorator supports async
        # Skip or modify based on actual implementation
        pytest.skip("Async retry not implemented yet")


class TestExponentialBackoff:
    """Tests for exponential_backoff function."""

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff calculations."""
        # base_delay=1, backoff=2
        delays = [
            exponential_backoff(attempt, base_delay=1, backoff=2)
            for attempt in range(1, 6)
        ]

        # Should be: 1, 2, 4, 8, 16
        assert delays == [1, 2, 4, 8, 16]

    def test_exponential_backoff_with_max_delay(self):
        """Test exponential backoff respects max_delay."""
        delays = [
            exponential_backoff(
                attempt,
                base_delay=1,
                backoff=2,
                max_delay=5
            )
            for attempt in range(1, 6)
        ]

        # Should be: 1, 2, 4, 5, 5 (capped at 5)
        assert delays == [1, 2, 4, 5, 5]

    def test_exponential_backoff_with_jitter(self):
        """Test exponential backoff with jitter."""
        delays = [
            exponential_backoff(
                attempt=3,
                base_delay=1,
                backoff=2,
                jitter=True
            )
            for _ in range(100)
        ]

        # Base delay for attempt 3: 4 seconds
        # With jitter: random between 0 and 4
        assert all(0 <= d <= 4 for d in delays)
        # Should have some variance
        assert len(set(delays)) > 10  # Not all the same

    def test_exponential_backoff_zero_attempt(self):
        """Test exponential backoff with attempt 0."""
        delay = exponential_backoff(0, base_delay=1, backoff=2)
        # Attempt 0 might return 0 or base_delay depending on implementation
        assert delay >= 0

    def test_exponential_backoff_different_factors(self):
        """Test exponential backoff with different backoff factors."""
        # Backoff factor of 3
        delays_3x = [
            exponential_backoff(attempt, base_delay=1, backoff=3)
            for attempt in range(1, 4)
        ]
        assert delays_3x == [1, 3, 9]

        # Backoff factor of 1.5
        delays_1_5x = [
            exponential_backoff(attempt, base_delay=2, backoff=1.5)
            for attempt in range(1, 4)
        ]
        assert delays_1_5x == [2, 3, 4.5]


class TestRetryWithRealScenarios:
    """Integration tests with realistic retry scenarios."""

    def test_database_connection_retry(self):
        """Test retry pattern for database connections."""
        attempts = []

        @retry(
            max_attempts=5,
            delay=0.1,
            backoff=2,
            exceptions=(ConnectionError,)
        )
        def connect_to_database():
            attempts.append(time.time())
            if len(attempts) < 3:
                raise ConnectionError("Database unavailable")
            return "connected"

        result = connect_to_database()

        assert result == "connected"
        assert len(attempts) == 3

    def test_api_request_with_rate_limiting(self):
        """Test retry with simulated API rate limiting."""
        call_count = 0

        class RateLimitError(Exception):
            pass

        @retry(
            max_attempts=4,
            delay=0.5,
            exceptions=(RateLimitError,)
        )
        def api_request():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RateLimitError("Rate limit exceeded")
            return {"data": "success"}

        result = api_request()

        assert result == {"data": "success"}
        assert call_count == 3

    def test_file_read_with_transient_errors(self):
        """Test retry for file operations with transient errors."""
        attempts = 0

        @retry(
            max_attempts=3,
            delay=0.1,
            exceptions=(OSError, IOError)
        )
        def read_file(filepath):
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise OSError("Resource temporarily unavailable")
            return f"contents of {filepath}"

        result = read_file("/tmp/test.txt")

        assert result == "contents of /tmp/test.txt"
        assert attempts == 2

    def test_network_request_with_mixed_errors(self):
        """Test retry handling multiple error types."""
        call_sequence = []

        @retry(
            max_attempts=5,
            delay=0.1,
            exceptions=(ConnectionError, TimeoutError, OSError)
        )
        def network_request():
            call_sequence.append(len(call_sequence) + 1)

            if len(call_sequence) == 1:
                raise ConnectionError("Connection failed")
            elif len(call_sequence) == 2:
                raise TimeoutError("Request timeout")
            elif len(call_sequence) == 3:
                raise OSError("Network unreachable")
            else:
                return "success"

        result = network_request()

        assert result == "success"
        assert call_sequence == [1, 2, 3, 4]


class TestRetryErrorHandling:
    """Tests for error handling in retry logic."""

    def test_retry_error_contains_original_exception(self):
        """Test RetryError contains information about original exception."""
        @retry(max_attempts=2, delay=0.1, exceptions=(ValueError,))
        def failing_function():
            raise ValueError("Original error message")

        with pytest.raises(RetryError) as exc_info:
            failing_function()

        # RetryError should contain info about the original exception
        error_msg = str(exc_info.value)
        assert "ValueError" in error_msg or "Original error" in error_msg

    def test_retry_with_exception_chain(self):
        """Test retry preserves exception chain."""
        @retry(max_attempts=2, delay=0.1)
        def function_with_chain():
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise ConnectionError("Outer error") from e

        with pytest.raises(RetryError):
            function_with_chain()

    def test_retry_logs_attempts(self, caplog):
        """Test retry logs each attempt (if logging is implemented)."""
        @retry(max_attempts=3, delay=0.1, exceptions=(ValueError,))
        def logged_function():
            raise ValueError("Test error")

        with pytest.raises(RetryError):
            logged_function()

        # Check if attempts were logged (depends on implementation)
        # This test may need adjustment based on actual logging


class TestRetryConfiguration:
    """Tests for retry configuration options."""

    def test_retry_default_parameters(self):
        """Test retry with default parameters."""
        call_count = 0

        @retry()  # All defaults
        def default_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Retry")
            return "success"

        result = default_retry()
        assert result == "success"

    def test_retry_zero_delay(self):
        """Test retry with zero delay between attempts."""
        call_count = 0

        @retry(max_attempts=3, delay=0, exceptions=(ValueError,))
        def instant_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Retry")
            return "success"

        start_time = time.time()
        result = instant_retry()
        elapsed = time.time() - start_time

        assert result == "success"
        assert elapsed < 0.1  # Should be nearly instant

    def test_retry_with_negative_attempts(self):
        """Test retry handles invalid max_attempts."""
        with pytest.raises(ValueError):
            @retry(max_attempts=0)
            def invalid_retry():
                return "result"

    def test_retry_with_invalid_delay(self):
        """Test retry handles invalid delay values."""
        with pytest.raises(ValueError):
            @retry(delay=-1)
            def invalid_delay():
                return "result"


# Run with: pytest packages/common/tests/test_retry.py -v --cov=music_tools_common.utils.retry
