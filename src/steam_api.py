#!/usr/bin/env python3
"""
Steam Web API Integration
Author: Wesley Ellis
Version: 1.0.0

Complete Steam Web API integration for VAPOR.
Handles authentication, game library retrieval, and user profiles.
"""

import asyncio
import aiohttp
import requests
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs
import re
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class SteamAPI:
    """
    Complete Steam Web API integration with caching and error handling.
    """
    
    BASE_URL = "https://api.steampowered.com"
    STORE_URL = "https://store.steampowered.com"
    COMMUNITY_URL = "https://steamcommunity.com"
    
    def __init__(self, api_key: str, cache_dir: Optional[Path] = None):
        """
        Initialize Steam API client.
        
        Args:
            api_key: Steam Web API key
            cache_dir: Directory for cache storage
        """
        self.api_key = api_key
        self.cache_dir = cache_dir or Path.home() / '.vapor' / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Session for connection pooling
        self.session = None
        self._init_session()
        
        # Cache settings
        self.cache_ttl = timedelta(hours=24)
        self._cache = {}
        
        logger.info("Steam API client initialized")
    
    def _init_session(self):
        """Initialize requests session with optimized settings"""
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
    
    async def _init_async_session(self) -> aiohttp.ClientSession:
        """Initialize async session for high-performance operations"""
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=10,
            keepalive_timeout=30
        )
        
        return aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    def resolve_steam_id(self, steam_input: str) -> Optional[str]:
        """
        Resolve various Steam ID formats to 64-bit Steam ID.
        
        Args:
            steam_input: Steam ID, custom URL, or profile URL
            
        Returns:
            64-bit Steam ID or None if not found
        """
        # Check if already a valid Steam ID64
        if re.match(r'^\d{17}$', steam_input):
            return steam_input
        
        # Check for Steam ID32
        if re.match(r'^STEAM_[0-5]:[0-1]:\d+$', steam_input):
            return self._convert_steamid32_to_64(steam_input)
        
        # Check for Steam ID3
        if re.match(r'^\[U:1:\d+\]$', steam_input):
            return self._convert_steamid3_to_64(steam_input)
        
        # Extract from URL
        if 'steamcommunity.com' in steam_input:
            # Profile URL
            if '/profiles/' in steam_input:
                match = re.search(r'/profiles/(\d{17})', steam_input)
                if match:
                    return match.group(1)
            
            # Custom URL
            elif '/id/' in steam_input:
                match = re.search(r'/id/([^/]+)', steam_input)
                if match:
                    return self._resolve_vanity_url(match.group(1))
        
        # Assume it's a vanity URL
        return self._resolve_vanity_url(steam_input)
    
    def _convert_steamid32_to_64(self, steamid32: str) -> str:
        """Convert Steam ID32 to Steam ID64"""
        parts = steamid32.replace('STEAM_', '').split(':')
        return str(int(parts[2]) * 2 + 76561197960265728 + int(parts[1]))
    
    def _convert_steamid3_to_64(self, steamid3: str) -> str:
        """Convert Steam ID3 to Steam ID64"""
        account_id = int(re.search(r'\[U:1:(\d+)\]', steamid3).group(1))
        return str(account_id + 76561197960265728)
    
    def _resolve_vanity_url(self, vanity_url: str) -> Optional[str]:
        """Resolve vanity URL to Steam ID64"""
        try:
            url = f"{self.BASE_URL}/ISteamUser/ResolveVanityURL/v1/"
            params = {
                'key': self.api_key,
                'vanityurl': vanity_url
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data['response']['success'] == 1:
                return str(data['response']['steamid'])
            
        except Exception as e:
            logger.error(f"Failed to resolve vanity URL {vanity_url}: {e}")
        
        return None
    
    def get_player_summary(self, steam_id: str) -> Optional[Dict]:
        """
        Get player profile information.
        
        Args:
            steam_id: 64-bit Steam ID
            
        Returns:
            Player profile data or None
        """
        try:
            url = f"{self.BASE_URL}/ISteamUser/GetPlayerSummaries/v2/"
            params = {
                'key': self.api_key,
                'steamids': steam_id
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            players = data.get('response', {}).get('players', [])
            
            if players:
                return players[0]
            
        except Exception as e:
            logger.error(f"Failed to get player summary for {steam_id}: {e}")
        
        return None
    
    def get_owned_games(self, steam_id: str, 
                       include_appinfo: bool = True,
                       include_played_free_games: bool = True) -> List[Dict]:
        """
        Get list of games owned by user.
        
        Args:
            steam_id: 64-bit Steam ID
            include_appinfo: Include game name and icon
            include_played_free_games: Include free games that have been played
            
        Returns:
            List of owned games
        """
        # Check cache first
        cache_key = f"games_{steam_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            url = f"{self.BASE_URL}/IPlayerService/GetOwnedGames/v1/"
            params = {
                'key': self.api_key,
                'steamid': steam_id,
                'include_appinfo': include_appinfo,
                'include_played_free_games': include_played_free_games,
                'format': 'json'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            games = data.get('response', {}).get('games', [])
            
            # Enhance game data
            for game in games:
                game['icon_url'] = self._get_game_icon_url(game.get('appid'), game.get('img_icon_url'))
                game['logo_url'] = self._get_game_logo_url(game.get('appid'), game.get('img_logo_url'))
                game['playtime_hours'] = round(game.get('playtime_forever', 0) / 60, 1)
            
            # Sort by playtime
            games.sort(key=lambda x: x.get('playtime_forever', 0), reverse=True)
            
            # Cache results
            self._set_cached(cache_key, games)
            
            logger.info(f"Retrieved {len(games)} games for {steam_id}")
            return games
            
        except Exception as e:
            logger.error(f"Failed to get owned games for {steam_id}: {e}")
            return []
    
    async def get_owned_games_async(self, steam_id: str) -> List[Dict]:
        """
        Async version of get_owned_games for better performance.
        """
        cache_key = f"games_{steam_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        async with await self._init_async_session() as session:
            try:
                url = f"{self.BASE_URL}/IPlayerService/GetOwnedGames/v1/"
                params = {
                    'key': self.api_key,
                    'steamid': steam_id,
                    'include_appinfo': True,
                    'include_played_free_games': True,
                    'format': 'json'
                }
                
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    games = data.get('response', {}).get('games', [])
                    
                    # Process games
                    for game in games:
                        game['icon_url'] = self._get_game_icon_url(game.get('appid'), game.get('img_icon_url'))
                        game['logo_url'] = self._get_game_logo_url(game.get('appid'), game.get('img_logo_url'))
                        game['playtime_hours'] = round(game.get('playtime_forever', 0) / 60, 1)
                    
                    games.sort(key=lambda x: x.get('playtime_forever', 0), reverse=True)
                    
                    self._set_cached(cache_key, games)
                    return games
                    
            except Exception as e:
                logger.error(f"Async failed to get games for {steam_id}: {e}")
                return []
    
    def get_game_details(self, app_id: int) -> Optional[Dict]:
        """
        Get detailed information about a specific game.
        
        Args:
            app_id: Steam application ID
            
        Returns:
            Game details or None
        """
        cache_key = f"game_detail_{app_id}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            url = f"{self.STORE_URL}/api/appdetails"
            params = {'appids': app_id}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if str(app_id) in data and data[str(app_id)]['success']:
                game_data = data[str(app_id)]['data']
                
                # Extract useful information
                details = {
                    'app_id': app_id,
                    'name': game_data.get('name'),
                    'type': game_data.get('type'),
                    'description': game_data.get('short_description'),
                    'header_image': game_data.get('header_image'),
                    'categories': [c['description'] for c in game_data.get('categories', [])],
                    'genres': [g['description'] for g in game_data.get('genres', [])],
                    'release_date': game_data.get('release_date', {}).get('date'),
                    'developers': game_data.get('developers', []),
                    'publishers': game_data.get('publishers', []),
                    'platforms': game_data.get('platforms', {}),
                    'metacritic': game_data.get('metacritic'),
                    'screenshots': [s['path_full'] for s in game_data.get('screenshots', [])[:5]]
                }
                
                self._set_cached(cache_key, details)
                return details
                
        except Exception as e:
            logger.error(f"Failed to get details for app {app_id}: {e}")
        
        return None
    
    def get_recently_played_games(self, steam_id: str, count: int = 10) -> List[Dict]:
        """
        Get recently played games.
        
        Args:
            steam_id: 64-bit Steam ID
            count: Number of games to return
            
        Returns:
            List of recently played games
        """
        try:
            url = f"{self.BASE_URL}/IPlayerService/GetRecentlyPlayedGames/v1/"
            params = {
                'key': self.api_key,
                'steamid': steam_id,
                'count': count,
                'format': 'json'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            games = data.get('response', {}).get('games', [])
            
            for game in games:
                game['icon_url'] = self._get_game_icon_url(game.get('appid'), game.get('img_icon_url'))
                game['playtime_2weeks_hours'] = round(game.get('playtime_2weeks', 0) / 60, 1)
                game['playtime_forever_hours'] = round(game.get('playtime_forever', 0) / 60, 1)
            
            return games
            
        except Exception as e:
            logger.error(f"Failed to get recent games for {steam_id}: {e}")
            return []
    
    def get_game_achievements(self, steam_id: str, app_id: int) -> Dict:
        """
        Get achievement progress for a game.
        
        Args:
            steam_id: 64-bit Steam ID
            app_id: Steam application ID
            
        Returns:
            Achievement data
        """
        try:
            # Get player achievements
            url = f"{self.BASE_URL}/ISteamUserStats/GetPlayerAchievements/v1/"
            params = {
                'key': self.api_key,
                'steamid': steam_id,
                'appid': app_id,
                'format': 'json'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                player_stats = data.get('playerstats', {})
                
                if player_stats.get('success'):
                    achievements = player_stats.get('achievements', [])
                    total = len(achievements)
                    unlocked = sum(1 for a in achievements if a.get('achieved', 0) == 1)
                    
                    return {
                        'app_id': app_id,
                        'game_name': player_stats.get('gameName'),
                        'total': total,
                        'unlocked': unlocked,
                        'percentage': round((unlocked / total * 100) if total > 0 else 0, 1),
                        'achievements': achievements[:10]  # Return first 10
                    }
            
        except Exception as e:
            logger.error(f"Failed to get achievements for {steam_id}/{app_id}: {e}")
        
        return {'total': 0, 'unlocked': 0, 'percentage': 0}
    
    def _get_game_icon_url(self, app_id: int, icon_hash: str) -> str:
        """Generate game icon URL"""
        if icon_hash:
            return f"https://media.steampowered.com/steamcommunity/public/images/apps/{app_id}/{icon_hash}.jpg"
        return ""
    
    def _get_game_logo_url(self, app_id: int, logo_hash: str) -> str:
        """Generate game logo URL"""
        if logo_hash:
            return f"https://media.steampowered.com/steamcommunity/public/images/apps/{app_id}/{logo_hash}.jpg"
        return ""
    
    def _get_cached(self, key: str) -> Optional[any]:
        """Get cached data if not expired"""
        cache_file = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                cached_time = datetime.fromisoformat(cache_data['timestamp'])
                if datetime.now() - cached_time < self.cache_ttl:
                    logger.debug(f"Cache hit for {key}")
                    return cache_data['data']
                    
            except Exception as e:
                logger.error(f"Cache read error: {e}")
        
        return None
    
    def _set_cached(self, key: str, data: any):
        """Store data in cache"""
        cache_file = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.json"
        
        try:
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
                
            logger.debug(f"Cached {key}")
            
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def clear_cache(self):
        """Clear all cached data"""
        try:
            for cache_file in self.cache_dir.glob('*.json'):
                cache_file.unlink()
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    def validate_api_key(self) -> bool:
        """
        Validate that the API key works.
        
        Returns:
            True if API key is valid
        """
        try:
            # Try a simple API call
            url = f"{self.BASE_URL}/ISteamWebAPIUtil/GetServerInfo/v1/"
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def get_steam_status(self) -> Dict:
        """
        Get Steam service status.
        
        Returns:
            Status information
        """
        try:
            # Check Steam store
            store_response = self.session.get(self.STORE_URL, timeout=5)
            store_up = store_response.status_code == 200
            
            # Check Steam community
            community_response = self.session.get(self.COMMUNITY_URL, timeout=5)
            community_up = community_response.status_code == 200
            
            # Check API
            api_up = self.validate_api_key()
            
            return {
                'store': 'online' if store_up else 'offline',
                'community': 'online' if community_up else 'offline',
                'api': 'online' if api_up else 'offline',
                'all_systems_operational': all([store_up, community_up, api_up])
            }
            
        except Exception as e:
            logger.error(f"Failed to get Steam status: {e}")
            return {
                'store': 'unknown',
                'community': 'unknown',
                'api': 'unknown',
                'all_systems_operational': False
            }


# Example usage and testing
async def test_steam_api():
    """Test Steam API functionality"""
    # You would need a real API key to test
    api_key = "YOUR_STEAM_API_KEY"
    steam_id = "76561197960435530"  # Example Steam ID
    
    api = SteamAPI(api_key)
    
    # Test API key validation
    if not api.validate_api_key():
        print("❌ Invalid API key")
        return
    
    print("✅ API key valid")
    
    # Test Steam status
    status = api.get_steam_status()
    print(f"Steam Status: {status}")
    
    # Test ID resolution
    resolved_id = api.resolve_steam_id("https://steamcommunity.com/id/gabelogannewell")
    print(f"Resolved ID: {resolved_id}")
    
    # Test player summary
    player = api.get_player_summary(steam_id)
    if player:
        print(f"Player: {player.get('personaname')}")
    
    # Test game library
    games = await api.get_owned_games_async(steam_id)
    print(f"Games owned: {len(games)}")
    
    if games:
        # Show top 5 most played
        print("\nTop 5 Most Played Games:")
        for game in games[:5]:
            print(f"  - {game['name']}: {game['playtime_hours']} hours")


if __name__ == "__main__":
    asyncio.run(test_steam_api())