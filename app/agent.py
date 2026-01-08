"""
Scoop AI Agent Service.

This module provides the main agent interface using the official
ClaudeSDKClient from claude-agent-sdk for session management.
"""

from typing import Dict, Optional, Any, AsyncIterator
import asyncio
import logging

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
    HookMatcher
)

from config import get_settings
from app.tools import scoop_server
from app.hooks import security_guardrail, audit_log_hook

logger = logging.getLogger("scoop_ai.agent")


class ScoopAgent:
    """
    Scoop AI Agent Service using ClaudeSDKClient.
    
    Manages user sessions with conversation memory and
    connects to custom MCP tools for product search.
    
    Usage:
        agent = ScoopAgent()
        response = await agent.chat("user123", "მაჩვენე პროტეინები")
        print(response)
    """
    
    def __init__(self):
        """Initialize the Scoop Agent service."""
        self.settings = get_settings()
        
        # Store active client sessions per user
        self._sessions: Dict[str, ClaudeSDKClient] = {}
        
        # Configure ClaudeAgentOptions
        self._default_options = ClaudeAgentOptions(
            # System prompt (Georgian sports nutrition consultant)
            system_prompt=self.settings.system_prompt,
            
            # MCP servers with custom tools
            mcp_servers={
                "scoop": scoop_server
            },
            
            # Allowed tools (MCP tool format: mcp__<server>__<tool>)
            allowed_tools=[
                "mcp__scoop__search_products",
                "mcp__scoop__get_product_details",
                "mcp__scoop__check_availability",
                "mcp__scoop__compare_products"
            ],
            
            # Security hooks
            hooks={
                "PreToolUse": [
                    HookMatcher(hooks=[security_guardrail, audit_log_hook])
                ]
            },
            
            # Permission mode (auto-approve edits)
            permission_mode=self.settings.permission_mode,
            
            # Maximum conversation turns
            max_turns=self.settings.max_turns,
            
            # Model configuration
            model=self.settings.default_model,
            
            # Working directory
            cwd=str(self.settings.cwd)
        )
    
    async def _get_or_create_client(self, user_id: str) -> ClaudeSDKClient:
        """
        Get existing client session or create a new one.
        
        Args:
            user_id: Unique user identifier
        
        Returns:
            ClaudeSDKClient instance for the user
        """
        if user_id not in self._sessions:
            logger.info(f"Creating new session for user: {user_id}")
            client = ClaudeSDKClient(options=self._default_options)
            await client.connect()
            self._sessions[user_id] = client
        
        return self._sessions[user_id]
    
    async def chat(
        self,
        user_id: str,
        message: str
    ) -> str:
        """
        Send a message and get the final text response.
        
        Args:
            user_id: Unique user identifier
            message: User's message in Georgian or English
        
        Returns:
            Final text response from the agent
        """
        client = await self._get_or_create_client(user_id)
        
        # Send query
        await client.query(message)
        
        # Collect response text
        response_text = ""
        
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
            
            elif isinstance(msg, ResultMessage):
                if msg.subtype != "success":
                    logger.error(f"Agent error: {msg.subtype}")
                    if not response_text:
                        response_text = "სამწუხაროდ, მოხდა შეცდომა. გთხოვთ, სცადოთ თავიდან."
        
        return response_text
    
    async def chat_stream(
        self,
        user_id: str,
        message: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send a message and stream responses as they arrive.
        
        Args:
            user_id: Unique user identifier
            message: User's message
        
        Yields:
            Dict with message type and content
        """
        client = await self._get_or_create_client(user_id)
        
        await client.query(message)
        
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        yield {
                            "type": "text",
                            "content": block.text
                        }
                    elif isinstance(block, ToolUseBlock):
                        yield {
                            "type": "tool_use",
                            "tool_name": block.name,
                            "tool_id": block.id
                        }
            
            elif isinstance(msg, ResultMessage):
                yield {
                    "type": "result",
                    "status": msg.subtype,
                    "cost": getattr(msg, "total_cost_usd", None)
                }
    
    async def clear_session(self, user_id: str) -> bool:
        """
        Clear a user's conversation history.
        
        Args:
            user_id: User to clear session for
        
        Returns:
            True if session was cleared
        """
        if user_id in self._sessions:
            try:
                await self._sessions[user_id].disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting session: {e}")
            
            del self._sessions[user_id]
            logger.info(f"Cleared session for user: {user_id}")
            return True
        
        return False
    
    async def interrupt_session(self, user_id: str) -> bool:
        """
        Interrupt an ongoing agent task.
        
        Args:
            user_id: User whose session to interrupt
        
        Returns:
            True if interrupt was sent
        """
        if user_id in self._sessions:
            await self._sessions[user_id].interrupt()
            logger.info(f"Interrupted session for user: {user_id}")
            return True
        
        return False
    
    def get_active_sessions(self) -> list[str]:
        """Get list of active user session IDs."""
        return list(self._sessions.keys())
    
    async def shutdown(self):
        """Disconnect all sessions gracefully."""
        for user_id in list(self._sessions.keys()):
            await self.clear_session(user_id)
        
        logger.info("All sessions disconnected")


# ==================== Singleton Instance ====================

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
