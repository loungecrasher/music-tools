"""Pytest configuration and fixtures for API tests.

This module provides reusable fixtures and test utilities for API testing.
"""

from unittest.mock import MagicMock, Mock

import pytest
import requests
from music_tools_common.api.base import BaseAPIClient
from music_tools_common.api.deezer import DeezerClient
from music_tools_common.api.spotify import SpotifyClient

# Fixtures for API clients


@pytest.fixture
def base_client():
    """Fixture providing a BaseAPIClient instance."""
    return BaseAPIClient("https://api.example.com")


@pytest.fixture
def spotify_client():
    """Fixture providing a SpotifyClient instance."""
    return SpotifyClient()


@pytest.fixture
def deezer_client():
    """Fixture providing a DeezerClient instance."""
    return DeezerClient()


@pytest.fixture
def all_clients(spotify_client, deezer_client):
    """Fixture providing all API clients."""
    return {
        'spotify': spotify_client,
        'deezer': deezer_client
    }


# Fixtures for mock responses

@pytest.fixture
def mock_success_response():
    """Fixture providing a successful mock HTTP response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'data': 'test'}
    mock_response.raise_for_status = Mock()
    return mock_response


@pytest.fixture
def mock_error_response():
    """Fixture providing an error mock HTTP response."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    return mock_response


@pytest.fixture
def mock_not_found_response():
    """Fixture providing a 404 Not Found mock response."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    return mock_response


@pytest.fixture
def mock_unauthorized_response():
    """Fixture providing a 401 Unauthorized mock response."""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
    return mock_response


@pytest.fixture
def mock_rate_limit_response():
    """Fixture providing a 429 Rate Limit mock response."""
    mock_response = Mock()
    mock_response.status_code = 429
    mock_response.headers = {'Retry-After': '30'}
    mock_response.raise_for_status.side_effect = requests.HTTPError("429 Too Many Requests")
    return mock_response


# Fixtures for test data

@pytest.fixture
def sample_spotify_track():
    """Fixture providing sample Spotify track data."""
    return {
        'id': '3n3Ppam7vgaVa1iaRUc9Lp',
        'name': 'Mr. Brightside',
        'artists': [
            {
                'id': '0C0XlULifJtAgn6ZNCW2eu',
                'name': 'The Killers'
            }
        ],
        'album': {
            'id': '4OHNH3sDzIxnmUADXzv2kT',
            'name': 'Hot Fuss'
        },
        'duration_ms': 222973,
        'popularity': 87,
        'explicit': False
    }


@pytest.fixture
def sample_spotify_artist():
    """Fixture providing sample Spotify artist data."""
    return {
        'id': '0C0XlULifJtAgn6ZNCW2eu',
        'name': 'The Killers',
        'genres': ['alternative rock', 'indie rock', 'modern rock'],
        'popularity': 82,
        'followers': {
            'total': 8500000
        }
    }


@pytest.fixture
def sample_spotify_album():
    """Fixture providing sample Spotify album data."""
    return {
        'id': '4OHNH3sDzIxnmUADXzv2kT',
        'name': 'Hot Fuss',
        'artists': [
            {
                'id': '0C0XlULifJtAgn6ZNCW2eu',
                'name': 'The Killers'
            }
        ],
        'release_date': '2004-06-15',
        'total_tracks': 11
    }


@pytest.fixture
def sample_deezer_track():
    """Fixture providing sample Deezer track data."""
    return {
        'id': 3135556,
        'title': 'Harder Better Faster Stronger',
        'artist': {
            'id': 27,
            'name': 'Daft Punk'
        },
        'album': {
            'id': 302127,
            'title': 'Discovery'
        },
        'duration': 224,
        'rank': 900000,
        'explicit_lyrics': False
    }


@pytest.fixture
def sample_deezer_artist():
    """Fixture providing sample Deezer artist data."""
    return {
        'id': 27,
        'name': 'Daft Punk',
        'nb_album': 30,
        'nb_fan': 5000000,
        'picture': 'https://api.deezer.com/artist/27/image'
    }


@pytest.fixture
def sample_deezer_album():
    """Fixture providing sample Deezer album data."""
    return {
        'id': 302127,
        'title': 'Discovery',
        'artist': {
            'id': 27,
            'name': 'Daft Punk'
        },
        'release_date': '2001-03-07',
        'nb_tracks': 14
    }


@pytest.fixture
def sample_spotify_search_results():
    """Fixture providing sample Spotify search results."""
    return {
        'tracks': {
            'items': [
                {
                    'id': 'track1',
                    'name': 'Rock Song 1',
                    'artists': [{'name': 'Artist 1'}]
                },
                {
                    'id': 'track2',
                    'name': 'Rock Song 2',
                    'artists': [{'name': 'Artist 2'}]
                }
            ],
            'total': 100,
            'limit': 2,
            'offset': 0
        }
    }


@pytest.fixture
def sample_deezer_search_results():
    """Fixture providing sample Deezer search results."""
    return {
        'data': [
            {
                'id': 1,
                'title': 'Rock Song 1',
                'artist': {'name': 'Artist 1'}
            },
            {
                'id': 2,
                'title': 'Rock Song 2',
                'artist': {'name': 'Artist 2'}
            }
        ],
        'total': 100
    }


# Utility fixtures

@pytest.fixture
def mock_session():
    """Fixture providing a mock requests.Session."""
    session = MagicMock(spec=requests.Session)
    session.headers = {}
    return session


# Parametrize helpers

def pytest_generate_tests(metafunc):
    """Generate parametrized tests for common scenarios."""
    # Parametrize HTTP error codes
    if 'http_error_code' in metafunc.fixturenames:
        metafunc.parametrize('http_error_code', [400, 401, 403, 404, 429, 500, 503])

    # Parametrize API endpoints
    if 'spotify_endpoint' in metafunc.fixturenames:
        endpoints = [
            'tracks/123',
            'artists/456',
            'albums/789',
            'playlists/abc',
            'search'
        ]
        metafunc.parametrize('spotify_endpoint', endpoints)

    if 'deezer_endpoint' in metafunc.fixturenames:
        endpoints = [
            'track/123',
            'artist/456',
            'album/789',
            'playlist/abc',
            'search'
        ]
        metafunc.parametrize('deezer_endpoint', endpoints)


# Helper functions

def create_mock_response(status_code=200, json_data=None, headers=None):
    """Helper function to create a mock HTTP response.

    Args:
        status_code: HTTP status code
        json_data: JSON data to return
        headers: Response headers

    Returns:
        Mock response object
    """
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.headers = headers or {}

    if status_code >= 400:
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            f"{status_code} Error"
        )
    else:
        mock_response.raise_for_status = Mock()

    if json_data is not None:
        mock_response.json.return_value = json_data
    else:
        mock_response.json.return_value = {'data': 'default'}

    return mock_response


def create_spotify_track_response(track_id='123', track_name='Test Track'):
    """Helper to create a Spotify track response.

    Args:
        track_id: Track ID
        track_name: Track name

    Returns:
        Mock response with Spotify track data
    """
    return create_mock_response(json_data={
        'id': track_id,
        'name': track_name,
        'artists': [{'name': 'Test Artist'}],
        'album': {'name': 'Test Album'},
        'duration_ms': 180000,
        'popularity': 75
    })


def create_deezer_track_response(track_id=123, track_title='Test Track'):
    """Helper to create a Deezer track response.

    Args:
        track_id: Track ID
        track_title: Track title

    Returns:
        Mock response with Deezer track data
    """
    return create_mock_response(json_data={
        'id': track_id,
        'title': track_title,
        'artist': {'name': 'Test Artist'},
        'album': {'title': 'Test Album'},
        'duration': 180,
        'rank': 500000
    })


def create_error_response(status_code=500):
    """Helper to create an error response.

    Args:
        status_code: HTTP error code

    Returns:
        Mock error response
    """
    return create_mock_response(status_code=status_code)


# Pytest marks

def pytest_configure(config):
    """Register custom pytest marks."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as API-related"
    )
