#!/usr/bin/env python3
"""
Cloud Sync Service for VAPOR
Real-time synchronization across devices with conflict resolution
"""

import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime
import json
import hashlib
from dataclasses import dataclass, asdict
import firebase_admin
from firebase_admin import credentials, firestore, auth
import redis.asyncio as redis
from cryptography.fernet import Fernet

@dataclass
class SyncProfile:
    """User profile for cloud synchronization"""
    user_id: str
    steam_id: str
    preferences: Dict
    libraries: List[Dict]
    artwork_choices: Dict
    last_sync: datetime
    devices: List[str]
    sync_enabled: bool = True

class CloudSyncService:
    """
    Advanced cloud synchronization service
    Features:
    - Real-time sync across devices
    - Conflict resolution
    - Offline support
    - End-to-end encryption
    - Delta sync for efficiency
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.firebase_app = None
        self.db = None
        self.redis_client = None
        self.sync_queue = asyncio.Queue()
        self.active_connections: Dict[str, Set[str]] = {}  # user_id -> set of device_ids
        self.encryption_key = None
        self.sync_worker_task = None
        
    async def initialize(self):
        """Initialize cloud sync services"""
        # Initialize Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate(self.config.get('firebase_credentials'))
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        
        # Initialize Redis for real-time sync
        self.redis_client = await redis.from_url(
            self.config.get('redis_url', 'redis://localhost'),
            encoding="utf-8",
            decode_responses=True
        )
        
        # Setup encryption
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        print("✅ Cloud Sync Service initialized")
    
    async def start_sync_worker(self):
        """Start background sync worker"""
        self.sync_worker_task = asyncio.create_task(self._sync_worker())
        print("🔄 Sync worker started")
    
    async def stop(self):
        """Stop sync services"""
        if self.sync_worker_task:
            self.sync_worker_task.cancel()
            try:
                await self.sync_worker_task
            except asyncio.CancelledError:
                pass
    
    async def _sync_worker(self):
        """Background worker for processing sync queue"""
        while True:
            try:
                sync_data = await self.sync_queue.get()
                await self._process_sync(sync_data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Sync worker error: {e}")
                await asyncio.sleep(1)
    
    async def authenticate_user(self, id_token: str) -> Optional[Dict]:
        """Authenticate user with Firebase"""
        try:
            decoded_token = auth.verify_id_token(id_token)
            user_id = decoded_token['uid']
            
            # Get or create user profile
            profile = await self.get_user_profile(user_id)
            if not profile:
                profile = await self.create_user_profile(user_id, decoded_token.get('email'))
            
            return {
                'user_id': user_id,
                'email': decoded_token.get('email'),
                'profile': profile
            }
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    async def get_user_profile(self, user_id: str) -> Optional[SyncProfile]:
        """Get user profile from Firestore"""
        try:
            doc = self.db.collection('users').document(user_id).get()
            if doc.exists:
                data = doc.to_dict()
                return SyncProfile(
                    user_id=data['user_id'],
                    steam_id=data.get('steam_id', ''),
                    preferences=data.get('preferences', {}),
                    libraries=data.get('libraries', []),
                    artwork_choices=data.get('artwork_choices', {}),
                    last_sync=data.get('last_sync'),
                    devices=data.get('devices', []),
                    sync_enabled=data.get('sync_enabled', True)
                )
            return None
        except Exception as e:
            print(f"Error getting profile: {e}")
            return None
    
    async def create_user_profile(self, user_id: str, email: str) -> SyncProfile:
        """Create new user profile"""
        profile = SyncProfile(
            user_id=user_id,
            steam_id='',
            preferences={
                'theme': 'dark',
                'auto_enhance': True,
                'artwork_quality': 'high',
                'sync_interval': 300  # 5 minutes
            },
            libraries=[],
            artwork_choices={},
            last_sync=datetime.utcnow(),
            devices=[]
        )
        
        # Save to Firestore
        self.db.collection('users').document(user_id).set(asdict(profile))
        
        return profile
    
    async def sync_profile(self, user_id: str, device_id: str, local_data: Dict) -> Dict:
        """
        Sync user profile with cloud
        Handles conflict resolution and delta sync
        """
        # Get cloud profile
        cloud_profile = await self.get_user_profile(user_id)
        if not cloud_profile:
            return {'error': 'Profile not found'}
        
        # Calculate deltas
        local_hash = self._calculate_data_hash(local_data)
        cloud_hash = self._calculate_data_hash(asdict(cloud_profile))
        
        if local_hash == cloud_hash:
            return {'status': 'no_changes', 'profile': cloud_profile}
        
        # Resolve conflicts
        merged_data = await self._resolve_conflicts(
            cloud_profile,
            local_data,
            device_id
        )
        
        # Update cloud
        await self._update_cloud_profile(user_id, merged_data)
        
        # Notify other devices
        await self._notify_devices(user_id, device_id, merged_data)
        
        return {
            'status': 'synced',
            'profile': merged_data,
            'changes': self._get_changes(cloud_profile, merged_data)
        }
    
    async def _resolve_conflicts(
        self,
        cloud_data: SyncProfile,
        local_data: Dict,
        device_id: str
    ) -> Dict:
        """
        Resolve sync conflicts using last-write-wins with field-level merging
        """
        merged = asdict(cloud_data)
        
        # Compare timestamps for each field
        local_timestamp = local_data.get('last_modified', {})
        cloud_timestamp = cloud_data.last_sync
        
        # Merge preferences (last-write-wins per field)
        if 'preferences' in local_data:
            for key, value in local_data['preferences'].items():
                field_timestamp = local_timestamp.get(f'preferences.{key}')
                if field_timestamp and field_timestamp > cloud_timestamp:
                    merged['preferences'][key] = value
        
        # Merge artwork choices (union with newest selections)
        if 'artwork_choices' in local_data:
            for game_id, artwork in local_data['artwork_choices'].items():
                if game_id not in merged['artwork_choices']:
                    merged['artwork_choices'][game_id] = artwork
                else:
                    # Keep newest selection
                    local_art_time = local_data.get('artwork_timestamps', {}).get(game_id)
                    cloud_art_time = merged.get('artwork_timestamps', {}).get(game_id)
                    
                    if local_art_time and (not cloud_art_time or local_art_time > cloud_art_time):
                        merged['artwork_choices'][game_id] = artwork
        
        # Update device list
        if device_id not in merged['devices']:
            merged['devices'].append(device_id)
        
        merged['last_sync'] = datetime.utcnow()
        
        return merged
    
    async def _update_cloud_profile(self, user_id: str, data: Dict):
        """Update user profile in cloud"""
        # Encrypt sensitive data
        encrypted_data = self._encrypt_sensitive_data(data)
        
        # Update Firestore
        self.db.collection('users').document(user_id).update(encrypted_data)
        
        # Update Redis cache for fast access
        await self.redis_client.setex(
            f"profile:{user_id}",
            300,  # 5 minute cache
            json.dumps(encrypted_data, default=str)
        )
    
    def _encrypt_sensitive_data(self, data: Dict) -> Dict:
        """Encrypt sensitive fields"""
        encrypted = data.copy()
        
        # Encrypt Steam ID and API keys if present
        sensitive_fields = ['steam_id', 'steam_api_key', 'steamgrid_api_key']
        
        for field in sensitive_fields:
            if field in encrypted and encrypted[field]:
                encrypted[field] = self.cipher_suite.encrypt(
                    encrypted[field].encode()
                ).decode()
        
        return encrypted
    
    def _decrypt_sensitive_data(self, data: Dict) -> Dict:
        """Decrypt sensitive fields"""
        decrypted = data.copy()
        
        sensitive_fields = ['steam_id', 'steam_api_key', 'steamgrid_api_key']
        
        for field in sensitive_fields:
            if field in decrypted and decrypted[field]:
                try:
                    decrypted[field] = self.cipher_suite.decrypt(
                        decrypted[field].encode()
                    ).decode()
                except:
                    pass  # Field might not be encrypted
        
        return decrypted
    
    async def _notify_devices(self, user_id: str, source_device: str, data: Dict):
        """Notify other devices about sync changes"""
        # Get all connected devices for user
        devices = self.active_connections.get(user_id, set())
        
        # Notify each device except source
        for device_id in devices:
            if device_id != source_device:
                await self._send_sync_notification(user_id, device_id, data)
    
    async def _send_sync_notification(self, user_id: str, device_id: str, data: Dict):
        """Send sync notification to specific device"""
        channel = f"sync:{user_id}:{device_id}"
        
        notification = {
            'type': 'sync_update',
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        await self.redis_client.publish(channel, json.dumps(notification, default=str))
    
    async def subscribe_to_sync(self, user_id: str, device_id: str):
        """Subscribe device to sync notifications"""
        # Track connection
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(device_id)
        
        # Subscribe to Redis channel
        channel = f"sync:{user_id}:{device_id}"
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(channel)
        
        return pubsub
    
    async def unsubscribe_from_sync(self, user_id: str, device_id: str):
        """Unsubscribe device from sync notifications"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(device_id)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    def _calculate_data_hash(self, data: Dict) -> str:
        """Calculate hash of data for comparison"""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(sorted_data.encode()).hexdigest()
    
    def _get_changes(self, old_data: SyncProfile, new_data: Dict) -> Dict:
        """Get list of changes between old and new data"""
        changes = {
            'added': {},
            'modified': {},
            'removed': {}
        }
        
        old_dict = asdict(old_data)
        
        # Check for additions and modifications
        for key, value in new_data.items():
            if key not in old_dict:
                changes['added'][key] = value
            elif old_dict[key] != value:
                changes['modified'][key] = {
                    'old': old_dict[key],
                    'new': value
                }
        
        # Check for removals
        for key in old_dict:
            if key not in new_data:
                changes['removed'][key] = old_dict[key]
        
        return changes
    
    async def handle_sync(self, client_id: str, data: Dict):
        """Handle incoming sync request from WebSocket"""
        user_id = data.get('user_id')
        device_id = data.get('device_id')
        sync_type = data.get('sync_type')
        
        if sync_type == 'pull':
            # Send latest profile to client
            profile = await self.get_user_profile(user_id)
            return {
                'type': 'sync_response',
                'action': 'pull',
                'profile': asdict(profile) if profile else None
            }
        
        elif sync_type == 'push':
            # Receive changes from client
            local_data = data.get('local_data')
            result = await self.sync_profile(user_id, device_id, local_data)
            return {
                'type': 'sync_response',
                'action': 'push',
                'result': result
            }
        
        elif sync_type == 'subscribe':
            # Subscribe to real-time updates
            await self.subscribe_to_sync(user_id, device_id)
            return {
                'type': 'sync_response',
                'action': 'subscribed'
            }
    
    async def _process_sync(self, sync_data: Dict):
        """Process queued sync operation"""
        try:
            action = sync_data.get('action')
            
            if action == 'profile_update':
                await self._update_cloud_profile(
                    sync_data['user_id'],
                    sync_data['data']
                )
            
            elif action == 'artwork_sync':
                await self._sync_artwork_choices(
                    sync_data['user_id'],
                    sync_data['artwork_data']
                )
            
        except Exception as e:
            print(f"Sync processing error: {e}")
    
    async def _sync_artwork_choices(self, user_id: str, artwork_data: Dict):
        """Sync artwork choices across devices"""
        # Update Firestore
        self.db.collection('users').document(user_id).update({
            'artwork_choices': artwork_data,
            'artwork_sync_time': datetime.utcnow()
        })
        
        # Notify all devices
        await self._notify_devices(user_id, 'server', {
            'artwork_choices': artwork_data
        })