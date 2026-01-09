"""
Scoop AI Agent V3 - Powered by Claude Agent SDK.

Uses ClaudeSDKClient for automatic tool orchestration and conversation management.
Replaces the manual agentic loop with SDK-managed sessions.
"""

import os
import logging
from typing import Dict, Optional

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


class ScoopAgent:
    """
    Scoop AI Agent V3 using Claude Agent SDK.

    Key improvements over V2:
    - Automatic tool orchestration (no manual agentic loop)
    - Built-in conversation history management
    - Security via hooks (not inline checks)
    - In-process MCP server for tools
    """

    def __init__(self):
        self.settings = get_settings()
        self.mcp_server = create_scoop_mcp_server()
        self._clients: Dict[str, ClaudeSDKClient] = {}
        logger.info("ScoopAgent V3 initialized with Claude Agent SDK")

    def _create_options(self) -> ClaudeAgentOptions:
        """Configure agent options for SDK client."""
        return ClaudeAgentOptions(
            # Model configuration
            model=os.getenv("DEFAULT_MODEL", self.settings.default_model),
            system_prompt=self.settings.system_prompt,

            # Working directory
            cwd=str(self.settings.cwd),

            # Permission mode - accept edits since we only have read-only tools
            permission_mode=self.settings.permission_mode,

            # MCP Server registration
            mcp_servers={
                "scoop-products": self.mcp_server,
            },

            # Explicitly allow only our tools
            allowed_tools=[
                "mcp__scoop-products__search_products",
                "mcp__scoop-products__get_product_details",
            ],

            # Security Hooks
            hooks={
                "UserPromptSubmit": [validate_user_prompt],
                "PreToolUse": [validate_tool_use],
                "PostToolUse": [log_tool_result],
            },

            # Limits
            max_turns=self.settings.max_turns,
        )

    async def _get_or_create_client(self, user_id: str) -> ClaudeSDKClient:
        """Get existing client for user or create a new one."""
        if user_id not in self._clients:
            logger.info(f"Creating new agent session for user: {user_id}")
            options = self._create_options()
            client = ClaudeSDKClient(options=options)
            await client.connect()
            self._clients[user_id] = client

        return self._clients[user_id]

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
        """
        try:
            client = await self._get_or_create_client(user_id)

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

            return full_response

        except Exception as e:
            logger.error(f"Agent error for user {user_id}: {e}")

            # Clear broken session
            await self.clear_session(user_id)

            # Return friendly error message
            return "სამწუხაროდ, ტექნიკური შეფერხებაა. გთხოვთ სცადოთ თავიდან."

    async def clear_session(self, user_id: str) -> bool:
        """
        Clear user's conversation session.

        Disconnects and removes the client, forcing a fresh session on next chat.
        """
        if user_id in self._clients:
            try:
                await self._clients[user_id].disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting client for {user_id}: {e}")
            finally:
                del self._clients[user_id]
            logger.info(f"Session cleared for user: {user_id}")
            return True
        return False

    def get_active_sessions(self) -> list:
        """Get list of active user session IDs."""
        return list(self._clients.keys())

    async def shutdown(self):
        """Shutdown all agent sessions gracefully."""
        logger.info("Shutting down all agent sessions...")
        for user_id in list(self._clients.keys()):
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
