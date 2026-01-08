"""
App module initialization.
Exports tools, hooks, and agent service.
"""

from app.tools import scoop_server, search_products, get_product_details, check_availability
from app.hooks import security_guardrail, BLOCKED_KEYWORDS
from app.agent import ScoopAgent, get_agent

__all__ = [
    # Tools
    "scoop_server",
    "search_products",
    "get_product_details",
    "check_availability",
    # Hooks
    "security_guardrail",
    "BLOCKED_KEYWORDS",
    # Agent
    "ScoopAgent",
    "get_agent",
]
