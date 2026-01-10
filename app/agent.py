"""
Scoop AI Agent V3 - Powered by Claude Agent SDK.

Uses ClaudeSDKClient for automatic tool orchestration and conversation management.
Replaces the manual agentic loop with SDK-managed sessions.
"""

import os
import time
import logging
from typing import Dict, Optional, NamedTuple
from dataclasses import dataclass

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)

from config import get_settings
from app.tools import create_scoop_mcp_server
from app.hooks import validate_user_prompt, validate_tool_use, log_tool_result

logger = logging.getLogger("scoop_ai.agent")


# ==================== Custom Exceptions ====================

class AgentError(Exception):
    """Base exception for agent errors."""
    pass


class SessionError(AgentError):
    """Session-related errors."""
    pass


class ToolExecutionError(AgentError):
    """Tool execution errors."""
    pass


# ==================== Session Data ====================

@dataclass
class SessionData:
    """Holds client and metadata for a session."""
    client: ClaudeSDKClient
    created_at: float
    last_activity: float

    def update_activity(self):
        self.last_activity = time.time()


class ScoopAgent:
    """
    Scoop AI Agent V3 using Claude Agent SDK.

    Key improvements over V2:
    - Automatic tool orchestration (no manual agentic loop)
    - Built-in conversation history management
    - Security via hooks (not inline checks)
    - In-process MCP server for tools
    - Session TTL with automatic cleanup
    """

    # Session timeout in seconds (30 minutes)
    SESSION_TTL = int(os.getenv("SESSION_TTL_SECONDS", "1800"))

    def __init__(self):
        self.settings = get_settings()
        self.mcp_server = create_scoop_mcp_server()
        self._sessions: Dict[str, SessionData] = {}
        logger.info(f"ScoopAgent V3 initialized (TTL: {self.SESSION_TTL}s)")

    def _create_options(self) -> ClaudeAgentOptions:
        """Configure agent options for SDK client.
        
        Performance Optimizations:
        - Prompt caching: Reduces latency by ~30-50% for repeated system prompts
        - max_turns=5: Limits conversation loops for faster responses
        """
        return ClaudeAgentOptions(
            # Model configuration
            model=os.getenv("DEFAULT_MODEL", self.settings.default_model),
            system_prompt=self.settings.system_prompt,

            # Working directory
            cwd=str(self.settings.cwd),

            # Permission mode - accept edits since we only have read-only tools
            permission_mode=self.settings.permission_mode,

            # Note: Prompt caching is handled automatically by Claude API
            # The SDK doesn't require explicit beta headers for this

            # MCP Server registration
            mcp_servers={
                "scoop-products": self.mcp_server,
            },

            # Explicitly allow only our tools
            allowed_tools=[
                "mcp__scoop-products__search_products",
                "mcp__scoop-products__get_product_details",
                "mcp__scoop-products__get_all_categories",
            ],

            # Security Hooks
            hooks={
                "UserPromptSubmit": [validate_user_prompt],
                "PreToolUse": [validate_tool_use],
                "PostToolUse": [log_tool_result],
            },

            # 🚀 PERFORMANCE: Limit turns for faster responses
            # Reduced from 5 to 2 to prevent timeout on broad queries
            # Each turn adds 10-40s Claude thinking time + tool execution
            max_turns=2,
        )

    async def _get_or_create_client(self, user_id: str) -> ClaudeSDKClient:
        """Get existing client for user or create a new one."""
        now = time.time()

        # Check if session exists and is not expired
        if user_id in self._sessions:
            session = self._sessions[user_id]
            if (now - session.last_activity) > self.SESSION_TTL:
                # Session expired, clean it up
                logger.info(f"Session expired for user: {user_id}")
                await self.clear_session(user_id)
            else:
                session.update_activity()
                return session.client

        # Create new session
        logger.info(f"Creating new agent session for user: {user_id}")
        try:
            options = self._create_options()
            client = ClaudeSDKClient(options=options)
            await client.connect()

            self._sessions[user_id] = SessionData(
                client=client,
                created_at=now,
                last_activity=now
            )
            return client

        except Exception as e:
            logger.error(f"Failed to create session for {user_id}: {e}")
            raise SessionError(f"Failed to create session: {e}") from e

    async def chat(self, user_id: str, message: str) -> str:
        """
        Process a chat message using Claude Agent SDK.

        The SDK handles:
        - Tool orchestration automatically
        - Conversation history
        - Security via hooks

        Args:
            user_id: Unique identifier for the user session
            message: User's message in Georgian or English

        Returns:
            Agent's response text

        Raises:
            SessionError: If session creation fails
            AgentError: If chat processing fails
        """
        client = await self._get_or_create_client(user_id)

        try:
            # Send message to agent
            # SDK handles tool loops automatically
            await client.query(message)

            # Collect response
            full_response = ""

            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            full_response += block.text

            if not full_response:
                full_response = "ბოდიში, პასუხის გენერირება ვერ მოხერხდა. გთხოვთ სცადოთ თავიდან."

            # Update session activity
            if user_id in self._sessions:
                self._sessions[user_id].update_activity()

            return full_response

        except SessionError:
            # Re-raise session errors
            raise

        except Exception as e:
            logger.error(f"Agent error for user {user_id}: {e}")

            # Clear broken session
            await self.clear_session(user_id)

            # Raise proper exception for handler
            raise AgentError(f"Chat processing failed: {e}") from e

    async def clear_session(self, user_id: str) -> bool:
        """
        Clear user's conversation session.

        Removes the client session, forcing a fresh session on next chat.
        Note: We don't await disconnect() to avoid asyncio cancel scope errors.
        """
        if user_id in self._sessions:
            # Just remove the session - don't try to disconnect
            # Disconnecting from a different task causes cancel scope errors
            del self._sessions[user_id]
            logger.info(f"Session cleared for user: {user_id}")
            return True
        return False

    async def cleanup_stale_sessions(self) -> int:
        """
        Remove sessions that have exceeded TTL.

        Returns:
            Number of sessions cleaned up.
        """
        now = time.time()
        stale_users = [
            user_id for user_id, session in self._sessions.items()
            if (now - session.last_activity) > self.SESSION_TTL
        ]

        for user_id in stale_users:
            await self.clear_session(user_id)

        if stale_users:
            logger.info(f"Cleaned up {len(stale_users)} stale sessions")

        return len(stale_users)

    def get_active_sessions(self) -> list:
        """Get list of active user session IDs with metadata."""
        now = time.time()
        return [
            {
                "user_id": user_id,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "age_seconds": int(now - session.created_at),
                "idle_seconds": int(now - session.last_activity),
            }
            for user_id, session in self._sessions.items()
        ]

    def get_session_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)

    async def shutdown(self):
        """Shutdown all agent sessions gracefully."""
        logger.info(f"Shutting down {len(self._sessions)} agent sessions...")
        for user_id in list(self._sessions.keys()):
            await self.clear_session(user_id)
        logger.info("All sessions closed")


# ==================== Singleton Management ====================

_agent_instance: Optional[ScoopAgent] = None


def get_agent() -> ScoopAgent:
    """Get or create the global agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ScoopAgent()
    return _agent_instance


async def shutdown_agent():
    """Shutdown the global agent instance."""
    global _agent_instance
    if _agent_instance is not None:
        await _agent_instance.shutdown()
        _agent_instance = None
        logger.info("Agent shutdown complete")
