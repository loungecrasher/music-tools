"""Tests for Deezer API client module."""

from unittest.mock import Mock, patch

import pytest
import requests
from music_tools_common.api.deezer import DeezerClient
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    Timeout,
)


class TestDeezerClientInitialization:
    """Tests for DeezerClient initialization."""

    def test_init_sets_correct_base_url(self):
        """Test that DeezerClient initializes with correct Deezer API URL."""
        client = DeezerClient()

        assert client.base_url == "https://api.deezer.com"

    def test_init_creates_session(self):
        """Test that DeezerClient creates a requests session."""
        client = DeezerClient()

        assert hasattr(client, 'session')
        assert isinstance(client.session, requests.Session)

    def test_multiple_instances_have_separate_sessions(self):
        """Test that multiple DeezerClient instances have separate sessions."""
        client1 = DeezerClient()
        client2 = DeezerClient()

        assert client1.session is not client2.session

    def test_inherits_from_base_client(self):
        """Test that DeezerClient inherits from BaseAPIClient."""
        from music_tools_common.api.base import BaseAPIClient

        client = DeezerClient()
        assert isinstance(client, BaseAPIClient)

    def test_has_get_method(self):
        """Test that DeezerClient has inherited get method."""
        client = DeezerClient()

        assert hasattr(client, 'get')
        assert callable(client.get)


class TestDeezerClientRequests:
    """Tests for DeezerClient API requests."""

    @patch('requests.Session.get')
    def test_get_track_success(self, mock_get):
        """Test successful request to get track details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 3135556,
            'title': 'Harder Better Faster Stronger',
            'artist': {'name': 'Daft Punk'},
            'album': {'title': 'Discovery'},
            'duration': 224
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("track/3135556")

        assert result is not None
        assert result['title'] == 'Harder Better Faster Stronger'
        assert result['artist']['name'] == 'Daft Punk'
        mock_get.assert_called_once_with(
            "https://api.deezer.com/track/3135556",
            params=None
        )

    @patch('requests.Session.get')
    def test_search_tracks(self, mock_get):
        """Test searching for tracks."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 1, 'title': 'Track 1', 'artist': {'name': 'Artist 1'}},
                {'id': 2, 'title': 'Track 2', 'artist': {'name': 'Artist 2'}}
            ],
            'total': 2
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        params = {'q': 'rock', 'limit': 2}
        result = client.get("search/track", params=params)

        assert result is not None
        assert 'data' in result
        assert len(result['data']) == 2
        mock_get.assert_called_once_with(
            "https://api.deezer.com/search/track",
            params=params
        )

    @patch('requests.Session.get')
    def test_get_artist_success(self, mock_get):
        """Test successful request to get artist details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 27,
            'name': 'Daft Punk',
            'nb_album': 30,
            'nb_fan': 5000000,
            'picture': 'https://api.deezer.com/artist/27/image'
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("artist/27")

        assert result is not None
        assert result['name'] == 'Daft Punk'
        assert result['nb_fan'] == 5000000

    @patch('requests.Session.get')
    def test_get_album_success(self, mock_get):
        """Test successful request to get album details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 302127,
            'title': 'Discovery',
            'artist': {'name': 'Daft Punk'},
            'release_date': '2001-03-07',
            'nb_tracks': 14
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("album/302127")

        assert result is not None
        assert result['title'] == 'Discovery'
        assert result['nb_tracks'] == 14

    @patch('requests.Session.get')
    def test_get_playlist_success(self, mock_get):
        """Test successful request to get playlist details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 1234567890,
            'title': 'Top Hits 2024',
            'nb_tracks': 50,
            'fans': 150000,
            'creator': {'name': 'Deezer'}
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("playlist/1234567890")

        assert result is not None
        assert result['title'] == 'Top Hits 2024'
        assert result['nb_tracks'] == 50

    @patch('requests.Session.get')
    def test_get_user_profile(self, mock_get):
        """Test successful request to get user profile."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 123456,
            'name': 'Test User',
            'country': 'US',
            'status': 0
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("user/123456")

        assert result is not None
        assert result['name'] == 'Test User'

    @patch('requests.Session.get')
    def test_get_artist_top_tracks(self, mock_get):
        """Test getting artist's top tracks."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 1, 'title': 'Hit Song 1', 'rank': 900000},
                {'id': 2, 'title': 'Hit Song 2', 'rank': 800000}
            ]
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("artist/27/top", params={'limit': 2})

        assert result is not None
        assert len(result['data']) == 2

    @patch('requests.Session.get')
    def test_get_artist_albums(self, mock_get):
        """Test getting artist's albums."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 1, 'title': 'Album 1'},
                {'id': 2, 'title': 'Album 2'}
            ],
            'total': 2
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("artist/27/albums")

        assert result is not None
        assert 'data' in result

    @patch('requests.Session.get')
    def test_get_album_tracks(self, mock_get):
        """Test getting tracks from an album."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 1, 'title': 'Track 1', 'duration': 180},
                {'id': 2, 'title': 'Track 2', 'duration': 210}
            ]
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("album/302127/tracks")

        assert result is not None
        assert len(result['data']) == 2

    @patch('requests.Session.get')
    def test_pagination_with_index(self, mock_get):
        """Test pagination using index parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'id': str(i)} for i in range(25)],
            'total': 100,
            'next': 'https://api.deezer.com/search?index=25'
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        params = {'index': 0, 'limit': 25}
        result = client.get("search", params=params)

        assert result is not None
        assert len(result['data']) == 25


class TestDeezerClientErrorHandling:
    """Tests for Deezer API error handling."""

    @patch('requests.Session.get')
    def test_unauthorized_401_error(self, mock_get):
        """Test handling of 401 Unauthorized error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("user/me")

        assert result is None

    @patch('requests.Session.get')
    def test_forbidden_403_error(self, mock_get):
        """Test handling of 403 Forbidden error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = HTTPError("403 Forbidden")
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("user/me/playlists")

        assert result is None

    @patch('requests.Session.get')
    def test_not_found_404_error(self, mock_get):
        """Test handling of 404 Not Found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("track/999999999")

        assert result is None

    @patch('requests.Session.get')
    def test_rate_limit_error(self, mock_get):
        """Test handling of rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("search")

        assert result is None

    @patch('requests.Session.get')
    def test_server_error_500(self, mock_get):
        """Test handling of 500 Internal Server Error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPError("500 Internal Server Error")
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("track/123")

        assert result is None

    @patch('requests.Session.get')
    def test_service_unavailable_503(self, mock_get):
        """Test handling of 503 Service Unavailable error."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = HTTPError("503 Service Unavailable")
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("artist/27")

        assert result is None

    @patch('requests.Session.get')
    def test_bad_request_400(self, mock_get):
        """Test handling of 400 Bad Request error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = HTTPError("400 Bad Request")
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("search", params={'invalid': 'param'})

        assert result is None

    @patch('requests.Session.get')
    def test_connection_error(self, mock_get):
        """Test handling of connection error."""
        mock_get.side_effect = ConnectionError("Failed to connect to Deezer API")

        client = DeezerClient()
        result = client.get("track/123")

        assert result is None

    @patch('requests.Session.get')
    def test_timeout_error(self, mock_get):
        """Test handling of timeout error."""
        mock_get.side_effect = Timeout("Request to Deezer API timed out")

        client = DeezerClient()
        result = client.get("search")

        assert result is None

    @patch('requests.Session.get')
    def test_invalid_json_response(self, mock_get):
        """Test handling of invalid JSON in response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("track/123")

        assert result is None

    @patch('requests.Session.get')
    def test_data_exception_error(self, mock_get):
        """Test handling of Deezer error response with error object."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'error': {
                'type': 'DataException',
                'message': 'no data',
                'code': 800
            }
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("track/invalid")

        # Deezer returns 200 with error object, but our client returns it
        assert result is not None
        assert 'error' in result


class TestDeezerClientDataRetrieval:
    """Tests for various data retrieval scenarios."""

    @patch('requests.Session.get')
    def test_search_with_strict_mode(self, mock_get):
        """Test search with strict mode enabled."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 1, 'title': 'Exact Match'}
            ]
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        params = {'q': 'exact match', 'strict': 'on'}
        result = client.get("search", params=params)

        assert result is not None
        assert len(result['data']) == 1

    @patch('requests.Session.get')
    def test_search_artist(self, mock_get):
        """Test searching for artists."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 1, 'name': 'Artist 1'},
                {'id': 2, 'name': 'Artist 2'}
            ]
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("search/artist", params={'q': 'rock'})

        assert result is not None
        assert 'data' in result

    @patch('requests.Session.get')
    def test_search_album(self, mock_get):
        """Test searching for albums."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 1, 'title': 'Album 1'},
                {'id': 2, 'title': 'Album 2'}
            ]
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("search/album", params={'q': 'discovery'})

        assert result is not None

    @patch('requests.Session.get')
    def test_get_genre_artists(self, mock_get):
        """Test getting artists for a genre."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 1, 'name': 'Rock Artist 1'},
                {'id': 2, 'name': 'Rock Artist 2'}
            ]
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("genre/132/artists")  # Rock genre ID

        assert result is not None

    @patch('requests.Session.get')
    def test_get_chart_tracks(self, mock_get):
        """Test getting chart tracks."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tracks': {
                'data': [
                    {'id': 1, 'title': 'Chart Track 1'},
                    {'id': 2, 'title': 'Chart Track 2'}
                ]
            }
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("chart")

        assert result is not None
        assert 'tracks' in result

    @patch('requests.Session.get')
    def test_get_editorial_selection(self, mock_get):
        """Test getting editorial selection."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 1, 'name': 'Editorial 1'},
                {'id': 2, 'name': 'Editorial 2'}
            ]
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("editorial")

        assert result is not None

    @patch('requests.Session.get')
    def test_get_radio_list(self, mock_get):
        """Test getting radio list."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': 1, 'title': 'Radio 1'},
                {'id': 2, 'title': 'Radio 2'}
            ]
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("radio")

        assert result is not None


class TestDeezerClientEdgeCases:
    """Tests for edge cases and special scenarios."""

    @patch('requests.Session.get')
    def test_empty_search_results(self, mock_get):
        """Test handling of empty search results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [],
            'total': 0
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("search", params={'q': 'nonexistentsong123456'})

        assert result is not None
        assert result['data'] == []
        assert result['total'] == 0

    @patch('requests.Session.get')
    def test_special_characters_in_search(self, mock_get):
        """Test search with special characters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': []}
        mock_get.return_value = mock_response

        client = DeezerClient()
        params = {'q': 'AC/DC'}
        result = client.get("search/artist", params=params)

        assert result is not None
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_unicode_in_search(self, mock_get):
        """Test search with Unicode characters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'name': 'Björk'}]
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        params = {'q': 'Björk'}
        result = client.get("search/artist", params=params)

        assert result is not None

    @patch('requests.Session.get')
    def test_very_long_query(self, mock_get):
        """Test search with very long query string."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': []}
        mock_get.return_value = mock_response

        client = DeezerClient()
        long_query = 'a' * 500
        result = client.get("search", params={'q': long_query})

        assert result is not None

    @patch('requests.Session.get')
    def test_numeric_string_ids(self, mock_get):
        """Test handling of numeric string IDs."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': '123456', 'title': 'Test'}
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("track/123456")

        assert result is not None

    @patch('requests.Session.get')
    def test_concurrent_requests_same_client(self, mock_get):
        """Test multiple concurrent-style requests with same client instance."""
        responses = [
            Mock(status_code=200, json=lambda: {'id': 1}),
            Mock(status_code=200, json=lambda: {'id': 2}),
            Mock(status_code=200, json=lambda: {'id': 3})
        ]
        mock_get.side_effect = responses

        client = DeezerClient()
        result1 = client.get("track/1")
        result2 = client.get("track/2")
        result3 = client.get("track/3")

        assert result1['id'] == 1
        assert result2['id'] == 2
        assert result3['id'] == 3
        assert mock_get.call_count == 3

    @patch('requests.Session.get')
    def test_response_with_null_values(self, mock_get):
        """Test handling of null values in response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 123,
            'title': 'Track',
            'artist': None,
            'contributors': []
        }
        mock_get.return_value = mock_response

        client = DeezerClient()
        result = client.get("track/123")

        assert result is not None
        assert result['artist'] is None


class TestDeezerClientIntegration:
    """Integration-style tests simulating real usage patterns."""

    @patch('requests.Session.get')
    def test_search_and_get_details_workflow(self, mock_get):
        """Test workflow: search for track, then get details."""
        # First request: search
        search_response = Mock()
        search_response.status_code = 200
        search_response.json.return_value = {
            'data': [{'id': 3135556, 'title': 'Test Track'}]
        }

        # Second request: get track details
        details_response = Mock()
        details_response.status_code = 200
        details_response.json.return_value = {
            'id': 3135556,
            'title': 'Test Track',
            'artist': {'name': 'Test Artist'},
            'album': {'title': 'Test Album'}
        }

        mock_get.side_effect = [search_response, details_response]

        client = DeezerClient()

        # Search
        search_result = client.get("search", params={'q': 'test'})
        assert search_result is not None
        track_id = search_result['data'][0]['id']

        # Get details
        details = client.get(f"track/{track_id}")
        assert details is not None
        assert details['title'] == 'Test Track'

    @patch('requests.Session.get')
    def test_pagination_workflow(self, mock_get):
        """Test workflow: paginate through results."""
        # Setup responses for multiple pages
        page1 = Mock(status_code=200)
        page1.json.return_value = {
            'data': [{'id': i} for i in range(25)],
            'total': 100,
            'next': 'https://api.deezer.com/search?index=25'
        }

        page2 = Mock(status_code=200)
        page2.json.return_value = {
            'data': [{'id': i} for i in range(25, 50)],
            'total': 100,
            'next': 'https://api.deezer.com/search?index=50'
        }

        mock_get.side_effect = [page1, page2]

        client = DeezerClient()

        # Get first page
        result1 = client.get("search", params={'index': 0})
        assert len(result1['data']) == 25

        # Get second page
        result2 = client.get("search", params={'index': 25})
        assert len(result2['data']) == 25

    @patch('requests.Session.get')
    def test_artist_exploration_workflow(self, mock_get):
        """Test workflow: get artist, then albums, then tracks."""
        # Artist details
        artist_response = Mock(status_code=200)
        artist_response.json.return_value = {
            'id': 27,
            'name': 'Daft Punk'
        }

        # Artist albums
        albums_response = Mock(status_code=200)
        albums_response.json.return_value = {
            'data': [{'id': 302127, 'title': 'Discovery'}]
        }

        # Album tracks
        tracks_response = Mock(status_code=200)
        tracks_response.json.return_value = {
            'data': [
                {'id': 1, 'title': 'Track 1'},
                {'id': 2, 'title': 'Track 2'}
            ]
        }

        mock_get.side_effect = [artist_response, albums_response, tracks_response]

        client = DeezerClient()

        # Get artist
        artist = client.get("artist/27")
        assert artist['name'] == 'Daft Punk'

        # Get albums
        albums = client.get("artist/27/albums")
        album_id = albums['data'][0]['id']

        # Get tracks
        tracks = client.get(f"album/{album_id}/tracks")
        assert len(tracks['data']) == 2


# Run with: pytest packages/common/tests/api/test_deezer.py -v
# Coverage: pytest packages/common/tests/api/test_deezer.py --cov=music_tools_common.api.deezer --cov-report=term-missing
