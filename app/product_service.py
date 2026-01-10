"""
Product Service - MongoDB Product Queries.

This service replaces the mock data with real MongoDB queries.
Uses the same QUERY_MAP as the original Scoop AI for Georgian→English translation.
"""

import re
from typing import Any, Dict, List, Optional
import logging

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


# Georgian → English keyword mapping (from original Scoop AI)
QUERY_MAP = {
    # Products
    "კრეატინ": "creatine", "პროტეინ": "protein", "ცილა": "protein",
    "bcaa": "bcaa", "ამინო": "amino", "პრევორკაუტ": "pre-workout",
    "ვიტამინ": "vitamin", "ომეგა": "omega",
    "გეინერ": "gainer|mass|weight", "გეინერი": "gainer|mass|weight",
    # Goals
    "მასა": "protein|gainer|mass", "წონა": "protein|gainer", "მომატება": "protein|gainer",
    "გამშრალება": "carnitine|ripped|burner", "კლება": "carnitine|burn",
    "გასახდომ": "carnitine|burner|fat",
    "ენერგია": "pre-workout|energy", "ძალა": "creatine|pre-workout",
    # Muscle  
    "კუნთ": "protein|creatine|bcaa|amino", "მუსკულ": "protein|creatine|bcaa"
}

# Category map
CATEGORY_MAP = {
    "პროტეინი": "protein",
    "კრეატინი": "creatine",
    "ვიტამინები": "vitamin",
    "ამინომჟავები": "bcaa|amino",
}


class ProductService:
    """
    Product service for MongoDB operations.
    
    Uses hybrid search: regex with Georgian→English translation.
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
        Search for products using Georgian→English translation.
        
        This matches the original Scoop AI search logic.
        """
        query_lower = query.lower()
        
        # Build search keywords from Georgian→English map
        keywords = []
        for geo, eng in QUERY_MAP.items():
            if geo in query_lower:
                keywords.extend(eng.split("|"))
        
        # Add original query if no keywords found
        if not keywords:
            keywords = [query_lower]
        
        # Add category if provided
        if category:
            eng_cat = CATEGORY_MAP.get(category.lower(), category)
            keywords.append(eng_cat)
        
        # Escape regex special chars
        keywords_escaped = [re.escape(kw) for kw in keywords]
        pattern = "|".join(set(keywords_escaped))
        
        if not pattern:
            return []
        
        # Build regex filter
        regex = {"$regex": pattern, "$options": "i"}
        
        filter_query = {
            "$or": [
                {"name": regex},
                {"brand": regex},
                {"category": regex},
                {"description": regex}
            ]
        }
        
        # Price filter
        if max_price:
            filter_query["price"] = {"$lte": max_price}
        
        # Stock filter
        if in_stock_only:
            filter_query["in_stock"] = True
        
        try:
            products = await self.collection.find(filter_query).limit(limit).to_list(length=limit)
            
            # Convert ObjectId to string
            for p in products:
                if "_id" in p:
                    p["id"] = str(p["_id"])
                    del p["_id"]
            
            logger.info(f"Found {len(products)} products for query: {query} (keywords: {keywords})")
            return products
            
        except Exception as e:
            logger.error(f"Product search failed: {e}")
            return []
    
    async def get_all_categories_with_products(
        self,
        products_per_category: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all products grouped by category.

        Returns a dict like:
        {
            "protein": [product1, product2, product3],
            "creatine": [product1, product2],
            ...
        }

        This enables answering "show all products" in a single tool call.
        """
        try:
            # Use aggregation to group by category
            # Note: Removed in_stock filter as it was returning 0 results
            pipeline = [
                {"$sort": {"price": 1}},  # Sort by price within each group
                {"$group": {
                    "_id": "$category",
                    "products": {"$push": "$$ROOT"},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}  # Sort categories alphabetically
            ]

            cursor = self.collection.aggregate(pipeline)
            result = {}

            async for doc in cursor:
                category = doc["_id"] or "other"
                products = doc["products"][:products_per_category]

                # Clean up ObjectId
                for p in products:
                    if "_id" in p:
                        p["id"] = str(p["_id"])
                        del p["_id"]

                result[category] = products

            logger.info(f"Found {len(result)} categories with products")
            return result

        except Exception as e:
            logger.error(f"Get all categories failed: {e}")
            return {}

    async def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a single product by ID."""
        try:
            from bson import ObjectId
            
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


# Global service instance
_product_service: Optional[ProductService] = None


def get_product_service(db: AsyncIOMotorDatabase) -> ProductService:
    """Get or create the product service."""
    global _product_service
    if _product_service is None:
        _product_service = ProductService(db)
    return _product_service
