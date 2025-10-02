#!/usr/bin/env python3
"""
VAPOR - Visual Artwork Processing & Organization Resource
Ultimate Steam Grid Artwork Manager

Author: Wesley Ellis
Version: 4.0.0
License: MIT

The fastest, most reliable Steam artwork manager available.
Transform your Steam library with one click!
"""

import sys
import os
import argparse
import asyncio
import logging
from pathlib import Path
from typing import Optional
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vapor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('VAPOR')

# ASCII Art Banner
BANNER = """
██╗   ██╗ █████╗ ██████╗  ██████╗ ██████╗ 
██║   ██║██╔══██╗██╔══██╗██╔═══██╗██╔══██╗
██║   ██║███████║██████╔╝██║   ██║██████╔╝
╚██╗ ██╔╝██╔══██║██╔═══╝ ██║   ██║██╔══██╗
 ╚████╔╝ ██║  ██║██║     ╚██████╔╝██║  ██║
  ╚═══╝  ╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝
        Steam Grid Artwork Manager v4.0
               By Wesley Ellis
"""


class VaporApp:
    """Main VAPOR application class"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize VAPOR application"""
        self.config_path = config_path or Path.home() / '.vapor' / 'config.json'
        self.config = self.load_config()
        self.mode = None
        self.api = None
        
    def load_config(self) -> dict:
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
        return {}
    
    def save_config(self):
        """Save configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def run_gui(self):
        """Run the GUI version of VAPOR"""
        print(BANNER)
        print("Starting VAPOR GUI...")
        
        try:
            # Import GUI components
            from steam_grid_artwork_manager import VaporArtworkManager
            import tkinter as tk
            
            # Create and run GUI
            root = tk.Tk()
            app = VaporArtworkManager(root)
            root.mainloop()
            
        except ImportError as e:
            logger.error(f"GUI dependencies not installed: {e}")
            print("\nError: GUI dependencies missing!")
            print("Install with: pip install -r requirements.txt")
            sys.exit(1)
        except Exception as e:
            logger.error(f"GUI error: {e}")
            print(f"\nError starting GUI: {e}")
            sys.exit(1)
    
    async def run_turbo(self, steam_id: str, api_key: str, level: str = "BALANCED"):
        """Run VAPOR in TURBO mode for maximum performance"""
        print(BANNER)
        print(f"🚀 Starting VAPOR TURBO ({level} mode)...")
        
        try:
            # Import TURBO components
            from vapor_turbo import VaporTurbo
            
            # Get Steam games (mock for demo, would use real Steam API)
            games = await self.get_steam_games(steam_id)
            
            # Create TURBO instance
            turbo = VaporTurbo(
                api_key=api_key,
                steam_id=steam_id,
                turbo_level=level
            )
            
            # Process library
            results = await turbo.turbo_enhance_library(games)
            
            # Save results
            self.save_results(results)
            
            # Cleanup
            await turbo.shutdown()
            
        except ImportError as e:
            logger.error(f"TURBO dependencies not installed: {e}")
            print("\nError: TURBO mode dependencies missing!")
            print("Install with: pip install -r requirements.txt")
            sys.exit(1)
        except Exception as e:
            logger.error(f"TURBO error: {e}")
            print(f"\nError in TURBO mode: {e}")
            sys.exit(1)
    
    async def run_cli(self, args):
        """Run VAPOR in CLI mode"""
        print(BANNER)
        
        # Check for required arguments
        if not args.steam_id or not args.api_key:
            if not self.config.get('steam_id') or not self.config.get('api_key'):
                print("\nError: Steam ID and API key required!")
                print("Use: vapor --steam-id YOUR_ID --api-key YOUR_KEY")
                print("Or run: vapor --setup")
                sys.exit(1)
            else:
                args.steam_id = args.steam_id or self.config['steam_id']
                args.api_key = args.api_key or self.config['api_key']
        
        # Import required components
        try:
            if args.optimized:
                from steamgrid_lib_optimized import OptimizedSteamGridAPI
                api_class = OptimizedSteamGridAPI
                print("✓ Using optimized networking")
            else:
                from steamgrid_lib import SteamGridAPI
                api_class = SteamGridAPI
                print("✓ Using standard networking")
            
            # Create API instance
            self.api = api_class(args.api_key)
            
            # Get games
            games = await self.get_steam_games(args.steam_id)
            print(f"✓ Found {len(games)} games in library")
            
            # Process games
            if args.game:
                # Process specific game
                game = next((g for g in games if str(g['appid']) == args.game), None)
                if game:
                    await self.process_game(game, args)
                else:
                    print(f"Game {args.game} not found in library")
            else:
                # Process all games
                print(f"\nProcessing {len(games)} games...")
                for i, game in enumerate(games, 1):
                    print(f"[{i}/{len(games)}] {game['name']}...")
                    await self.process_game(game, args)
            
            print("\n✅ Processing complete!")
            
        except Exception as e:
            logger.error(f"CLI error: {e}")
            print(f"\nError: {e}")
            sys.exit(1)
    
    async def process_game(self, game: dict, args):
        """Process a single game"""
        try:
            # Search for game on SteamGridDB
            if hasattr(self.api, 'search_game_optimized'):
                sgdb_game = await self.api.search_game_optimized(game['appid'])
            else:
                sgdb_game = self.api.search_game(game['appid'])
            
            if not sgdb_game:
                print(f"  ⚠️  {game['name']}: Not found on SteamGridDB")
                return
            
            # Get artwork
            artwork_types = args.types.split(',') if args.types else ['grid', 'hero', 'logo', 'icon']
            
            for art_type in artwork_types:
                if hasattr(self.api, 'get_artwork_optimized'):
                    artwork = await self.api.get_artwork_optimized(
                        sgdb_game['id'],
                        art_type,
                        limit=args.limit
                    )
                else:
                    artwork = self.api.get_artwork(
                        sgdb_game['id'],
                        art_type,
                        limit=args.limit
                    )
                
                if artwork:
                    # Select best artwork
                    best = max(artwork, key=lambda x: x.get('score', 0))
                    
                    if args.download:
                        # Download artwork
                        save_path = Path(args.output) / f"{game['appid']}_{art_type}.jpg"
                        save_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        if hasattr(self.api, 'download_artwork_optimized'):
                            success = await self.api.download_artwork_optimized(
                                best['url'],
                                save_path
                            )
                        else:
                            # Use standard download
                            import requests
                            response = requests.get(best['url'])
                            if response.status_code == 200:
                                save_path.write_bytes(response.content)
                                success = True
                            else:
                                success = False
                        
                        if success:
                            print(f"  ✓ {art_type}: Downloaded")
                        else:
                            print(f"  ✗ {art_type}: Download failed")
                    else:
                        print(f"  ✓ {art_type}: {best['url']}")
                else:
                    print(f"  ⚠️  {art_type}: No artwork found")
                    
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    async def get_steam_games(self, steam_id: str) -> list:
        """Get user's Steam games"""
        # For demo, return mock games
        # In production, would use Steam Web API
        return [
            {'appid': 220, 'name': 'Half-Life 2', 'playtime_forever': 1234},
            {'appid': 440, 'name': 'Team Fortress 2', 'playtime_forever': 5678},
            {'appid': 730, 'name': 'Counter-Strike: Global Offensive', 'playtime_forever': 10000},
        ]
    
    def save_results(self, results: dict):
        """Save processing results"""
        output_path = Path.home() / '.vapor' / 'results.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Results saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def setup_wizard(self):
        """Interactive setup wizard"""
        print(BANNER)
        print("Welcome to VAPOR Setup Wizard!\n")
        
        # Get Steam ID
        steam_id = input("Enter your Steam ID (or profile URL): ").strip()
        if 'steamcommunity.com' in steam_id:
            # Extract ID from URL
            steam_id = steam_id.split('/')[-1]
        
        # Get API keys
        print("\nYou'll need API keys from:")
        print("1. Steam Web API: https://steamcommunity.com/dev/apikey")
        print("2. SteamGridDB: https://www.steamgriddb.com/profile/preferences/api\n")
        
        steam_api_key = input("Enter Steam Web API key: ").strip()
        sgdb_api_key = input("Enter SteamGridDB API key: ").strip()
        
        # Save configuration
        self.config = {
            'steam_id': steam_id,
            'steam_api_key': steam_api_key,
            'api_key': sgdb_api_key,
            'default_mode': 'gui',
            'turbo_level': 'BALANCED',
            'output_dir': str(Path.home() / 'Pictures' / 'Steam Artwork')
        }
        self.save_config()
        
        print("\n✅ Setup complete! Configuration saved.")
        print("\nYou can now run:")
        print("  vapor          - Launch GUI")
        print("  vapor --turbo  - Run in TURBO mode")
        print("  vapor --cli    - Run in CLI mode")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='VAPOR - Visual Artwork Processing & Organization Resource',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vapor                    Launch GUI (default)
  vapor --turbo           Run in TURBO mode (fastest)
  vapor --cli             Run in CLI mode
  vapor --setup           Run setup wizard
  
  vapor --cli --steam-id 76561197960435530 --api-key YOUR_KEY
  vapor --turbo MAXIMUM   Run TURBO at maximum speed
  
For more information: https://github.com/wesellis/VAPOR
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--gui', action='store_true', help='Run GUI mode (default)')
    mode_group.add_argument('--turbo', nargs='?', const='BALANCED', 
                           choices=['MAXIMUM', 'BALANCED', 'EFFICIENT'],
                           help='Run TURBO mode for maximum performance')
    mode_group.add_argument('--cli', action='store_true', help='Run CLI mode')
    mode_group.add_argument('--setup', action='store_true', help='Run setup wizard')
    
    # Authentication
    parser.add_argument('--steam-id', help='Steam ID or profile URL')
    parser.add_argument('--api-key', help='SteamGridDB API key')
    parser.add_argument('--steam-api-key', help='Steam Web API key')
    
    # Options
    parser.add_argument('--game', help='Process specific game by App ID')
    parser.add_argument('--types', default='grid,hero,logo,icon',
                       help='Artwork types to process (comma-separated)')
    parser.add_argument('--limit', type=int, default=10,
                       help='Maximum artwork per type (default: 10)')
    parser.add_argument('--download', action='store_true',
                       help='Download artwork (CLI mode)')
    parser.add_argument('--output', default='./artwork',
                       help='Output directory for downloads')
    parser.add_argument('--optimized', action='store_true',
                       help='Use optimized networking')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create app instance
    app = VaporApp()
    
    # Handle modes
    if args.setup:
        app.setup_wizard()
    elif args.turbo:
        # Run TURBO mode
        if not args.steam_id or not args.api_key:
            # Try to load from config
            if app.config.get('steam_id') and app.config.get('api_key'):
                args.steam_id = app.config['steam_id']
                args.api_key = app.config['api_key']
            else:
                print("Error: Steam ID and API key required for TURBO mode")
                print("Run: vapor --setup")
                sys.exit(1)
        
        asyncio.run(app.run_turbo(args.steam_id, args.api_key, args.turbo))
    elif args.cli:
        # Run CLI mode
        asyncio.run(app.run_cli(args))
    else:
        # Default to GUI
        app.run_gui()


if __name__ == '__main__':
    main()