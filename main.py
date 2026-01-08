"""
Scoop AI Agent - FastAPI Server.

Optimized for Cloud Run + Botpress Integration.
Uses standard Anthropic SDK with tool_use.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import get_settings
from app.agent import get_agent, shutdown_agent, set_product_service
from app.database import db_manager
from app.product_service import get_product_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("scoop_ai")


# ==================== Lifespan Handler ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown - optimized for Cloud Run."""
    logger.info("🚀 Starting Scoop AI Agent Server...")
    
    # Connect MongoDB in background (non-blocking)
    import asyncio
    
    async def connect_mongodb():
        try:
            settings = get_settings()
            mongodb_uri = os.getenv("MONGODB_URI", settings.mongodb_uri)
            mongodb_database = os.getenv("MONGODB_DATABASE", settings.mongodb_database)
            
            await db_manager.connect(mongodb_uri, mongodb_database)
            
            db = await db_manager.get_database()
            product_service = get_product_service(db)
            set_product_service(product_service)
            
            logger.info("✅ MongoDB connected")
        except Exception as e:
            logger.warning(f"⚠️ MongoDB failed: {e} - using mock data")
    
    asyncio.create_task(connect_mongodb())
    logger.info("✅ Server started")
    
    yield
    
    logger.info("🛑 Shutting down...")
    await shutdown_agent()
    await db_manager.disconnect()


# ==================== FastAPI App ====================

app = FastAPI(
    title="Scoop AI Agent",
    description="სპორტული კვების კონსულტანტი - Anthropic SDK",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Models ====================

class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    user_id: str
    response: str
    text: str = ""
    success: bool = True
    error: Optional[str] = None
    choices: Optional[List[str]] = None


# ==================== Endpoints ====================

@app.get("/")
async def root():
    return {
        "name": "Scoop AI Agent",
        "version": "2.0.0",
        "sdk": "Anthropic SDK (standard)",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "connected" if db_manager.is_connected else "mock"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        agent = get_agent()
        logger.info(f"Chat: {request.user_id} - {request.message[:50]}...")
        
        response_text = await agent.chat(request.user_id, request.message)
        
        choices = None
        if "მაგალითად:" in response_text:
            choices = ["პროტეინი", "კრეატინი", "BCAA", "ვიტამინები"]
        
        return ChatResponse(
            user_id=request.user_id,
            response=response_text,
            text=response_text,
            choices=choices,
            success=True
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        error_msg = "სამწუხაროდ, მოხდა შეცდომა."
        return ChatResponse(
            user_id=request.user_id,
            response=error_msg,
            text=error_msg,
            success=False,
            error=str(e)
        )


@app.post("/session/clear")
async def clear_session(user_id: str):
    agent = get_agent()
    cleared = await agent.clear_session(user_id)
    return {"user_id": user_id, "cleared": cleared}


@app.get("/sessions")
async def list_sessions():
    agent = get_agent()
    return {"sessions": agent.get_active_sessions()}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
