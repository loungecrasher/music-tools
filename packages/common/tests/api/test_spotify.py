"""Tests for Spotify API client module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.exceptions import (
    ConnectionError,
    Timeout,
    HTTPError,
)

from music_tools_common.api.spotify import SpotifyClient


class TestSpotifyClientInitialization:
    """Tests for SpotifyClient initialization."""

    def test_init_sets_correct_base_url(self):
        """Test that SpotifyClient initializes with correct Spotify API URL."""
        client = SpotifyClient()

        assert client.base_url == "https://api.spotify.com/v1"

    def test_init_creates_session(self):
        """Test that SpotifyClient creates a requests session."""
        client = SpotifyClient()

        assert hasattr(client, 'session')
        assert isinstance(client.session, requests.Session)

    def test_multiple_instances_have_separate_sessions(self):
        """Test that multiple SpotifyClient instances have separate sessions."""
        client1 = SpotifyClient()
        client2 = SpotifyClient()

        assert client1.session is not client2.session

    def test_inherits_from_base_client(self):
        """Test that SpotifyClient inherits from BaseAPIClient."""
        from music_tools_common.api.base import BaseAPIClient

        client = SpotifyClient()
        assert isinstance(client, BaseAPIClient)

    def test_has_get_method(self):
        """Test that SpotifyClient has inherited get method."""
        client = SpotifyClient()

        assert hasattr(client, 'get')
        assert callable(client.get)


class TestSpotifyClientRequests:
    """Tests for SpotifyClient API requests."""

    @patch('requests.Session.get')
    def test_get_track_success(self, mock_get):
        """Test successful request to get track details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '3n3Ppam7vgaVa1iaRUc9Lp',
            'name': 'Mr. Brightside',
            'artists': [{'name': 'The Killers'}],
            'album': {'name': 'Hot Fuss'}
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("tracks/3n3Ppam7vgaVa1iaRUc9Lp")

        assert result is not None
        assert result['name'] == 'Mr. Brightside'
        assert result['artists'][0]['name'] == 'The Killers'
        mock_get.assert_called_once_with(
            "https://api.spotify.com/v1/tracks/3n3Ppam7vgaVa1iaRUc9Lp",
            params=None
        )

    @patch('requests.Session.get')
    def test_search_tracks(self, mock_get):
        """Test searching for tracks."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tracks': {
                'items': [
                    {'id': '1', 'name': 'Track 1'},
                    {'id': '2', 'name': 'Track 2'}
                ],
                'total': 2
            }
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        params = {'q': 'rock', 'type': 'track', 'limit': 2}
        result = client.get("search", params=params)

        assert result is not None
        assert 'tracks' in result
        assert len(result['tracks']['items']) == 2
        mock_get.assert_called_once_with(
            "https://api.spotify.com/v1/search",
            params=params
        )

    @patch('requests.Session.get')
    def test_get_artist_success(self, mock_get):
        """Test successful request to get artist details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '0OdUWJ0sBjDrqHygGUXeCF',
            'name': 'Band of Horses',
            'genres': ['indie rock', 'alternative'],
            'popularity': 65
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("artists/0OdUWJ0sBjDrqHygGUXeCF")

        assert result is not None
        assert result['name'] == 'Band of Horses'
        assert 'indie rock' in result['genres']

    @patch('requests.Session.get')
    def test_get_album_success(self, mock_get):
        """Test successful request to get album details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '4aawyAB9vmqN3uQ7FjRGTy',
            'name': 'Global Warming',
            'artists': [{'name': 'Pitbull'}],
            'release_date': '2012-11-19',
            'total_tracks': 13
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("albums/4aawyAB9vmqN3uQ7FjRGTy")

        assert result is not None
        assert result['name'] == 'Global Warming'
        assert result['total_tracks'] == 13

    @patch('requests.Session.get')
    def test_get_playlist_success(self, mock_get):
        """Test successful request to get playlist details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': '37i9dQZF1DXcBWIGoYBM5M',
            'name': 'Today\'s Top Hits',
            'tracks': {'total': 50},
            'followers': {'total': 31000000}
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("playlists/37i9dQZF1DXcBWIGoYBM5M")

        assert result is not None
        assert result['name'] == 'Today\'s Top Hits'
        assert result['tracks']['total'] == 50

    @patch('requests.Session.get')
    def test_get_user_profile(self, mock_get):
        """Test successful request to get user profile."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'testuser',
            'display_name': 'Test User',
            'followers': {'total': 100},
            'country': 'US'
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("users/testuser")

        assert result is not None
        assert result['display_name'] == 'Test User'

    @patch('requests.Session.get')
    def test_pagination_with_limit_offset(self, mock_get):
        """Test pagination using limit and offset parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [{'id': str(i)} for i in range(10)],
            'limit': 10,
            'offset': 20,
            'total': 100
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        params = {'limit': 10, 'offset': 20}
        result = client.get("me/tracks", params=params)

        assert result is not None
        assert result['limit'] == 10
        assert result['offset'] == 20
        assert len(result['items']) == 10

    @patch('requests.Session.get')
    def test_market_parameter(self, mock_get):
        """Test request with market parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tracks': {'items': []}
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        params = {'q': 'test', 'type': 'track', 'market': 'US'}
        result = client.get("search", params=params)

        assert result is not None
        mock_get.assert_called_once()
        call_params = mock_get.call_args[1]['params']
        assert call_params['market'] == 'US'


class TestSpotifyClientErrorHandling:
    """Tests for Spotify API error handling."""

    @patch('requests.Session.get')
    def test_unauthorized_401_error(self, mock_get):
        """Test handling of 401 Unauthorized error (invalid/expired token)."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = HTTPError("401 Unauthorized")
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("me/tracks")

        assert result is None

    @patch('requests.Session.get')
    def test_forbidden_403_error(self, mock_get):
        """Test handling of 403 Forbidden error (insufficient permissions)."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = HTTPError("403 Forbidden")
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("me/player/play")

        assert result is None

    @patch('requests.Session.get')
    def test_not_found_404_error(self, mock_get):
        """Test handling of 404 Not Found error (invalid resource)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("tracks/invalidtrackid123")

        assert result is None

    @patch('requests.Session.get')
    def test_rate_limit_429_error(self, mock_get):
        """Test handling of 429 Rate Limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = HTTPError("429 Too Many Requests")
        mock_response.headers = {'Retry-After': '30'}
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("search")

        assert result is None

    @patch('requests.Session.get')
    def test_server_error_500(self, mock_get):
        """Test handling of 500 Internal Server Error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = HTTPError("500 Internal Server Error")
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("tracks/123")

        assert result is None

    @patch('requests.Session.get')
    def test_service_unavailable_503(self, mock_get):
        """Test handling of 503 Service Unavailable error."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.raise_for_status.side_effect = HTTPError("503 Service Unavailable")
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("me/tracks")

        assert result is None

    @patch('requests.Session.get')
    def test_bad_request_400(self, mock_get):
        """Test handling of 400 Bad Request error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = HTTPError("400 Bad Request")
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("search", params={'invalid': 'param'})

        assert result is None

    @patch('requests.Session.get')
    def test_connection_error(self, mock_get):
        """Test handling of connection error."""
        mock_get.side_effect = ConnectionError("Failed to connect to Spotify API")

        client = SpotifyClient()
        result = client.get("tracks/123")

        assert result is None

    @patch('requests.Session.get')
    def test_timeout_error(self, mock_get):
        """Test handling of timeout error."""
        mock_get.side_effect = Timeout("Request to Spotify API timed out")

        client = SpotifyClient()
        result = client.get("search")

        assert result is None

    @patch('requests.Session.get')
    def test_invalid_json_response(self, mock_get):
        """Test handling of invalid JSON in response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("tracks/123")

        assert result is None


class TestSpotifyClientDataRetrieval:
    """Tests for various data retrieval scenarios."""

    @patch('requests.Session.get')
    def test_get_multiple_tracks(self, mock_get):
        """Test getting multiple tracks in one request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tracks': [
                {'id': '1', 'name': 'Track 1'},
                {'id': '2', 'name': 'Track 2'},
                {'id': '3', 'name': 'Track 3'}
            ]
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        params = {'ids': '1,2,3'}
        result = client.get("tracks", params=params)

        assert result is not None
        assert len(result['tracks']) == 3

    @patch('requests.Session.get')
    def test_get_artist_top_tracks(self, mock_get):
        """Test getting artist's top tracks."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tracks': [
                {'id': '1', 'name': 'Hit Song 1', 'popularity': 95},
                {'id': '2', 'name': 'Hit Song 2', 'popularity': 87}
            ]
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("artists/123/top-tracks", params={'market': 'US'})

        assert result is not None
        assert len(result['tracks']) == 2
        assert result['tracks'][0]['popularity'] > result['tracks'][1]['popularity']

    @patch('requests.Session.get')
    def test_get_related_artists(self, mock_get):
        """Test getting related artists."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'artists': [
                {'id': '1', 'name': 'Similar Artist 1'},
                {'id': '2', 'name': 'Similar Artist 2'}
            ]
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("artists/123/related-artists")

        assert result is not None
        assert 'artists' in result
        assert len(result['artists']) == 2

    @patch('requests.Session.get')
    def test_get_new_releases(self, mock_get):
        """Test getting new album releases."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'albums': {
                'items': [
                    {'id': '1', 'name': 'New Album 1'},
                    {'id': '2', 'name': 'New Album 2'}
                ]
            }
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("browse/new-releases", params={'limit': 2})

        assert result is not None
        assert 'albums' in result

    @patch('requests.Session.get')
    def test_get_featured_playlists(self, mock_get):
        """Test getting featured playlists."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': 'Popular Playlists',
            'playlists': {
                'items': [
                    {'id': '1', 'name': 'Playlist 1'},
                    {'id': '2', 'name': 'Playlist 2'}
                ]
            }
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("browse/featured-playlists")

        assert result is not None
        assert 'playlists' in result

    @patch('requests.Session.get')
    def test_get_categories(self, mock_get):
        """Test getting browse categories."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'categories': {
                'items': [
                    {'id': 'rock', 'name': 'Rock'},
                    {'id': 'pop', 'name': 'Pop'}
                ]
            }
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("browse/categories")

        assert result is not None
        assert 'categories' in result

    @patch('requests.Session.get')
    def test_get_recommendations(self, mock_get):
        """Test getting track recommendations."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tracks': [
                {'id': '1', 'name': 'Recommended 1'},
                {'id': '2', 'name': 'Recommended 2'}
            ],
            'seeds': [{'id': 'seed1', 'type': 'artist'}]
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        params = {
            'seed_artists': 'artist1,artist2',
            'limit': 2
        }
        result = client.get("recommendations", params=params)

        assert result is not None
        assert 'tracks' in result
        assert 'seeds' in result


class TestSpotifyClientEdgeCases:
    """Tests for edge cases and special scenarios."""

    @patch('requests.Session.get')
    def test_empty_search_results(self, mock_get):
        """Test handling of empty search results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tracks': {
                'items': [],
                'total': 0
            }
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        result = client.get("search", params={'q': 'nonexistentsong123456'})

        assert result is not None
        assert result['tracks']['items'] == []
        assert result['tracks']['total'] == 0

    @patch('requests.Session.get')
    def test_special_characters_in_search(self, mock_get):
        """Test search with special characters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'tracks': {'items': []}}
        mock_get.return_value = mock_response

        client = SpotifyClient()
        params = {'q': 'AC/DC', 'type': 'artist'}
        result = client.get("search", params=params)

        assert result is not None
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_unicode_in_search(self, mock_get):
        """Test search with Unicode characters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tracks': {
                'items': [{'name': 'Björk - Army of Me'}]
            }
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        params = {'q': 'Björk', 'type': 'artist'}
        result = client.get("search", params=params)

        assert result is not None

    @patch('requests.Session.get')
    def test_very_long_query(self, mock_get):
        """Test search with very long query string."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'tracks': {'items': []}}
        mock_get.return_value = mock_response

        client = SpotifyClient()
        long_query = 'a' * 500
        result = client.get("search", params={'q': long_query})

        assert result is not None

    @patch('requests.Session.get')
    def test_multiple_search_types(self, mock_get):
        """Test search with multiple types."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tracks': {'items': []},
            'artists': {'items': []},
            'albums': {'items': []}
        }
        mock_get.return_value = mock_response

        client = SpotifyClient()
        params = {'q': 'rock', 'type': 'track,artist,album'}
        result = client.get("search", params=params)

        assert result is not None
        assert 'tracks' in result
        assert 'artists' in result
        assert 'albums' in result

    @patch('requests.Session.get')
    def test_concurrent_requests_same_client(self, mock_get):
        """Test multiple concurrent-style requests with same client instance."""
        responses = [
            Mock(status_code=200, json=lambda: {'id': '1'}),
            Mock(status_code=200, json=lambda: {'id': '2'}),
            Mock(status_code=200, json=lambda: {'id': '3'})
        ]
        mock_get.side_effect = responses

        client = SpotifyClient()
        result1 = client.get("tracks/1")
        result2 = client.get("tracks/2")
        result3 = client.get("tracks/3")

        assert result1['id'] == '1'
        assert result2['id'] == '2'
        assert result3['id'] == '3'
        assert mock_get.call_count == 3


class TestSpotifyClientIntegration:
    """Integration-style tests simulating real usage patterns."""

    @patch('requests.Session.get')
    def test_search_and_get_details_workflow(self, mock_get):
        """Test workflow: search for track, then get details."""
        # First request: search
        search_response = Mock()
        search_response.status_code = 200
        search_response.json.return_value = {
            'tracks': {
                'items': [{'id': 'track123', 'name': 'Test Track'}]
            }
        }

        # Second request: get track details
        details_response = Mock()
        details_response.status_code = 200
        details_response.json.return_value = {
            'id': 'track123',
            'name': 'Test Track',
            'artists': [{'name': 'Test Artist'}],
            'album': {'name': 'Test Album'}
        }

        mock_get.side_effect = [search_response, details_response]

        client = SpotifyClient()

        # Search
        search_result = client.get("search", params={'q': 'test', 'type': 'track'})
        assert search_result is not None
        track_id = search_result['tracks']['items'][0]['id']

        # Get details
        details = client.get(f"tracks/{track_id}")
        assert details is not None
        assert details['name'] == 'Test Track'

    @patch('requests.Session.get')
    def test_pagination_workflow(self, mock_get):
        """Test workflow: paginate through results."""
        # Setup responses for multiple pages
        page1 = Mock(status_code=200)
        page1.json.return_value = {
            'items': [{'id': str(i)} for i in range(20)],
            'limit': 20,
            'offset': 0,
            'total': 100,
            'next': 'https://api.spotify.com/v1/me/tracks?offset=20'
        }

        page2 = Mock(status_code=200)
        page2.json.return_value = {
            'items': [{'id': str(i)} for i in range(20, 40)],
            'limit': 20,
            'offset': 20,
            'total': 100,
            'next': 'https://api.spotify.com/v1/me/tracks?offset=40'
        }

        mock_get.side_effect = [page1, page2]

        client = SpotifyClient()

        # Get first page
        result1 = client.get("me/tracks", params={'limit': 20, 'offset': 0})
        assert len(result1['items']) == 20

        # Get second page
        result2 = client.get("me/tracks", params={'limit': 20, 'offset': 20})
        assert len(result2['items']) == 20
        assert result2['offset'] == 20


# Run with: pytest packages/common/tests/api/test_spotify.py -v
# Coverage: pytest packages/common/tests/api/test_spotify.py --cov=music_tools_common.api.spotify --cov-report=term-missing
