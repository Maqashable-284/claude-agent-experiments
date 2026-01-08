"""
Scoop AI Agent Service - Standard Anthropic SDK.

Uses the standard Anthropic SDK with tool_use for product search.
More reliable on Cloud Run than the Agent SDK.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any

from anthropic import AsyncAnthropic

from config import get_settings

logger = logging.getLogger("scoop_ai.agent")


# ==================== Tool Definitions ====================

TOOLS = [
    {
        "name": "search_products",
        "description": "პროდუქტების ძებნა მონაცემთა ბაზაში. გამოიყენეთ საძიებო სიტყვით.",
        "input_schema": {
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
    },
    {
        "name": "get_product_details",
        "description": "კონკრეტული პროდუქტის დეტალური ინფორმაცია ID-ით.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "პროდუქტის უნიკალური ID"
                }
            },
            "required": ["product_id"]
        }
    }
]


# ==================== Mock Products (Fallback) ====================

MOCK_PRODUCTS = [
    {
        "id": "prod_001",
        "name": "Optimum Nutrition Gold Standard Whey",
        "name_ka": "ოპტიმუმ ნიუტრიშენ გოლდ სტანდარტ ვეი",
        "category": "protein",
        "brand": "Optimum Nutrition",
        "price": 189.00,
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
        "in_stock": True,
        "description": "ენერგია და ფოკუსი ვარჯიშის წინ"
    }
]


# Global product service (set from main.py)
_product_service = None


def set_product_service(service):
    global _product_service
    _product_service = service


# ==================== Tool Execution ====================

async def execute_tool(name: str, input_data: Dict[str, Any]) -> str:
    """Execute a tool and return the result as a string."""
    
    if name == "search_products":
        return await search_products(input_data)
    elif name == "get_product_details":
        return await get_product_details(input_data)
    else:
        return f"Unknown tool: {name}"


async def search_products(args: Dict) -> str:
    """Search for products."""
    query = args.get("query", "").lower()
    category = args.get("category")
    max_price = args.get("max_price")
    
    # Try MongoDB first, fallback to mock
    if _product_service:
        try:
            results = await _product_service.search_products(
                query=query,
                category=category,
                max_price=max_price,
                limit=10
            )
        except Exception as e:
            logger.error(f"MongoDB search error: {e}")
            results = []
    else:
        # Use mock data
        results = []
        for p in MOCK_PRODUCTS:
            if query in p.get("name", "").lower() or query in p.get("name_ka", "").lower() or query in p.get("category", "").lower():
                if category and p.get("category") != category:
                    continue
                if max_price and p.get("price", 0) > max_price:
                    continue
                results.append(p)
    
    if results:
        text = f"მოიძებნა {len(results)} პროდუქტი:\n\n"
        for i, p in enumerate(results, 1):
            name = p.get("name_ka") or p.get("name", "Unknown")
            price = p.get("price", 0)
            status = "✅ მარაგშია" if p.get("in_stock") else "❌ ამოიწურა"
            text += f"{i}. **{name}**\n   ფასი: {price} ₾ | {status}\n   ID: {p.get('id', 'N/A')}\n\n"
        return text
    else:
        return f"სამწუხაროდ, '{query}' მოთხოვნით პროდუქტი ვერ მოიძებნა."


async def get_product_details(args: Dict) -> str:
    """Get product details by ID."""
    product_id = args.get("product_id", "")
    
    # Try MongoDB first
    product = None
    if _product_service:
        try:
            product = await _product_service.get_product_by_id(product_id)
        except:
            pass
    
    # Fallback to mock
    if not product:
        for p in MOCK_PRODUCTS:
            if p.get("id") == product_id:
                product = p
                break
    
    if product:
        name = product.get("name_ka") or product.get("name", "Unknown")
        return f"""## {name}
**ბრენდი:** {product.get('brand', 'N/A')}
**კატეგორია:** {product.get('category', 'N/A')}
**ფასი:** {product.get('price', 0)} ₾
**მარაგი:** {'✅ მარაგშია' if product.get('in_stock') else '❌ ამოიწურა'}

{product.get('description', '')}"""
    
    return f"პროდუქტი ID '{product_id}' ვერ მოიძებნა."


# ==================== Agent Class ====================

class ScoopAgent:
    """
    Scoop AI Agent using standard Anthropic SDK.
    
    Implements agentic loop with tool_use.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", self.settings.anthropic_api_key)
        )
        self.model = os.getenv("DEFAULT_MODEL", self.settings.default_model)
        self._sessions: Dict[str, List[Dict]] = {}  # user_id -> messages
    
    def _get_messages(self, user_id: str) -> List[Dict]:
        """Get or create message history for user."""
        if user_id not in self._sessions:
            self._sessions[user_id] = []
        return self._sessions[user_id]
    
    async def chat(self, user_id: str, message: str) -> str:
        """
        Process a chat message with agentic tool loop.
        """
        messages = self._get_messages(user_id)
        messages.append({"role": "user", "content": message})
        
        # Agentic loop
        max_iterations = 5
        
        for _ in range(max_iterations):
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.settings.system_prompt,
                tools=TOOLS,
                messages=messages
            )
            
            # Check if we need to execute tools
            if response.stop_reason == "tool_use":
                # Extract tool calls
                assistant_content = response.content
                messages.append({"role": "assistant", "content": assistant_content})
                
                # Execute each tool
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        logger.info(f"Executing tool: {block.name}")
                        result = await execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })
                
                messages.append({"role": "user", "content": tool_results})
            else:
                # No more tools, extract final text
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text
                
                messages.append({"role": "assistant", "content": response.content})
                
                # Keep only last 20 messages to prevent context overflow
                if len(messages) > 20:
                    self._sessions[user_id] = messages[-20:]
                
                return final_text
        
        return "მოხდა შეცდომა. გთხოვთ, სცადოთ თავიდან."
    
    async def clear_session(self, user_id: str) -> bool:
        """Clear user's conversation history."""
        if user_id in self._sessions:
            del self._sessions[user_id]
            return True
        return False
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active user sessions."""
        return list(self._sessions.keys())


# ==================== Singleton ====================

_agent_instance: Optional[ScoopAgent] = None


def get_agent() -> ScoopAgent:
    """Get or create the global agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ScoopAgent()
    return _agent_instance


async def shutdown_agent():
    """Shutdown the agent."""
    global _agent_instance
    _agent_instance = None
