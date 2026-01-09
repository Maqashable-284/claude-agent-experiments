"""
Scoop AI Tools Definition using Claude Agent SDK.
Wraps the ProductService in an MCP Server.
"""

import logging
from typing import Any, Dict, Optional

from claude_agent_sdk import tool, create_sdk_mcp_server

from app.product_service import ProductService

logger = logging.getLogger("scoop_ai.tools")


# Global reference to product service (injected from main)
_service: Optional[ProductService] = None


def set_tool_service(service: ProductService):
    """Set the product service for tools to use."""
    global _service
    _service = service
    logger.info("Product service injected into tools")


# ==================== Mock Products (Fallback) ====================

MOCK_PRODUCTS = [
    {
        "id": "prod_001",
        "name": "Optimum Nutrition Gold Standard Whey",
        "name_ka": "ოპტიმუმ ნიუტრიშენ გოლდ სტანდარტ ვეი",
        "category": "protein",
        "brand": "Optimum Nutrition",
        "price": 189.00,
        "servings": 74,
        "in_stock": True,
        "description": "პრემიუმ ვეი პროტეინი - 24გ პროტეინი პორციაზე"
    },
    {
        "id": "prod_002",
        "name": "MuscleTech Nitro-Tech",
        "name_ka": "მასლთექ ნიტრო-თექ",
        "category": "protein",
        "brand": "MuscleTech",
        "price": 159.00,
        "servings": 40,
        "in_stock": True,
        "description": "სამეცნიერო ფორმულა - 30გ პროტეინი + კრეატინი"
    },
    {
        "id": "prod_003",
        "name": "Optimum Nutrition Creatine",
        "name_ka": "ოპტიმუმ ნიუტრიშენ კრეატინი",
        "category": "creatine",
        "brand": "Optimum Nutrition",
        "price": 79.00,
        "servings": 120,
        "in_stock": True,
        "description": "სუფთა კრეატინ მონოჰიდრატი"
    },
    {
        "id": "prod_004",
        "name": "BSN NO-Xplode Pre-Workout",
        "name_ka": "BSN ნო-ექსპლოუდ პრე-ვორქაუთი",
        "category": "pre_workout",
        "brand": "BSN",
        "price": 129.00,
        "servings": 30,
        "in_stock": True,
        "description": "ენერგია და ფოკუსი ვარჯიშის წინ"
    }
]


# ==================== Tool Implementations ====================

@tool(
    name="search_products",
    description="პროდუქტების ძებნა მონაცემთა ბაზაში. გამოიყენეთ საძიებო სიტყვით. Search for sports nutrition products in the database.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "საძიებო სიტყვა (პროდუქტის სახელი, ბრენდი, კატეგორია)"
            },
            "category": {
                "type": "string",
                "description": "კატეგორია (protein, creatine, bcaa, pre_workout)"
            },
            "max_price": {
                "type": "number",
                "description": "მაქსიმალური ფასი ლარებში"
            }
        },
        "required": ["query"]
    }
)
async def search_products_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Search products wrapper for MCP."""
    query = args.get("query", "")
    category = args.get("category")
    max_price = args.get("max_price")

    # Handle empty strings as None
    if category == "":
        category = None

    logger.info(f"Tool Call: search_products(query={query}, category={category}, max_price={max_price})")

    # Try MongoDB first, fallback to mock
    results = []

    if _service:
        try:
            results = await _service.search_products(
                query=query,
                category=category,
                max_price=max_price,
                limit=10
            )
        except Exception as e:
            logger.error(f"MongoDB search error: {e}")
            results = []

    # Fallback to mock data if no results from DB
    if not results:
        query_lower = query.lower()
        for p in MOCK_PRODUCTS:
            if (query_lower in p.get("name", "").lower() or
                query_lower in p.get("name_ka", "").lower() or
                query_lower in p.get("category", "").lower() or
                query_lower in p.get("brand", "").lower()):
                if category and p.get("category") != category:
                    continue
                if max_price and p.get("price", 0) > max_price:
                    continue
                results.append(p)

    if results:
        text = f"მოიძებნა {len(results)} პროდუქტი:\n\n"
        for i, p in enumerate(results, 1):
            name = p.get("name") or p.get("name_ka", "Unknown")
            price = p.get("price", 0)
            brand = p.get("brand", "")
            servings = p.get("servings", "")
            product_url = p.get("product_url") or p.get("url") or p.get("link", "")
            
            text += f"{i}. **{name}**\n"
            text += f"   💰 ფასი: {price} ₾"
            if brand:
                text += f" | 🏷️ {brand}"
            if servings:
                text += f" | 📦 {servings} პორცია"
            text += "\n"
            if product_url:
                text += f"   🔗 [პროდუქტის ნახვა]({product_url})\n"
            text += "\n"

        return {"content": [{"type": "text", "text": text}]}
    else:
        return {"content": [{"type": "text", "text": f"სამწუხაროდ, '{query}' მოთხოვნით პროდუქტი ვერ მოიძებნა."}]}


@tool(
    name="get_product_details",
    description="კონკრეტული პროდუქტის დეტალური ინფორმაცია ID-ით. Get detailed information about a specific product by its ID.",
    input_schema={
        "type": "object",
        "properties": {
            "product_id": {
                "type": "string",
                "description": "პროდუქტის უნიკალური ID"
            }
        },
        "required": ["product_id"]
    }
)
async def get_product_details_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get product details wrapper for MCP."""
    product_id = args.get("product_id", "")

    logger.info(f"Tool Call: get_product_details(product_id={product_id})")

    product = None

    # Try MongoDB first
    if _service:
        try:
            product = await _service.get_product_by_id(product_id)
        except Exception as e:
            logger.error(f"Get product error: {e}")

    # Fallback to mock
    if not product:
        for p in MOCK_PRODUCTS:
            if p.get("id") == product_id:
                product = p
                break

    if product:
        name = product.get("name_ka") or product.get("name", "Unknown")
        product_url = product.get("product_url") or product.get("url") or product.get("link", "")
        
        text = f"""## {name}

**ბრენდი:** {product.get('brand', 'N/A')}
**კატეგორია:** {product.get('category', 'N/A')}
**ფასი:** {product.get('price', 0)} ₾
**პორციები:** {product.get('servings', 'N/A')}
**მარაგი:** {'✅ მარაგშია' if product.get('in_stock') else '❌ ამოიწურა'}

{product.get('description', '')}"""

        if product_url:
            text += f"\n\n🔗 **[შეიძინეთ ოფიციალურ საიტზე]({product_url})**"

        return {"content": [{"type": "text", "text": text}]}
    else:
        return {"content": [{"type": "text", "text": f"პროდუქტი ID '{product_id}' ვერ მოიძებნა."}]}


# ==================== MCP Server Factory ====================

def create_scoop_mcp_server():
    """Creates the in-process MCP server instance."""
    return create_sdk_mcp_server(
        name="scoop-products",
        tools=[search_products_tool, get_product_details_tool]
    )
