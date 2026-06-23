# animeiat-cli

A terminal application for searching and playing anime episodes from multiple web providers.

![License](https://img.shields.io/github/license/PanDuroDev/animeiat_cli?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey?style=for-the-badge)

## Table of Contents

- [For End Users](#for-end-users)
  - [What It Does](#what-it-does)
  - [Before You Start](#before-you-start)
  - [Quick Install](#quick-install)
  - [How to Use It](#how-to-use-it)
  - [Troubleshooting](#troubleshooting)
- [For Developers](#for-developers)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [CLI Reference](#cli-reference)
  - [Configuration](#configuration)
  - [Project Structure](#project-structure)
  - [Contributing](#contributing)
- [License](#license)

---

## For End Users

### What It Does

animeiat-cli is a program that runs in your terminal (command prompt) and lets you search for anime, browse episodes, and play them in your preferred media player. It pulls episode data from multiple anime websites, so you do not need to open a browser or deal with ads.

Key capabilities:

- Search anime by name across multiple source websites.
- Browse episode lists with keyboard navigation.
- Play episodes directly in VLC, MPV, or another installed media player.
- Pick up where you left off — watch history is saved locally.
- Bookmark shows as favorites or download episodes for offline viewing.
- All data stays on your machine. No account required.

### Before You Start

You need:

- **A computer** running Windows, macOS, or Linux.
- **Python** version 3.10 or newer installed on your system.
- **A media player** such as VLC or MPV. The app will detect one automatically.
- **Chrome or Edge browser** (optional) — used only to extract cookies for provider access. The app does not read personal data.

If you are not sure how to install Python, download it from [python.org](https://www.python.org/downloads/) and check the box that says "Add Python to PATH" during installation (Windows) or use your system package manager (macOS/Linux).

### Quick Install

1. **Install Python and a media player** (see [Before You Start](#before-you-start) above).

2. **Download the project.** Click the green "Code" button on the [GitHub page](https://github.com/PanDuroDev/animeiat_cli) and select "Download ZIP", then extract it. Or use Git:

   ```bash
   git clone https://github.com/PanDuroDev/animeiat_cli.git
   cd animeiat_cli
   ```

3. **Install the required Python packages.** Open a terminal (Command Prompt on Windows, Terminal on macOS/Linux) in the project folder and run:

   ```bash
   pip install -r requirements.txt
   ```

   If this fails, try `pip3` instead of `pip`, or run `python -m pip install -r requirements.txt`.

4. **Install the Playwright browser component** (needed for cookie-based provider access):

   ```bash
   playwright install chromium
   ```

   On Linux you may need to run `playwright install --with-deps chromium` to install system libraries.

5. **Run the application:**

   ```bash
   python anime_cli.py
   ```

   Use `python3` on macOS and Linux if `python` is not found.

The app will attempt to auto-install any missing dependencies on first run. If `playwright install chromium` succeeds, everything is ready.

#### Docker

If you have Docker installed, you can skip the manual setup:

```bash
docker build -t animeiat-cli .
docker run -it animeiat-cli
```

### How to Use It

Run `python anime_cli.py` to start the interactive TUI (Terminal User Interface).

The main menu shows these options:

- **Search** — type an anime name to search across providers.
- **URL** — paste a direct URL from a supported provider.
- **Favorites** — browse your bookmarked shows.
- **Continue Watching** — resume a show you started.
- **Download Manager** — manage queued downloads.
- **Settings** — change player, quality, appearance, and more.
- **Exit** — quit the application.

Use the arrow keys (Up/Down) to move through lists and press Enter to select. Press `d` to toggle a details panel on the right side of the screen. Press `Esc` to go back and `q` to quit.

#### Non-interactive mode

You can also use the app without the TUI:

```bash
# Play a specific URL directly
python anime_cli.py --url https://example.com/anime/... --no-tui

# List episodes as JSON
python anime_cli.py --url https://... --list-episodes --json

# Queue an episode for download
python anime_cli.py --url https://... --download

# Show version
python anime_cli.py --version
```

### Troubleshooting

| Problem | Likely cause | Solution |
|---------|-------------|----------|
| `pip` is not recognized | Python not in PATH | Reinstall Python and check "Add Python to PATH". Restart your terminal. |
| `playwright install chromium` fails | Missing system dependencies (Linux) | Run `playwright install --with-deps chromium` instead. |
| "No player found" on startup | VLC or MPV not installed | Install one of the supported players. See [Before You Start](#before-you-start). |
| App opens but no search results | Browser cookies not available | The app needs cookies from Chrome or Edge to access providers. Open the browser, visit the provider site once, then restart the app. |
| TUI looks garbled or misaligned | Terminal font or size issue | Use a modern terminal (Windows Terminal, iTerm2, GNOME Terminal). Set the font to a monospace font. |

---

## For Developers

### Requirements

- Python 3.10 or later.
- Windows, macOS, or Linux.
- One of: VLC, MPV, IINA (macOS only), Celluloid, Haruna.
- Chrome or Edge (optional, for cookie extraction).

Runtime dependencies (installed via `pip install -r requirements.txt`):

| Package | Purpose |
|---------|---------|
| `rich` | Terminal UI rendering |
| `httpx` | HTTP client for provider API calls |
| `beautifulsoup4` + `lxml` | HTML parsing |
| `playwright` | Browser cookie extraction |
| `pycryptodome` | Cookie decryption |
| `keyring` | Cookie key fallback on macOS/Linux (optional) |

### Installation

```bash
git clone https://github.com/PanDuroDev/animeiat_cli.git
cd animeiat_cli
pip install -r requirements.txt
playwright install chromium
python anime_cli.py
```

On Linux, if `playwright install chromium` fails, run:

```bash
playwright install --with-deps chromium
```

### CLI Reference

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--help` | `-h` | — | — | Show help message and exit |
| `--player` | `-p` | string | `auto` | Preferred player: `auto`, `vlc`, `mpv`, `iina`, `celluloid`, `haruna` |
| `--quality` | `-q` | string | `auto` | Stream quality: `auto`, `1080p`, `720p`, `480p`, `360p` |
| `--url` | `-u` | string | — | Anime URL to play (overrides search) |
| `--no-tui` | — | flag | `false` | Non-interactive mode: play and exit |
| `--version` | `-V` | flag | `false` | Show version and exit |
| `--json` | — | flag | `false` | JSON output (machine-readable, non-interactive mode) |
| `--list-episodes` | — | flag | `false` | List all episodes and exit (non-interactive) |
| `--download` | — | flag | `false` | Queue stream URL for download and exit |

### Configuration

The config file is created automatically on first run. Location:

| Platform | Path |
|----------|------|
| Windows | `%APPDATA%\animeiat_cli\config.json` |
| macOS/Linux | `~/.config/animeiat_cli/config.json` |

Available keys:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `preferred_player` | string | `"auto"` | Media player to use. Options: `auto`, `vlc`, `mpv`, `iina`, `celluloid`, `haruna` |
| `default_quality` | string | `"auto"` | Stream quality preference. Options: `auto`, `1080p`, `720p`, `480p`, `360p` |
| `preferred_browser` | string | `"auto"` | Browser for cookie extraction: `auto`, `chrome`, `edge` |
| `history_tracking` | bool | `true` | Enable or disable watch history |
| `fullscreen` | bool | `true` | Launch media player in fullscreen mode |
| `custom_player_args` | string | `""` | Extra CLI arguments passed to the media player (e.g. `--volume=80 --fs-screen=2`) |
| `nerd_fonts` | bool | `false` | Enable Nerd Font icons in the TUI (requires a Nerd Font installed) |
| `scraping_method` | string | `"auto"` | Scraping backend: `auto`, `playwright`, `httpx` |
| `enabled_sources` | array | `[0, 1]` | Indices of enabled provider sources. Set in Settings > Search Sources |
| `search_history` | array | `[]` | Recent search queries (max 5, managed automatically) |

### Project Structure

```
animeiat-cli/
├── anime_cli.py              # Entry point — delegates to src/
├── requirements.txt          # Python package dependencies
├── pyproject.toml            # Project metadata (PEP 621)
├── setup.py                  # Cython build configuration
├── Dockerfile                # Container build
├── src/
│   ├── ui/
│   │   ├── tui.py            # Interactive terminal UI (Rich-based)
│   │   └── cli.py            # CLI argument parsing and routing
│   ├── providers/
│   │   ├── witanime.py       # Witanime provider
│   │   ├── anineko.py        # Anineko provider
│   │   └── anime3rb.py       # Anime3rb provider
│   ├── playback/
│   │   ├── discovery.py      # Player detection and installation
│   │   ├── launch.py         # Player process launch (VLC, MPV, IINA, etc.)
│   │   └── progress.py       # Playback progress polling via IPC
│   ├── cache/
│   │   └── stream_cache.py   # SQLite-backed stream URL cache
│   ├── config/
│   │   └── __init__.py       # Config file read/write, theme, icon helpers
│   └── db/
│       └── __init__.py       # SQLite database layer (accounts, favorites, history)
├── scraping.py               # Legacy scraper (deprecated — import src.providers instead)
├── config.py                 # Legacy re-export (deprecated)
├── db.py                     # Legacy re-export (deprecated)
└── player.py                 # Legacy re-export (deprecated)
```

### Contributing

Development happens on the `develop` branch. To set up a development environment:

```bash
git checkout develop
pip install -r requirements.txt
playwright install chromium
pytest tests/ -v
```

All 74 tests must pass before submitting a pull request. See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines on branching, code style, and PR workflow.

---

## License

[MIT](./LICENSE)
