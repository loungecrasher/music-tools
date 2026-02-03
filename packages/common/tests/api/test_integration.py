"""Integration tests for API module.

Tests multi-client scenarios, cross-platform operations, and complex workflows.
"""

import threading
from unittest.mock import Mock, patch

import pytest
import requests
from music_tools_common.api.base import BaseAPIClient
from music_tools_common.api.deezer import DeezerClient
from music_tools_common.api.spotify import SpotifyClient
from requests.exceptions import ConnectionError, Timeout


class TestMultiClientOperations:
    """Tests for using multiple API clients simultaneously."""

    @patch("requests.Session.get")
    def test_spotify_and_deezer_clients_independently(self, mock_get):
        """Test that Spotify and Deezer clients work independently."""
        # Setup responses for both clients
        spotify_response = Mock()
        spotify_response.status_code = 200
        spotify_response.json.return_value = {"service": "spotify"}

        deezer_response = Mock()
        deezer_response.status_code = 200
        deezer_response.json.return_value = {"service": "deezer"}

        mock_get.side_effect = [spotify_response, deezer_response]

        # Create both clients
        spotify_client = SpotifyClient()
        deezer_client = DeezerClient()

        # Make requests
        spotify_result = spotify_client.get("tracks/123")
        deezer_result = deezer_client.get("track/456")

        # Verify both worked
        assert spotify_result["service"] == "spotify"
        assert deezer_result["service"] == "deezer"
        assert mock_get.call_count == 2

    @patch("requests.Session.get")
    def test_multiple_clients_separate_sessions(self, mock_get):
        """Test that multiple clients maintain separate sessions."""
        spotify1 = SpotifyClient()
        spotify2 = SpotifyClient()
        deezer1 = DeezerClient()

        # Sessions should be independent
        assert spotify1.session is not spotify2.session
        assert spotify1.session is not deezer1.session
        assert spotify2.session is not deezer1.session

    @patch("requests.Session.get")
    def test_cross_platform_search(self, mock_get):
        """Test searching for same content across platforms."""
        # Spotify search response
        spotify_response = Mock()
        spotify_response.status_code = 200
        spotify_response.json.return_value = {
            "tracks": {"items": [{"id": "spotify123", "name": "Test Song"}]}
        }

        # Deezer search response
        deezer_response = Mock()
        deezer_response.status_code = 200
        deezer_response.json.return_value = {"data": [{"id": 456789, "title": "Test Song"}]}

        mock_get.side_effect = [spotify_response, deezer_response]

        spotify_client = SpotifyClient()
        deezer_client = DeezerClient()

        # Search on both platforms
        spotify_results = spotify_client.get("search", params={"q": "test song"})
        deezer_results = deezer_client.get("search", params={"q": "test song"})

        # Verify both returned results
        assert len(spotify_results["tracks"]["items"]) > 0
        assert len(deezer_results["data"]) > 0

    @patch("requests.Session.get")
    def test_parallel_requests_different_clients(self, mock_get):
        """Test making parallel requests to different API clients."""
        # Setup responses
        responses = [
            Mock(status_code=200, json=lambda: {"source": "spotify1"}),
            Mock(status_code=200, json=lambda: {"source": "deezer1"}),
            Mock(status_code=200, json=lambda: {"source": "spotify2"}),
            Mock(status_code=200, json=lambda: {"source": "deezer2"}),
        ]
        mock_get.side_effect = responses

        spotify_client = SpotifyClient()
        deezer_client = DeezerClient()

        # Make requests
        s1 = spotify_client.get("tracks/1")
        d1 = deezer_client.get("track/1")
        s2 = spotify_client.get("tracks/2")
        d2 = deezer_client.get("track/2")

        # Verify all succeeded
        assert s1["source"] == "spotify1"
        assert d1["source"] == "deezer1"
        assert s2["source"] == "spotify2"
        assert d2["source"] == "deezer2"


class TestErrorHandlingAcrossClients:
    """Tests for error handling patterns across multiple clients."""

    @patch("requests.Session.get")
    def test_one_client_fails_other_succeeds(self, mock_get):
        """Test that failure in one client doesn't affect another."""
        # Spotify fails, Deezer succeeds
        spotify_response = Mock()
        spotify_response.status_code = 500
        spotify_response.raise_for_status.side_effect = Exception("Spotify error")

        deezer_response = Mock()
        deezer_response.status_code = 200
        deezer_response.json.return_value = {"data": "success"}

        mock_get.side_effect = [Exception("Spotify error"), deezer_response]

        spotify_client = SpotifyClient()
        deezer_client = DeezerClient()

        spotify_result = spotify_client.get("tracks/123")
        deezer_result = deezer_client.get("track/456")

        assert spotify_result is None
        assert deezer_result is not None
        assert deezer_result["data"] == "success"

    @patch("requests.Session.get")
    def test_fallback_pattern_spotify_to_deezer(self, mock_get):
        """Test fallback pattern: try Spotify, fallback to Deezer."""
        # Spotify fails
        spotify_error = Mock()
        spotify_error.raise_for_status.side_effect = Exception("404")

        # Deezer succeeds
        deezer_response = Mock()
        deezer_response.status_code = 200
        deezer_response.json.return_value = {"id": 123, "title": "Found on Deezer"}

        mock_get.side_effect = [Exception("404"), deezer_response]

        spotify_client = SpotifyClient()
        deezer_client = DeezerClient()

        # Try Spotify first
        result = spotify_client.get("tracks/unknown")
        if result is None:
            # Fallback to Deezer
            result = deezer_client.get("track/123")

        assert result is not None
        assert result["title"] == "Found on Deezer"

    @patch("requests.Session.get")
    def test_both_clients_fail_gracefully(self, mock_get):
        """Test graceful handling when both clients fail."""
        mock_get.side_effect = [ConnectionError("Spotify down"), ConnectionError("Deezer down")]

        spotify_client = SpotifyClient()
        deezer_client = DeezerClient()

        spotify_result = spotify_client.get("tracks/123")
        deezer_result = deezer_client.get("track/456")

        assert spotify_result is None
        assert deezer_result is None


class TestSessionPersistence:
    """Tests for session management and persistence."""

    @patch("requests.Session.get")
    def test_session_reuse_across_requests(self, mock_get):
        """Test that session is reused for multiple requests."""
        responses = [
            Mock(status_code=200, json=lambda: {"request": 1}),
            Mock(status_code=200, json=lambda: {"request": 2}),
            Mock(status_code=200, json=lambda: {"request": 3}),
        ]
        mock_get.side_effect = responses

        client = SpotifyClient()
        session = client.session

        client.get("tracks/1")
        client.get("tracks/2")
        client.get("tracks/3")

        # Session should be the same object
        assert client.session is session

    @patch("requests.Session.get")
    def test_session_headers_persist(self, mock_get):
        """Test that session modifications persist across requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        client = SpotifyClient()

        # Add custom headers to session
        client.session.headers.update({"Authorization": "Bearer token123"})
        custom_header = client.session.headers.get("Authorization")

        # Make request
        client.get("me/tracks")

        # Header should still be there
        assert client.session.headers.get("Authorization") == custom_header

    def test_multiple_instances_independent_sessions(self):
        """Test that different instances have independent sessions."""
        client1 = SpotifyClient()
        client2 = SpotifyClient()

        client1.session.headers.update({"X-Custom": "client1"})
        client2.session.headers.update({"X-Custom": "client2"})

        assert client1.session.headers.get("X-Custom") == "client1"
        assert client2.session.headers.get("X-Custom") == "client2"


class TestConcurrentAPIRequests:
    """Tests for concurrent API request scenarios."""

    @patch("requests.Session.get")
    def test_sequential_requests_same_client(self, mock_get):
        """Test sequential requests maintain order."""
        responses = [Mock(status_code=200, json=lambda n=i: {"order": n}) for i in range(5)]
        mock_get.side_effect = responses

        client = SpotifyClient()
        results = []

        for i in range(5):
            result = client.get(f"tracks/{i}")
            results.append(result)

        # Verify order maintained
        for i, result in enumerate(results):
            assert result["order"] == i

    @patch("requests.Session.get")
    def test_client_thread_safety_basic(self, mock_get):
        """Test basic thread safety of client usage."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_get.return_value = mock_response

        client = SpotifyClient()
        results = []
        lock = threading.Lock()

        def make_request(endpoint):
            result = client.get(endpoint)
            with lock:
                results.append(result)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(f"tracks/{i}",))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert len(results) == 5
        for result in results:
            assert result is not None


class TestComplexWorkflows:
    """Tests for complex multi-step workflows."""

    @patch("requests.Session.get")
    def test_complete_music_discovery_workflow(self, mock_get):
        """Test complete workflow: search artist, get albums, get tracks."""
        # 1. Search for artist
        search_response = Mock(status_code=200)
        search_response.json.return_value = {
            "artists": {"items": [{"id": "artist123", "name": "Test Artist"}]}
        }

        # 2. Get artist details
        artist_response = Mock(status_code=200)
        artist_response.json.return_value = {
            "id": "artist123",
            "name": "Test Artist",
            "genres": ["rock"],
        }

        # 3. Get artist albums
        albums_response = Mock(status_code=200)
        albums_response.json.return_value = {
            "items": [{"id": "album1", "name": "Album 1"}, {"id": "album2", "name": "Album 2"}]
        }

        # 4. Get album tracks
        tracks_response = Mock(status_code=200)
        tracks_response.json.return_value = {
            "items": [{"id": "track1", "name": "Track 1"}, {"id": "track2", "name": "Track 2"}]
        }

        mock_get.side_effect = [search_response, artist_response, albums_response, tracks_response]

        client = SpotifyClient()

        # Execute workflow
        search = client.get("search", params={"q": "test artist", "type": "artist"})
        artist_id = search["artists"]["items"][0]["id"]

        artist = client.get(f"artists/{artist_id}")
        assert artist["name"] == "Test Artist"

        albums = client.get(f"artists/{artist_id}/albums")
        assert len(albums["items"]) == 2

        album_id = albums["items"][0]["id"]
        tracks = client.get(f"albums/{album_id}/tracks")
        assert len(tracks["items"]) == 2

    @patch("requests.Session.get")
    def test_data_aggregation_across_platforms(self, mock_get):
        """Test aggregating data from multiple platforms."""
        # Spotify response
        spotify_response = Mock(status_code=200)
        spotify_response.json.return_value = {
            "tracks": {"items": [{"id": "1", "name": "Song A", "popularity": 80}]}
        }

        # Deezer response
        deezer_response = Mock(status_code=200)
        deezer_response.json.return_value = {"data": [{"id": 1, "title": "Song A", "rank": 500000}]}

        mock_get.side_effect = [spotify_response, deezer_response]

        spotify_client = SpotifyClient()
        deezer_client = DeezerClient()

        # Get data from both
        spotify_data = spotify_client.get("search", params={"q": "Song A"})
        deezer_data = deezer_client.get("search", params={"q": "Song A"})

        # Aggregate
        aggregated = {
            "spotify": spotify_data["tracks"]["items"][0],
            "deezer": deezer_data["data"][0],
        }

        assert aggregated["spotify"]["popularity"] == 80
        assert aggregated["deezer"]["rank"] == 500000

    @patch("requests.Session.get")
    def test_retry_with_fallback_workflow(self, mock_get):
        """Test workflow with retry and fallback logic."""
        # First attempt fails
        error_response = Mock()
        error_response.raise_for_status.side_effect = Exception("503")

        # Retry succeeds
        success_response = Mock(status_code=200)
        success_response.json.return_value = {"data": "success"}

        mock_get.side_effect = [Exception("503"), success_response]

        client = SpotifyClient()

        # First attempt
        result = client.get("tracks/123")

        # Retry on failure
        if result is None:
            result = client.get("tracks/123")

        assert result is not None
        assert result["data"] == "success"


class TestDataConsistency:
    """Tests for data consistency across operations."""

    @patch("requests.Session.get")
    def test_same_endpoint_returns_consistent_data(self, mock_get):
        """Test that calling same endpoint returns consistent data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "track123", "name": "Test Track"}
        mock_get.return_value = mock_response

        client = SpotifyClient()

        # Call same endpoint multiple times
        result1 = client.get("tracks/track123")
        result2 = client.get("tracks/track123")
        result3 = client.get("tracks/track123")

        # Should return same data
        assert result1 == result2
        assert result2 == result3

    @patch("requests.Session.get")
    def test_different_clients_same_data_format(self, mock_get):
        """Test that different client types maintain their data formats."""
        spotify_response = Mock(status_code=200)
        spotify_response.json.return_value = {"id": "spotify123", "type": "track"}

        deezer_response = Mock(status_code=200)
        deezer_response.json.return_value = {"id": 456, "type": "track"}

        mock_get.side_effect = [spotify_response, deezer_response]

        spotify_client = SpotifyClient()
        deezer_client = DeezerClient()

        spotify_result = spotify_client.get("tracks/spotify123")
        deezer_result = deezer_client.get("track/456")

        # Each maintains its own format
        assert isinstance(spotify_result["id"], str)
        assert isinstance(deezer_result["id"], int)


class TestModuleExports:
    """Tests for module-level exports and imports."""

    def test_all_clients_importable(self):
        """Test that all API clients can be imported from module."""
        from music_tools_common.api import BaseAPIClient, DeezerClient, SpotifyClient  # noqa: F811

        # Should not raise ImportError
        assert BaseAPIClient is not None
        assert SpotifyClient is not None
        assert DeezerClient is not None

    def test_module_all_export(self):
        """Test __all__ export list."""
        from music_tools_common import api

        assert hasattr(api, "__all__")
        assert "BaseAPIClient" in api.__all__
        assert "SpotifyClient" in api.__all__
        assert "DeezerClient" in api.__all__

    def test_instantiate_all_exported_classes(self):
        """Test that all exported classes can be instantiated."""
        from music_tools_common.api import BaseAPIClient, DeezerClient, SpotifyClient  # noqa: F811

        # Should be able to create instances
        base = BaseAPIClient("https://api.example.com")
        spotify = SpotifyClient()
        deezer = DeezerClient()

        assert base is not None
        assert spotify is not None
        assert deezer is not None


class TestRealWorldScenarios:
    """Tests simulating real-world usage scenarios."""

    @patch("requests.Session.get")
    def test_playlist_creation_workflow(self, mock_get):
        """Test workflow for creating a playlist from search results."""
        # Search for tracks
        search_response = Mock(status_code=200)
        search_response.json.return_value = {
            "tracks": {
                "items": [
                    {"id": "track1", "name": "Song 1"},
                    {"id": "track2", "name": "Song 2"},
                    {"id": "track3", "name": "Song 3"},
                ]
            }
        }

        # Get track details
        detail_responses = [
            Mock(
                status_code=200,
                json=lambda i=i: {"id": f"track{i}", "name": f"Song {i}", "duration_ms": 180000},
            )
            for i in range(1, 4)
        ]

        mock_get.side_effect = [search_response] + detail_responses

        client = SpotifyClient()

        # Search for tracks
        search_results = client.get("search", params={"q": "rock", "type": "track"})
        track_ids = [track["id"] for track in search_results["tracks"]["items"]]

        # Get details for each track
        tracks_details = []
        for track_id in track_ids:
            details = client.get(f"tracks/{track_id}")
            tracks_details.append(details)

        assert len(tracks_details) == 3
        for i, track in enumerate(tracks_details, 1):
            assert track["name"] == f"Song {i}"

    @patch("requests.Session.get")
    def test_artist_comparison_across_platforms(self, mock_get):
        """Test comparing same artist across Spotify and Deezer."""
        # Spotify artist
        spotify_response = Mock(status_code=200)
        spotify_response.json.return_value = {
            "id": "spotify_artist",
            "name": "Famous Artist",
            "followers": {"total": 5000000},
            "popularity": 95,
        }

        # Deezer artist
        deezer_response = Mock(status_code=200)
        deezer_response.json.return_value = {
            "id": 12345,
            "name": "Famous Artist",
            "nb_fan": 3000000,
        }

        mock_get.side_effect = [spotify_response, deezer_response]

        spotify_client = SpotifyClient()
        deezer_client = DeezerClient()

        spotify_artist = spotify_client.get("artists/spotify_artist")
        deezer_artist = deezer_client.get("artist/12345")

        # Compare
        comparison = {
            "name": spotify_artist["name"],
            "spotify_followers": spotify_artist["followers"]["total"],
            "deezer_fans": deezer_artist["nb_fan"],
        }

        assert comparison["name"] == "Famous Artist"
        assert comparison["spotify_followers"] > comparison["deezer_fans"]


# Run with: pytest packages/common/tests/api/test_integration.py -v
# Coverage: pytest packages/common/tests/api/test_integration.py --cov=music_tools_common.api --cov-report=term-missing
