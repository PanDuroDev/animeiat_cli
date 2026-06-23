# animeiat-cli

**Stream & Play anime from the terminal.**

An interactive TUI (Terminal User Interface) application for searching, browsing, and playing anime episodes from multiple providers. Built with Python and [Rich](https://github.com/Textualize/rich).

---

## Features

- **Multi-provider**: Anime3rb, Witanime, Anineko, HiAnime, 9Anime
- **Interactive TUI**: Search, browse, select episodes with keyboard navigation
- **Smooth animations**: Terminal-native scroll transitions (no `time.sleep()`)
- **Multi-player**: VLC, MPV, IINA (macOS), Celluloid, Haruna
- **Playback tracking**: Resume from where you left off
- **Cookie extraction**: Auto-extract from Chrome/Edge for provider access
- **Favorites & Continue Watching**: Persistent watch history
- **Download manager**: Queue episodes for download
- **Stream caching**: Configurable TTL cache for resolved URLs
- **Multi-platform**: Windows, macOS, Linux
- **Docker**: Ready-to-run container image
- **AniList / MyAnimeList**: Account linking (scaffolding)

---

## Quick Start

### Requirements

- **Python** 3.10 or later
- One of: **VLC**, **MPV**, **IINA** (macOS), **Celluloid**, or **Haruna**

### Install

```bash
# 1. Clone the repo
git clone https://github.com/PanDuroDev/animeiat_cli.git
cd animeiat_cli

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Playwright browser (for cookie extraction)
playwright install chromium

# 4. Run
python anime_cli.py
```

> The app will auto-install missing dependencies on first run.

### Run with Docker

```bash
docker build -t animeiat-cli .
docker run -it animeiat-cli
```

---

## Installation Guides

### Windows

1. **Install Python 3.10+**
   - Download from [python.org](https://www.python.org/downloads/)
   - **Important**: Check "Add Python to PATH" during installation

2. **Install a player** (pick one)
   - [VLC](https://www.videolan.org/vlc/) — `winget install VideoLAN.VLC`
   - [MPV](https://mpv.io/installation/) — `winget install mpv.net`
   - Or via Chocolatey: `choco install vlc` / `choco install mpv`

3. **Clone and install**
   ```powershell
   git clone https://github.com/anomalyco/animeiat-cli.git
   cd animeiat-cli
   pip install -r requirements.txt
   playwright install chromium
   python anime_cli.py
   ```

4. **Troubleshooting**
   - If `playwright install chromium` fails, run PowerShell as Administrator and try again
   - If you see encoding issues, your terminal must support UTF-8

---

### macOS

1. **Install Python 3.10+**
   ```bash
   brew install python@3.13
   ```
   Or download from [python.org](https://www.python.org/downloads/)

2. **Install a player**
   ```bash
   brew install --cask vlc mpv iina
   ```

3. **Clone and install**
   ```bash
   git clone https://github.com/anomalyco/animeiat-cli.git
   cd animeiat-cli
   pip3 install -r requirements.txt
   playwright install chromium
   python3 anime_cli.py
   ```

---

### Linux (Debian / Ubuntu)

```bash
# Python 3.10+ is usually pre-installed
sudo apt update
sudo apt install -y python3 python3-pip python3-venv mpv

# Clone and run
git clone https://github.com/PanDuroDev/animeiat_cli.git
cd animeiat_cli
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python3 anime_cli.py
```

**Other distributions:**

| Distro | Player install |
|--------|---------------|
| Fedora | `sudo dnf install mpv` |
| Arch   | `sudo pacman -S mpv` |
| openSUSE | `sudo zypper install mpv` |
| Alpine | `sudo apk add mpv` |
| Gentoo | `sudo emerge media-video/mpv` |
| Void   | `sudo xbps-install -S mpv` |

---

## Usage

### Interactive mode (default)

```bash
python anime_cli.py
```

Keyboard controls inside the TUI:
- `↑`/`↓` — Navigate items
- `Enter` — Select / Play
- `d` — Toggle details panel
- `Esc` — Go back
- `q` — Quit

### CLI mode

```bash
# Play a specific URL
python anime_cli.py --url https://anime3rb.com/... --no-tui

# With preferred player
python anime_cli.py --player mpv

# List episodes (JSON output)
python anime_cli.py --url https://... --list-episodes --json

# Download an episode
python anime_cli.py --url https://... --download
```

---

## Configuration

Config file location:
- **Windows**: `%APPDATA%\animeiat_cli\config.json`
- **macOS/Linux**: `~/.config/animeiat_cli/config.json`

Settings available:
- Default player and quality
- Preferred search sources
- Custom player arguments (e.g., `--fullscreen --volume=80`)
- Theme (customizable colors)
- Stream cache TTL

---

## Project Structure

```
animeiat-cli/
├── anime_cli.py          # Entry point
├── src/
│   ├── ui/               # TUI & CLI interface
│   │   ├── tui.py        # Interactive terminal UI
│   │   └── cli.py        # CLI argument parsing
│   ├── providers/        # Anime source providers
│   ├── playback/         # Player discovery & launch
│   ├── cache/            # Stream URL caching
│   ├── config/           # Configuration management
│   └── db/               # SQLite database layer
├── scraping.py           # Legacy scraping (deprecated)
├── Dockerfile            # Container build
└── requirements.txt      # Python dependencies
```

---

## Development

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development setup and guidelines.

Tests live in the `develop` branch:
```bash
git checkout develop
pip install -r requirements.txt
pytest tests/ -v
```

---

## License

[MIT](./LICENSE)

---

## Links

- [GitHub Repository](https://github.com/PanDuroDev/animeiat_cli)
- [Issue Tracker](https://github.com/PanDuroDev/animeiat_cli/issues)
