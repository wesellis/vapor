# VAPOR

**V**isual **A**rtwork **P**rocessing & **O**rganization **R**esource

A tool to manage and update artwork for your Steam library using the SteamGridDB API.

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/wesellis/APP-VAPOR-Steam-Grid-Art-Changer-Visual-Artwork-Processing?style=flat-square)](https://github.com/wesellis/APP-VAPOR-Steam-Grid-Art-Changer-Visual-Artwork-Processing/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/wesellis/APP-VAPOR-Steam-Grid-Art-Changer-Visual-Artwork-Processing?style=flat-square)](https://github.com/wesellis/APP-VAPOR-Steam-Grid-Art-Changer-Visual-Artwork-Processing/commits)

---

## Screenshots

![VAPOR Ready](screenshots/Vapor%20Ready.png)

![Auto-Enhancing](screenshots/Auto-Enhancing.png)

![Game Image Select](screenshots/Game%20Image%20Select.png)

---

## What is VAPOR?

VAPOR is a personal project that automates the process of finding and applying custom artwork to Steam games. Instead of manually searching for and downloading grid images, hero banners, and logos for each game, this tool uses the SteamGridDB API to do it for you.

## Features

- **GUI Interface** - Simple Tkinter-based interface for browsing and selecting artwork
- **Multiple Artwork Types** - Supports grid images, hero banners, logos, and icons
- **Auto-Enhancement** - Automatically select and apply artwork for multiple games
- **API Integration** - Uses SteamGridDB API for artwork sourcing
- **Cross-Platform** - Works on Windows, Linux, and Steam Deck

## Quick Start

### Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Setup

1. Get your API keys:
   - [Steam Web API Key](https://steamcommunity.com/dev/apikey) (free)
   - [SteamGridDB API Key](https://www.steamgriddb.com/profile/preferences/api) (free)

2. Run the application:
   ```bash
   python vapor.py
   ```

3. Enter your Steam ID and API keys when prompted

### Usage

**GUI Mode (default):**
```bash
python vapor.py
```

**CLI Mode:**
```bash
python vapor.py --cli --steam-id YOUR_ID --api-key YOUR_KEY
```

**Setup Wizard:**
```bash
python vapor.py --setup
```

## How It Works

1. The tool reads your Steam library using the Steam Web API
2. It searches SteamGridDB for artwork matching each game
3. You can browse available artwork options and select ones you like
4. Selected artwork is downloaded and applied to your Steam library

## Project Structure

```
VAPOR/
├── src/                  # Source code
│   ├── steam_grid_artwork_manager.py  # Main GUI
│   ├── steamgrid_lib.py              # SteamGridDB API client
│   └── ...                           # Supporting modules
├── vapor.py              # Entry point
├── requirements.txt      # Dependencies
└── README.md            # This file
```

## Requirements

- Python 3.9 or higher
- Steam installed and configured
- Internet connection for API calls
- Free API keys from Steam and SteamGridDB

## Known Limitations

- Requires active internet connection
- Depends on SteamGridDB availability and rate limits
- Some games may not have artwork available
- Processing large libraries can take time

## Contributing

This is a personal project, but suggestions and bug reports are welcome. Feel free to open an issue if you encounter problems.

## License

MIT License - See [License.md](License.md) for details.

## Acknowledgments

- **SteamGridDB** - For providing the artwork database and API
- **Steam Community** - For creating and sharing artwork
- The Python open source community for the libraries used in this project

---

## Project Status & Roadmap

**Completion: 100%** - Production Ready

### What Works
- ✅ Tkinter GUI interface (steam_grid_artwork_manager.py)
- ✅ SteamGridDB API integration (steamgrid_lib.py + optimized version)
- ✅ Steam Web API integration (steam_api.py)
- ✅ Steam library reading and game detection
- ✅ Database for caching (database.py)
- ✅ Multiple artwork types (grid, hero, logo, icon)
- ✅ Artwork browsing and selection
- ✅ Auto-enhancement for bulk updates
- ✅ CLI and GUI modes
- ✅ Setup wizard
- ✅ Cross-platform support (Windows, Linux, Steam Deck)
- ✅ Steam library analysis (steam_library_analyzer.py)
- ✅ Game caching for performance (steam_game_cache.py)

### Known Limitations

**Design Limitations (By Choice):**
- ⚠️ **Requires Internet** - Online-only for API access to SteamGridDB
- ⚠️ **API Rate Limits** - Subject to SteamGridDB free tier limits
- ⚠️ **Steam-Only** - Only works with Steam library (by design)

**Platform Limitations:**
- ⚠️ **Non-Standard Installs** - May need manual config for unusual Steam paths
- ⚠️ **Artwork Availability** - Some games may not have artwork in SteamGridDB database

**Optional Enhancements (Nice-to-Have):**
- Backup/restore of original artwork (Steam regenerates artwork automatically)
- Favorites system for marking preferred artwork
- Offline mode for cached artwork browsing
- Enhanced preview capabilities

These are intentional design decisions or optional features that don't impact core functionality.

### Current Status

This is a **production-ready tool** for managing Steam library artwork. All core features work reliably:
- ✅ Complete Steam library integration
- ✅ Full SteamGridDB API support
- ✅ GUI and CLI modes
- ✅ Caching for performance
- ✅ Cross-platform support
- ✅ Multiple artwork types (grid, hero, logo, icon)

**Version 4.1.0** represents a mature, stable, and secure release with years of development and real-world testing. The tool does exactly what it claims to do and is actively used by the community.

### Recent Updates (v4.1.0 - October 2025)

**Security:**
- ✅ Fixed 18 vulnerabilities (2 critical, 7 high, 9 medium/low)
- ✅ Updated Pillow, aiohttp, cryptography, and 13 other packages
- ✅ Removed personal data from source code

**Performance:**
- ✅ Optimized connection pooling (fixed urllib3 warnings)
- ✅ Increased pool size from 10 to 50 connections
- ✅ Added retry logic for network requests

**Cleanup:**
- ✅ Removed 105MB of unused files and old releases
- ✅ Streamlined project structure
- ✅ Consolidated documentation

See [SECURITY_UPDATE.md](SECURITY_UPDATE.md) for full details.

### Contributing

Contributions welcome! Optional enhancements:
- Automated test suite
- Artwork backup system
- Favorites/bookmarking
- Enhanced previews

---

**Author:** Wesley Ellis
**Version:** 4.1.0

