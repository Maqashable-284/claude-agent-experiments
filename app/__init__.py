"""
App module initialization.
Exports agent, tools, hooks, and product service.

V3 - Claude Agent SDK Migration
"""

from app.agent import ScoopAgent, get_agent, shutdown_agent
from app.database import db_manager, get_db
from app.product_service import ProductService, get_product_service
from app.tools import set_tool_service, create_scoop_mcp_server
from app.hooks import validate_user_prompt, validate_tool_use, log_tool_result

__all__ = [
    # Agent
    "ScoopAgent",
    "get_agent",
    "shutdown_agent",
    # Database
    "db_manager",
    "get_db",
    # Products
    "ProductService",
    "get_product_service",
    # Tools (V3)
    "set_tool_service",
    "create_scoop_mcp_server",
    # Hooks (V3)
    "validate_user_prompt",
    "validate_tool_use",
    "log_tool_result",
]
