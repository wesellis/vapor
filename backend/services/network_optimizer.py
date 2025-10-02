#!/usr/bin/env python3
"""
Network Optimization Service for VAPOR v3.0
Advanced networking features for maximum performance
"""

import asyncio
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import aiohttp
from collections import deque
import math

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class NetworkMetrics:
    """Real-time network performance metrics"""
    latency_ms: float
    bandwidth_mbps: float
    packet_loss: float
    jitter_ms: float
    requests_per_second: float
    error_rate: float
    cache_hit_rate: float

class AdaptiveRateLimiter:
    """
    Dynamic rate limiting that adapts to API response times
    """
    
    def __init__(self, initial_rate: float = 10.0):
        self.current_rate = initial_rate
        self.min_rate = 1.0
        self.max_rate = 50.0
        self.tokens = initial_rate
        self.last_update = time.time()
        self.response_times = deque(maxlen=100)
        self.error_count = 0
        self.success_count = 0
        
    async def acquire(self):
        """Acquire permission to make request"""
        while self.tokens < 1:
            # Refill tokens
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.current_rate, self.tokens + elapsed * self.current_rate)
            self.last_update = now
            
            if self.tokens < 1:
                await asyncio.sleep(0.1)
        
        self.tokens -= 1
        return True
    
    def record_response(self, response_time: float, success: bool):
        """Record response and adapt rate"""
        self.response_times.append(response_time)
        
        if success:
            self.success_count += 1
            # Increase rate if responses are fast
            if response_time < 0.5 and self.current_rate < self.max_rate:
                self.current_rate = min(self.max_rate, self.current_rate * 1.1)
        else:
            self.error_count += 1
            # Decrease rate on errors
            if self.current_rate > self.min_rate:
                self.current_rate = max(self.min_rate, self.current_rate * 0.5)
    
    def get_current_rate(self) -> float:
        """Get current requests per second rate"""
        return self.current_rate
    
    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        avg_response = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        return {
            'current_rate': self.current_rate,
            'tokens_available': self.tokens,
            'average_response_time': avg_response,
            'success_rate': self.success_count / max(1, self.success_count + self.error_count)
        }

class CircuitBreaker:
    """
    Circuit breaker pattern for fault tolerance
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.success_count = 0
        
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            # Check if we should try half-open
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
        self.success_count += 1
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
    
    def get_state(self) -> str:
        """Get current circuit state"""
        return self.state.value
    
    def reset(self):
        """Reset circuit breaker"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.success_count = 0

class CDNManager:
    """
    Intelligent CDN endpoint selection
    """
    
    def __init__(self):
        self.endpoints = {
            'primary': 'https://cdn1.steamgriddb.com',
            'secondary': 'https://cdn2.steamgriddb.com',
            'tertiary': 'https://cdn3.steamgriddb.com'
        }
        self.endpoint_latencies = {}
        self.current_endpoint = 'primary'
        
    async def select_best_endpoint(self) -> str:
        """Select CDN endpoint with lowest latency"""
        if not self.endpoint_latencies:
            await self._measure_latencies()
        
        # Select endpoint with lowest latency
        best_endpoint = min(
            self.endpoint_latencies.items(),
            key=lambda x: x[1],
            default=('primary', float('inf'))
        )[0]
        
        self.current_endpoint = best_endpoint
        return self.endpoints[best_endpoint]
    
    async def _measure_latencies(self):
        """Measure latency to each endpoint"""
        async with aiohttp.ClientSession() as session:
            for name, url in self.endpoints.items():
                try:
                    start = time.time()
                    async with session.head(url, timeout=5) as response:
                        latency = (time.time() - start) * 1000  # Convert to ms
                        self.endpoint_latencies[name] = latency
                except:
                    self.endpoint_latencies[name] = float('inf')
    
    def get_current_endpoint(self) -> str:
        """Get current CDN endpoint"""
        return self.endpoints[self.current_endpoint]
    
    async def fallback(self) -> str:
        """Fallback to next best endpoint"""
        endpoints = sorted(
            self.endpoint_latencies.items(),
            key=lambda x: x[1]
        )
        
        # Find next endpoint after current
        for i, (name, _) in enumerate(endpoints):
            if name == self.current_endpoint and i < len(endpoints) - 1:
                self.current_endpoint = endpoints[i + 1][0]
                break
        
        return self.endpoints[self.current_endpoint]

class ResumableDownloader:
    """
    Resume interrupted downloads with range requests
    """
    
    def __init__(self, chunk_size: int = 1024 * 1024):  # 1MB chunks
        self.chunk_size = chunk_size
        self.download_cache = {}
        
    async def download(
        self,
        url: str,
        session: aiohttp.ClientSession,
        progress_callback: Optional[Callable] = None
    ) -> bytes:
        """Download file with resume support"""
        # Check if partial download exists
        if url in self.download_cache:
            downloaded_bytes = self.download_cache[url]
            start_byte = len(downloaded_bytes)
        else:
            downloaded_bytes = bytearray()
            start_byte = 0
        
        headers = {}
        if start_byte > 0:
            headers['Range'] = f'bytes={start_byte}-'
        
        try:
            async with session.get(url, headers=headers) as response:
                # Check if server supports range requests
                if start_byte > 0 and response.status != 206:
                    # Server doesn't support resume, start over
                    downloaded_bytes = bytearray()
                    start_byte = 0
                
                total_size = int(response.headers.get('Content-Length', 0))
                
                async for chunk in response.content.iter_chunked(self.chunk_size):
                    downloaded_bytes.extend(chunk)
                    
                    if progress_callback:
                        progress = len(downloaded_bytes) / (total_size + start_byte)
                        await progress_callback(progress)
                
                # Clear cache on successful download
                if url in self.download_cache:
                    del self.download_cache[url]
                
                return bytes(downloaded_bytes)
                
        except Exception as e:
            # Cache partial download for resume
            if downloaded_bytes:
                self.download_cache[url] = downloaded_bytes
            raise e

class NetworkPerformanceMonitor:
    """
    Monitor and optimize network performance
    """
    
    def __init__(self):
        self.metrics_history = deque(maxlen=1000)
        self.current_metrics = NetworkMetrics(
            latency_ms=0,
            bandwidth_mbps=0,
            packet_loss=0,
            jitter_ms=0,
            requests_per_second=0,
            error_rate=0,
            cache_hit_rate=0
        )
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.cache_hits = 0
        self.total_bytes = 0
        
    def record_request(
        self,
        latency_ms: float,
        bytes_transferred: int,
        success: bool,
        cache_hit: bool = False
    ):
        """Record network request metrics"""
        self.request_count += 1
        if not success:
            self.error_count += 1
        if cache_hit:
            self.cache_hits += 1
        self.total_bytes += bytes_transferred
        
        # Update current metrics
        elapsed = time.time() - self.start_time
        self.current_metrics = NetworkMetrics(
            latency_ms=latency_ms,
            bandwidth_mbps=(self.total_bytes * 8) / (elapsed * 1_000_000),
            packet_loss=0,  # Would need actual packet analysis
            jitter_ms=self._calculate_jitter(),
            requests_per_second=self.request_count / elapsed,
            error_rate=self.error_count / max(1, self.request_count),
            cache_hit_rate=self.cache_hits / max(1, self.request_count)
        )
        
        self.metrics_history.append(self.current_metrics)
    
    def _calculate_jitter(self) -> float:
        """Calculate network jitter from latency variance"""
        if len(self.metrics_history) < 2:
            return 0
        
        latencies = [m.latency_ms for m in self.metrics_history]
        avg_latency = sum(latencies) / len(latencies)
        variance = sum((l - avg_latency) ** 2 for l in latencies) / len(latencies)
        return math.sqrt(variance)
    
    def get_metrics(self) -> NetworkMetrics:
        """Get current network metrics"""
        return self.current_metrics
    
    def get_optimization_suggestions(self) -> List[str]:
        """Get network optimization suggestions"""
        suggestions = []
        
        if self.current_metrics.error_rate > 0.1:
            suggestions.append("High error rate detected - consider reducing request rate")
        
        if self.current_metrics.latency_ms > 1000:
            suggestions.append("High latency detected - consider using closer CDN endpoint")
        
        if self.current_metrics.cache_hit_rate < 0.5:
            suggestions.append("Low cache hit rate - consider increasing cache size")
        
        if self.current_metrics.bandwidth_mbps < 1:
            suggestions.append("Low bandwidth utilization - consider parallel downloads")
        
        return suggestions

class ConnectionPoolWarmup:
    """
    Pre-warm connection pools for better performance
    """
    
    @staticmethod
    async def warmup(session: aiohttp.ClientSession, urls: List[str]):
        """Warm up connections to specified URLs"""
        tasks = []
        for url in urls:
            tasks.append(ConnectionPoolWarmup._warmup_single(session, url))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    @staticmethod
    async def _warmup_single(session: aiohttp.ClientSession, url: str):
        """Warm up single connection"""
        try:
            async with session.head(url, timeout=5) as response:
                pass  # Just establishing connection
        except:
            pass  # Ignore warmup failures