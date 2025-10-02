#!/usr/bin/env python3
"""
VAPOR FAST - Streamlined Steam Grid Artwork Manager
No bullshit, just fast artwork updates.

Author: Wesley Ellis
Version: 5.0 (The Fast One)
"""

import asyncio
import aiohttp
import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set
import time
import sys
import os

# Add minimal dependencies
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL not installed. Image optimization disabled.")

class FastVapor:
    """Streamlined VAPOR - Does one thing well: Updates Steam artwork FAST"""

    def __init__(self, api_key: str = None, steam_id: str = None):
        # Paths - find Steam first
        self.steam_path = self._find_steam()

        # API Configuration
        self.api_key = api_key or os.getenv('STEAMGRID_API_KEY', '')
        self.steam_id = steam_id or self._detect_steam_id()

        # Set grid path
        self.grid_path = self.steam_path / "userdata" / self.steam_id / "config" / "grid"
        self.cache_path = Path.home() / ".vapor" / "cache.json"

        # Simple cache
        self.cache = self._load_cache()

        # API settings
        self.api_base = "https://www.steamgriddb.com/api/v2"
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        # Performance tracking
        self.stats = {"games": 0, "updated": 0, "skipped": 0, "time": 0}

    def _find_steam(self) -> Path:
        """Find Steam installation directory"""
        common_paths = [
            Path.home() / ".steam/steam",  # Linux
            Path.home() / ".local/share/Steam",  # Linux alt
            Path("C:/Program Files (x86)/Steam"),  # Windows
            Path("C:/Program Files/Steam"),  # Windows alt
            Path("/Applications/Steam.app/Contents/MacOS"),  # macOS
        ]

        for path in common_paths:
            if path.exists():
                return path

        # Try to find it from registry on Windows
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Valve\\Steam")
                steam_path = Path(winreg.QueryValueEx(key, "InstallPath")[0])
                if steam_path.exists():
                    return steam_path
            except:
                pass

        raise FileNotFoundError("Steam installation not found")

    def _detect_steam_id(self) -> str:
        """Auto-detect the most recently used Steam ID"""
        userdata = self.steam_path / "userdata"
        if not userdata.exists():
            return ""

        # Find most recently modified profile
        profiles = [d for d in userdata.iterdir() if d.is_dir() and d.name.isdigit()]
        if profiles:
            return max(profiles, key=lambda x: x.stat().st_mtime).name
        return ""

    def _load_cache(self) -> Dict:
        """Load the hash cache"""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_cache(self):
        """Save the hash cache"""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, 'w') as f:
            json.dump(self.cache, f)

    def _get_file_hash(self, filepath: Path) -> str:
        """Get quick hash of a file"""
        if not filepath.exists():
            return ""
        # Just check size and mtime for speed
        stat = filepath.stat()
        return f"{stat.st_size}_{stat.st_mtime}"

    def _get_installed_games(self) -> List[Dict]:
        """Get list of installed Steam games"""
        games = []

        # Parse Steam library folders
        libraryfolders = self.steam_path / "steamapps" / "libraryfolders.vdf"
        if not libraryfolders.exists():
            return games

        # Quick and dirty VDF parser for app IDs
        with open(libraryfolders, 'r', encoding='utf-8') as f:
            content = f.read()

        import re
        # Find all app IDs in the file
        app_ids = re.findall(r'"(\d+)"\s*"\d+"', content)

        for app_id in set(app_ids):  # Remove duplicates
            games.append({"appid": int(app_id), "name": f"Game_{app_id}"})

        return games

    async def _fetch_json(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        """Fetch JSON from API"""
        try:
            async with session.get(url, headers=self.headers, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
        except:
            pass
        return None

    async def _download_image(self, session: aiohttp.ClientSession, url: str, dest: Path) -> bool:
        """Download an image file"""
        try:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    # Download to temp file first
                    temp = dest.with_suffix('.tmp')
                    content = await response.read()
                    temp.write_bytes(content)

                    # Optimize if PIL available
                    if HAS_PIL:
                        try:
                            with Image.open(temp) as img:
                                # Quick optimization
                                if img.width > 920 or img.height > 430:
                                    img.thumbnail((920, 430), Image.Resampling.LANCZOS)
                                img.save(dest, "JPEG", optimize=True, quality=85)
                            temp.unlink()
                        except:
                            # If optimization fails, just use original
                            temp.rename(dest)
                    else:
                        temp.rename(dest)

                    return True
        except:
            pass
        return False

    async def _process_game(self, session: aiohttp.ClientSession, game: Dict) -> bool:
        """Process artwork for a single game"""
        app_id = game['appid']

        # Check cache
        grid_file = self.grid_path / f"{app_id}p.jpg"  # Main grid image
        current_hash = self._get_file_hash(grid_file)
        cached_hash = self.cache.get(str(app_id), {}).get('hash', '')

        if current_hash == cached_hash and grid_file.exists():
            self.stats['skipped'] += 1
            return False

        # Search for game on SteamGridDB
        search_url = f"{self.api_base}/search/autocomplete/{app_id}"
        data = await self._fetch_json(session, search_url)

        if not data or not data.get('data'):
            return False

        game_id = data['data'][0]['id']

        # Get grid artwork
        grids_url = f"{self.api_base}/grids/game/{game_id}"
        grids = await self._fetch_json(session, grids_url)

        if grids and grids.get('data'):
            # Get the best grid image (first one is usually highest rated)
            best_grid = grids['data'][0]

            # Download the image
            success = await self._download_image(session, best_grid['url'], grid_file)

            if success:
                # Update cache
                self.cache[str(app_id)] = {
                    'hash': self._get_file_hash(grid_file),
                    'updated': time.time()
                }
                self.stats['updated'] += 1
                return True

        return False

    async def _process_batch(self, session: aiohttp.ClientSession, games: List[Dict]):
        """Process a batch of games concurrently"""
        tasks = [self._process_game(session, game) for game in games]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def update_library(self, batch_size: int = 10):
        """Main function - Update entire Steam library artwork"""
        start_time = time.time()
        print("🚀 VAPOR FAST - Starting artwork update...")

        # Get installed games
        games = self._get_installed_games()
        if not games:
            print("❌ No Steam games found")
            return

        self.stats['games'] = len(games)
        print(f"📦 Found {len(games)} games")

        # Ensure grid directory exists
        self.grid_path.mkdir(parents=True, exist_ok=True)

        # Process games in batches
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(games), batch_size):
                batch = games[i:i + batch_size]
                await self._process_batch(session, batch)

                # Simple progress
                progress = min(i + batch_size, len(games))
                print(f"⚡ Progress: {progress}/{len(games)} games processed...")

                # Small delay to respect rate limits
                if i + batch_size < len(games):
                    await asyncio.sleep(0.5)

        # Save cache
        self._save_cache()

        # Report results
        self.stats['time'] = time.time() - start_time
        print(f"\n✅ VAPOR FAST - Complete!")
        print(f"📊 Stats:")
        print(f"  • Games processed: {self.stats['games']}")
        print(f"  • Artwork updated: {self.stats['updated']}")
        print(f"  • Skipped (unchanged): {self.stats['skipped']}")
        print(f"  • Time taken: {self.stats['time']:.1f} seconds")
        print(f"  • Speed: {self.stats['games'] / self.stats['time']:.1f} games/second")

    def run_cli(self):
        """Simple CLI mode"""
        print("""
██╗   ██╗ █████╗ ██████╗  ██████╗ ██████╗
██║   ██║██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
██║   ██║███████║██████╔╝██║   ██║██████╔╝  FAST
╚██╗ ██╔╝██╔══██║██╔═══╝ ██║   ██║██╔══██╗
 ╚████╔╝ ██║  ██║██║     ╚██████╔╝██║  ██║
  ╚═══╝  ╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝
        The Streamlined Steam Artwork Manager
""")

        # Check for API key
        if not self.api_key:
            print("⚠️  No SteamGridDB API key found!")
            print("Get one free at: https://www.steamgriddb.com/profile/preferences/api")
            key = input("Enter API key (or press Enter to skip): ").strip()
            if key:
                self.api_key = key
                self.headers = {"Authorization": f"Bearer {self.api_key}"}

        # Run the update
        asyncio.run(self.update_library())

        print("\n💡 Tip: Restart Steam to see the new artwork!")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="VAPOR FAST - Quick Steam artwork updates")
    parser.add_argument("--api-key", help="SteamGridDB API key")
    parser.add_argument("--steam-id", help="Steam user ID")
    parser.add_argument("--batch-size", type=int, default=10, help="Games to process simultaneously")
    args = parser.parse_args()

    try:
        vapor = FastVapor(api_key=args.api_key, steam_id=args.steam_id)

        if args.batch_size:
            asyncio.run(vapor.update_library(batch_size=args.batch_size))
        else:
            vapor.run_cli()

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("Make sure Steam is installed and you've logged in at least once.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()