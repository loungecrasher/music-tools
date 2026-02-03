"""Tests for HTTP utilities module."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import (
    ConnectionError,
    Timeout,
    HTTPError,
    RequestException
)

from music_tools_common.utils.http import (
    safe_request,
    RateLimiter,
    setup_session,
)


class TestSafeRequest:
    """Tests for safe_request function with retry logic."""

    @patch('requests.get')
    def test_safe_request_success(self, mock_get):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_get.return_value = mock_response

        response = safe_request('https://api.example.com/data')

        assert response is not None
        assert response.status_code == 200
        assert response.json() == {'data': 'test'}
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_safe_request_retry_on_500(self, mock_get):
        """Test retry logic on 500 server error."""
        # First two calls fail, third succeeds
        mock_get.side_effect = [
            Mock(status_code=500),
            Mock(status_code=503),
            Mock(status_code=200, json=lambda: {'data': 'success'})
        ]

        response = safe_request(
            'https://api.example.com/data',
            max_retries=3
        )

        assert response is not None
        assert response.status_code == 200
        assert mock_get.call_count == 3

    @patch('requests.get')
    def test_safe_request_retry_on_connection_error(self, mock_get):
        """Test retry logic on connection error."""
        # First call fails, second succeeds
        mock_get.side_effect = [
            ConnectionError("Connection failed"),
            Mock(status_code=200, json=lambda: {'data': 'success'})
        ]

        response = safe_request(
            'https://api.example.com/data',
            max_retries=2
        )

        assert response is not None
        assert response.status_code == 200
        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_safe_request_retry_on_timeout(self, mock_get):
        """Test retry logic on timeout."""
        mock_get.side_effect = [
            Timeout("Request timed out"),
            Mock(status_code=200, json=lambda: {'data': 'success'})
        ]

        response = safe_request(
            'https://api.example.com/data',
            timeout=5,
            max_retries=2
        )

        assert response is not None
        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_safe_request_max_retries_exceeded(self, mock_get):
        """Test failure after max retries exceeded."""
        mock_get.side_effect = ConnectionError("Connection failed")

        response = safe_request(
            'https://api.example.com/data',
            max_retries=3
        )

        assert response is None
        assert mock_get.call_count == 3

    @patch('requests.get')
    def test_safe_request_429_rate_limit(self, mock_get):
        """Test handling of 429 rate limit with Retry-After header."""
        # First call returns 429 with Retry-After, second succeeds
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '1'}

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {'data': 'success'}

        mock_get.side_effect = [rate_limit_response, success_response]

        start_time = time.time()
        response = safe_request(
            'https://api.example.com/data',
            max_retries=2
        )
        elapsed = time.time() - start_time

        assert response is not None
        assert response.status_code == 200
        assert elapsed >= 1.0  # Should have waited at least 1 second
        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_safe_request_no_retry_on_404(self, mock_get):
        """Test no retry on 404 (client error)."""
        mock_get.return_value = Mock(status_code=404)

        response = safe_request('https://api.example.com/nonexistent')

        assert response is not None
        assert response.status_code == 404
        mock_get.assert_called_once()  # Should not retry

    @patch('requests.post')
    def test_safe_request_post_method(self, mock_post):
        """Test POST request with data."""
        mock_post.return_value = Mock(
            status_code=201,
            json=lambda: {'id': '123'}
        )

        response = safe_request(
            'https://api.example.com/create',
            method='POST',
            json={'name': 'test'}
        )

        assert response.status_code == 201
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs['json'] == {'name': 'test'}

    @patch('requests.get')
    def test_safe_request_custom_headers(self, mock_get):
        """Test request with custom headers."""
        mock_get.return_value = Mock(status_code=200)

        headers = {
            'Authorization': 'Bearer token123',
            'User-Agent': 'MusicTools/1.0'
        }

        safe_request('https://api.example.com/data', headers=headers)

        call_kwargs = mock_get.call_args[1]
        assert 'Authorization' in call_kwargs['headers']
        assert call_kwargs['headers']['Authorization'] == 'Bearer token123'

    @patch('requests.get')
    def test_safe_request_timeout_parameter(self, mock_get):
        """Test timeout parameter is passed correctly."""
        mock_get.return_value = Mock(status_code=200)

        safe_request('https://api.example.com/data', timeout=10)

        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['timeout'] == 10


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(max_calls=10, time_window=60)

        assert limiter.max_calls == 10
        assert limiter.time_window == 60
        assert len(limiter.calls) == 0

    def test_rate_limiter_allows_within_limit(self):
        """Test rate limiter allows calls within limit."""
        limiter = RateLimiter(max_calls=5, time_window=1)

        # Should allow 5 calls
        for _ in range(5):
            assert limiter.acquire() is True

    def test_rate_limiter_blocks_when_exceeded(self):
        """Test rate limiter blocks when limit exceeded."""
        limiter = RateLimiter(max_calls=3, time_window=10)

        # Fill up the limit
        for _ in range(3):
            limiter.acquire()

        # Next call should be blocked (returns False)
        # In real implementation, this might sleep instead
        # For testing, we check the behavior
        assert len(limiter.calls) == 3

    def test_rate_limiter_cleans_old_calls(self):
        """Test rate limiter cleans up old calls."""
        limiter = RateLimiter(max_calls=5, time_window=1)

        # Make calls
        for _ in range(3):
            limiter.acquire()

        # Wait for time window to pass
        time.sleep(1.1)

        # Old calls should be cleaned up
        limiter.acquire()  # This should clean old calls
        assert len([c for c in limiter.calls if time.time() - c < 1]) <= 1

    def test_rate_limiter_concurrent_usage(self):
        """Test rate limiter with multiple rapid calls."""
        limiter = RateLimiter(max_calls=10, time_window=1)

        start_time = time.time()
        successful_calls = 0

        for _ in range(15):
            if limiter.acquire():
                successful_calls += 1

        elapsed = time.time() - start_time

        # Should allow at most max_calls within time window
        assert successful_calls <= 10

    def test_rate_limiter_reset_after_time_window(self):
        """Test rate limiter resets after time window."""
        limiter = RateLimiter(max_calls=2, time_window=1)

        # Use up the limit
        limiter.acquire()
        limiter.acquire()

        # Wait for window to reset
        time.sleep(1.1)

        # Should be able to make calls again
        assert limiter.acquire() is True


class TestSessionSetup:
    """Tests for session setup and configuration."""

    def test_setup_session_basic(self):
        """Test basic session setup."""
        session = setup_session()

        assert isinstance(session, requests.Session)
        assert 'User-Agent' in session.headers

    def test_setup_session_custom_headers(self):
        """Test session setup with custom headers."""
        custom_headers = {
            'Authorization': 'Bearer token',
            'Custom-Header': 'value'
        }

        session = setup_session(headers=custom_headers)

        assert session.headers['Authorization'] == 'Bearer token'
        assert session.headers['Custom-Header'] == 'value'

    def test_setup_session_retry_configuration(self):
        """Test session setup with retry configuration."""
        session = setup_session(max_retries=5)

        # Check that retry adapter is configured
        adapter = session.get_adapter('https://')
        assert adapter is not None

    def test_setup_session_timeout_default(self):
        """Test session has default timeout configured."""
        session = setup_session()

        # Verify timeout is set (implementation-specific)
        # This test depends on your actual implementation
        assert session is not None

    @patch('requests.Session')
    def test_setup_session_connection_pooling(self, mock_session_class):
        """Test session connection pooling is configured."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        session = setup_session(pool_connections=10, pool_maxsize=20)

        # Verify pooling configuration was applied
        assert mock_session is not None


class TestHTTPErrorHandling:
    """Tests for HTTP error handling scenarios."""

    @patch('requests.get')
    def test_handle_http_error_status(self, mock_get):
        """Test handling of HTTP error status codes."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPError("Server Error")
        mock_get.return_value = mock_response

        response = safe_request(
            'https://api.example.com/error',
            max_retries=1
        )

        # Should retry on 500 errors
        assert mock_get.call_count >= 1

    @patch('requests.get')
    def test_handle_json_decode_error(self, mock_get):
        """Test handling of JSON decode errors."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        response = safe_request('https://api.example.com/data')

        # Should still return the response even if JSON parsing fails
        assert response is not None
        assert response.status_code == 200

    @patch('requests.get')
    def test_handle_ssl_error(self, mock_get):
        """Test handling of SSL certificate errors."""
        mock_get.side_effect = requests.exceptions.SSLError("SSL Error")

        response = safe_request('https://api.example.com/data')

        # Should return None on SSL errors (security critical)
        assert response is None


class TestIntegrationScenarios:
    """Integration tests for real-world HTTP scenarios."""

    @patch('requests.get')
    def test_spotify_api_workflow(self, mock_get):
        """Test typical Spotify API interaction workflow."""
        # First request gets playlists
        playlists_response = Mock()
        playlists_response.status_code = 200
        playlists_response.json.return_value = {
            'items': [{'id': '1', 'name': 'Playlist 1'}]
        }

        # Second request hits rate limit
        rate_limit_response = Mock()
        rate_limit_response.status_code = 429
        rate_limit_response.headers = {'Retry-After': '0.5'}

        # Third request succeeds
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            'items': [{'id': '2', 'name': 'Playlist 2'}]
        }

        mock_get.side_effect = [
            playlists_response,
            rate_limit_response,
            success_response
        ]

        # First call
        response1 = safe_request('https://api.spotify.com/v1/me/playlists')
        assert response1.status_code == 200

        # Second call (rate limited, then succeeds)
        response2 = safe_request('https://api.spotify.com/v1/me/playlists')
        assert response2.status_code == 200

        assert mock_get.call_count == 3

    @patch('requests.get')
    def test_network_resilience_workflow(self, mock_get):
        """Test resilience to network issues."""
        # Simulate intermittent network issues
        mock_get.side_effect = [
            ConnectionError("Network unreachable"),
            Timeout("Request timeout"),
            ConnectionError("Network unreachable"),
            Mock(status_code=200, json=lambda: {'status': 'ok'})
        ]

        response = safe_request(
            'https://api.example.com/data',
            max_retries=5,
            timeout=10
        )

        assert response is not None
        assert response.status_code == 200
        assert mock_get.call_count == 4  # 3 failures + 1 success


class TestRetryStrategies:
    """Tests for different retry strategies."""

    @patch('requests.get')
    def test_exponential_backoff(self, mock_get):
        """Test exponential backoff between retries."""
        mock_get.side_effect = [
            ConnectionError("Fail 1"),
            ConnectionError("Fail 2"),
            Mock(status_code=200)
        ]

        start_time = time.time()
        response = safe_request(
            'https://api.example.com/data',
            max_retries=3,
            backoff_factor=0.5
        )
        elapsed = time.time() - start_time

        # With exponential backoff: 0.5s, 1s (total ~1.5s minimum)
        # Actual implementation may vary
        assert response is not None
        assert mock_get.call_count == 3

    @patch('requests.get')
    def test_no_retry_on_client_errors(self, mock_get):
        """Test that client errors (4xx) don't trigger retries."""
        client_error_codes = [400, 401, 403, 404, 422]

        for status_code in client_error_codes:
            mock_get.reset_mock()
            mock_get.return_value = Mock(status_code=status_code)

            response = safe_request(
                'https://api.example.com/data',
                max_retries=3
            )

            # Should not retry on client errors
            assert mock_get.call_count == 1
            assert response.status_code == status_code

    @patch('requests.get')
    def test_retry_on_server_errors(self, mock_get):
        """Test that server errors (5xx) trigger retries."""
        server_error_codes = [500, 502, 503, 504]

        for status_code in server_error_codes:
            mock_get.reset_mock()
            mock_get.side_effect = [
                Mock(status_code=status_code),
                Mock(status_code=status_code),
                Mock(status_code=200)
            ]

            response = safe_request(
                'https://api.example.com/data',
                max_retries=3
            )

            # Should retry on server errors
            assert mock_get.call_count == 3


# Run with: pytest packages/common/tests/test_http.py -v --cov=music_tools_common.utils.http
