# animeiat-cli

<p align="center">
  <a href="README.ar.md">العربية</a> &nbsp;|&nbsp; <strong>English</strong>
</p>

A terminal application for searching and playing anime episodes from multiple web providers. No ads. No browser needed.

![License](https://img.shields.io/github/license/PanDuroDev/animeiat_cli?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey?style=for-the-badge)
[![Latest Release](https://img.shields.io/github/v/release/PanDuroDev/animeiat_cli?style=for-the-badge)](https://github.com/PanDuroDev/animeiat_cli/releases)

## Table of Contents

- [For End Users](#for-end-users)
  - [What It Does](#what-it-does)
  - [Before You Start](#before-you-start)
  - [Download Prebuilt Binary](#download-prebuilt-binary)
  - [Quick Install (from source)](#quick-install-from-source)
  - [How to Use It](#how-to-use-it)
  - [Troubleshooting](#troubleshooting)
- [For Developers](#for-developers)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Build System](#build-system)
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
- **Python 3.10+** (if running from source) or just download the prebuilt binary.
- **A media player** such as VLC or MPV. The app will detect one automatically.
- **Chrome or Edge browser** (optional) — used only to extract cookies for provider access. The app does not read personal data.

If you are not sure how to install Python, download it from [python.org](https://www.python.org/downloads/) and check the box that says "Add Python to PATH" during installation (Windows) or use your system package manager (macOS/Linux).

### Download Prebuilt Binary

Prebuilt executables are available on the [Releases page](https://github.com/PanDuroDev/animeiat_cli/releases).

| Platform | File | Status |
|----------|------|--------|
| Windows | `animeiat-cli-windows.zip` | Available |
| macOS | — | Build via CI or manually (see [Build System](#build-system)) |
| Linux | — | Build via CI or manually (see [Build System](#build-system)) |

> **Note:** Cross-compilation is not supported. Each platform must be built natively.
> Push a version tag (`v*`) to trigger [GitHub Actions](https://github.com/PanDuroDev/animeiat_cli/actions) to build all platforms automatically.

No Python installation required for prebuilt binaries. Just download, extract, and run.

#> **Note:** This `main` branch is for production use. Development (including tests and experimental scripts) is on the `develop` branch.

## Quick Install (from source)

1. **Install Python and a media player** (see [Before You Start](#before-you-start) above).

2. **Download the project:**

   ```bash
   git clone https://github.com/PanDuroDev/animeiat_cli.git
   cd animeiat_cli
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   If this fails, try `pip3` instead of `pip`, or run `python -m pip install -r requirements.txt`.

4. **Install Playwright Chromium:**

   ```bash
   playwright install chromium
   ```

   On Linux: `playwright install --with-deps chromium`.

5. **Run:**

   ```bash
   animeiat-cli

   # Or via Python module:
   python -m src.ui.cli
   ```

   Use `python3` on macOS/Linux if `python` is not found.

#### Docker

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
| `playwright` | Browser automation & cookie extraction |
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

On Linux, if `playwright install chromium` fails:

```bash
playwright install --with-deps chromium
```

### Build System

The project uses **PyInstaller** to create standalone executables.  
No C compiler, no Cython, no manual runtime bundling needed.

#### Quick Start

```bash
# Install build dependencies
pip install pyinstaller

# Build (default: onedir + bundled Chromium)
python build/build.py

# Build as single executable file
python build/build.py --onefile

# Build without Chromium (downloads on first run)
python build/build.py --lite

# Check build environment
python build/build.py --check

# Clean previous build artifacts
python build/build.py --clean
```

#### Build Options

| Flag | Output | Chromium | Use Case |
|------|--------|----------|----------|
| *(default)* | `dist/animeiat-cli/` (folder) | Bundled (~170MB) | Fast launch, stable Playwright |
| `--onefile` | `dist/animeiat-cli.exe` (single file) | Bundled (~900MB) | Easy distribution |
| `--lite` | `dist/animeiat-cli-lite/` (folder) | Downloaded on first run (~30MB) | Small download size |
| `--clean` | — | — | Remove `dist/` and build cache |

The build script:
1. Detects your OS (Windows / macOS / Linux)
2. Installs PyInstaller if missing (`pip install pyinstaller`)
3. Downloads Chromium via Playwright (unless `--lite`)
4. Runs PyInstaller with the spec file (`build/animeiat-cli.spec`)
5. Validates the output by running `--version` on the built executable

#### Cross-Platform

No cross-compilation. Build on each target platform separately:

```bash
# Windows
python build\build.py

# macOS / Linux
python build/build.py
```

Each platform produces a native executable with no external Python dependencies.

#### How It Works

```
build/
├── build.py              # Build script (one command for all platforms)
└── animeiat-cli.spec     # PyInstaller spec file (hidden imports, data files)
```

- `build/animeiat-cli.spec` defines what goes into the executable: all `src/` modules, lxml, Cryptodome, Playwright, Chromium browser.
- `build/build.py` orchestrates the entire process: dependency check, Chromium download, PyInstaller execution, post-build validation.

#### CI/CD

A [GitHub Actions workflow](https://github.com/PanDuroDev/animeiat_cli/actions) builds the project on every push to `main` and every version tag (`v*`):

| Trigger | Build matrix | Artifacts |
|---------|-------------|-----------|
| Push to `main` | Windows, macOS, Linux | onedir + onefile (uploaded as CI artifacts) |
| Tag push `v*` | Windows, macOS, Linux | Attached to Release automatically |

To trigger a full cross-platform build, push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow will build all three platforms and upload the executables to the Release page.

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
├── build/
│   ├── build.py              # Build script (PyInstaller wrapper, one command)
│   └── animeiat-cli.spec     # PyInstaller spec file
├── .github/
│   └── workflows/
│       └── build.yml         # CI/CD: auto-builds Windows, macOS, Linux
├── src/
│   ├── __init__.py
│   ├── chromium.py           # Chromium auto-install helper
│   ├── ui/
│   │   ├── __init__.py       # UI exports
│   │   ├── tui.py            # Interactive TUI (Rich-based, ~2450 lines)
│   │   └── cli.py            # CLI entry point & argument parsing
│   ├── providers/
│   │   ├── __init__.py       # Provider registry
│   │   ├── _cookies.py       # Browser cookie extraction
│   │   ├── _utils.py         # Shared helpers (URL validation, quality classification)
│   │   ├── _scraper.py       # Shared scraping logic (httpx + Playwright)
│   │   ├── witanime.py       # WitAnime provider
│   │   ├── anineko.py        # Anineko provider
│   │   └── anime3rb.py       # Anime3rb provider
│   ├── playback/
│   │   ├── __init__.py       # Playback interface
│   │   ├── discovery.py      # Player detection (VLC, MPV, IINA, etc.)
│   │   ├── launch.py         # Player process launch
│   │   └── progress.py       # Playback progress polling via IPC
│   ├── cache/
│   │   ├── __init__.py       # Cache interface
│   │   └── stream_cache.py   # SQLite-backed stream URL cache
│   ├── config/
│   │   └── __init__.py       # Config read/write, theme, icons
│   └── db/
│       └── __init__.py       # SQLite DB: accounts, favorites, history, downloads
├── requirements.txt          # Python package dependencies
├── pyproject.toml            # Project metadata (PEP 621)
├── setup.py                  # Legacy Cython build (deprecated — use build/build.py)
├── Dockerfile                # Container build
├── CHANGELOG.md              # Release notes
├── CONTRIBUTING.md           # Contribution guidelines
└── LICENSE                   # MIT license
```

### Contributing

Development happens on the `develop` branch. To set up a development environment:

```bash
git checkout develop
pip install -r requirements.txt
playwright install chromium
pytest tests/ -v
```

All tests must pass before submitting a pull request. See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines on branching, code style, and PR workflow.

#### Development Resources

- [Project Board](https://github.com/PanDuroDev/animeiat_cli/projects) — track progress and planned features
- [Issues](https://github.com/PanDuroDev/animeiat_cli/issues) — report bugs or suggest features
- [Discussions](https://github.com/PanDuroDev/animeiat_cli/discussions) — ask questions and share ideas
- [CHANGELOG.md](./CHANGELOG.md) — what changed in each release

---

## License

[MIT](./LICENSE)

---

<p align="center">
  <a href="README.ar.md">العربية</a> &nbsp;|&nbsp; <strong>English</strong>
</p>
