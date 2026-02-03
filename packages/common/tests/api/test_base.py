"""Tests for base API client module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import (
    ConnectionError,
    Timeout,
    HTTPError,
    RequestException
)

from music_tools_common.api.base import BaseAPIClient


class TestBaseAPIClient:
    """Tests for BaseAPIClient class."""

    def test_init_with_valid_url(self):
        """Test initialization with valid base URL."""
        client = BaseAPIClient("https://api.example.com")

        assert client.base_url == "https://api.example.com"
        assert isinstance(client.session, requests.Session)

    def test_init_with_trailing_slash(self):
        """Test initialization handles trailing slash in URL."""
        client = BaseAPIClient("https://api.example.com/")

        assert client.base_url == "https://api.example.com/"
        assert isinstance(client.session, requests.Session)

    def test_session_is_persistent(self):
        """Test that session is persistent across requests."""
        client = BaseAPIClient("https://api.example.com")
        session1 = client.session
        session2 = client.session

        assert session1 is session2


class TestBaseAPIClientGet:
    """Tests for BaseAPIClient GET request method."""

    @patch('requests.Session.get')
    def test_get_success_without_params(self, mock_get):
        """Test successful GET request without parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("endpoint")

        assert result == {'data': 'test'}
        mock_get.assert_called_once_with(
            "https://api.example.com/endpoint",
            params=None
        )

    @patch('requests.Session.get')
    def test_get_success_with_params(self, mock_get):
        """Test successful GET request with query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'items': [1, 2, 3]}
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        params = {'limit': 10, 'offset': 0}
        result = client.get("search", params=params)

        assert result == {'items': [1, 2, 3]}
        mock_get.assert_called_once_with(
            "https://api.example.com/search",
            params=params
        )

    @patch('requests.Session.get')
    def test_get_success_with_nested_endpoint(self, mock_get):
        """Test GET request with nested endpoint path."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'user': 'data'}
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("users/123/profile")

        assert result == {'user': 'data'}
        mock_get.assert_called_once_with(
            "https://api.example.com/users/123/profile",
            params=None
        )

    @patch('requests.Session.get')
    def test_get_empty_response(self, mock_get):
        """Test GET request with empty JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("empty")

        assert result == {}

    @patch('requests.Session.get')
    def test_get_array_response(self, mock_get):
        """Test GET request returning JSON array."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [1, 2, 3, 4, 5]
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("list")

        assert result == [1, 2, 3, 4, 5]

    @patch('requests.Session.get')
    def test_get_handles_404_error(self, mock_get):
        """Test GET request handles 404 Not Found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("nonexistent")

        assert result is None

    @patch('requests.Session.get')
    def test_get_handles_500_error(self, mock_get):
        """Test GET request handles 500 Internal Server Error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPError("500 Internal Server Error")
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("error")

        assert result is None

    @patch('requests.Session.get')
    def test_get_handles_401_unauthorized(self, mock_get):
        """Test GET request handles 401 Unauthorized error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("protected")

        assert result is None

    @patch('requests.Session.get')
    def test_get_handles_403_forbidden(self, mock_get):
        """Test GET request handles 403 Forbidden error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = HTTPError("403 Forbidden")
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("forbidden")

        assert result is None

    @patch('requests.Session.get')
    def test_get_handles_429_rate_limit(self, mock_get):
        """Test GET request handles 429 Rate Limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("rate-limited")

        assert result is None

    @patch('requests.Session.get')
    def test_get_handles_connection_error(self, mock_get):
        """Test GET request handles connection error."""
        mock_get.side_effect = ConnectionError("Failed to connect")

        client = BaseAPIClient("https://api.example.com")
        result = client.get("endpoint")

        assert result is None

    @patch('requests.Session.get')
    def test_get_handles_timeout(self, mock_get):
        """Test GET request handles timeout error."""
        mock_get.side_effect = Timeout("Request timed out")

        client = BaseAPIClient("https://api.example.com")
        result = client.get("slow-endpoint")

        assert result is None

    @patch('requests.Session.get')
    def test_get_handles_generic_request_exception(self, mock_get):
        """Test GET request handles generic request exception."""
        mock_get.side_effect = RequestException("Unknown error")

        client = BaseAPIClient("https://api.example.com")
        result = client.get("endpoint")

        assert result is None

    @patch('requests.Session.get')
    def test_get_handles_json_decode_error(self, mock_get):
        """Test GET request handles invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("invalid-json")

        assert result is None

    @patch('requests.Session.get')
    def test_get_with_empty_endpoint(self, mock_get):
        """Test GET request with empty endpoint string."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'root': 'data'}
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("")

        assert result == {'root': 'data'}
        mock_get.assert_called_once_with(
            "https://api.example.com/",
            params=None
        )

    @patch('requests.Session.get')
    def test_get_with_special_chars_in_params(self, mock_get):
        """Test GET request with special characters in parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'results': []}
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        params = {'query': 'AC/DC', 'genre': 'rock & roll'}
        result = client.get("search", params=params)

        assert result == {'results': []}
        mock_get.assert_called_once_with(
            "https://api.example.com/search",
            params=params
        )

    @patch('requests.Session.get')
    def test_get_with_numeric_params(self, mock_get):
        """Test GET request with numeric parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'page': 2}
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        params = {'limit': 50, 'offset': 100, 'year': 2024}
        result = client.get("items", params=params)

        assert result == {'page': 2}
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_get_with_boolean_params(self, mock_get):
        """Test GET request with boolean parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'filtered': True}
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        params = {'active': True, 'verified': False}
        result = client.get("users", params=params)

        assert result == {'filtered': True}

    @patch('requests.Session.get')
    @patch('music_tools_common.api.base.logger')
    def test_get_logs_error_on_failure(self, mock_logger, mock_get):
        """Test that errors are logged when GET request fails."""
        mock_get.side_effect = ConnectionError("Network error")

        client = BaseAPIClient("https://api.example.com")
        result = client.get("endpoint")

        assert result is None
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "API request failed" in call_args

    @patch('requests.Session.get')
    @patch('music_tools_common.api.base.logger')
    def test_get_logs_http_error_details(self, mock_logger, mock_get):
        """Test that HTTP errors are logged with details."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = HTTPError("503 Service Unavailable")
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("endpoint")

        assert result is None
        mock_logger.error.assert_called_once()


class TestBaseAPIClientEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @patch('requests.Session.get')
    def test_get_with_very_long_endpoint(self, mock_get):
        """Test GET request with very long endpoint path."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'ok'}
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        long_endpoint = "/".join(["path"] * 50)
        result = client.get(long_endpoint)

        assert result == {'data': 'ok'}

    @patch('requests.Session.get')
    def test_get_with_none_params(self, mock_get):
        """Test GET request explicitly passing None as params."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("endpoint", params=None)

        assert result == {'data': 'test'}
        mock_get.assert_called_once_with(
            "https://api.example.com/endpoint",
            params=None
        )

    @patch('requests.Session.get')
    def test_get_with_empty_params_dict(self, mock_get):
        """Test GET request with empty parameters dictionary."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': 'test'}
        mock_get.return_value = mock_response

        client = BaseAPIClient("https://api.example.com")
        result = client.get("endpoint", params={})

        assert result == {'data': 'test'}

    @patch('requests.Session.get')
    def test_multiple_consecutive_requests(self, mock_get):
        """Test multiple consecutive GET requests using same client."""
        mock_response1 = Mock(status_code=200)
        mock_response1.json.return_value = {'request': 1}
        mock_response2 = Mock(status_code=200)
        mock_response2.json.return_value = {'request': 2}
        mock_response3 = Mock(status_code=200)
        mock_response3.json.return_value = {'request': 3}

        mock_get.side_effect = [mock_response1, mock_response2, mock_response3]

        client = BaseAPIClient("https://api.example.com")
        result1 = client.get("endpoint1")
        result2 = client.get("endpoint2")
        result3 = client.get("endpoint3")

        assert result1 == {'request': 1}
        assert result2 == {'request': 2}
        assert result3 == {'request': 3}
        assert mock_get.call_count == 3

    def test_base_url_stored_correctly(self):
        """Test that base_url is stored and accessible."""
        urls = [
            "https://api.example.com",
            "http://localhost:8000",
            "https://api.service.io/v2",
        ]

        for url in urls:
            client = BaseAPIClient(url)
            assert client.base_url == url

    @patch('requests.Session.get')
    def test_get_preserves_response_type(self, mock_get):
        """Test that various JSON response types are preserved."""
        test_cases = [
            {'string': 'value'},
            [1, 2, 3],
            {'nested': {'data': {'value': 123}}},
            {'null_value': None},
            {'bool': True},
            {'number': 42.5},
        ]

        client = BaseAPIClient("https://api.example.com")

        for expected in test_cases:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = expected
            mock_get.return_value = mock_response

            result = client.get("test")
            assert result == expected


class TestBaseAPIClientIntegration:
    """Integration-style tests for BaseAPIClient."""

    @patch('requests.Session.get')
    def test_full_request_lifecycle(self, mock_get):
        """Test complete request lifecycle from init to response."""
        # Create client
        client = BaseAPIClient("https://api.example.com")
        assert client.base_url == "https://api.example.com"

        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [{'id': 1}, {'id': 2}],
            'total': 2
        }
        mock_get.return_value = mock_response

        # Make request
        result = client.get("items", params={'limit': 2})

        # Verify result
        assert result is not None
        assert 'items' in result
        assert len(result['items']) == 2
        assert result['total'] == 2

    @patch('requests.Session.get')
    def test_error_recovery_pattern(self, mock_get):
        """Test error handling and recovery pattern."""
        client = BaseAPIClient("https://api.example.com")

        # First request fails
        mock_get.side_effect = ConnectionError("Network error")
        result1 = client.get("endpoint")
        assert result1 is None

        # Second request succeeds (simulating retry logic)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'recovered': True}
        mock_get.side_effect = None
        mock_get.return_value = mock_response

        result2 = client.get("endpoint")
        assert result2 == {'recovered': True}


# Run with: pytest packages/common/tests/api/test_base.py -v
# Coverage: pytest packages/common/tests/api/test_base.py --cov=music_tools_common.api.base --cov-report=term-missing
