#!/usr/bin/env python3
"""
VAPOR Database Manager
Author: Wesley Ellis
Version: 1.0.0

SQLite database for persistent storage of game data, artwork, and settings.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from contextlib import contextmanager
import hashlib
import threading

logger = logging.getLogger(__name__)


class VaporDatabase:
    """
    Thread-safe SQLite database manager for VAPOR.
    Handles all persistent storage needs.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to database file
        """
        self.db_path = db_path or Path.home() / '.vapor' / 'vapor.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Initialize database
        self._init_database()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection.execute("PRAGMA journal_mode = WAL")
        return self._local.connection
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions"""
        conn = self.connection
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    steam_id TEXT PRIMARY KEY,
                    username TEXT,
                    profile_url TEXT,
                    avatar_url TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    settings TEXT DEFAULT '{}'
                )
            """)
            
            # Games table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    app_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT,
                    icon_url TEXT,
                    logo_url TEXT,
                    header_image TEXT,
                    categories TEXT,
                    genres TEXT,
                    developers TEXT,
                    publishers TEXT,
                    release_date TEXT,
                    metacritic_score INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User games relationship
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_games (
                    steam_id TEXT,
                    app_id INTEGER,
                    playtime_forever INTEGER DEFAULT 0,
                    playtime_2weeks INTEGER DEFAULT 0,
                    last_played TIMESTAMP,
                    achievements_total INTEGER DEFAULT 0,
                    achievements_unlocked INTEGER DEFAULT 0,
                    installed BOOLEAN DEFAULT FALSE,
                    favorite BOOLEAN DEFAULT FALSE,
                    hidden BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (steam_id, app_id),
                    FOREIGN KEY (steam_id) REFERENCES users(steam_id),
                    FOREIGN KEY (app_id) REFERENCES games(app_id)
                )
            """)
            
            # Artwork table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS artwork (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    thumbnail_url TEXT,
                    author TEXT,
                    score INTEGER DEFAULT 0,
                    width INTEGER,
                    height INTEGER,
                    file_size INTEGER,
                    downloaded BOOLEAN DEFAULT FALSE,
                    local_path TEXT,
                    applied BOOLEAN DEFAULT FALSE,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (app_id) REFERENCES games(app_id),
                    UNIQUE(app_id, type, url)
                )
            """)
            
            # Processing history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    steam_id TEXT,
                    app_id INTEGER,
                    action TEXT,
                    status TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (steam_id) REFERENCES users(steam_id),
                    FOREIGN KEY (app_id) REFERENCES games(app_id)
                )
            """)
            
            # API cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_games_steam_id ON user_games(steam_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_games_app_id ON user_games(app_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_artwork_app_id ON artwork(app_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_artwork_type ON artwork(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processing_history_steam_id ON processing_history(steam_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_cache_expires ON api_cache(expires_at)")
            
            logger.info("Database tables initialized")
    
    # === User Management ===
    
    def upsert_user(self, steam_id: str, username: str = None, 
                   profile_url: str = None, avatar_url: str = None,
                   settings: Dict = None) -> bool:
        """Insert or update user"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (steam_id, username, profile_url, avatar_url, settings)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(steam_id) DO UPDATE SET
                        username = COALESCE(?, username),
                        profile_url = COALESCE(?, profile_url),
                        avatar_url = COALESCE(?, avatar_url),
                        settings = COALESCE(?, settings),
                        last_updated = CURRENT_TIMESTAMP
                """, (steam_id, username, profile_url, avatar_url, 
                     json.dumps(settings or {}),
                     username, profile_url, avatar_url,
                     json.dumps(settings or {})))
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to upsert user {steam_id}: {e}")
            return False
    
    def get_user(self, steam_id: str) -> Optional[Dict]:
        """Get user information"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM users WHERE steam_id = ?", (steam_id,))
            row = cursor.fetchone()
            
            if row:
                user = dict(row)
                user['settings'] = json.loads(user.get('settings', '{}'))
                return user
                
        except Exception as e:
            logger.error(f"Failed to get user {steam_id}: {e}")
        
        return None
    
    # === Game Management ===
    
    def upsert_game(self, app_id: int, name: str, **kwargs) -> bool:
        """Insert or update game"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                # Prepare JSON fields
                categories = json.dumps(kwargs.get('categories', []))
                genres = json.dumps(kwargs.get('genres', []))
                developers = json.dumps(kwargs.get('developers', []))
                publishers = json.dumps(kwargs.get('publishers', []))
                
                cursor.execute("""
                    INSERT INTO games (
                        app_id, name, type, icon_url, logo_url, header_image,
                        categories, genres, developers, publishers,
                        release_date, metacritic_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(app_id) DO UPDATE SET
                        name = ?,
                        type = COALESCE(?, type),
                        icon_url = COALESCE(?, icon_url),
                        logo_url = COALESCE(?, logo_url),
                        header_image = COALESCE(?, header_image),
                        categories = COALESCE(?, categories),
                        genres = COALESCE(?, genres),
                        developers = COALESCE(?, developers),
                        publishers = COALESCE(?, publishers),
                        release_date = COALESCE(?, release_date),
                        metacritic_score = COALESCE(?, metacritic_score),
                        last_updated = CURRENT_TIMESTAMP
                """, (
                    app_id, name, kwargs.get('type'), kwargs.get('icon_url'),
                    kwargs.get('logo_url'), kwargs.get('header_image'),
                    categories, genres, developers, publishers,
                    kwargs.get('release_date'), kwargs.get('metacritic_score'),
                    name, kwargs.get('type'), kwargs.get('icon_url'),
                    kwargs.get('logo_url'), kwargs.get('header_image'),
                    categories, genres, developers, publishers,
                    kwargs.get('release_date'), kwargs.get('metacritic_score')
                ))
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to upsert game {app_id}: {e}")
            return False
    
    def get_game(self, app_id: int) -> Optional[Dict]:
        """Get game information"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM games WHERE app_id = ?", (app_id,))
            row = cursor.fetchone()
            
            if row:
                game = dict(row)
                # Parse JSON fields
                game['categories'] = json.loads(game.get('categories', '[]'))
                game['genres'] = json.loads(game.get('genres', '[]'))
                game['developers'] = json.loads(game.get('developers', '[]'))
                game['publishers'] = json.loads(game.get('publishers', '[]'))
                return game
                
        except Exception as e:
            logger.error(f"Failed to get game {app_id}: {e}")
        
        return None
    
    def link_user_game(self, steam_id: str, app_id: int,
                      playtime_forever: int = 0, playtime_2weeks: int = 0,
                      **kwargs) -> bool:
        """Link game to user library"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_games (
                        steam_id, app_id, playtime_forever, playtime_2weeks,
                        last_played, achievements_total, achievements_unlocked,
                        installed, favorite, hidden
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(steam_id, app_id) DO UPDATE SET
                        playtime_forever = ?,
                        playtime_2weeks = ?,
                        last_played = COALESCE(?, last_played),
                        achievements_total = COALESCE(?, achievements_total),
                        achievements_unlocked = COALESCE(?, achievements_unlocked),
                        installed = COALESCE(?, installed),
                        favorite = COALESCE(?, favorite),
                        hidden = COALESCE(?, hidden)
                """, (
                    steam_id, app_id, playtime_forever, playtime_2weeks,
                    kwargs.get('last_played'), kwargs.get('achievements_total'),
                    kwargs.get('achievements_unlocked'), kwargs.get('installed', False),
                    kwargs.get('favorite', False), kwargs.get('hidden', False),
                    playtime_forever, playtime_2weeks,
                    kwargs.get('last_played'), kwargs.get('achievements_total'),
                    kwargs.get('achievements_unlocked'), kwargs.get('installed'),
                    kwargs.get('favorite'), kwargs.get('hidden')
                ))
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to link game {app_id} to user {steam_id}: {e}")
            return False
    
    def get_user_games(self, steam_id: str, 
                      include_hidden: bool = False,
                      only_installed: bool = False,
                      only_favorites: bool = False) -> List[Dict]:
        """Get user's game library"""
        try:
            query = """
                SELECT g.*, ug.*
                FROM user_games ug
                JOIN games g ON ug.app_id = g.app_id
                WHERE ug.steam_id = ?
            """
            
            conditions = []
            if not include_hidden:
                conditions.append("ug.hidden = 0")
            if only_installed:
                conditions.append("ug.installed = 1")
            if only_favorites:
                conditions.append("ug.favorite = 1")
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            query += " ORDER BY ug.playtime_forever DESC"
            
            cursor = self.connection.cursor()
            cursor.execute(query, (steam_id,))
            
            games = []
            for row in cursor.fetchall():
                game = dict(row)
                # Parse JSON fields
                game['categories'] = json.loads(game.get('categories', '[]'))
                game['genres'] = json.loads(game.get('genres', '[]'))
                game['developers'] = json.loads(game.get('developers', '[]'))
                game['publishers'] = json.loads(game.get('publishers', '[]'))
                games.append(game)
            
            return games
            
        except Exception as e:
            logger.error(f"Failed to get games for user {steam_id}: {e}")
            return []
    
    # === Artwork Management ===
    
    def add_artwork(self, app_id: int, art_type: str, url: str, **kwargs) -> int:
        """Add artwork to database"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO artwork (
                        app_id, type, url, thumbnail_url, author, score,
                        width, height, file_size, downloaded, local_path, applied
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    app_id, art_type, url,
                    kwargs.get('thumbnail_url'), kwargs.get('author'),
                    kwargs.get('score', 0), kwargs.get('width'),
                    kwargs.get('height'), kwargs.get('file_size'),
                    kwargs.get('downloaded', False), kwargs.get('local_path'),
                    kwargs.get('applied', False)
                ))
                
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Failed to add artwork: {e}")
            return 0
    
    def get_artwork(self, app_id: int, art_type: str = None,
                   only_downloaded: bool = False) -> List[Dict]:
        """Get artwork for a game"""
        try:
            query = "SELECT * FROM artwork WHERE app_id = ?"
            params = [app_id]
            
            if art_type:
                query += " AND type = ?"
                params.append(art_type)
            
            if only_downloaded:
                query += " AND downloaded = 1"
            
            query += " ORDER BY score DESC, date_added DESC"
            
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get artwork for {app_id}: {e}")
            return []
    
    def mark_artwork_downloaded(self, artwork_id: int, local_path: str) -> bool:
        """Mark artwork as downloaded"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE artwork 
                    SET downloaded = 1, local_path = ?
                    WHERE id = ?
                """, (local_path, artwork_id))
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to mark artwork {artwork_id} as downloaded: {e}")
            return False
    
    # === Cache Management ===
    
    def get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT value FROM api_cache
                WHERE key = ? AND datetime(expires_at) > datetime('now')
            """, (key,))
            
            row = cursor.fetchone()
            if row:
                return json.loads(row['value'])
                
        except Exception as e:
            logger.error(f"Failed to get cache {key}: {e}")
        
        return None
    
    def set_cached(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Set cached value with TTL"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                # Use UTC time to match SQLite's datetime('now') which is UTC
                expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute("""
                    INSERT INTO api_cache (key, value, expires_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = ?,
                        expires_at = ?,
                        created_at = CURRENT_TIMESTAMP
                """, (key, json.dumps(value), expires_at,
                     json.dumps(value), expires_at))
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to set cache {key}: {e}")
            return False
    
    def clean_expired_cache(self):
        """Remove expired cache entries"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM api_cache WHERE expires_at < datetime('now')")
                deleted = cursor.rowcount
                
                if deleted > 0:
                    logger.info(f"Cleaned {deleted} expired cache entries")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Failed to clean cache: {e}")
            return 0
    
    # === Settings Management ===
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting value"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                return json.loads(row['value'])
                
        except Exception as e:
            logger.error(f"Failed to get setting {key}: {e}")
        
        return default
    
    def set_setting(self, key: str, value: Any) -> bool:
        """Set setting value"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO settings (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = ?,
                        updated_at = CURRENT_TIMESTAMP
                """, (key, json.dumps(value), json.dumps(value)))
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False
    
    # === History & Analytics ===
    
    def add_processing_history(self, steam_id: str, app_id: int,
                              action: str, status: str, details: str = None):
        """Add processing history entry"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO processing_history 
                    (steam_id, app_id, action, status, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (steam_id, app_id, action, status, details))
                
                return cursor.lastrowid > 0
                
        except Exception as e:
            logger.error(f"Failed to add history: {e}")
            return False
    
    def get_processing_stats(self, steam_id: str = None) -> Dict:
        """Get processing statistics"""
        try:
            cursor = self.connection.cursor()
            
            # Total games processed
            if steam_id:
                cursor.execute("""
                    SELECT COUNT(DISTINCT app_id) as total
                    FROM processing_history
                    WHERE steam_id = ? AND status = 'success'
                """, (steam_id,))
            else:
                cursor.execute("""
                    SELECT COUNT(DISTINCT app_id) as total
                    FROM processing_history
                    WHERE status = 'success'
                """)
            
            total_processed = cursor.fetchone()['total']
            
            # Total artwork downloaded
            cursor.execute("SELECT COUNT(*) as total FROM artwork WHERE downloaded = 1")
            total_artwork = cursor.fetchone()['total']
            
            # Success rate
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as success,
                    COUNT(*) as total
                FROM processing_history
            """)
            
            rates = cursor.fetchone()
            success_rate = (rates['success'] / rates['total'] * 100) if rates['total'] > 0 else 0
            
            return {
                'games_processed': total_processed,
                'artwork_downloaded': total_artwork,
                'success_rate': round(success_rate, 1),
                'total_operations': rates['total']
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
            logger.info("Database connection closed")


# Test database functionality
def test_database():
    """Test database operations"""
    db = VaporDatabase(Path("test_vapor.db"))
    
    try:
        # Test user operations
        print("Testing user operations...")
        assert db.upsert_user("123456789", "TestUser", settings={'theme': 'dark'})
        user = db.get_user("123456789")
        assert user['username'] == "TestUser"
        print("✅ User operations working")
        
        # Test game operations
        print("Testing game operations...")
        assert db.upsert_game(220, "Half-Life 2", type="game", 
                            genres=["Action", "FPS"])
        game = db.get_game(220)
        assert game['name'] == "Half-Life 2"
        print("✅ Game operations working")
        
        # Test user-game link
        print("Testing user-game linking...")
        assert db.link_user_game("123456789", 220, playtime_forever=1234)
        games = db.get_user_games("123456789")
        assert len(games) > 0
        print("✅ User-game linking working")
        
        # Test artwork
        print("Testing artwork operations...")
        art_id = db.add_artwork(220, "grid", "http://example.com/art.jpg", score=100)
        assert art_id > 0
        artwork = db.get_artwork(220)
        assert len(artwork) > 0
        print("✅ Artwork operations working")
        
        # Test cache
        print("Testing cache operations...")
        db.set_cached("test_key", {"data": "value"}, ttl_seconds=60)
        cached = db.get_cached("test_key")
        assert cached["data"] == "value"
        print("✅ Cache operations working")
        
        # Test settings
        print("Testing settings...")
        db.set_setting("app_theme", "dark")
        theme = db.get_setting("app_theme")
        assert theme == "dark"
        print("✅ Settings working")
        
        # Get stats
        stats = db.get_processing_stats()
        print(f"\n📊 Database Stats: {stats}")
        
        print("\n✅ All database tests passed!")
        
    finally:
        db.close()
        # Clean up test database
        Path("test_vapor.db").unlink(missing_ok=True)


if __name__ == "__main__":
    test_database()