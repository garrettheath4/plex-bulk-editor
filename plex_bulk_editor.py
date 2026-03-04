#!/usr/bin/env python3
"""
Bulk edit Plex episode metadata for specials
"""

import argparse
import json
import logging
import os
import csv
import sys
import urllib3

import requests
from plexapi.server import PlexServer

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============================================================
# CONFIGURATION - EDIT THESE VALUES
# ============================================================

# Use hostname (not resolved IP) so Cursor sandbox allowlist allows the connection.
# Use https if Plex "Secure connections" is set to Required (otherwise you get
# RemoteDisconnected: Remote end closed connection without response).
# Overridden by --plex-url CLI argument (default: http://localhost:32400).
PLEX_URL = 'http://localhost:32400'
PLEX_TOKEN = os.environ.get('PLEX_TOKEN', '').strip()

# Session that skips SSL verify (Plex often uses self-signed certs on LAN).
_plex_session = requests.Session()
_plex_session.verify = False

# Your TV library name in Plex. Overridden by --tv-library CLI argument (default: TV Shows).
TV_LIBRARY_NAME = 'TV Shows'

# Suffixes to strip from parsed titles (case-insensitive). For example: `Pilot [HD]` -> `Pilot`
QUALITY_VALUES_TO_STRIP = ('HD', '4K', '480p', '720p', '1080p')

# ============================================================
# OPTION 1: Edit episodes from a CSV file
# ============================================================

def edit_from_csv(show_name: str, csv_file: str):
    """
    Edit episodes from a CSV file.

    CSV Format (with header):
    season,episode,title,summary
    0,631,Allegiance,Behind the scenes featurette
    0,632,Making of SG-1,Documentary about the show

    Args:
        csv_file: Path to CSV file with episode data
    """
    plex = PlexServer(PLEX_URL, PLEX_TOKEN, session=_plex_session)
    library = plex.library.section(TV_LIBRARY_NAME)
    show = library.get(show_name)

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            season_num = int(row['season'])
            episode_num = int(row['episode'])
            new_title = row['title']
            new_summary = row.get('summary', '')  # Optional

            try:
                # Get the episode
                episode = show.episode(season=season_num, episode=episode_num)

                print(f"Found: S{season_num:02d}E{episode_num:03d} - Current title: '{episode.title}'")

                # Edit the episode metadata
                edits = {'title.value': new_title}
                if new_summary:
                    edits['summary.value'] = new_summary

                episode.edit(**edits)
                episode.reload()

                print(f"  ✓ Updated to: '{episode.title}'")

            except Exception as e:
                print(f"  ✗ Error updating S{season_num:02d}E{episode_num:03d}: {e}")

# ============================================================
# OPTION 2: Parse titles from filenames
# ============================================================

def edit_from_filenames(show_name: str, dry_run=False):
    """
    Parse episode titles from filenames automatically.
    Expects format: "Show Name - s00e631 - Episode Title.ext"
    """
    plex = PlexServer(PLEX_URL, PLEX_TOKEN, session=_plex_session)
    library = plex.library.section(TV_LIBRARY_NAME)
    show = library.get(show_name)

    # Get all specials (Season 0)
    season = show.season(0)

    for episode in season.episodes():
        # Get the filename
        media = episode.media[0]
        part = media.parts[0]
        filepath = part.file
        filename = filepath.split('/')[-1]  # Get just the filename

        # Parse the title from filename
        # Format: "Show Name - s00e631 - Episode Title.ext"
        try:
            # Split by ' - ' and get the part after episode number
            parts = filename.split(' - ')
            if len(parts) >= 3:
                # Remove file extension from title
                title_with_ext = parts[2]
                new_title = title_with_ext.rsplit('.', 1)[0]
                # Strip quality suffixes (case-insensitive)
                for quality in QUALITY_VALUES_TO_STRIP:
                    suffix = f" [{quality}]"
                    if new_title.upper().endswith(suffix.upper()):
                        new_title = new_title[:-len(suffix)].rstrip()
                        break

                current_title = episode.title

                # Only update if different
                if current_title != new_title:
                    print(f"S{episode.seasonNumber:02d}E{episode.episodeNumber:03d}")
                    print(f"  Current: '{current_title}'")
                    print(f"  New:     '{new_title}'")

                    if not dry_run:
                        episode.edit(**{'title.value': new_title})
                        print(f"  ✓ Updated")
                    else:
                        print(f"  ✗ Skipped (dry run)")
                else:
                    print(f"S{episode.seasonNumber:02d}E{episode.episodeNumber:03d} - Already correct: '{current_title}'")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

# ============================================================
# OPTION 3: Interactive mode
# ============================================================

def edit_interactive(show_name: str):
    """
    Interactively edit episodes one by one
    """
    plex = PlexServer(PLEX_URL, PLEX_TOKEN, session=_plex_session)
    library = plex.library.section(TV_LIBRARY_NAME)
    show = library.get(show_name)

    # Get all specials (Season 0)
    season = show.season(0)

    for episode in season.episodes():
        print(f"\n{'='*60}")
        print(f"Season {episode.seasonNumber}, Episode {episode.episodeNumber}")
        print(f"Current Title: {episode.title}")
        print(f"Current Summary: {episode.summary[:100]}..." if episode.summary else "No summary")

        # Get filename for reference
        media = episode.media[0]
        part = media.parts[0]
        filepath = part.file
        filename = filepath.split('/')[-1]
        print(f"Filename: {filename}")

        choice = input("\nEdit this episode? (y/n/q to quit): ").lower()

        if choice == 'q':
            break
        elif choice == 'y':
            new_title = input("New title (press Enter to skip): ")
            new_summary = input("New summary (press Enter to skip): ")

            edits = {}
            if new_title:
                edits['title.value'] = new_title
            if new_summary:
                edits['summary.value'] = new_summary

            if edits:
                episode.edit(**edits)
                episode.reload()
                print("✓ Updated!")

# ============================================================
# OPTION 4: Specific episodes
# ============================================================

def edit_specific_episodes(show_name: str, episodes_dict: dict):
    """
    Edit specific episodes with a dictionary.

    Args:
        episodes_dict: Dict with format {(season, episode): {'title': '', 'summary': ''}}

    Example:
        episodes = {
            (0, 631): {'title': 'Allegiance', 'summary': 'Behind the scenes'},
            (0, 632): {'title': 'Making of SG-1', 'summary': 'Documentary'},
        }
    """
    plex = PlexServer(PLEX_URL, PLEX_TOKEN, session=_plex_session)
    library = plex.library.section(TV_LIBRARY_NAME)
    show = library.get(show_name)

    for (season_num, episode_num), metadata in episodes_dict.items():
        try:
            episode = show.episode(season=season_num, episode=episode_num)

            print(f"\nS{season_num:02d}E{episode_num:03d}")
            print(f"  Current: '{episode.title}'")

            edits = {}
            if 'title' in metadata:
                edits['title.value'] = metadata['title']
            if 'summary' in metadata:
                edits['summary.value'] = metadata['summary']

            episode.edit(**edits)
            episode.reload()

            print(f"  New:     '{episode.title}'")
            print(f"  ✓ Updated")

        except Exception as e:
            print(f"  ✗ Error: {e}")

# ============================================================
# HELPER: Get your Plex token
# ============================================================

def find_plex_token():
    """
    Instructions to find your Plex token
    """
    print("""
    To find your Plex token:

    1. Sign in to Plex Web (app.plex.tv)
    2. Browse to a library item
    3. Click the three dots (...) > Get Info > View XML
    4. Look at the URL - your token is after "X-Plex-Token="

    Or use this method:
    """)

    from plexapi.myplex import MyPlexAccount
    username = input("Plex username/email: ")
    password = input("Plex password: ")

    account = MyPlexAccount(username, password)
    print(f"\nYour Plex token: {account.authenticationToken}")

# ============================================================
# HELPER: List all shows/episodes
# ============================================================

def list_specials(show_name: str):
    """
    List all special episodes for reference
    """
    plex = PlexServer(PLEX_URL, PLEX_TOKEN, session=_plex_session)
    library = plex.library.section(TV_LIBRARY_NAME)
    show = library.get(show_name)

    # Get Season 0 (Specials)
    try:
        season = show.season(0)
        print(f"\nSpecials for '{show_name}':")
        print("=" * 80)

        for episode in season.episodes():
            media = episode.media[0] if episode.media else None
            part = media.parts[0] if media else None
            filename = part.file.split('/')[-1] if part else "N/A"

            print(f"S{episode.seasonNumber:02d}E{episode.episodeNumber:03d} - {episode.title}")
            print(f"  File: {filename}")
            print()

    except Exception as e:
        print(f"Error: {e}")

# ============================================================
# MAIN - CLI
# ============================================================

def _episodes_json_to_dict(path: str) -> dict:
    """Load JSON array of {season, episode, title?, summary?} into episodes_dict format."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {
        (int(item['season']), int(item['episode'])): {
            k: v for k, v in item.items() if k in ('title', 'summary') and v
        }
        for item in data
    }


def _connection_error_message():
    print(
        "\n⚠️  Could not reach Plex server. Common causes:\n"
        "  • Running from a different machine/network than where 'nc' worked\n"
        "  • IPv6 unreachable (script now forces IPv4; try again)\n"
        "  • Plex server or port 32400 not reachable from this host\n"
    )


def main():
    global PLEX_URL, TV_LIBRARY_NAME
    parser = argparse.ArgumentParser(
        description='Plex Episode Metadata Bulk Editor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--plex-url',
        default='http://localhost:32400',
        help='Plex server URL (default: http://localhost:32400)',
    )
    parser.add_argument(
        '--tv-library',
        default='TV Shows',
        help='Plex TV library name (default: TV Shows)',
    )
    subparsers = parser.add_subparsers(dest='command', required=True, metavar='COMMAND')

    # edit-csv
    p_edit_csv = subparsers.add_parser('edit-csv', help='Edit episodes from a CSV file')
    p_edit_csv.add_argument('show', help='Plex TV show name')
    p_edit_csv.add_argument('csv_file', help='Path to CSV (columns: season, episode, title, summary)')

    # edit-filenames
    p_edit_filenames = subparsers.add_parser('edit-filenames', help='Parse titles from filenames')
    p_edit_filenames.add_argument('show', help='Plex TV show name')
    p_edit_filenames.add_argument('--dry-run', action='store_true', help='Show changes without applying')

    # interactive
    p_interactive = subparsers.add_parser('interactive', help='Interactively edit episodes one by one')
    p_interactive.add_argument('show', help='Plex TV show name')

    # edit-episodes
    p_edit_episodes = subparsers.add_parser('edit-episodes', help='Edit specific episodes from a JSON file')
    p_edit_episodes.add_argument('show', help='Plex TV show name')
    p_edit_episodes.add_argument(
        'episodes_file',
        help='JSON file: array of {"season", "episode", "title", "summary?"}',
    )

    # list-specials
    p_list_specials = subparsers.add_parser('list-specials', help='List all special episodes')
    p_list_specials.add_argument('show', help='Plex TV show name')

    # find-token
    subparsers.add_parser('find-token', help='Print instructions to find your Plex token')

    args = parser.parse_args()
    PLEX_URL = args.plex_url
    TV_LIBRARY_NAME = args.tv_library
    show_name = getattr(args, 'show', None)

    if args.command == 'find-token':
        find_plex_token()
        return
    if not PLEX_TOKEN:
        print('No Plex token found. Set PLEX_TOKEN or run: python main.py find-token')
        find_plex_token()
        sys.exit(1)

    print('Plex Episode Metadata Bulk Editor')
    print('=' * 60)

    try:
        if args.command == 'edit-csv':
            edit_from_csv(show_name, args.csv_file)
        elif args.command == 'edit-filenames':
            edit_from_filenames(show_name, dry_run=args.dry_run)
        elif args.command == 'interactive':
            edit_interactive(show_name)
        elif args.command == 'edit-episodes':
            episodes_dict = _episodes_json_to_dict(args.episodes_file)
            edit_specific_episodes(show_name, episodes_dict)
        elif args.command == 'list-specials':
            list_specials(show_name)
    except requests.exceptions.ConnectionError:
        _connection_error_message()
        raise


if __name__ == '__main__':
    main()
