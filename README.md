# VAPOR

**V**isual **A**rtwork **P**rocessing & **O**rganization **R**esource

A simple tool to help manage and update artwork for your Steam library using the SteamGridDB API.

![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

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

**Author:** Wesley Ellis
**Version:** 4.0.0

