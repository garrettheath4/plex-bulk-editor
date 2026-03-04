# Plex Episode Metadata Bulk Editor

Bulk edit Plex episode metadata (titles, summaries), especially useful for **specials** (Season 0). Uses the Plex API to update your TV library without touching the media files.

## Features

- **edit-csv** — Update episodes from a CSV file (season, episode, title, summary)
- **edit-filenames** — Derive titles from filenames (e.g. `Show Name - s00e631 - Episode Title.ext`)
- **edit-episodes** — Update specific episodes from a JSON file
- **interactive** — Step through episodes and edit one-by-one
- **list-specials** — List all special episodes for a show
- **find-token** — Print instructions (and optional login flow) to get your Plex token

## Requirements

- Python 3
- [plexapi](https://github.com/pkkid/python-plexapi), [requests](https://requests.readthedocs.io/)

```bash
# Install pipenv
pip3 install pipenv
# Set up and activate the Python virtual environment
pipenv install
pipenv shell
```

## Setup

1. **Plex token**
   Set the `PLEX_TOKEN` environment variable, or run `./plex_bulk_editor.py find-token` for instructions.

   ```bash
   export PLEX_TOKEN='your_token_here'
   ```

2. **Configuration** (optional)
   - **Plex token** — Set `PLEX_TOKEN` (see above).
   - **Plex URL** — Use `--plex-url` (default: `http://localhost:32400`). Use `https://` if your server requires secure connections.
   - **TV library** — Use `--tv-library` (default: `TV Shows`) if your Plex TV library has a different name.

   The script uses a session that skips SSL verification (for self-signed certs on LAN).

## Usage

Optional global arguments (can appear before the command):

| Argument | Default | Description |
|----------|---------|-------------|
| `--plex-url URL` | `http://localhost:32400` | Plex server URL |
| `--tv-library NAME` | `TV Shows` | Plex TV library name |

All commands that modify or list a show require the **show name** as the first argument after the command (exact name as in Plex).

| Command | Description |
|--------|-------------|
| `edit-csv SHOW CSV_FILE` | Edit episodes from CSV |
| `edit-filenames SHOW [--dry-run]` | Set titles from filenames |
| `edit-episodes SHOW EPISODES_JSON` | Edit episodes from JSON |
| `interactive SHOW` | Interactive edit |
| `list-specials SHOW` | List specials |
| `find-token` | How to get your Plex token (no show needed) |

### Examples

```bash
# Get your Plex token (no PLEX_TOKEN needed)
./plex_bulk_editor.py find-token

# List specials (uses default http://localhost:32400 and "TV Shows" library)
./plex_bulk_editor.py list-specials "Star Trek: The Next Generation"

# Custom Plex URL and TV library
./plex_bulk_editor.py --plex-url https://myplex.example.com:32400 --tv-library Television list-specials "Star Trek: The Next Generation"

# Preview filename-based title updates
./plex_bulk_editor.py edit-filenames "Star Trek: The Next Generation" --dry-run

# Apply title/summary from filenames
./plex_bulk_editor.py edit-filenames "Star Trek: The Next Generation"

# Bulk edit from CSV (columns: season, episode, title, summary)
./plex_bulk_editor.py edit-csv "Star Trek: The Next Generation" episodes.csv

# Bulk edit from JSON (array of {season, episode, title, summary?})
./plex_bulk_editor.py edit-episodes "Star Trek: The Next Generation" episodes.json

# Interactive mode
./plex_bulk_editor.py interactive "Star Trek: The Next Generation"
```

### CSV format (edit-csv)

```csv
season,episode,title,summary
0,631,Allegiance,Behind the scenes featurette
0,632,Making of SG-1,Documentary about the show
```

### JSON format (edit-episodes)

```json
[
  {"season": 0, "episode": 631, "title": "Allegiance", "summary": "Behind the scenes"},
  {"season": 0, "episode": 632, "title": "Making of SG-1"}
]
```

### Filename format (edit-filenames)

Expected pattern: `Show Name - s00e631 - Episode Title.ext`
The script uses the part after the episode number as the new title.

## License

Use and modify as you like.
