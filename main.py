"""
Scoop AI Agent - FastAPI Server with MongoDB.

Optimized for Cloud Run + Botpress Integration.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import get_settings
from app.agent import get_agent, shutdown_agent
from app.database import db_manager
from app.product_service import get_product_service
from app.tools import set_product_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("scoop_ai")


# ==================== Lifespan Handler ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    logger.info("🚀 Starting Scoop AI Agent Server...")
    
    # Connect to MongoDB
    mongodb_uri = os.getenv("MONGODB_URI", settings.mongodb_uri)
    mongodb_database = os.getenv("MONGODB_DATABASE", settings.mongodb_database)
    
    try:
        await db_manager.connect(mongodb_uri, mongodb_database)
        
        # Initialize product service and inject into tools
        db = await db_manager.get_database()
        product_service = get_product_service(db)
        set_product_service(product_service)
        
        logger.info("✅ MongoDB connected and ProductService initialized")
    except Exception as e:
        logger.warning(f"⚠️ MongoDB connection failed: {e}")
        logger.warning("⚠️ Running with mock data (no database)")
    
    if not settings.anthropic_api_key:
        logger.warning("⚠️ ANTHROPIC_API_KEY not set!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Scoop AI Agent Server...")
    await shutdown_agent()
    await db_manager.disconnect()


# ==================== FastAPI App ====================

app = FastAPI(
    title="Scoop AI Agent",
    description="ქართული სპორტული კვების კონსულტანტი - Claude Agent SDK + MongoDB",
    version="1.2.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Request/Response Models ====================

class ChatRequest(BaseModel):
    """Chat request - compatible with Botpress."""
    user_id: str = Field(..., description="Unique user identifier")
    message: str = Field(..., description="User message", min_length=1, max_length=5000)
    # Optional: session management
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response - optimized for Botpress integration."""
    user_id: str
    response: str
    success: bool = True
    error: Optional[str] = None
    # Botpress-friendly fields
    text: str = ""  # Duplicate of response for Botpress
    choices: Optional[List[str]] = None  # Quick replies


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    active_sessions: int


# ==================== Endpoints ====================

@app.get("/", response_model=dict)
async def root():
    """Root endpoint - API info."""
    return {
        "name": "Scoop AI Agent",
        "description": "სპორტული კვების კონსულტანტი",
        "version": "1.2.0",
        "features": ["Claude Agent SDK", "MongoDB", "MCP Tools", "Botpress Ready"],
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Cloud Run."""
    agent = get_agent()
    db_status = "connected" if db_manager.is_connected else "disconnected"
    
    return HealthResponse(
        status="healthy",
        version="1.2.0",
        database=db_status,
        active_sessions=len(agent.get_active_sessions())
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    
    Botpress Integration:
    - Send: {"user_id": "bp_xxx", "message": "..."}
    - Receive: {"response": "...", "text": "...", "choices": [...]}
    """
    try:
        agent = get_agent()
        
        logger.info(f"Chat request from {request.user_id}: {request.message[:50]}...")
        
        response_text = await agent.chat(request.user_id, request.message)
        
        # Extract quick reply suggestions (if any)
        choices = None
        if "მაგალითად:" in response_text or "შეგიძლიათ:" in response_text:
            choices = ["პროტეინი", "კრეატინი", "BCAA", "ვიტამინები"]
        
        return ChatResponse(
            user_id=request.user_id,
            response=response_text,
            text=response_text,  # Botpress reads this
            choices=choices,
            success=True
        )
    
    except Exception as e:
        logger.error(f"Chat error for {request.user_id}: {e}")
        error_msg = "სამწუხაროდ, მოხდა შეცდომა. გთხოვთ, სცადოთ თავიდან."
        return ChatResponse(
            user_id=request.user_id,
            response=error_msg,
            text=error_msg,
            success=False,
            error=str(e)
        )


@app.post("/session/clear")
async def clear_session(user_id: str):
    """Clear a user's conversation history."""
    agent = get_agent()
    cleared = await agent.clear_session(user_id)
    
    return {
        "user_id": user_id,
        "cleared": cleared,
        "message": "სესია გასუფთავდა" if cleared else "სესია ვერ მოიძებნა"
    }


@app.get("/sessions")
async def list_sessions():
    """List all active sessions."""
    agent = get_agent()
    return {
        "active_sessions": agent.get_active_sessions(),
        "count": len(agent.get_active_sessions())
    }


@app.get("/db/status")
async def database_status():
    """Get database connection status."""
    is_connected = db_manager.is_connected
    ping_ok = await db_manager.ping() if is_connected else False
    
    return {
        "connected": is_connected,
        "ping": ping_ok,
        "message": "MongoDB connected" if ping_ok else "Using mock data"
    }


# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    port = int(os.getenv("PORT", settings.port))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.debug
    )
