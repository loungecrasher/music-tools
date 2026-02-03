"""Spotify playlist management and track utilities.

This module provides direct implementations for Spotify playlist operations
using the spotipy library through the music_tools_common auth system.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()


def _get_spotify_client():
    """Get authenticated Spotify client."""
    try:
        from music_tools_common.auth import get_spotify_client
        return get_spotify_client()
    except ImportError:
        raise ImportError("music_tools_common not available. Please install it first.")
    except ValueError as e:
        raise ValueError(f"Spotify not configured: {e}")


def _extract_playlist_id(url_or_id: str) -> str:
    """Extract playlist ID from URL or return as-is if already an ID."""
    # Handle full URLs
    match = re.search(r'playlist[/:]([a-zA-Z0-9]+)', url_or_id)
    if match:
        return match.group(1)
    # Assume it's already an ID
    return url_or_id.strip()


def _get_all_playlist_tracks(sp, playlist_id: str) -> List[Dict[str, Any]]:
    """Get all tracks from a playlist (handles pagination)."""
    tracks = []
    results = sp.playlist_tracks(playlist_id)

    while results:
        for item in results['items']:
            if item['track']:  # Skip None tracks
                tracks.append(item)

        if results['next']:
            results = sp.next(results)
        else:
            break

    return tracks


def run_playlist_manager():
    """Interactive Spotify Playlist Manager."""
    console.print(Panel(
        "[bold green]Spotify Playlist Manager[/bold green]\n\n"
        "Manage your Spotify playlists with options to:\n"
        "• View playlist details and tracks\n"
        "• Create new playlists\n"
        "• Copy tracks between playlists\n"
        "• Remove duplicates from playlists",
        title="[bold]Spotify Playlist Manager[/bold]",
        border_style="green"
    ))

    try:
        sp = _get_spotify_client()
        user = sp.me()
        console.print(f"\n[green]✓ Connected as:[/green] {user['display_name']}\n")
    except Exception as e:
        console.print(f"[bold red]Error connecting to Spotify:[/bold red] {str(e)}")
        Prompt.ask("\nPress Enter to continue")
        return

    while True:
        console.print("\n[bold cyan]Playlist Manager Options:[/bold cyan]")
        console.print("1. List my playlists")
        console.print("2. View playlist details")
        console.print("3. Create new playlist")
        console.print("4. Copy tracks to new playlist")
        console.print("5. Find & remove duplicates")
        console.print("0. Back to menu")

        choice = Prompt.ask("\nSelect option", choices=["0", "1", "2", "3", "4", "5"], default="0")

        if choice == "0":
            break
        elif choice == "1":
            _list_playlists(sp)
        elif choice == "2":
            _view_playlist_details(sp)
        elif choice == "3":
            _create_playlist(sp, user['id'])
        elif choice == "4":
            _copy_tracks_to_new_playlist(sp, user['id'])
        elif choice == "5":
            _find_remove_duplicates(sp)


def _list_playlists(sp):
    """List user's playlists."""
    with console.status("[bold green]Fetching playlists...[/bold green]"):
        playlists = sp.current_user_playlists(limit=50)

    if not playlists['items']:
        console.print("[yellow]No playlists found.[/yellow]")
        return

    table = Table(title=f"Your Playlists ({playlists['total']} total)")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Name", style="green")
    table.add_column("Tracks", justify="right")
    table.add_column("Owner", style="cyan")
    table.add_column("Public", justify="center")

    for i, playlist in enumerate(playlists['items'], 1):
        table.add_row(
            str(i),
            playlist['name'][:40],
            str(playlist['tracks']['total']),
            playlist['owner']['display_name'][:20],
            "✓" if playlist['public'] else "✗"
        )

    console.print(table)


def _view_playlist_details(sp):
    """View details of a specific playlist."""
    playlist_url = Prompt.ask("\nEnter playlist URL or ID")
    if not playlist_url:
        return

    playlist_id = _extract_playlist_id(playlist_url)

    with console.status("[bold green]Fetching playlist details...[/bold green]"):
        try:
            playlist = sp.playlist(playlist_id)
            tracks = _get_all_playlist_tracks(sp, playlist_id)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return

    # Show playlist info
    console.print(Panel(
        f"[bold]{playlist['name']}[/bold]\n"
        f"Owner: {playlist['owner']['display_name']}\n"
        f"Tracks: {len(tracks)}\n"
        f"Followers: {playlist['followers']['total']}\n"
        f"Public: {'Yes' if playlist['public'] else 'No'}",
        title="Playlist Details",
        border_style="cyan"
    ))

    # Show first 10 tracks
    if tracks:
        table = Table(title=f"Tracks (showing first 10 of {len(tracks)})")
        table.add_column("#", style="dim", justify="right")
        table.add_column("Title", style="green")
        table.add_column("Artist", style="cyan")
        table.add_column("Album", style="yellow")

        for i, item in enumerate(tracks[:10], 1):
            track = item['track']
            artists = ", ".join(a['name'] for a in track['artists'])
            table.add_row(
                str(i),
                track['name'][:40],
                artists[:30],
                track['album']['name'][:30]
            )

        console.print(table)


def _create_playlist(sp, user_id: str):
    """Create a new playlist."""
    name = Prompt.ask("\nPlaylist name")
    if not name:
        return

    description = Prompt.ask("Description (optional)", default="")
    public = Confirm.ask("Make public?", default=False)

    try:
        playlist = sp.user_playlist_create(
            user_id,
            name,
            public=public,
            description=description
        )
        console.print(f"\n[bold green]✓ Created playlist:[/bold green] {playlist['name']}")
        console.print(f"[dim]URL: {playlist['external_urls']['spotify']}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error creating playlist:[/bold red] {str(e)}")


def _copy_tracks_to_new_playlist(sp, user_id: str):
    """Copy tracks from one playlist to a new one."""
    source_url = Prompt.ask("\nSource playlist URL or ID")
    if not source_url:
        return

    source_id = _extract_playlist_id(source_url)

    with console.status("[bold green]Fetching source playlist...[/bold green]"):
        try:
            source = sp.playlist(source_id)
            tracks = _get_all_playlist_tracks(sp, source_id)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return

    console.print(f"\nSource: [cyan]{source['name']}[/cyan] ({len(tracks)} tracks)")

    new_name = Prompt.ask("New playlist name", default=f"{source['name']} (Copy)")
    public = Confirm.ask("Make public?", default=False)

    try:
        # Create new playlist
        new_playlist = sp.user_playlist_create(user_id, new_name, public=public)

        # Add tracks in batches of 100
        track_uris = [t['track']['uri'] for t in tracks if t['track']]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Adding tracks...", total=len(track_uris))

            for i in range(0, len(track_uris), 100):
                batch = track_uris[i:i+100]
                sp.playlist_add_items(new_playlist['id'], batch)
                progress.update(task, advance=len(batch))

        console.print(f"\n[bold green]✓ Created playlist with {len(track_uris)} tracks[/bold green]")
        console.print(f"[dim]URL: {new_playlist['external_urls']['spotify']}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


def _find_remove_duplicates(sp):
    """Find and optionally remove duplicate tracks from a playlist."""
    playlist_url = Prompt.ask("\nPlaylist URL or ID")
    if not playlist_url:
        return

    playlist_id = _extract_playlist_id(playlist_url)

    with console.status("[bold green]Analyzing playlist...[/bold green]"):
        try:
            playlist = sp.playlist(playlist_id)
            tracks = _get_all_playlist_tracks(sp, playlist_id)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            return

    # Find duplicates by track ID
    seen = {}
    duplicates = []

    for i, item in enumerate(tracks):
        track = item['track']
        if track:
            track_id = track['id']
            if track_id in seen:
                duplicates.append((i, track))
            else:
                seen[track_id] = i

    if not duplicates:
        console.print(f"\n[green]✓ No duplicates found in '{playlist['name']}'[/green]")
        return

    console.print(f"\n[yellow]Found {len(duplicates)} duplicate tracks:[/yellow]")

    table = Table()
    table.add_column("Position", justify="right")
    table.add_column("Track", style="green")
    table.add_column("Artist", style="cyan")

    for pos, track in duplicates[:10]:
        artists = ", ".join(a['name'] for a in track['artists'])
        table.add_row(str(pos + 1), track['name'][:40], artists[:30])

    if len(duplicates) > 10:
        console.print(f"[dim]... and {len(duplicates) - 10} more[/dim]")

    console.print(table)

    if Confirm.ask("\nRemove duplicates?", default=False):
        # Remove duplicates (from end to preserve positions)
        with console.status("[bold green]Removing duplicates...[/bold green]"):
            for pos, track in sorted(duplicates, key=lambda x: x[0], reverse=True):
                sp.playlist_remove_specific_occurrences_of_items(
                    playlist_id,
                    [{"uri": track['uri'], "positions": [pos]}]
                )

        console.print(f"[bold green]✓ Removed {len(duplicates)} duplicates[/bold green]")


def filter_tracks_after_date(
    playlist_url: str,
    cutoff_date: str,
    new_playlist_name: Optional[str] = None,
    description: Optional[str] = None,
    public: bool = False,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Filter tracks from a playlist by release date."""
    sp = _get_spotify_client()
    playlist_id = _extract_playlist_id(playlist_url)

    cutoff = datetime.strptime(cutoff_date, "%Y-%m-%d")

    # Get all tracks
    tracks = _get_all_playlist_tracks(sp, playlist_id)

    # Filter by date
    filtered = []
    for item in tracks:
        track = item['track']
        if track and track['album']:
            release_date = track['album']['release_date']
            # Handle different date precisions
            try:
                if len(release_date) == 4:  # Year only
                    track_date = datetime(int(release_date), 1, 1)
                elif len(release_date) == 7:  # Year-month
                    track_date = datetime.strptime(release_date, "%Y-%m")
                else:
                    track_date = datetime.strptime(release_date, "%Y-%m-%d")

                if track_date >= cutoff:
                    filtered.append(track)
            except ValueError:
                pass  # Skip tracks with invalid dates

    result = {
        "total_tracks": len(tracks),
        "filtered_tracks": len(filtered),
        "cutoff_date": cutoff_date,
        "tracks": filtered
    }

    if not dry_run and new_playlist_name and filtered:
        user = sp.me()
        new_playlist = sp.user_playlist_create(
            user['id'],
            new_playlist_name,
            public=public,
            description=description or f"Tracks released after {cutoff_date}"
        )

        track_uris = [t['uri'] for t in filtered]
        for i in range(0, len(track_uris), 100):
            sp.playlist_add_items(new_playlist['id'], track_uris[i:i+100])

        result["new_playlist_url"] = new_playlist['external_urls']['spotify']

    return result


def collect_recently_added_tracks(
    playlist_ids: List[str],
    cutoff_date: str,
    new_playlist_name: Optional[str] = None,
    description: Optional[str] = None,
    public: bool = False,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Collect tracks added to multiple playlists after a specific date.

    Args:
        playlist_ids: List of Spotify playlist URLs or IDs
        cutoff_date: Date string in YYYY-MM-DD format
        new_playlist_name: Name for the new combined playlist
        description: Description for the new playlist
        public: Whether the new playlist should be public
        dry_run: If True, just return results without creating playlist

    Returns:
        Dictionary with results and track information
    """
    sp = _get_spotify_client()
    cutoff = datetime.strptime(cutoff_date, "%Y-%m-%d")

    all_tracks = []
    seen_track_ids = set()  # Avoid duplicates
    playlist_stats = []

    for playlist_url in playlist_ids:
        playlist_id = _extract_playlist_id(playlist_url)

        try:
            playlist = sp.playlist(playlist_id)
            tracks = _get_all_playlist_tracks(sp, playlist_id)

            added_count = 0
            for item in tracks:
                if not item.get('track') or not item.get('added_at'):
                    continue

                track = item['track']
                track_id = track.get('id')

                if not track_id or track_id in seen_track_ids:
                    continue

                # Parse the added_at date
                added_at_str = item['added_at']  # ISO format: 2024-01-15T12:30:00Z
                try:
                    added_at = datetime.fromisoformat(added_at_str.replace('Z', '+00:00'))
                    added_at = added_at.replace(tzinfo=None)  # Remove timezone for comparison
                except ValueError:
                    continue

                if added_at >= cutoff:
                    all_tracks.append({
                        'track': track,
                        'added_at': added_at_str,
                        'from_playlist': playlist['name']
                    })
                    seen_track_ids.add(track_id)
                    added_count += 1

            playlist_stats.append({
                'name': playlist['name'],
                'total_tracks': len(tracks),
                'matched_tracks': added_count
            })
        except Exception as e:
            playlist_stats.append({
                'name': playlist_url,
                'error': str(e)
            })

    result = {
        'total_playlists': len(playlist_ids),
        'total_tracks_found': len(all_tracks),
        'cutoff_date': cutoff_date,
        'playlist_stats': playlist_stats,
        'tracks': all_tracks
    }

    if not dry_run and new_playlist_name and all_tracks:
        user = sp.me()
        new_playlist = sp.user_playlist_create(
            user['id'],
            new_playlist_name,
            public=public,
            description=description or f"Tracks added after {cutoff_date} from {len(playlist_ids)} playlists"
        )

        track_uris = [t['track']['uri'] for t in all_tracks]
        for i in range(0, len(track_uris), 100):
            sp.playlist_add_items(new_playlist['id'], track_uris[i:i+100])

        result['new_playlist_url'] = new_playlist['external_urls']['spotify']
        result['new_playlist_id'] = new_playlist['id']

    return result


def run_collect_from_folder():
    """Collect recently added tracks from multiple playlists into one."""
    console.print(Panel(
        "[bold green]Collect Recently Added Tracks from Playlist Folder[/bold green]\n\n"
        "Scan a folder of playlists and collect all tracks that were\n"
        "ADDED to those playlists after a specific date.\n"
        "Combine them into a single new playlist.\n\n"
        "[dim]Note: Spotify doesn't expose folders via API, so we use naming\n"
        "patterns to identify playlists in a 'folder' (e.g., 'EDM/', '2024 - ')[/dim]",
        title="[bold]Collect From Playlist Folder[/bold]",
        border_style="green"
    ))

    try:
        sp = _get_spotify_client()
        user = sp.me()
        console.print(f"\n[green]✓ Connected as:[/green] {user['display_name']}\n")
    except Exception as e:
        console.print(f"[bold red]Error connecting to Spotify:[/bold red] {str(e)}")
        Prompt.ask("\nPress Enter to continue")
        return

    # Get playlists to scan
    console.print("[bold cyan]How would you like to select playlists?[/bold cyan]")
    console.print("1. [bold]Select by folder/prefix[/bold] (e.g., 'EDM/', 'Chill -', '2024')")
    console.print("2. Select specific playlists from list")
    console.print("3. Enter playlist URLs/IDs manually")

    choice = Prompt.ask("Select option", choices=["1", "2", "3"], default="1")

    playlist_ids = []

    if choice == "1":
        # Folder/prefix matching (primary option)
        console.print("\n[bold cyan]Enter the folder prefix or pattern to match:[/bold cyan]")
        console.print("[dim]Examples:")
        console.print("  • 'EDM/' - matches 'EDM/House', 'EDM/Techno', etc.")
        console.print("  • 'Chill -' - matches 'Chill - Morning', 'Chill - Evening'")
        console.print("  • '2024' - matches any playlist with '2024' in the name[/dim]")

        pattern = Prompt.ask("\nFolder/prefix pattern")

        with console.status("[bold green]Searching for matching playlists...[/bold green]"):
            all_playlists = []
            results = sp.current_user_playlists(limit=50)
            while results:
                all_playlists.extend(results['items'])
                if results['next']:
                    results = sp.next(results)
                else:
                    break

        matched = [pl for pl in all_playlists if pattern.lower() in pl['name'].lower()]

        if not matched:
            console.print(f"[yellow]No playlists found matching '{pattern}'[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        # Sort by name for better display
        matched = sorted(matched, key=lambda x: x['name'])

        console.print(f"\n[green]Found {len(matched)} playlists in folder '{pattern}':[/green]")

        table = Table(title=f"Playlists matching '{pattern}'")
        table.add_column("#", style="dim", justify="right")
        table.add_column("Name", style="green")
        table.add_column("Tracks", justify="right")

        for i, pl in enumerate(matched, 1):
            table.add_row(str(i), pl['name'], str(pl['tracks']['total']))

        console.print(table)

        total_tracks = sum(pl['tracks']['total'] for pl in matched)
        console.print(f"\n[cyan]Total: {len(matched)} playlists, {total_tracks} tracks[/cyan]")

        if not Confirm.ask("\nUse these playlists?", default=True):
            Prompt.ask("\nPress Enter to continue")
            return

        playlist_ids = [pl['id'] for pl in matched]

    elif choice == "2":
        # Select from user's playlists
        with console.status("[bold green]Fetching your playlists...[/bold green]"):
            all_playlists = []
            results = sp.current_user_playlists(limit=50)
            while results:
                all_playlists.extend(results['items'])
                if results['next']:
                    results = sp.next(results)
                else:
                    break

        # Display playlists
        table = Table(title=f"Your Playlists ({len(all_playlists)} total)")
        table.add_column("#", style="dim", justify="right")
        table.add_column("Name", style="green")
        table.add_column("Tracks", justify="right")

        for i, pl in enumerate(all_playlists, 1):
            table.add_row(str(i), pl['name'][:50], str(pl['tracks']['total']))

        console.print(table)

        # Get selection
        console.print("\n[dim]Enter playlist numbers separated by commas (e.g., 1,3,5-10)[/dim]")
        selection = Prompt.ask("Select playlists")

        # Parse selection
        selected_indices = set()
        for part in selection.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                for i in range(int(start), int(end) + 1):
                    selected_indices.add(i)
            elif part.isdigit():
                selected_indices.add(int(part))

        for idx in selected_indices:
            if 1 <= idx <= len(all_playlists):
                playlist_ids.append(all_playlists[idx - 1]['id'])

    elif choice == "3":
        # Manual entry
        console.print("\n[dim]Enter playlist URLs or IDs, one per line. Enter empty line when done.[/dim]")
        while True:
            url = Prompt.ask("Playlist URL/ID (or Enter to finish)", default="")
            if not url:
                break
            playlist_ids.append(url.strip("'\""))

    if not playlist_ids:
        console.print("[yellow]No playlists selected.[/yellow]")
        Prompt.ask("\nPress Enter to continue")
        return

    console.print(f"\n[bold cyan]Selected {len(playlist_ids)} playlists[/bold cyan]")

    # Get cutoff date
    cutoff_date = Prompt.ask("Enter cutoff date (YYYY-MM-DD) - tracks added AFTER this date")

    # Get new playlist name
    new_playlist_name = Prompt.ask("Name for new combined playlist", default="")
    if not new_playlist_name:
        new_playlist_name = None

    # Collect tracks
    console.print(f"\n[bold cyan]Scanning {len(playlist_ids)} playlists...[/bold cyan]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Collecting tracks...", total=None)
            result = collect_recently_added_tracks(
                playlist_ids,
                cutoff_date,
                new_playlist_name=new_playlist_name,
                dry_run=new_playlist_name is None
            )
            progress.update(task, description="Complete!")

        # Show results
        console.print("\n[bold green]Results:[/bold green]")
        console.print(f"Playlists scanned: {result['total_playlists']}")
        console.print(f"Tracks found (added after {cutoff_date}): {result['total_tracks_found']}")

        # Show per-playlist stats
        table = Table(title="Playlist Breakdown")
        table.add_column("Playlist", style="cyan")
        table.add_column("Matched", justify="right", style="green")
        table.add_column("Total", justify="right")

        for stat in result['playlist_stats']:
            if 'error' in stat:
                table.add_row(stat['name'][:40], f"[red]Error: {stat['error'][:20]}[/red]", "-")
            else:
                table.add_row(stat['name'][:40], str(stat['matched_tracks']), str(stat['total_tracks']))

        console.print(table)

        if result.get('new_playlist_url'):
            console.print(f"\n[bold green]✓ Created playlist with {result['total_tracks_found']} tracks![/bold green]")
            console.print(f"URL: {result['new_playlist_url']}")
        elif result['total_tracks_found'] > 0 and not new_playlist_name:
            console.print("\n[dim]No new playlist created (no name provided)[/dim]")

            if Confirm.ask("Create playlist now?", default=True):
                name = Prompt.ask("Playlist name")
                if name:
                    with console.status("[bold green]Creating playlist...[/bold green]"):
                        user = sp.me()
                        new_playlist = sp.user_playlist_create(
                            user['id'],
                            name,
                            public=False,
                            description=f"Tracks added after {cutoff_date} from {len(playlist_ids)} playlists"
                        )

                        track_uris = [t['track']['uri'] for t in result['tracks']]
                        for i in range(0, len(track_uris), 100):
                            sp.playlist_add_items(new_playlist['id'], track_uris[i:i+100])

                    console.print("\n[bold green]✓ Created playlist![/bold green]")
                    console.print(f"URL: {new_playlist['external_urls']['spotify']}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")

    Prompt.ask("\nPress Enter to continue")


def run_tracks_after_date():
    """Interactive wrapper for filtering Spotify tracks by release date."""
    console.print(Panel(
        "[bold green]Filter Spotify Tracks by Release Date[/bold green]\n\n"
        "Filter tracks from a Spotify playlist based on their release date.\n"
        "You can create a new playlist with tracks released after a specific date.",
        title="[bold]Spotify Tracks After Date[/bold]",
        border_style="green"
    ))

    try:
        sp = _get_spotify_client()
        user = sp.me()
        console.print(f"\n[green]✓ Connected as:[/green] {user['display_name']}\n")
    except Exception as e:
        console.print(f"[bold red]Error connecting to Spotify:[/bold red] {str(e)}")
        Prompt.ask("\nPress Enter to continue")
        return

    playlist_url = Prompt.ask("\nEnter Spotify playlist URL or ID")
    if not playlist_url:
        Prompt.ask("\nPress Enter to continue")
        return

    playlist_url = playlist_url.strip("'\"")
    cutoff_date = Prompt.ask("Enter cutoff date (YYYY-MM-DD)")

    new_playlist_name = Prompt.ask("Enter name for new playlist (or press Enter to just preview)", default="")
    new_playlist_name = new_playlist_name if new_playlist_name else None

    description = ""
    if new_playlist_name:
        description = Prompt.ask("Enter description for new playlist (optional)", default="")

    console.print("\n[bold cyan]Filtering tracks...[/bold cyan]")
    console.print(f"Playlist: {playlist_url}")
    console.print(f"Cutoff date: {cutoff_date}")

    try:
        with console.status("[bold green]Analyzing playlist...[/bold green]"):
            result = filter_tracks_after_date(
                playlist_url,
                cutoff_date,
                new_playlist_name=new_playlist_name,
                description=description,
                public=False,
                dry_run=new_playlist_name is None
            )

        console.print("\n[bold green]Results:[/bold green]")
        console.print(f"Total tracks in playlist: {result['total_tracks']}")
        console.print(f"Tracks after {cutoff_date}: {result['filtered_tracks']}")

        if result.get('new_playlist_url'):
            console.print("\n[bold green]✓ Created new playlist![/bold green]")
            console.print(f"URL: {result['new_playlist_url']}")
        elif result['filtered_tracks'] > 0:
            console.print("\n[dim]No new playlist created (preview mode)[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error filtering tracks:[/bold red] {str(e)}")

    Prompt.ask("\nPress Enter to continue")


logger = logging.getLogger('music_tools.spotify_tracks')


def _get_all_playlists(sp) -> List[Dict[str, Any]]:
    """Fetch every playlist in the user's library (handles pagination)."""
    playlists = []
    results = sp.current_user_playlists(limit=50)
    while results:
        playlists.extend(results["items"])
        if results.get("next"):
            results = sp.next(results)
        else:
            break
    return playlists


def run_recent_tracks_aggregator():
    """Aggregate recently added tracks from all playlists into one.

    Scans all (or selected) playlists in the user's library, collects
    tracks added within a configurable number of days, deduplicates them,
    and creates or updates a single consolidated playlist sorted by date
    added (newest first).
    """
    console.print(Panel(
        "[bold green]Recent Tracks Aggregator[/bold green]\n\n"
        "Scans your playlists and collects every track added within\n"
        "a configurable window (default: 30 days) into a single playlist.\n\n"
        "Features:\n"
        "  - Scans all playlists or a filtered subset\n"
        "  - Deduplicates across playlists (keeps earliest add date)\n"
        "  - Creates a new playlist or updates an existing one\n"
        "  - Dry-run mode to preview without changes\n"
        "  - Sorted newest-first",
        title="[bold]Recent Tracks Aggregator[/bold]",
        border_style="green"
    ))

    # --- Authenticate ---
    try:
        sp = _get_spotify_client()
        user = sp.me()
        user_id = user["id"]
        console.print(f"\n[green]Connected as:[/green] {user['display_name']} ({user_id})\n")
    except Exception as e:
        console.print(f"[bold red]Error connecting to Spotify:[/bold red] {str(e)}")
        Prompt.ask("\nPress Enter to continue")
        return

    # --- Configuration ---
    days_back_str = Prompt.ask("How many days back to look?", default="30")
    try:
        days_back = int(days_back_str)
        if days_back < 1:
            raise ValueError()
    except ValueError:
        console.print("[yellow]Invalid number. Using default of 30 days.[/yellow]")
        days_back = 30

    playlist_name = Prompt.ask(
        "Name for the aggregated playlist",
        default=f"Recent Adds (Last {days_back} Days)"
    )

    # Playlist scope
    console.print("\n[bold cyan]Which playlists to scan?[/bold cyan]")
    console.print("1. All my playlists")
    console.print("2. Filter by name pattern (e.g. 'EDM/', '2024')")
    scope_choice = Prompt.ask("Select option", choices=["1", "2"], default="1")

    filter_pattern = None
    if scope_choice == "2":
        filter_pattern = Prompt.ask("Enter name pattern to match")

    dry_run = Confirm.ask("Dry run? (preview only, no playlist changes)", default=False)

    # --- Fetch playlists ---
    with console.status("[bold green]Fetching your playlists...[/bold green]"):
        all_playlists = _get_all_playlists(sp)

    console.print(f"Found {len(all_playlists)} playlists in your library.")

    if filter_pattern:
        target_playlists = [
            p for p in all_playlists
            if filter_pattern.lower() in p["name"].lower()
        ]
        console.print(
            f"Filtered to {len(target_playlists)} playlists matching "
            f"'{filter_pattern}'."
        )
    else:
        target_playlists = all_playlists

    if not target_playlists:
        console.print("[yellow]No playlists to scan.[/yellow]")
        Prompt.ask("\nPress Enter to continue")
        return

    # --- Scan playlists for recent tracks ---
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    recent_tracks: Dict[str, Dict[str, Any]] = {}
    skipped: List[str] = []
    playlist_stats: List[Dict[str, Any]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            "Scanning playlists...", total=len(target_playlists)
        )

        for playlist in target_playlists:
            pname = playlist["name"]
            pid = playlist["id"]
            progress.update(task, description=f"Scanning: {pname[:40]}")

            matched_count = 0
            try:
                results = sp.playlist_tracks(
                    pid,
                    fields="items(added_at,track(uri,name,artists(name),type)),next",
                    limit=100,
                )
            except Exception as e:
                logger.warning("Skipped playlist %s: %s", pname, e)
                skipped.append(pname)
                playlist_stats.append({"name": pname, "error": str(e)})
                progress.advance(task)
                continue

            page_num = 0
            while results:
                for item in results.get("items", []):
                    track = item.get("track")
                    if not track or not track.get("uri"):
                        continue
                    # Skip local files and podcast episodes
                    if track["uri"].startswith("spotify:local:"):
                        continue
                    if track.get("type") == "episode":
                        continue

                    added_at_str = item.get("added_at")
                    if not added_at_str:
                        continue

                    try:
                        added_at = datetime.fromisoformat(
                            added_at_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        continue

                    if added_at >= cutoff:
                        uri = track["uri"]
                        artist = (
                            track["artists"][0]["name"]
                            if track.get("artists")
                            else "Unknown"
                        )
                        # Keep earliest add date when same track in multiple playlists
                        if uri not in recent_tracks or added_at < recent_tracks[uri]["added_at"]:
                            recent_tracks[uri] = {
                                "name": track["name"],
                                "artist": artist,
                                "added_at": added_at,
                                "source": pname,
                            }
                        matched_count += 1

                if results.get("next"):
                    try:
                        results = sp.next(results)
                    except Exception:
                        break
                    page_num += 1
                    if page_num % 5 == 0:
                        time.sleep(0.5)
                else:
                    break

            playlist_stats.append({
                "name": pname,
                "total": playlist["tracks"]["total"],
                "matched": matched_count,
            })
            progress.advance(task)

    # --- Display results ---
    console.print(f"\n{'─' * 50}")
    console.print(
        f"[bold green]Found {len(recent_tracks)} unique tracks[/bold green] "
        f"added in the last {days_back} days."
    )

    if skipped:
        console.print(
            f"[yellow]Skipped {len(skipped)} playlists due to API errors.[/yellow]"
        )

    # Per-playlist breakdown
    stats_with_matches = [s for s in playlist_stats if s.get("matched", 0) > 0]
    if stats_with_matches:
        table = Table(title="Playlists With Recent Adds")
        table.add_column("Playlist", style="cyan")
        table.add_column("Matched", justify="right", style="green")
        table.add_column("Total", justify="right", style="dim")

        for stat in sorted(stats_with_matches, key=lambda s: s["matched"], reverse=True):
            table.add_row(
                stat["name"][:45],
                str(stat["matched"]),
                str(stat.get("total", "-")),
            )
        console.print(table)

    if not recent_tracks:
        console.print("[yellow]No recent tracks found. Nothing to do.[/yellow]")
        Prompt.ask("\nPress Enter to continue")
        return

    # Sort newest first
    sorted_tracks = sorted(
        recent_tracks.items(), key=lambda x: x[1]["added_at"], reverse=True
    )

    # Show preview
    preview_count = min(15, len(sorted_tracks))
    table = Table(title=f"Preview (newest {preview_count} of {len(sorted_tracks)})")
    table.add_column("Date Added", style="dim")
    table.add_column("Artist", style="cyan")
    table.add_column("Track", style="green")
    table.add_column("Source Playlist", style="yellow")

    for _, info in sorted_tracks[:preview_count]:
        table.add_row(
            info["added_at"].strftime("%Y-%m-%d"),
            info["artist"][:25],
            info["name"][:35],
            info["source"][:25],
        )
    if len(sorted_tracks) > preview_count:
        table.add_row("...", f"+ {len(sorted_tracks) - preview_count} more", "", "")

    console.print(table)

    # --- Dry run exit ---
    if dry_run:
        console.print(
            f"\n[bold yellow][DRY RUN][/bold yellow] Would add "
            f"{len(sorted_tracks)} tracks to '{playlist_name}'."
        )
        Prompt.ask("\nPress Enter to continue")
        return

    # --- Create or update playlist ---
    if not Confirm.ask(
        f"\nAdd {len(sorted_tracks)} tracks to '{playlist_name}'?", default=True
    ):
        console.print("[yellow]Cancelled.[/yellow]")
        Prompt.ask("\nPress Enter to continue")
        return

    try:
        # Look for existing playlist with same name owned by user
        target_id = None
        for p in all_playlists:
            if p["name"] == playlist_name and p["owner"]["id"] == user_id:
                target_id = p["id"]
                console.print(
                    f"[cyan]Found existing playlist '{playlist_name}' "
                    f"- replacing contents.[/cyan]"
                )
                break

        if not target_id:
            new_pl = sp.user_playlist_create(
                user_id,
                playlist_name,
                public=False,
                description=(
                    f"Auto-generated: tracks added to playlists "
                    f"in the last {days_back} days."
                ),
            )
            target_id = new_pl["id"]
            console.print(f"[green]Created new playlist: {playlist_name}[/green]")

        # Clear existing tracks
        sp.playlist_replace_items(target_id, [])

        # Add in batches of 100
        track_uris = [uri for uri, _ in sorted_tracks]
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            add_task = progress.add_task("Adding tracks...", total=len(track_uris))
            for batch_start in range(0, len(track_uris), 100):
                batch = track_uris[batch_start: batch_start + 100]
                sp.playlist_add_items(target_id, batch)
                progress.advance(add_task, advance=len(batch))

        console.print(
            f"\n[bold green]Done! {len(track_uris)} tracks added to "
            f"'{playlist_name}'[/bold green]"
        )
        console.print(
            f"[dim]https://open.spotify.com/playlist/{target_id}[/dim]"
        )

    except Exception as e:
        console.print(f"[bold red]Error creating/updating playlist:[/bold red] {str(e)}")
        logger.error("Recent tracks aggregator error: %s", e, exc_info=True)

    Prompt.ask("\nPress Enter to continue")
