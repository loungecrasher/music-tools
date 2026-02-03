"""
Tests for Database Models
"""

from datetime import datetime

import pytest
from music_tools_common.database import (
    ArtistCountry,
    Playlist,
    PlaylistTrack,
    ProcessingLog,
    ProcessingStatus,
    ServiceType,
    Setting,
    Track,
    get_all_indexes,
    get_all_schemas,
)
from pydantic import ValidationError


class TestPlaylistModel:
    """Test Playlist model."""

    def test_valid_playlist(self):
        """Test creating valid playlist."""
        playlist = Playlist(
            id='pl_001',
            name='Test Playlist',
            url='https://example.com/playlist/001',
            owner='user123',
            tracks_count=10,
            service=ServiceType.SPOTIFY,
            is_algorithmic=False
        )

        assert playlist.id == 'pl_001'
        assert playlist.name == 'Test Playlist'
        assert playlist.service == ServiceType.SPOTIFY
        assert playlist.tracks_count == 10

    def test_playlist_defaults(self):
        """Test playlist with default values."""
        playlist = Playlist(
            id='pl_001',
            name='Test Playlist',
            url='https://example.com/playlist/001',
            service=ServiceType.SPOTIFY
        )

        assert playlist.owner == 'unknown'
        assert playlist.tracks_count == 0
        assert playlist.is_algorithmic is False
        assert isinstance(playlist.added_on, datetime)

    def test_playlist_validation(self):
        """Test playlist validation."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            Playlist(
                id='pl_001',
                name='',
                url='https://example.com/playlist/001',
                service=ServiceType.SPOTIFY
            )

        # Negative tracks_count should fail
        with pytest.raises(ValidationError):
            Playlist(
                id='pl_001',
                name='Test',
                url='https://example.com/playlist/001',
                service=ServiceType.SPOTIFY,
                tracks_count=-1
            )

    def test_playlist_to_dict(self):
        """Test playlist to_dict conversion."""
        playlist = Playlist(
            id='pl_001',
            name='Test Playlist',
            url='https://example.com/playlist/001',
            service=ServiceType.SPOTIFY
        )

        data = playlist.to_dict()

        assert isinstance(data, dict)
        assert data['id'] == 'pl_001'
        assert data['name'] == 'Test Playlist'
        assert data['service'] == 'spotify'
        assert 'added_on' in data
        assert 'last_updated' in data

    def test_playlist_schema(self):
        """Test playlist schema generation."""
        schema = Playlist.get_table_schema()
        assert 'CREATE TABLE' in schema
        assert 'playlists' in schema

        indexes = Playlist.get_indexes()
        assert len(indexes) == 3
        assert any('idx_playlist_service' in idx for idx in indexes)


class TestTrackModel:
    """Test Track model."""

    def test_valid_track(self):
        """Test creating valid track."""
        track = Track(
            id='tr_001',
            name='Song Title',
            artist='Artist Name',
            album='Album Name',
            duration=180000,
            release_date='2024-01-01',
            isrc='USRC12345678',
            service=ServiceType.SPOTIFY
        )

        assert track.id == 'tr_001'
        assert track.name == 'Song Title'
        assert track.artist == 'Artist Name'
        assert track.duration == 180000

    def test_track_defaults(self):
        """Test track with default values."""
        track = Track(
            id='tr_001',
            name='Song Title',
            artist='Artist Name',
            service=ServiceType.SPOTIFY
        )

        assert track.album is None
        assert track.duration == 0
        assert track.release_date is None
        assert track.isrc is None

    def test_track_validation(self):
        """Test track validation."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            Track(
                id='tr_001',
                name='',
                artist='Artist',
                service=ServiceType.SPOTIFY
            )

        # Empty artist should fail
        with pytest.raises(ValidationError):
            Track(
                id='tr_001',
                name='Song',
                artist='',
                service=ServiceType.SPOTIFY
            )

        # Negative duration should fail
        with pytest.raises(ValidationError):
            Track(
                id='tr_001',
                name='Song',
                artist='Artist',
                duration=-1,
                service=ServiceType.SPOTIFY
            )

    def test_track_to_dict(self):
        """Test track to_dict conversion."""
        track = Track(
            id='tr_001',
            name='Song Title',
            artist='Artist Name',
            service=ServiceType.SPOTIFY
        )

        data = track.to_dict()

        assert isinstance(data, dict)
        assert data['id'] == 'tr_001'
        assert data['name'] == 'Song Title'
        assert data['artist'] == 'Artist Name'

    def test_track_schema(self):
        """Test track schema generation."""
        schema = Track.get_table_schema()
        assert 'CREATE TABLE' in schema
        assert 'tracks' in schema

        indexes = Track.get_indexes()
        assert len(indexes) == 3


class TestPlaylistTrackModel:
    """Test PlaylistTrack model."""

    def test_valid_playlist_track(self):
        """Test creating valid playlist-track relationship."""
        pt = PlaylistTrack(
            playlist_id='pl_001',
            track_id='tr_001',
            position=1
        )

        assert pt.playlist_id == 'pl_001'
        assert pt.track_id == 'tr_001'
        assert pt.position == 1

    def test_playlist_track_defaults(self):
        """Test playlist-track with defaults."""
        pt = PlaylistTrack(
            playlist_id='pl_001',
            track_id='tr_001'
        )

        assert pt.position is None
        assert isinstance(pt.added_at, datetime)

    def test_playlist_track_validation(self):
        """Test playlist-track validation."""
        # Negative position should fail
        with pytest.raises(ValidationError):
            PlaylistTrack(
                playlist_id='pl_001',
                track_id='tr_001',
                position=-1
            )


class TestSettingModel:
    """Test Setting model."""

    def test_valid_setting(self):
        """Test creating valid setting."""
        setting = Setting(
            key='api_key',
            value='secret123'
        )

        assert setting.key == 'api_key'
        assert setting.value == 'secret123'

    def test_setting_complex_value(self):
        """Test setting with complex value."""
        setting = Setting(
            key='config',
            value={'option1': True, 'option2': 'value'}
        )

        assert setting.key == 'config'
        assert isinstance(setting.value, dict)

    def test_setting_validation(self):
        """Test setting validation."""
        # Empty key should fail
        with pytest.raises(ValidationError):
            Setting(key='', value='value')


class TestArtistCountryModel:
    """Test ArtistCountry model."""

    def test_valid_artist_country(self):
        """Test creating valid artist-country mapping."""
        ac = ArtistCountry(
            artist_name='Daft Punk',
            country='France',
            confidence=0.95
        )

        assert ac.artist_name == 'Daft Punk'
        assert ac.country == 'France'
        assert ac.confidence == 0.95

    def test_artist_country_defaults(self):
        """Test artist-country with defaults."""
        ac = ArtistCountry(
            artist_name='The Beatles',
            country='United Kingdom'
        )

        assert ac.confidence == 1.0
        assert ac.hit_count == 0
        assert isinstance(ac.created_at, datetime)

    def test_artist_country_validation(self):
        """Test artist-country validation."""
        # Empty artist name should fail
        with pytest.raises(ValidationError):
            ArtistCountry(artist_name='', country='France')

        # Empty country should fail
        with pytest.raises(ValidationError):
            ArtistCountry(artist_name='Artist', country='')

        # Invalid confidence should fail
        with pytest.raises(ValidationError):
            ArtistCountry(
                artist_name='Artist',
                country='Country',
                confidence=1.5
            )

        # Negative hit_count should fail
        with pytest.raises(ValidationError):
            ArtistCountry(
                artist_name='Artist',
                country='Country',
                hit_count=-1
            )


class TestProcessingLogModel:
    """Test ProcessingLog model."""

    def test_valid_processing_log(self):
        """Test creating valid processing log."""
        log = ProcessingLog(
            file_path='/path/to/file.mp3',
            artist_name='Artist Name',
            country='France',
            status=ProcessingStatus.SUCCESS
        )

        assert log.file_path == '/path/to/file.mp3'
        assert log.artist_name == 'Artist Name'
        assert log.country == 'France'
        assert log.status == ProcessingStatus.SUCCESS

    def test_processing_log_error(self):
        """Test processing log with error."""
        log = ProcessingLog(
            file_path='/path/to/file.mp3',
            artist_name='Artist Name',
            status=ProcessingStatus.ERROR,
            error_message='API failed'
        )

        assert log.status == ProcessingStatus.ERROR
        assert log.error_message == 'API failed'
        assert log.country is None

    def test_processing_log_to_dict(self):
        """Test processing log to_dict conversion."""
        log = ProcessingLog(
            file_path='/path/to/file.mp3',
            artist_name='Artist Name',
            status=ProcessingStatus.SUCCESS
        )

        data = log.to_dict()

        assert isinstance(data, dict)
        assert data['file_path'] == '/path/to/file.mp3'
        assert data['status'] == 'success'


class TestServiceType:
    """Test ServiceType enum."""

    def test_service_types(self):
        """Test service type values."""
        assert ServiceType.SPOTIFY == 'spotify'
        assert ServiceType.DEEZER == 'deezer'
        assert ServiceType.APPLE_MUSIC == 'apple_music'
        assert ServiceType.YOUTUBE_MUSIC == 'youtube_music'
        assert ServiceType.TIDAL == 'tidal'


class TestProcessingStatus:
    """Test ProcessingStatus enum."""

    def test_processing_statuses(self):
        """Test processing status values."""
        assert ProcessingStatus.SUCCESS == 'success'
        assert ProcessingStatus.ERROR == 'error'
        assert ProcessingStatus.SKIPPED == 'skipped'
        assert ProcessingStatus.PENDING == 'pending'


class TestSchemaGeneration:
    """Test schema generation utilities."""

    def test_get_all_schemas(self):
        """Test getting all schemas."""
        schemas = get_all_schemas()

        assert isinstance(schemas, dict)
        assert 'playlists' in schemas
        assert 'tracks' in schemas
        assert 'playlist_tracks' in schemas
        assert 'settings' in schemas
        assert 'artist_country' in schemas
        assert 'processing_log' in schemas

        for table, schema in schemas.items():
            assert 'CREATE TABLE' in schema

    def test_get_all_indexes(self):
        """Test getting all indexes."""
        indexes = get_all_indexes()

        assert isinstance(indexes, dict)
        assert 'playlists' in indexes
        assert 'tracks' in indexes

        for table, index_list in indexes.items():
            assert isinstance(index_list, list)
            for index in index_list:
                assert 'CREATE INDEX' in index


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
