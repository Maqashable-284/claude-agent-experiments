"""
Product Service - MongoDB Product Queries.

This service replaces the mock data with real MongoDB queries.
"""

from typing import Any, Dict, List, Optional
import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class ProductService:
    """
    Product service for MongoDB operations.
    
    Collections used:
    - products: Main product catalog
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.products
    
    async def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        in_stock_only: bool = False,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for products in MongoDB.
        
        Uses text search and optional filters.
        """
        # Build filter
        filter_query = {}
        
        # Text search on name and description
        if query:
            filter_query["$or"] = [
                {"name": {"$regex": query, "$options": "i"}},
                {"name_ka": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"brand": {"$regex": query, "$options": "i"}},
                {"category": {"$regex": query, "$options": "i"}},
            ]
        
        # Category filter
        if category:
            filter_query["category"] = category
        
        # Price filter
        if max_price:
            filter_query["price"] = {"$lte": max_price}
        
        # Stock filter
        if in_stock_only:
            filter_query["in_stock"] = True
        
        try:
            cursor = self.collection.find(filter_query).limit(limit)
            products = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string
            for p in products:
                if "_id" in p:
                    p["id"] = str(p["_id"])
                    del p["_id"]
            
            logger.info(f"Found {len(products)} products for query: {query}")
            return products
            
        except Exception as e:
            logger.error(f"Product search failed: {e}")
            return []
    
    async def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a single product by ID."""
        try:
            from bson import ObjectId
            
            # Try as ObjectId first, then as string
            try:
                filter_q = {"_id": ObjectId(product_id)}
            except:
                filter_q = {"id": product_id}
            
            product = await self.collection.find_one(filter_q)
            
            if product:
                if "_id" in product:
                    product["id"] = str(product["_id"])
                    del product["_id"]
                return product
            
            return None
            
        except Exception as e:
            logger.error(f"Get product failed: {e}")
            return None
    
    async def check_availability(self, product_id: str) -> Dict[str, Any]:
        """Check product availability."""
        product = await self.get_product_by_id(product_id)
        
        if not product:
            return {"available": False, "error": "პროდუქტი ვერ მოიძებნა"}
        
        return {
            "product_id": product.get("id"),
            "product_name": product.get("name_ka", product.get("name")),
            "available": product.get("in_stock", False),
            "quantity": product.get("stock_count", 0)
        }
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all product categories with counts."""
        try:
            pipeline = [
                {"$group": {
                    "_id": "$category",
                    "count": {"$sum": 1},
                    "in_stock_count": {
                        "$sum": {"$cond": ["$in_stock", 1, 0]}
                    }
                }},
                {"$sort": {"count": -1}}
            ]
            
            cursor = self.collection.aggregate(pipeline)
            categories = await cursor.to_list(length=50)
            
            return [
                {
                    "id": cat["_id"],
                    "name": cat["_id"],
                    "product_count": cat["count"],
                    "in_stock_count": cat["in_stock_count"]
                }
                for cat in categories
            ]
            
        except Exception as e:
            logger.error(f"Get categories failed: {e}")
            return []


# Global service instance
_product_service: Optional[ProductService] = None


def get_product_service(db: AsyncIOMotorDatabase) -> ProductService:
    """Get or create the product service."""
    global _product_service
    if _product_service is None:
        _product_service = ProductService(db)
    return _product_service
