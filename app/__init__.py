"""
App module initialization.
Exports agent and product service.
"""

from app.agent import ScoopAgent, get_agent, shutdown_agent, set_product_service
from app.database import db_manager, get_db
from app.product_service import ProductService, get_product_service

__all__ = [
    # Agent
    "ScoopAgent",
    "get_agent",
    "shutdown_agent",
    "set_product_service",
    # Database
    "db_manager",
    "get_db",
    # Products
    "ProductService",
    "get_product_service",
]
