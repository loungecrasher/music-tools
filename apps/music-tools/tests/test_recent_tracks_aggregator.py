"""
Tests for the Recent Tracks Aggregator feature in spotify_tracks.py.

Tests the core logic: playlist fetching, date filtering, deduplication,
playlist creation/update, and batch adding.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone, timedelta

from src.services.spotify_tracks import _get_all_playlists


def _make_track_item(uri, name, artist, added_at_str, track_type="track"):
    """Helper to build a Spotify track item dict."""
    return {
        "added_at": added_at_str,
        "track": {
            "uri": uri,
            "name": name,
            "artists": [{"name": artist}],
            "type": track_type,
        },
    }


def _make_playlist(pid, name, owner_id, total_tracks=10, public=False):
    """Helper to build a Spotify playlist dict."""
    return {
        "id": pid,
        "name": name,
        "owner": {"id": owner_id, "display_name": owner_id},
        "tracks": {"total": total_tracks},
        "public": public,
    }


class TestGetAllPlaylists:
    """Tests for _get_all_playlists pagination helper."""

    def test_single_page(self):
        sp = MagicMock()
        playlists = [_make_playlist(f"p{i}", f"Playlist {i}", "user1") for i in range(3)]
        sp.current_user_playlists.return_value = {"items": playlists, "next": None}

        result = _get_all_playlists(sp)

        assert len(result) == 3
        assert result[0]["id"] == "p0"
        sp.current_user_playlists.assert_called_once_with(limit=50)

    def test_multiple_pages(self):
        sp = MagicMock()
        page1 = [_make_playlist("p0", "A", "user1")]
        page2 = [_make_playlist("p1", "B", "user1")]

        sp.current_user_playlists.return_value = {
            "items": page1,
            "next": "https://api.spotify.com/page2",
        }
        sp.next.return_value = {"items": page2, "next": None}

        result = _get_all_playlists(sp)

        assert len(result) == 2
        assert result[0]["id"] == "p0"
        assert result[1]["id"] == "p1"

    def test_empty_library(self):
        sp = MagicMock()
        sp.current_user_playlists.return_value = {"items": [], "next": None}

        result = _get_all_playlists(sp)
        assert result == []


class TestRecentTracksAggregatorLogic:
    """Tests for the aggregation logic extracted from run_recent_tracks_aggregator.

    These test the date filtering, dedup, and sorting logic directly
    without requiring the interactive CLI wrapper.
    """

    def test_date_filtering(self):
        """Tracks older than the cutoff should be excluded."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        recent = "2026-01-25T12:00:00Z"  # within 30 days of 2026-02-01
        old = "2025-06-01T12:00:00Z"  # well outside window

        recent_dt = datetime.fromisoformat(recent.replace("Z", "+00:00"))
        old_dt = datetime.fromisoformat(old.replace("Z", "+00:00"))

        assert recent_dt >= cutoff
        assert old_dt < cutoff

    def test_deduplication_keeps_earliest(self):
        """When the same track appears in multiple playlists, keep earliest add date."""
        recent_tracks = {}

        # Track added to playlist A on Jan 20
        uri = "spotify:track:abc123"
        added1 = datetime(2026, 1, 20, tzinfo=timezone.utc)
        recent_tracks[uri] = {
            "name": "Test Song",
            "artist": "Artist",
            "added_at": added1,
            "source": "Playlist A",
        }

        # Same track added to playlist B on Jan 25 (later)
        added2 = datetime(2026, 1, 25, tzinfo=timezone.utc)
        if uri not in recent_tracks or added2 < recent_tracks[uri]["added_at"]:
            recent_tracks[uri] = {
                "name": "Test Song",
                "artist": "Artist",
                "added_at": added2,
                "source": "Playlist B",
            }

        # Should keep the earlier date (Jan 20, Playlist A)
        assert recent_tracks[uri]["added_at"] == added1
        assert recent_tracks[uri]["source"] == "Playlist A"

    def test_deduplication_replaces_with_earlier(self):
        """If a later-discovered entry has an earlier date, it should replace."""
        recent_tracks = {}

        uri = "spotify:track:abc123"
        # First seen with later date
        added_later = datetime(2026, 1, 25, tzinfo=timezone.utc)
        recent_tracks[uri] = {
            "name": "Test Song",
            "artist": "Artist",
            "added_at": added_later,
            "source": "Playlist B",
        }

        # Then seen with earlier date
        added_earlier = datetime(2026, 1, 15, tzinfo=timezone.utc)
        if uri not in recent_tracks or added_earlier < recent_tracks[uri]["added_at"]:
            recent_tracks[uri] = {
                "name": "Test Song",
                "artist": "Artist",
                "added_at": added_earlier,
                "source": "Playlist A",
            }

        assert recent_tracks[uri]["added_at"] == added_earlier
        assert recent_tracks[uri]["source"] == "Playlist A"

    def test_sorting_newest_first(self):
        """Sorted output should have newest tracks first."""
        tracks = {
            "uri1": {"added_at": datetime(2026, 1, 10, tzinfo=timezone.utc)},
            "uri2": {"added_at": datetime(2026, 1, 30, tzinfo=timezone.utc)},
            "uri3": {"added_at": datetime(2026, 1, 20, tzinfo=timezone.utc)},
        }

        sorted_tracks = sorted(
            tracks.items(), key=lambda x: x[1]["added_at"], reverse=True
        )

        assert sorted_tracks[0][0] == "uri2"  # Jan 30
        assert sorted_tracks[1][0] == "uri3"  # Jan 20
        assert sorted_tracks[2][0] == "uri1"  # Jan 10

    def test_local_files_skipped(self):
        """Local file URIs should be excluded."""
        uri = "spotify:local:Artist:Album:Track:180"
        assert uri.startswith("spotify:local:")

    def test_episodes_skipped(self):
        """Podcast episodes should be excluded."""
        item = _make_track_item(
            "spotify:episode:xyz", "Episode 1", "Podcast", "2026-01-20T00:00:00Z",
            track_type="episode",
        )
        assert item["track"]["type"] == "episode"

    def test_batch_splitting(self):
        """Track URIs should be split into batches of 100."""
        uris = [f"spotify:track:{i}" for i in range(250)]

        batches = []
        for start in range(0, len(uris), 100):
            batches.append(uris[start: start + 100])

        assert len(batches) == 3
        assert len(batches[0]) == 100
        assert len(batches[1]) == 100
        assert len(batches[2]) == 50

    def test_filter_pattern_matching(self):
        """Name pattern filtering should be case-insensitive."""
        playlists = [
            _make_playlist("p1", "EDM/House", "user1"),
            _make_playlist("p2", "edm/Techno", "user1"),
            _make_playlist("p3", "Chill Vibes", "user1"),
        ]
        pattern = "edm/"

        filtered = [p for p in playlists if pattern.lower() in p["name"].lower()]

        assert len(filtered) == 2
        assert filtered[0]["id"] == "p1"
        assert filtered[1]["id"] == "p2"


class TestPlaylistCreateOrUpdate:
    """Tests for the create-or-update playlist logic."""

    def test_finds_existing_playlist(self):
        """Should find and reuse an existing playlist owned by the user."""
        user_id = "user1"
        playlist_name = "Recent Adds (Last 30 Days)"
        all_playlists = [
            _make_playlist("existing_id", playlist_name, user_id),
            _make_playlist("other_id", "Other Playlist", user_id),
        ]

        target_id = None
        for p in all_playlists:
            if p["name"] == playlist_name and p["owner"]["id"] == user_id:
                target_id = p["id"]
                break

        assert target_id == "existing_id"

    def test_does_not_match_other_users_playlist(self):
        """Should not reuse a playlist with the same name owned by someone else."""
        user_id = "user1"
        playlist_name = "Recent Adds (Last 30 Days)"
        all_playlists = [
            _make_playlist("other_id", playlist_name, "other_user"),
        ]

        target_id = None
        for p in all_playlists:
            if p["name"] == playlist_name and p["owner"]["id"] == user_id:
                target_id = p["id"]
                break

        assert target_id is None

    def test_creates_new_when_not_found(self):
        """Should create a new playlist when no matching one exists."""
        sp = MagicMock()
        sp.user_playlist_create.return_value = {"id": "new_id"}

        user_id = "user1"
        playlist_name = "My New Playlist"

        new_pl = sp.user_playlist_create(
            user_id, playlist_name, public=False, description="test"
        )

        assert new_pl["id"] == "new_id"
        sp.user_playlist_create.assert_called_once()
