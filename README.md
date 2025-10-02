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

**Completion: ~85%**

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

### Known Limitations & Missing Features

**Minor Issues:**
- ⚠️ **Steam Path Detection**: May not work for non-standard Steam installations
- ⚠️ **Rate Limiting**: Basic API limits but could be more sophisticated
- ⚠️ **Offline Mode**: Requires internet connection for all operations

**Potential Enhancements:**
- ⚠️ **Backup/Restore**: No built-in backup of original artwork before replacement
- ⚠️ **Artwork Preview**: Limited preview capabilities in GUI
- ⚠️ **Batch Operations**: Could be more optimized for very large libraries (1000+ games)
- ⚠️ **Custom Upload**: Cannot upload your own artwork to SteamGridDB
- ⚠️ **Artwork Favorites**: No way to mark favorite artwork for reuse

**Code Quality:**
- ⚠️ **Testing**: No automated test suite
- ⚠️ **Documentation**: Limited inline code comments
- ⚠️ **Error Messages**: Could be more user-friendly

### What Needs Work (Low Priority)

1. **Testing Suite** - Add pytest tests
2. **Backup System** - Auto-backup original artwork
3. **Enhanced Preview** - Better artwork preview in GUI
4. **Favorites System** - Save and reuse favorite artwork
5. **Offline Cache** - Allow offline browsing of previously cached artwork
6. **Performance Optimization** - Further optimize for massive libraries
7. **Better Error Handling** - More informative error messages
8. **Documentation** - More code comments and usage examples

### Current Status

This is a **well-developed and functional tool** for managing Steam library artwork. The core functionality works reliably, with good API integration, caching, and both GUI and CLI modes. Version 4.0.0 indicates active development and iteration.

The tool does what it claims and is production-ready for most users. Missing features are mostly nice-to-haves rather than critical functionality.

### Contributing

If you'd like to add missing features, contributions are welcome. Priority areas:
1. Adding automated tests
2. Implementing backup/restore functionality
3. Improving GUI artwork previews
4. Optimizing performance for large libraries

---

**Author:** Wesley Ellis
**Version:** 4.0.0

