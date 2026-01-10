"""
Scoop AI Agent V3 - FastAPI Server.

Powered by Claude Agent SDK for automatic tool orchestration.
Optimized for Cloud Run + Botpress Integration.
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional, List, Dict
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import get_settings
from app.agent import get_agent, shutdown_agent, AgentError, SessionError
from app.database import db_manager, DatabaseConnectionError
from app.product_service import get_product_service
from app.tools import set_tool_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("scoop_ai")


# ==================== Rate Limiting ====================

class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for this client."""
        now = time.time()
        minute_ago = now - 60

        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]

        # Check limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False

        self.requests[client_id].append(now)
        return True

    def cleanup(self):
        """Remove stale entries."""
        now = time.time()
        minute_ago = now - 60
        stale_clients = [
            client_id for client_id, times in self.requests.items()
            if all(t <= minute_ago for t in times)
        ]
        for client_id in stale_clients:
            del self.requests[client_id]


rate_limiter = RateLimiter(
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
)


# ==================== Lifespan Handler ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown - optimized for Cloud Run."""
    logger.info("Starting Scoop AI Agent V3 (Claude Agent SDK)...")

    # Connect MongoDB synchronously to avoid race conditions
    try:
        settings = get_settings()
        mongodb_uri = os.getenv("MONGODB_URI", settings.mongodb_uri)
        mongodb_database = os.getenv("MONGODB_DATABASE", settings.mongodb_database)

        await db_manager.connect(mongodb_uri, mongodb_database)

        db = await db_manager.get_database()
        product_service = get_product_service(db)

        # Inject service into Tools
        set_tool_service(product_service)

        logger.info("MongoDB connected & Tools configured")
    except DatabaseConnectionError as e:
        logger.warning(f"MongoDB connection failed: {e} - using mock data")
    except Exception as e:
        logger.warning(f"Unexpected error during startup: {e} - using mock data")

    # Start session cleanup task
    import asyncio

    async def cleanup_sessions():
        """Periodic cleanup of stale sessions and rate limiter."""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            try:
                agent = get_agent()
                await agent.cleanup_stale_sessions()
                rate_limiter.cleanup()
                logger.debug("Session and rate limiter cleanup completed")
            except Exception as e:
                logger.warning(f"Cleanup task error: {e}")

    cleanup_task = asyncio.create_task(cleanup_sessions())
    logger.info("Server started (SDK mode)")

    yield

    logger.info("Shutting down...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await shutdown_agent()
    await db_manager.disconnect()


# ==================== FastAPI App ====================

app = FastAPI(
    title="Scoop AI Agent V3",
    description="სპორტული კვების კონსულტანტი - Claude Agent SDK",
    version="3.1.0",
    lifespan=lifespan
)

# CORS Configuration - restrict in production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
if ALLOWED_ORIGINS == ["*"]:
    # Development mode - allow all
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production mode - restricted origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )


# ==================== Rate Limiting Middleware ====================

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to /chat endpoint."""
    if request.url.path == "/chat":
        # Get client identifier (user_id from body or IP)
        client_ip = request.client.host if request.client else "unknown"

        if not rate_limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "response_text_geo": "ძალიან ბევრი მოთხოვნა. გთხოვთ მოიცადოთ ერთი წუთი.",
                    "current_state": "CHAT",
                    "success": False,
                    "error": "Rate limit exceeded"
                }
            )

    return await call_next(request)


# ==================== Models ====================

class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None  # Botpress compatibility


class ChatResponse(BaseModel):
    # V7 compatibility
    response_text_geo: str
    current_state: str = "CHAT"
    # Original SDK fields
    user_id: str = ""
    response: str = ""
    text: str = ""
    success: bool = True
    error: Optional[str] = None
    quick_replies: Optional[List[dict]] = None


# ==================== Endpoints ====================

@app.get("/")
async def root():
    return {
        "name": "Scoop AI Agent V3",
        "version": "3.0.0",
        "sdk": "Claude Agent SDK",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "connected" if db_manager.is_connected else "mock",
        "sdk": "claude-agent-sdk"
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        agent = get_agent()
        logger.info(f"Chat: {request.user_id} - {request.message[:50]}...")

        response_text = await agent.chat(request.user_id, request.message)

        # Parse quick_replies from LLM response
        quick_replies = []
        clean_response = response_text
        
        # Check for [QUICK_REPLIES] section
        if "[QUICK_REPLIES]" in response_text and "[/QUICK_REPLIES]" in response_text:
            try:
                # Extract the quick replies section
                start = response_text.find("[QUICK_REPLIES]")
                end = response_text.find("[/QUICK_REPLIES]") + len("[/QUICK_REPLIES]")
                qr_section = response_text[start:end]
                
                # Remove from clean response (including the --- separator)
                clean_response = response_text[:start].rstrip()
                if clean_response.endswith("---"):
                    clean_response = clean_response[:-3].rstrip()
                
                # Parse individual replies
                lines = qr_section.replace("[QUICK_REPLIES]", "").replace("[/QUICK_REPLIES]", "").strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if line.startswith("•"):
                        text = line[1:].strip()
                        if text:
                            quick_replies.append({"title": text, "payload": text})
            except Exception as e:
                logger.warning(f"Failed to parse quick_replies: {e}")
        
        # Fallback to static replies if none parsed
        if not quick_replies:
            quick_replies = [
                {"title": "🔍 მეტი ინფორმაცია", "payload": "მეტი დეტალები მინდა"},
                {"title": "💰 ფასები", "payload": "ფასები შეადარე"},
                {"title": "🛒 სხვა ვარიანტები", "payload": "სხვა ვარიანტები მაჩვენე"}
            ]

        # V7-compatible response
        return {
            "response_text_geo": clean_response,
            "current_state": "CHAT",
            "picked_product_ids": [],
            "primary_image_url": "",
            "carousel": None,
            "quick_replies": quick_replies,
            "topic": None,
            "recommended_index": None,
            # SDK fields
            "user_id": request.user_id,
            "response": clean_response,
            "text": clean_response,
            "success": True
        }

    except SessionError as e:
        logger.warning(f"Session error for {request.user_id}: {e}")
        error_msg = "სესია ვერ მოიძებნა. გთხოვთ დაიწყოთ თავიდან."
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "response_text_geo": error_msg,
                "current_state": "CHAT",
                "user_id": request.user_id,
                "success": False,
                "error": "session_error"
            }
        )

    except AgentError as e:
        logger.error(f"Agent error for {request.user_id}: {e}")
        error_msg = "აგენტის შეცდომა. გთხოვთ სცადოთ თავიდან."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "response_text_geo": error_msg,
                "current_state": "CHAT",
                "user_id": request.user_id,
                "success": False,
                "error": "agent_error"
            }
        )

    except TimeoutError:
        logger.error(f"Timeout for {request.user_id}")
        error_msg = "მოთხოვნას ძალიან დიდი დრო დასჭირდა. გთხოვთ სცადოთ თავიდან."
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content={
                "response_text_geo": error_msg,
                "current_state": "CHAT",
                "user_id": request.user_id,
                "success": False,
                "error": "timeout"
            }
        )

    except Exception as e:
        logger.exception(f"Unexpected error for {request.user_id}: {e}")
        error_msg = "სამწუხაროდ, მოხდა შეცდომა. გთხოვთ სცადოთ თავიდან."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "response_text_geo": error_msg,
                "current_state": "CHAT",
                "user_id": request.user_id,
                "success": False,
                "error": "internal_error"
            }
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
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
