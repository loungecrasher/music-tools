"""Deezer playlist checking and management utilities.

This module provides direct implementations for Deezer playlist operations
using the Deezer API through requests.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()

# Deezer API base URL
DEEZER_API_BASE = "https://api.deezer.com"


def _extract_playlist_id(url_or_id: str) -> str:
    """Extract playlist ID from URL or return as-is if already an ID."""
    # Handle full URLs like https://www.deezer.com/en/playlist/14618296541
    match = re.search(r'playlist[/:](\d+)', url_or_id)
    if match:
        return match.group(1)
    # Handle just numbers
    if url_or_id.strip().isdigit():
        return url_or_id.strip()
    # Assume it's already an ID
    return url_or_id.strip()


def _get_playlist_info(playlist_id: str) -> Dict[str, Any]:
    """Get playlist information from Deezer API."""
    response = requests.get(f"{DEEZER_API_BASE}/playlist/{playlist_id}")
    response.raise_for_status()
    data = response.json()

    if 'error' in data:
        raise ValueError(f"Deezer API error: {data['error'].get('message', 'Unknown error')}")

    return data


def _get_all_playlist_tracks(playlist_id: str) -> List[Dict[str, Any]]:
    """Get all tracks from a Deezer playlist (handles pagination)."""
    tracks = []
    url = f"{DEEZER_API_BASE}/playlist/{playlist_id}/tracks"

    while url:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if 'error' in data:
            raise ValueError(f"Deezer API error: {data['error'].get('message', 'Unknown error')}")

        tracks.extend(data.get('data', []))
        url = data.get('next')  # Pagination URL

    return tracks


def _check_track_availability(track: Dict[str, Any]) -> Dict[str, Any]:
    """Check if a track is available and get additional info."""
    track_id = track.get('id')

    if not track_id:
        return {
            **track,
            'available': False,
            'reason': 'No track ID'
        }

    try:
        response = requests.get(f"{DEEZER_API_BASE}/track/{track_id}")
        data = response.json()

        if 'error' in data:
            return {
                **track,
                'available': False,
                'reason': data['error'].get('message', 'Track not found')
            }

        # Check if track is readable (available for streaming)
        is_readable = data.get('readable', True)

        return {
            **track,
            'available': is_readable,
            'reason': 'Not available in your region' if not is_readable else None,
            'full_data': data
        }
    except Exception as e:
        return {
            **track,
            'available': False,
            'reason': str(e)
        }


async def _check_track_availability_async(
    session: aiohttp.ClientSession,
    track: Dict[str, Any],
    semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """Check track availability using async HTTP."""
    track_id = track.get('id')

    if not track_id:
        return {**track, 'available': False, 'reason': 'No track ID'}

    async with semaphore:
        try:
            async with session.get(
                f"{DEEZER_API_BASE}/track/{track_id}"
            ) as response:
                data = await response.json()

            if 'error' in data:
                return {
                    **track,
                    'available': False,
                    'reason': data['error'].get('message', 'Track not found')
                }

            is_readable = data.get('readable', True)
            return {
                **track,
                'available': is_readable,
                'reason': 'Not available in your region' if not is_readable else None,
                'full_data': data
            }
        except Exception as e:
            return {**track, 'available': False, 'reason': str(e)}


async def _check_tracks_batch(
    tracks: List[Dict[str, Any]],
    max_concurrent: int = 10
) -> List[Dict[str, Any]]:
    """Check availability for all tracks concurrently.

    Args:
        tracks: List of track dicts from the Deezer API.
        max_concurrent: Maximum number of simultaneous requests.

    Returns:
        List of track dicts with availability info, in original order.
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit=max_concurrent)

    async with aiohttp.ClientSession(
        timeout=timeout, connector=connector
    ) as session:
        tasks = [
            _check_track_availability_async(session, track, semaphore)
            for track in tracks
        ]
        return await asyncio.gather(*tasks)


def analyse_playlist(
    playlist_url: str,
    debug_dir: Optional[Path] = None,
    use_api_fallback: bool = True
) -> List[Dict[str, Any]]:
    """Analyze a Deezer playlist and check track availability.

    Args:
        playlist_url: Deezer playlist URL or ID
        debug_dir: Optional directory to save debug output
        use_api_fallback: Whether to use API for additional checks

    Returns:
        List of track dictionaries with availability info
    """
    playlist_id = _extract_playlist_id(playlist_url)

    # Get playlist info
    playlist_info = _get_playlist_info(playlist_id)

    # Get all tracks
    tracks = _get_all_playlist_tracks(playlist_id)

    # Check availability for each track (concurrent when using API)
    if use_api_fallback:
        results = asyncio.run(_check_tracks_batch(tracks))
    else:
        results = [{**track, 'available': True, 'reason': None} for track in tracks]

    # Save debug output if requested
    if debug_dir:
        debug_dir = Path(debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)

        debug_file = debug_dir / f"playlist_{playlist_id}_debug.json"
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump({
                'playlist': playlist_info,
                'tracks': results
            }, f, indent=2, ensure_ascii=False)

    return results


def export_playlist_report(
    tracks: List[Dict[str, Any]],
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Export playlist analysis report to files.

    Args:
        tracks: List of analyzed tracks
        output_dir: Directory to save report files

    Returns:
        Dictionary with file paths and counts
    """
    output_dir = Path(output_dir) if output_dir else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    available = [t for t in tracks if t.get('available', True)]
    unavailable = [t for t in tracks if not t.get('available', True)]

    # Generate available tracks list
    available_file = output_dir / f"deezer_available_{timestamp}.txt"
    with open(available_file, 'w', encoding='utf-8') as f:
        for track in available:
            artist = track.get('artist', {}).get('name', 'Unknown Artist')
            title = track.get('title', 'Unknown Title')
            f.write(f"{artist} - {title}\n")

    # Generate unavailable tracks list
    unavailable_file = output_dir / f"deezer_unavailable_{timestamp}.txt"
    with open(unavailable_file, 'w', encoding='utf-8') as f:
        for track in unavailable:
            artist = track.get('artist', {}).get('name', 'Unknown Artist')
            title = track.get('title', 'Unknown Title')
            reason = track.get('reason', 'Unknown reason')
            f.write(f"{artist} - {title} [{reason}]\n")

    # Generate full report
    report_file = output_dir / f"deezer_report_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'total': len(tracks),
            'available_count': len(available),
            'unavailable_count': len(unavailable),
            'available_tracks': [
                {
                    'id': t.get('id'),
                    'title': t.get('title'),
                    'artist': t.get('artist', {}).get('name'),
                    'album': t.get('album', {}).get('title')
                }
                for t in available
            ],
            'unavailable_tracks': [
                {
                    'id': t.get('id'),
                    'title': t.get('title'),
                    'artist': t.get('artist', {}).get('name'),
                    'reason': t.get('reason')
                }
                for t in unavailable
            ]
        }, f, indent=2, ensure_ascii=False)

    return {
        'total_count': len(tracks),
        'available_count': len(available),
        'unavailable_count': len(unavailable),
        'available_file': str(available_file),
        'unavailable_file': str(unavailable_file),
        'report_file': str(report_file)
    }


def run_deezer_playlist_checker():
    """Interactive Deezer playlist checker."""
    console.print(Panel(
        "[bold green]Deezer Playlist Checker[/bold green]\n\n"
        "Analyze a Deezer playlist and check track availability.\n"
        "This tool will:\n"
        "• Check which tracks are available/unavailable\n"
        "• Generate detailed reports\n"
        "• Export track lists to files",
        title="[bold]Deezer Playlist Checker[/bold]",
        border_style="green"
    ))

    playlist_url = Prompt.ask("\nEnter Deezer playlist URL or ID")
    if not playlist_url:
        console.print("[yellow]No playlist URL provided.[/yellow]")
        Prompt.ask("\nPress Enter to continue")
        return

    playlist_url = playlist_url.strip("'\"")

    # Validate playlist exists
    try:
        playlist_id = _extract_playlist_id(playlist_url)
        with console.status("[bold green]Checking playlist...[/bold green]"):
            playlist_info = _get_playlist_info(playlist_id)

        console.print(f"\n[green]✓ Found playlist:[/green] {playlist_info['title']}")
        console.print(f"[dim]Creator: {playlist_info.get('creator', {}).get('name', 'Unknown')}[/dim]")
        console.print(f"[dim]Tracks: {playlist_info.get('nb_tracks', 'Unknown')}[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error accessing playlist:[/bold red] {str(e)}")
        Prompt.ask("\nPress Enter to continue")
        return

    output_dir_str = Prompt.ask("\nOutput directory (Enter for current)", default="")
    output_dir = Path(output_dir_str) if output_dir_str else Path.cwd()

    check_availability = Confirm.ask("Check individual track availability?", default=True)

    console.print("\n[bold cyan]Analyzing playlist...[/bold cyan]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching tracks...", total=None)
            tracks = analyse_playlist(
                playlist_url,
                use_api_fallback=check_availability
            )
            progress.update(task, description="Analysis complete!")

        # Show summary
        available = [t for t in tracks if t.get('available', True)]
        unavailable = [t for t in tracks if not t.get('available', True)]

        console.print("\n[bold green]✓ Analysis complete![/bold green]")
        console.print(f"Total tracks: {len(tracks)}")
        console.print(f"[green]Available: {len(available)}[/green]")
        console.print(f"[red]Unavailable: {len(unavailable)}[/red]")

        # Show unavailable tracks if any
        if unavailable:
            console.print("\n[yellow]Unavailable tracks:[/yellow]")
            table = Table()
            table.add_column("Track", style="yellow")
            table.add_column("Artist", style="cyan")
            table.add_column("Reason", style="red")

            for track in unavailable[:10]:
                table.add_row(
                    track.get('title', 'Unknown')[:40],
                    track.get('artist', {}).get('name', 'Unknown')[:30],
                    track.get('reason', 'Unknown')[:30]
                )

            if len(unavailable) > 10:
                console.print(f"[dim]... and {len(unavailable) - 10} more[/dim]")

            console.print(table)

        # Export reports
        if Confirm.ask("\nExport reports to files?", default=True):
            with console.status("[bold green]Generating reports...[/bold green]"):
                files = export_playlist_report(tracks, output_dir=output_dir)

            console.print("\n[bold green]✓ Reports generated:[/bold green]")
            console.print(f"Available list: {files['available_file']}")
            console.print(f"Unavailable list: {files['unavailable_file']}")
            console.print(f"Full report: {files['report_file']}")

    except Exception as e:
        console.print(f"[bold red]Error analyzing playlist:[/bold red] {str(e)}")

    Prompt.ask("\nPress Enter to continue")
