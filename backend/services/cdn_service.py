#!/usr/bin/env python3
"""
CDN Service for VAPOR - Global artwork delivery network
Handles image optimization, caching, and distribution
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import hashlib
import time
from PIL import Image
import io
import redis.asyncio as redis
from fastapi import UploadFile
import boto3
from botocore.exceptions import ClientError

class CDNService:
    """
    Advanced CDN management for artwork delivery
    Features:
    - Multi-region distribution
    - WebP/AVIF conversion
    - Progressive loading
    - Smart caching
    - Bandwidth optimization
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.s3_client = None
        self.cloudflare_api = config.get('cloudflare_api_key')
        
        # CDN endpoints by region
        self.cdn_endpoints = {
            'us-east': 'https://cdn-us-east.vaporapp.com',
            'us-west': 'https://cdn-us-west.vaporapp.com',
            'eu-west': 'https://cdn-eu-west.vaporapp.com',
            'asia-pacific': 'https://cdn-asia.vaporapp.com'
        }
        
        # Image optimization settings
        self.image_sizes = {
            'thumbnail': (150, 225),
            'small': (300, 450),
            'medium': (600, 900),
            'large': (1200, 1800),
            'original': None
        }
        
        # Cache configuration
        self.cache_ttl = {
            'hot': 3600,      # 1 hour for popular content
            'warm': 86400,    # 1 day for regular content
            'cold': 604800    # 1 week for rarely accessed
        }
        
    async def initialize(self):
        """Initialize CDN connections"""
        # Redis for caching
        self.redis_client = await redis.from_url(
            self.config.get('redis_url', 'redis://localhost'),
            encoding="utf-8",
            decode_responses=True
        )
        
        # S3 for storage
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.config.get('aws_access_key'),
            aws_secret_access_key=self.config.get('aws_secret_key'),
            region_name=self.config.get('aws_region', 'us-east-1')
        )
        
        print("✅ CDN Service initialized")
    
    async def upload_artwork(
        self,
        game_id: int,
        artwork_type: str,
        image_data: bytes,
        metadata: Dict
    ) -> Dict:
        """
        Upload artwork to CDN with optimization
        Returns URLs for different sizes and formats
        """
        # Generate unique ID
        artwork_id = self._generate_artwork_id(game_id, artwork_type, image_data)
        
        # Process image into multiple formats
        processed_images = await self._process_image_variants(image_data)
        
        # Upload to S3 with CloudFront
        urls = {}
        for size, img_data in processed_images.items():
            key = f"artwork/{game_id}/{artwork_type}/{artwork_id}/{size}"
            
            # Upload WebP version
            webp_url = await self._upload_to_s3(
                key + ".webp",
                img_data['webp'],
                'image/webp'
            )
            
            # Upload JPEG fallback
            jpeg_url = await self._upload_to_s3(
                key + ".jpg",
                img_data['jpeg'],
                'image/jpeg'
            )
            
            urls[size] = {
                'webp': webp_url,
                'jpeg': jpeg_url,
                'dimensions': img_data['dimensions']
            }
        
        # Store metadata in Redis
        await self._cache_artwork_metadata(artwork_id, {
            'game_id': game_id,
            'artwork_type': artwork_type,
            'urls': urls,
            'metadata': metadata,
            'uploaded_at': time.time()
        })
        
        # Purge CloudFlare cache for this game
        await self._purge_cloudflare_cache(game_id)
        
        return {
            'artwork_id': artwork_id,
            'urls': urls,
            'cdn_regions': list(self.cdn_endpoints.keys())
        }
    
    async def _process_image_variants(self, image_data: bytes) -> Dict:
        """Process image into multiple sizes and formats"""
        variants = {}
        
        # Open original image
        img = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA' or img.mode == 'LA':
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        
        for size_name, dimensions in self.image_sizes.items():
            if dimensions:
                # Resize image
                resized = img.copy()
                resized.thumbnail(dimensions, Image.Resampling.LANCZOS)
            else:
                resized = img
            
            # Save as WebP (better compression)
            webp_buffer = io.BytesIO()
            resized.save(webp_buffer, format='WEBP', quality=85, method=6)
            webp_data = webp_buffer.getvalue()
            
            # Save as JPEG (fallback)
            jpeg_buffer = io.BytesIO()
            resized.save(jpeg_buffer, format='JPEG', quality=90, optimize=True)
            jpeg_data = jpeg_buffer.getvalue()
            
            variants[size_name] = {
                'webp': webp_data,
                'jpeg': jpeg_data,
                'dimensions': resized.size
            }
        
        return variants
    
    async def _upload_to_s3(self, key: str, data: bytes, content_type: str) -> str:
        """Upload file to S3 bucket"""
        try:
            bucket = self.config.get('s3_bucket', 'vapor-artwork')
            
            self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl='public, max-age=31536000',  # 1 year cache
                Metadata={
                    'uploaded': str(int(time.time()))
                }
            )
            
            # Return CloudFront URL
            cloudfront_domain = self.config.get('cloudfront_domain', 'cdn.vaporapp.com')
            return f"https://{cloudfront_domain}/{key}"
            
        except ClientError as e:
            print(f"S3 upload error: {e}")
            raise
    
    def _generate_artwork_id(self, game_id: int, artwork_type: str, image_data: bytes) -> str:
        """Generate unique ID for artwork"""
        hasher = hashlib.sha256()
        hasher.update(f"{game_id}:{artwork_type}".encode())
        hasher.update(image_data)
        return hasher.hexdigest()[:16]
    
    async def _cache_artwork_metadata(self, artwork_id: str, metadata: Dict):
        """Cache artwork metadata in Redis"""
        import json
        
        key = f"artwork:meta:{artwork_id}"
        await self.redis_client.setex(
            key,
            self.cache_ttl['warm'],
            json.dumps(metadata)
        )
    
    async def get_artwork_url(
        self,
        artwork_id: str,
        size: str = 'medium',
        format: str = 'webp',
        region: Optional[str] = None
    ) -> Optional[str]:
        """
        Get optimized artwork URL
        Automatically selects best CDN endpoint
        """
        # Get metadata from cache
        import json
        
        key = f"artwork:meta:{artwork_id}"
        metadata_json = await self.redis_client.get(key)
        
        if not metadata_json:
            return None
        
        metadata = json.loads(metadata_json)
        urls = metadata.get('urls', {})
        
        if size not in urls:
            size = 'medium'  # Fallback to medium
        
        if format not in urls[size]:
            format = 'jpeg'  # Fallback to JPEG
        
        base_url = urls[size][format]
        
        # Select best CDN endpoint based on region
        if region and region in self.cdn_endpoints:
            cdn_domain = self.cdn_endpoints[region]
        else:
            cdn_domain = await self._get_nearest_cdn_endpoint()
        
        # Replace domain with CDN endpoint
        return base_url.replace('https://cdn.vaporapp.com', cdn_domain)
    
    async def _get_nearest_cdn_endpoint(self) -> str:
        """Get nearest CDN endpoint based on latency"""
        # For now, return default
        # In production, would test latency to each endpoint
        return self.cdn_endpoints.get('us-east', 'https://cdn.vaporapp.com')
    
    async def _purge_cloudflare_cache(self, game_id: int):
        """Purge CloudFlare cache for specific game"""
        if not self.cloudflare_api:
            return
        
        zone_id = self.config.get('cloudflare_zone_id')
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'Authorization': f'Bearer {self.cloudflare_api}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'files': [
                    f"https://cdn.vaporapp.com/artwork/{game_id}/*"
                ]
            }
            
            async with session.post(
                f'https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache',
                headers=headers,
                json=data
            ) as response:
                if response.status == 200:
                    print(f"✅ CloudFlare cache purged for game {game_id}")
                else:
                    print(f"⚠️ CloudFlare purge failed: {response.status}")
    
    async def prefetch_popular_artwork(self, game_ids: List[int]):
        """Prefetch popular artwork to edge locations"""
        for game_id in game_ids:
            # Trigger edge caching by making requests to each region
            for region, endpoint in self.cdn_endpoints.items():
                asyncio.create_task(self._warm_edge_cache(game_id, endpoint))
    
    async def _warm_edge_cache(self, game_id: int, endpoint: str):
        """Warm edge cache for specific game"""
        async with aiohttp.ClientSession() as session:
            # Request common artwork sizes to warm cache
            sizes = ['thumbnail', 'medium']
            for size in sizes:
                url = f"{endpoint}/artwork/{game_id}/grid/*/size/{size}.webp"
                try:
                    async with session.head(url, timeout=5) as response:
                        pass  # Just warming cache
                except:
                    pass
    
    async def get_bandwidth_stats(self) -> Dict:
        """Get CDN bandwidth statistics"""
        stats = {
            'total_bandwidth_gb': 0,
            'cache_hit_rate': 0,
            'requests_per_second': 0,
            'popular_games': [],
            'cdn_costs': 0
        }
        
        # In production, would query CloudFlare/CloudFront APIs
        # For now, return mock data
        stats['cache_hit_rate'] = 0.92  # 92% cache hit rate
        stats['requests_per_second'] = 1250
        stats['total_bandwidth_gb'] = 450.5
        
        return stats
    
    async def optimize_delivery(self, user_location: Dict) -> Dict:
        """Optimize content delivery based on user location"""
        # Determine best CDN endpoint
        region = self._get_region_from_location(user_location)
        
        # Return optimized settings
        return {
            'cdn_endpoint': self.cdn_endpoints.get(region, self.cdn_endpoints['us-east']),
            'image_format': 'webp' if user_location.get('supports_webp', True) else 'jpeg',
            'progressive_loading': True,
            'lazy_load_threshold': 3,  # Number of viewport heights
            'prefetch_count': 5  # Number of images to prefetch
        }
    
    def _get_region_from_location(self, location: Dict) -> str:
        """Map user location to CDN region"""
        country = location.get('country', 'US')
        
        # Simple mapping - in production would use geolocation database
        if country in ['US', 'CA', 'MX']:
            if location.get('timezone', '').startswith('America/Los'):
                return 'us-west'
            return 'us-east'
        elif country in ['GB', 'FR', 'DE', 'IT', 'ES']:
            return 'eu-west'
        elif country in ['JP', 'KR', 'CN', 'AU', 'IN']:
            return 'asia-pacific'
        
        return 'us-east'  # Default
    
    async def health_check(self) -> str:
        """Check CDN health status"""
        try:
            # Check Redis connection
            await self.redis_client.ping()
            
            # Check S3 access
            self.s3_client.head_bucket(
                Bucket=self.config.get('s3_bucket', 'vapor-artwork')
            )
            
            return "healthy"
        except:
            return "unhealthy"