"""
MCP Tools Module - Product Search with MongoDB.

This module defines custom tools for the Scoop AI agent using
the official @tool decorator from claude-agent-sdk.
Uses MongoDB via ProductService for real product data.
"""

from typing import Any, Dict, List, Optional
import os

from claude_agent_sdk import tool, create_sdk_mcp_server

# Global reference to product service (set during startup)
_product_service = None


def set_product_service(service):
    """Set the product service instance (called from main.py)."""
    global _product_service
    _product_service = service


# ==================== Mock Data (Fallback if no MongoDB) ====================

MOCK_PRODUCTS = [
    {
        "id": "prod_001",
        "name": "Optimum Nutrition Gold Standard Whey",
        "name_ka": "ოპტიმუმ ნიუტრიშენ გოლდ სტანდარტ ვეი",
        "category": "protein",
        "brand": "Optimum Nutrition",
        "price": 189.00,
        "currency": "GEL",
        "in_stock": True,
        "stock_count": 45,
        "description": "პრემიუმ ვეი პროტეინი - 24გ პროტეინი პორციაზე",
    },
    {
        "id": "prod_002",
        "name": "MuscleTech Nitro-Tech",
        "name_ka": "მასლთექ ნიტრო-თექ",
        "category": "protein",
        "brand": "MuscleTech",
        "price": 159.00,
        "currency": "GEL",
        "in_stock": True,
        "stock_count": 32,
        "description": "სამეცნიერო ფორმულა - 30გ პროტეინი + კრეატინი",
    },
    {
        "id": "prod_003",
        "name": "Optimum Nutrition Creatine",
        "name_ka": "ოპტიმუმ ნიუტრიშენ კრეატინი",
        "category": "creatine",
        "brand": "Optimum Nutrition",
        "price": 79.00,
        "currency": "GEL",
        "in_stock": True,
        "stock_count": 89,
        "description": "სუფთა კრეატინ მონოჰიდრატი",
    },
]


# ==================== Helper Functions ====================

async def _search_products_db(query: str, category: str = None, max_price: float = None, in_stock_only: bool = False) -> List[Dict]:
    """Search products using MongoDB or fallback to mock."""
    if _product_service:
        return await _product_service.search_products(
            query=query,
            category=category,
            max_price=max_price,
            in_stock_only=in_stock_only,
            limit=10
        )
    
    # Fallback to mock data
    results = []
    query_lower = query.lower() if query else ""
    
    for product in MOCK_PRODUCTS:
        name_match = (
            query_lower in product.get("name", "").lower() or
            query_lower in product.get("name_ka", "").lower() or
            query_lower in product.get("category", "").lower() or
            query_lower in product.get("brand", "").lower()
        )
        
        if not name_match and query:
            continue
        if category and product.get("category") != category:
            continue
        if max_price and product.get("price", 0) > max_price:
            continue
        if in_stock_only and not product.get("in_stock"):
            continue
        
        results.append(product)
    
    return results


async def _get_product_db(product_id: str) -> Optional[Dict]:
    """Get product by ID from MongoDB or mock."""
    if _product_service:
        return await _product_service.get_product_by_id(product_id)
    
    # Fallback to mock
    for product in MOCK_PRODUCTS:
        if product.get("id") == product_id:
            return product
    return None


# ==================== MCP Tool Definitions ====================

@tool(
    "search_products",
    "პროდუქტების ძებნა მონაცემთა ბაზაში. საძიებო სიტყვა და ფილტრები.",
    {"query": str, "max_price": float, "category": str, "in_stock_only": bool}
)
async def search_products(args: dict[str, Any]) -> dict[str, Any]:
    """Search for sports nutrition products."""
    query = args.get("query", "")
    max_price = args.get("max_price")
    category = args.get("category")
    in_stock_only = args.get("in_stock_only", False)
    
    results = await _search_products_db(query, category, max_price, in_stock_only)
    
    if results:
        text = f"მოიძებნა {len(results)} პროდუქტი:\n\n"
        for i, p in enumerate(results, 1):
            name = p.get("name_ka") or p.get("name", "Unknown")
            price = p.get("price", 0)
            currency = p.get("currency", "GEL")
            in_stock = p.get("in_stock", False)
            product_id = p.get("id", "")
            
            status = "✅ მარაგშია" if in_stock else "❌ ამოიწურა"
            text += f"{i}. **{name}**\n"
            text += f"   ფასი: {price} {currency} | {status}\n"
            text += f"   ID: {product_id}\n\n"
    else:
        text = f"სამწუხაროდ, '{query}' მოთხოვნით პროდუქტი ვერ მოიძებნა."
    
    return {"content": [{"type": "text", "text": text}]}


@tool(
    "get_product_details",
    "კონკრეტული პროდუქტის დეტალური ინფორმაცია ID-ით.",
    {"product_id": str}
)
async def get_product_details(args: dict[str, Any]) -> dict[str, Any]:
    """Get detailed product information."""
    product_id = args.get("product_id", "")
    
    product = await _get_product_db(product_id)
    
    if product:
        name = product.get("name_ka") or product.get("name", "Unknown")
        text = f"""## {name}
**ბრენდი:** {product.get('brand', 'N/A')}
**კატეგორია:** {product.get('category', 'N/A')}
**ფასი:** {product.get('price', 0)} {product.get('currency', 'GEL')}

### აღწერა
{product.get('description', 'აღწერა არ არის')}

**მარაგი:** {'✅ მარაგშია' if product.get('in_stock') else '❌ ამოიწურა'}
"""
        return {"content": [{"type": "text", "text": text}]}
    
    return {
        "content": [{"type": "text", "text": f"პროდუქტი ID '{product_id}' ვერ მოიძებნა."}],
        "is_error": True
    }


@tool(
    "check_availability",
    "პროდუქტის მარაგში არსებობის შემოწმება.",
    {"product_id": str}
)
async def check_availability(args: dict[str, Any]) -> dict[str, Any]:
    """Check product availability."""
    product_id = args.get("product_id", "")
    
    product = await _get_product_db(product_id)
    
    if product:
        name = product.get("name_ka") or product.get("name", "Unknown")
        if product.get("in_stock"):
            text = f"✅ **{name}** მარაგშია!\nხელმისაწვდომია: {product.get('stock_count', 'N/A')} ერთეული"
        else:
            text = f"❌ **{name}** ამჟამად არ არის მარაგში."
        
        return {"content": [{"type": "text", "text": text}]}
    
    return {
        "content": [{"type": "text", "text": f"პროდუქტი ID '{product_id}' ვერ მოიძებნა."}],
        "is_error": True
    }


# ==================== Create MCP Server ====================

scoop_server = create_sdk_mcp_server(
    name="scoop",
    version="1.0.0",
    tools=[
        search_products,
        get_product_details,
        check_availability,
    ]
)
