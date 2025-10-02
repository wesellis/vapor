#!/usr/bin/env python3
"""
VAPOR Backend API v3.0
Modern FastAPI backend with cloud features, AI recommendations, and real-time sync
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
from typing import List, Optional, Dict
import asyncio
import uvicorn
from datetime import datetime
import jwt
from passlib.context import CryptContext

from .routers import artwork, users, steam, analytics, community
from .services import CloudSyncService, AIRecommendationEngine, CDNService
from .database import get_db, init_database
from .websocket import ConnectionManager
from .config import Settings

# Initialize settings
settings = Settings()

# Create FastAPI app
app = FastAPI(
    title="VAPOR API",
    description="Professional Steam Grid Artwork Management API",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
connection_manager = ConnectionManager()
cloud_sync = CloudSyncService()
ai_engine = AIRecommendationEngine()
cdn_service = CDNService()

@app.on_event("startup")
async def startup():
    """Initialize backend services on startup"""
    # Initialize Redis for rate limiting and caching
    redis_client = await redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )
    await FastAPILimiter.init(redis_client)
    
    # Initialize database
    await init_database()
    
    # Start background services
    asyncio.create_task(cloud_sync.start_sync_worker())
    asyncio.create_task(ai_engine.load_models())
    
    print("🚀 VAPOR Backend API started successfully")

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    await cloud_sync.stop()
    await connection_manager.disconnect_all()
    print("👋 VAPOR Backend API shutting down")

# Include routers
app.include_router(artwork.router, prefix="/api/v3/artwork", tags=["artwork"])
app.include_router(users.router, prefix="/api/v3/users", tags=["users"])
app.include_router(steam.router, prefix="/api/v3/steam", tags=["steam"])
app.include_router(analytics.router, prefix="/api/v3/analytics", tags=["analytics"])
app.include_router(community.router, prefix="/api/v3/community", tags=["community"])

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "VAPOR API",
        "version": "3.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v3/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "services": {
            "database": await check_database_health(),
            "redis": await check_redis_health(),
            "cdn": await cdn_service.health_check(),
            "ai_engine": ai_engine.is_ready()
        }
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time features"""
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data["type"] == "sync":
                await cloud_sync.handle_sync(client_id, data)
            elif data["type"] == "preview":
                await handle_live_preview(client_id, data)
            elif data["type"] == "progress":
                await handle_progress_update(client_id, data)
                
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await connection_manager.disconnect(client_id)

async def check_database_health():
    """Check database connectivity"""
    try:
        db = await get_db()
        await db.execute("SELECT 1")
        return "healthy"
    except:
        return "unhealthy"

async def check_redis_health():
    """Check Redis connectivity"""
    try:
        redis_client = await redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        return "healthy"
    except:
        return "unhealthy"

async def handle_live_preview(client_id: str, data: dict):
    """Handle live preview sharing"""
    # Broadcast preview to other connected clients
    await connection_manager.broadcast(
        {
            "type": "preview_update",
            "client_id": client_id,
            "artwork": data["artwork"]
        },
        exclude=client_id
    )

async def handle_progress_update(client_id: str, data: dict):
    """Handle progress updates"""
    # Store progress in Redis for quick access
    redis_client = await redis.from_url(settings.REDIS_URL)
    await redis_client.setex(
        f"progress:{client_id}",
        300,  # 5 minute TTL
        data["progress"]
    )
    
    # Broadcast to interested clients
    await connection_manager.send_to_client(
        client_id,
        {
            "type": "progress",
            "value": data["progress"]
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )