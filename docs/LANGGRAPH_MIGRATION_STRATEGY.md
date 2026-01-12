# LangGraph Migration Strategy for Scoop AI

> **Version:** 1.0
> **Date:** January 2026
> **Current Architecture:** Claude Agent SDK v4.0
> **Target Architecture:** LangGraph + LangChain

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Analysis](#2-current-architecture-analysis)
3. [Proposed LangGraph Structure](#3-proposed-langgraph-project-structure)
4. [Architecture Comparison](#4-architecture-comparison)
5. [State Schema Design](#5-state-schema-design)
6. [Implementation Examples](#6-implementation-examples)
7. [Infrastructure: MongoDB vs LangSmith](#7-infrastructure-mongodb-vs-langsmith)
8. [Migration Risks & Mitigations](#8-migration-risks--mitigations)
9. [Decision Framework](#9-decision-framework)
10. [Questions for Stakeholders](#10-questions-for-stakeholders)

---

## 1. Executive Summary

### Current State

Scoop AI is a Georgian-language sports nutrition chatbot built on the **Claude Agent SDK** with:
- Automatic tool orchestration (ReAct pattern)
- In-process MCP server with 3 tools
- In-memory session management (30-min TTL)
- Security through hooks pattern
- MongoDB for product data

### Migration Recommendation

| Scenario | Recommendation |
|----------|----------------|
| Current functionality (Q&A chatbot) | **STAY with Claude SDK** |
| Adding checkout flows, confirmations | **MIGRATE to LangGraph** |
| Need persistent conversations across restarts | **MIGRATE to LangGraph** |
| Complex branching workflows | **MIGRATE to LangGraph** |

### Key Finding

**The current linear ReAct loop does not require LangGraph.** Migration should only proceed if:
1. Human-in-the-loop workflows are planned (cart confirmation, checkout)
2. Persistent state across Cloud Run restarts is required
3. Complex branching logic beyond intent routing is needed

---

## 2. Current Architecture Analysis

### Component Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     CURRENT ARCHITECTURE                        │
│                    (Claude Agent SDK v4.0)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌─────────────────┐     ┌──────────────┐  │
│  │   FastAPI   │────▶│   ScoopAgent    │────▶│  Claude API  │  │
│  │  (main.py)  │     │   (agent.py)    │     │  (Sonnet 4)  │  │
│  └─────────────┘     └─────────────────┘     └──────────────┘  │
│         │                    │                      │          │
│         │                    ▼                      │          │
│         │           ┌─────────────────┐             │          │
│         │           │   MCP Server    │◀────────────┘          │
│         │           │   (tools.py)    │                        │
│         │           └─────────────────┘                        │
│         │                    │                                 │
│         │                    ▼                                 │
│         │           ┌─────────────────┐                        │
│         │           │    MongoDB      │                        │
│         │           │  (products)     │                        │
│         │           └─────────────────┘                        │
│         │                                                      │
│         ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  SECURITY LAYER                         │   │
│  │  ┌──────────────┐ ┌────────────┐ ┌───────────────────┐  │   │
│  │  │UserPrompt    │ │PreToolUse  │ │PostToolUse        │  │   │
│  │  │Submit Hook   │ │Hook        │ │Hook               │  │   │
│  │  │(validation)  │ │(whitelist) │ │(logging)          │  │   │
│  │  └──────────────┘ └────────────┘ └───────────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `main.py` | FastAPI server, rate limiting, endpoints | ~400 |
| `app/agent.py` | ScoopAgent class, session management | ~180 |
| `app/tools.py` | MCP server, 3 product tools | ~310 |
| `app/hooks.py` | Security validation hooks | ~210 |
| `config.py` | Settings, 235-line Georgian prompt | ~300 |
| `app/database.py` | MongoDB async connection | ~80 |
| `app/product_service.py` | Product queries, Georgian translation | ~150 |

### Current Flow

```
User Message
     │
     ▼
┌─────────────────┐
│ UserPromptSubmit│──▶ BLOCK if violation
│     Hook        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Claude SDK     │
│  Auto-Loop      │──▶ Decides tools automatically
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PreToolUse     │──▶ BLOCK if unauthorized tool
│     Hook        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Tool Execution │
│  (MCP Server)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostToolUse    │──▶ Logging only
│     Hook        │
└────────┬────────┘
         │
         ▼
    Response
```

**Key Observation:** This is a **linear ReAct pattern**. The SDK handles the agentic loop internally. There are no explicit cycles, branches, or human-in-the-loop interrupts.

---

## 3. Proposed LangGraph Project Structure

```
scoop-ai-langgraph/
├── main.py                          # FastAPI entrypoint (minimal changes)
├── config.py                        # Settings (unchanged)
├── requirements.txt                 # + langgraph, langchain-anthropic
├── Dockerfile
│
├── app/
│   ├── __init__.py
│   │
│   ├── graph/                       # 🔵 LangGraph Core
│   │   ├── __init__.py
│   │   ├── builder.py               # Graph compilation: create_graph()
│   │   ├── state.py                 # StateSchema definition (TypedDict)
│   │   └── checkpointer.py          # MongoDB-backed checkpointer
│   │
│   ├── nodes/                       # 🟢 Graph Nodes (Pure Functions)
│   │   ├── __init__.py
│   │   ├── intent_classifier.py     # classify_intent(state) → state
│   │   ├── product_search.py        # search_products(state) → state
│   │   ├── recommendation.py        # generate_recommendation(state) → state
│   │   ├── explanation.py           # generate_explanation(state) → state
│   │   └── guardrails.py            # security_check(state) → state
│   │
│   ├── edges/                       # 🟠 Conditional Routing
│   │   ├── __init__.py
│   │   └── router.py                # route_by_intent(state) → str
│   │
│   ├── tools/                       # 🔧 LangChain Tools
│   │   ├── __init__.py
│   │   ├── mongo_search.py          # VectorStore search tool
│   │   └── product_api.py           # Product catalog tool
│   │
│   ├── memory/                      # 💾 State Persistence
│   │   ├── __init__.py
│   │   ├── mongo_saver.py           # MongoDBSaver for checkpoints
│   │   └── short_term.py            # In-memory conversation buffer
│   │
│   └── services/                    # 🛠️ Business Logic (unchanged)
│       ├── __init__.py
│       ├── database.py              # Keep existing
│       └── product_service.py       # Keep existing
│
└── tests/
    ├── test_graph.py
    └── test_nodes.py
```

---

## 4. Architecture Comparison

### Feature Matrix

| Feature | Claude SDK (Current) | LangGraph | Winner |
|---------|---------------------|-----------|--------|
| **Setup Complexity** | Low (SDK handles loop) | High (manual graph) | Claude SDK |
| **Tool Orchestration** | Automatic (ReAct) | Manual node definition | Claude SDK |
| **Cyclic Workflows** | Not supported | Native support | LangGraph |
| **Human-in-the-Loop** | Not supported | `interrupt_before` | LangGraph |
| **State Persistence** | In-memory only | MongoDB checkpointer | LangGraph |
| **Branching Logic** | Via prompt engineering | Conditional edges | LangGraph |
| **Debugging** | Hooks + logging | LangSmith tracing | LangGraph |
| **Cost per Message** | Single LLM call | Multiple node calls | Claude SDK |
| **Georgian Support** | System prompt | Per-node prompts | Equal |

### When to Use Each

```
                    ┌─────────────────────────────────────┐
                    │         DECISION MATRIX             │
                    └─────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │   Do you need cyclic flows?   │
                    │   (checkout, confirmations)   │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────YES─────┴─────NO────────┐
                    │                               │
                    ▼                               ▼
            ┌───────────────┐               ┌───────────────┐
            │   LangGraph   │               │  Claude SDK   │
            │   Required    │               │  Sufficient   │
            └───────────────┘               └───────────────┘
```

### Cost Implications

| Metric | Claude SDK | LangGraph |
|--------|-----------|-----------|
| LLM Calls per Request | 1-2 (auto-managed) | 3-5 (per node) |
| Latency (p50) | ~2-3s | ~4-6s |
| Latency (p99) | ~5-8s | ~10-15s |
| Monthly Cost (10K conv/day) | ~$500-800 | ~$1,200-2,000 |

**Note:** LangGraph adds latency because each node is a separate LLM call. The Claude SDK batches tool calls efficiently.

---

## 5. State Schema Design

### Proposed State Definition

```python
# app/graph/state.py

from typing import TypedDict, List, Optional, Literal, Annotated
from langgraph.graph import MessagesState
from langchain_core.messages import BaseMessage
import operator

class ProductResult(TypedDict):
    """Individual product from search."""
    id: str
    name: str
    brand: str
    price: float
    category: str
    url: str

class QuickReply(TypedDict):
    """Quick reply button."""
    title: str
    payload: str

class ScoopState(MessagesState):
    """
    Scoop AI Graph State Schema.

    Inherits from MessagesState to get automatic message handling.
    All fields are optional except messages (from parent).
    """

    # ─── Identity ────────────────────────────────────────────
    user_id: str
    session_id: str

    # ─── Intent Classification ───────────────────────────────
    intent: Optional[Literal[
        "RECOMMENDATION",    # User wants product suggestions
        "EXPLANATION",       # User wants to learn about a product
        "COMPARISON",        # User comparing products
        "GREETING",          # Hello, hi, გამარჯობა
        "FAREWELL",          # Bye, ნახვამდის
        "OFF_TOPIC",         # Non-nutrition topics
        "SECURITY_VIOLATION" # Blocked content
    ]]

    # ─── Search Context ──────────────────────────────────────
    search_query: Optional[str]           # Extracted query in Georgian
    search_query_en: Optional[str]        # Translated to English
    category_filter: Optional[str]        # Optional category
    price_max: Optional[float]            # Optional price ceiling

    # ─── Product Context ─────────────────────────────────────
    product_results: Annotated[List[ProductResult], operator.add]
    selected_product_id: Optional[str]
    product_details: Optional[dict]

    # ─── Response Building ───────────────────────────────────
    response_text_geo: str                # Georgian response
    quick_replies: List[QuickReply]

    # ─── Conversation Metadata ───────────────────────────────
    turn_count: int
    last_tool_used: Optional[str]
    security_flags: List[str]             # Any security violations

    # ─── Checkpointing ───────────────────────────────────────
    checkpoint_ns: Optional[str]          # Namespace for multi-tenant

# Default state factory
def create_initial_state(user_id: str, session_id: str) -> ScoopState:
    """Create initial state for new conversation."""
    return ScoopState(
        messages=[],
        user_id=user_id,
        session_id=session_id,
        intent=None,
        search_query=None,
        search_query_en=None,
        category_filter=None,
        price_max=None,
        product_results=[],
        selected_product_id=None,
        product_details=None,
        response_text_geo="",
        quick_replies=[],
        turn_count=0,
        last_tool_used=None,
        security_flags=[],
        checkpoint_ns=f"scoop:{user_id}"
    )
```

---

## 6. Implementation Examples

### 6.1 Graph Builder

```python
# app/graph/builder.py

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from langchain_anthropic import ChatAnthropic

from app.graph.state import ScoopState
from app.nodes.guardrails import security_check
from app.nodes.intent_classifier import classify_intent
from app.nodes.product_search import search_products
from app.nodes.recommendation import generate_recommendation
from app.nodes.explanation import generate_explanation
from app.edges.router import route_by_intent, route_after_search
from config import settings

def create_graph(checkpointer: MongoDBSaver | None = None):
    """
    Build the Scoop AI conversation graph.

    Flow:
    1. Security Check (guardrails)
    2. Intent Classification
    3. Route to appropriate handler
    4. Generate response
    """

    # Initialize LLM
    llm = ChatAnthropic(
        model=settings.DEFAULT_MODEL,
        temperature=0.7,
        max_tokens=1024
    )

    # Create graph with state schema
    graph = StateGraph(ScoopState)

    # ─── Add Nodes ───────────────────────────────────────────
    graph.add_node("security_check", security_check)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("search_products", search_products)
    graph.add_node("generate_recommendation", generate_recommendation)
    graph.add_node("generate_explanation", generate_explanation)
    graph.add_node("handle_greeting", handle_greeting)
    graph.add_node("handle_off_topic", handle_off_topic)

    # ─── Add Edges ───────────────────────────────────────────

    # Entry point: always start with security
    graph.add_edge(START, "security_check")

    # After security: route based on check result
    graph.add_conditional_edges(
        "security_check",
        lambda state: "blocked" if state.get("security_flags") else "continue",
        {
            "blocked": END,  # Short-circuit on security violation
            "continue": "classify_intent"
        }
    )

    # After classification: route by intent
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "RECOMMENDATION": "search_products",
            "EXPLANATION": "search_products",
            "GREETING": "handle_greeting",
            "OFF_TOPIC": "handle_off_topic",
            "FAREWELL": END
        }
    )

    # After search: route to appropriate generator
    graph.add_conditional_edges(
        "search_products",
        route_after_search,
        {
            "recommendation": "generate_recommendation",
            "explanation": "generate_explanation"
        }
    )

    # Terminal nodes
    graph.add_edge("generate_recommendation", END)
    graph.add_edge("generate_explanation", END)
    graph.add_edge("handle_greeting", END)
    graph.add_edge("handle_off_topic", END)

    # ─── Compile ─────────────────────────────────────────────
    return graph.compile(checkpointer=checkpointer)


def handle_greeting(state: ScoopState) -> dict:
    """Handle greeting messages."""
    return {
        "response_text_geo": "გამარჯობა! 👋 მე ვარ Scoop AI - თქვენი პერსონალური კონსულტანტი სპორტულ კვებაზე. რით შემიძლია დაგეხმაროთ?",
        "quick_replies": [
            {"title": "🏋️ პროტეინები", "payload": "მაჩვენე პროტეინები"},
            {"title": "⚡ კრეატინი", "payload": "კრეატინის შესახებ"},
            {"title": "📦 ყველა პროდუქტი", "payload": "მაჩვენე ყველა პროდუქტი"}
        ]
    }


def handle_off_topic(state: ScoopState) -> dict:
    """Handle off-topic messages."""
    return {
        "response_text_geo": "ბოდიში, მაგრამ მე მხოლოდ სპორტული კვების პროდუქტებზე შემიძლია დაგეხმაროთ. რა გაინტერესებთ კვებასთან დაკავშირებით?",
        "quick_replies": [
            {"title": "🔍 პროდუქტის ძებნა", "payload": "მინდა ვიპოვო პროდუქტი"},
            {"title": "📋 კატეგორიები", "payload": "მაჩვენე კატეგორიები"}
        ]
    }
```

### 6.2 Security Node (Guardrails)

```python
# app/nodes/guardrails.py

from typing import List
import re
from app.graph.state import ScoopState

# Blocked patterns (from current hooks.py)
BLOCKED_KEYWORDS = [
    "steroid", "anabolic", "testosterone", "hgh", "sarms",
    "hacking", "injection", "overdose", "suicide"
]

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous",
    r"system\s*prompt",
    r"jailbreak",
    r"act\s+as\s+(if\s+)?you",
    r"pretend\s+(you\s+)?(are|were)",
    # Georgian patterns
    r"დაივიწყე\s+ყველაფერი",
    r"უგულებელყავი\s+ინსტრუქციები"
]

def security_check(state: ScoopState) -> dict:
    """
    Security guardrail node.

    Checks for:
    1. Blocked keywords (drugs, hacking, etc.)
    2. Prompt injection attempts
    3. Message length limits

    Returns updated state with security_flags if violation detected.
    """
    # Get last user message
    messages = state.get("messages", [])
    if not messages:
        return {}

    last_message = messages[-1]
    if not hasattr(last_message, "content"):
        return {}

    content = last_message.content.lower()
    flags: List[str] = []

    # Check message length
    if len(content) > 5000:
        flags.append("MESSAGE_TOO_LONG")

    # Check blocked keywords
    for keyword in BLOCKED_KEYWORDS:
        if keyword in content:
            flags.append(f"BLOCKED_KEYWORD:{keyword}")

    # Check injection patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            flags.append(f"INJECTION_ATTEMPT:{pattern[:20]}")

    if flags:
        return {
            "security_flags": flags,
            "response_text_geo": "ბოდიში, ამ თხოვნას ვერ შევასრულებ. რით შემიძლია დაგეხმაროთ სპორტულ კვებასთან დაკავშირებით?",
            "quick_replies": [
                {"title": "🏋️ პროტეინები", "payload": "მაჩვენე პროტეინები"},
                {"title": "⚡ კრეატინი", "payload": "კრეატინის შესახებ"}
            ]
        }

    return {"security_flags": []}
```

### 6.3 Intent Classification Node

```python
# app/nodes/intent_classifier.py

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from app.graph.state import ScoopState
from config import settings

INTENT_PROMPT = """You are an intent classifier for a Georgian sports nutrition chatbot.

Classify the user's message into ONE of these intents:
- RECOMMENDATION: User wants product suggestions (e.g., "რა პროტეინს მირჩევთ?")
- EXPLANATION: User wants to learn about a specific product (e.g., "რა არის კრეატინი?")
- COMPARISON: User comparing products (e.g., "რა განსხვავებაა ISO და Whey-ს შორის?")
- GREETING: Hello, hi, გამარჯობა
- FAREWELL: Bye, ნახვამდის
- OFF_TOPIC: Non-nutrition topics

User message: {message}

Respond with ONLY the intent label, nothing else."""

async def classify_intent(state: ScoopState) -> dict:
    """
    Classify user intent using LLM.

    Returns dict with 'intent' field.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"intent": "GREETING"}

    last_message = messages[-1].content

    llm = ChatAnthropic(
        model=settings.DEFAULT_MODEL,
        temperature=0,
        max_tokens=50
    )

    prompt = ChatPromptTemplate.from_template(INTENT_PROMPT)
    chain = prompt | llm

    result = await chain.ainvoke({"message": last_message})
    intent = result.content.strip().upper()

    # Validate intent
    valid_intents = ["RECOMMENDATION", "EXPLANATION", "COMPARISON",
                     "GREETING", "FAREWELL", "OFF_TOPIC"]
    if intent not in valid_intents:
        intent = "OFF_TOPIC"

    return {"intent": intent, "turn_count": state.get("turn_count", 0) + 1}
```

### 6.4 Router Functions

```python
# app/edges/router.py

from app.graph.state import ScoopState

def route_by_intent(state: ScoopState) -> str:
    """
    Route to appropriate node based on classified intent.

    Returns node name as string.
    """
    intent = state.get("intent", "OFF_TOPIC")

    routing = {
        "RECOMMENDATION": "search_products",
        "EXPLANATION": "search_products",
        "COMPARISON": "search_products",
        "GREETING": "handle_greeting",
        "FAREWELL": "__end__",
        "OFF_TOPIC": "handle_off_topic",
        "SECURITY_VIOLATION": "__end__"
    }

    return routing.get(intent, "handle_off_topic")


def route_after_search(state: ScoopState) -> str:
    """
    Route after product search based on original intent.
    """
    intent = state.get("intent")

    if intent in ["RECOMMENDATION", "COMPARISON"]:
        return "recommendation"
    elif intent == "EXPLANATION":
        return "explanation"
    else:
        return "recommendation"  # Default
```

### 6.5 MongoDB Checkpointer

```python
# app/graph/checkpointer.py

from langgraph.checkpoint.mongodb import MongoDBSaver
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

_checkpointer: MongoDBSaver | None = None

async def get_checkpointer() -> MongoDBSaver:
    """
    Get or create MongoDB checkpointer for graph state persistence.

    Uses singleton pattern to avoid multiple connections.
    """
    global _checkpointer

    if _checkpointer is None:
        client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            maxPoolSize=10,
            minPoolSize=1
        )

        _checkpointer = MongoDBSaver(
            client=client,
            db_name=settings.MONGODB_DATABASE,
            collection_name="langgraph_checkpoints"
        )

    return _checkpointer


async def clear_checkpoints(user_id: str) -> int:
    """
    Clear all checkpoints for a user.

    Returns number of deleted checkpoints.
    """
    checkpointer = await get_checkpointer()
    # Implementation depends on MongoDBSaver API
    # This is a placeholder
    return 0
```

### 6.6 LangChain Tool Conversion

```python
# app/tools/mongo_search.py

from typing import Optional, List
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from app.product_service import ProductService

class SearchProductsInput(BaseModel):
    """Input for product search."""
    query: str = Field(description="Search query in Georgian or English")
    category: Optional[str] = Field(default=None, description="Category filter")
    max_price: Optional[float] = Field(default=None, description="Maximum price")

@tool("search_products", args_schema=SearchProductsInput)
async def search_products_tool(
    query: str,
    category: Optional[str] = None,
    max_price: Optional[float] = None
) -> List[dict]:
    """
    Search for sports nutrition products.

    Args:
        query: Search query (supports Georgian)
        category: Optional category filter
        max_price: Optional maximum price

    Returns:
        List of matching products with id, name, price, url
    """
    service = ProductService()

    results = await service.search_products(
        query=query,
        category=category,
        max_price=max_price,
        limit=10
    )

    return [
        {
            "id": str(p.get("_id", "")),
            "name": p.get("name", ""),
            "brand": p.get("brand", ""),
            "price": p.get("price", 0),
            "category": p.get("category", ""),
            "url": p.get("product_url", "")
        }
        for p in results
    ]


class GetProductInput(BaseModel):
    """Input for getting product details."""
    product_id: str = Field(description="Product ID")

@tool("get_product_details", args_schema=GetProductInput)
async def get_product_details_tool(product_id: str) -> dict:
    """
    Get detailed information about a specific product.

    Args:
        product_id: The product's unique identifier

    Returns:
        Full product details including description, ingredients, etc.
    """
    service = ProductService()
    product = await service.get_product_by_id(product_id)

    if not product:
        return {"error": "Product not found"}

    return {
        "id": str(product.get("_id", "")),
        "name": product.get("name", ""),
        "brand": product.get("brand", ""),
        "price": product.get("price", 0),
        "category": product.get("category", ""),
        "description": product.get("description", ""),
        "servings": product.get("servings", 0),
        "in_stock": product.get("in_stock", True),
        "url": product.get("product_url", "")
    }
```

### 6.7 Updated FastAPI Integration

```python
# main.py (partial - integration with LangGraph)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.graph.builder import create_graph
from app.graph.checkpointer import get_checkpointer
from app.graph.state import create_initial_state
from langchain_core.messages import HumanMessage

app = FastAPI(title="Scoop AI LangGraph")

# Graph instance (created at startup)
_graph = None

@app.on_event("startup")
async def startup():
    global _graph
    checkpointer = await get_checkpointer()
    _graph = create_graph(checkpointer=checkpointer)

class ChatRequest(BaseModel):
    user_id: str
    message: str
    conversation_id: str | None = None

class ChatResponse(BaseModel):
    response_text_geo: str
    quick_replies: list
    success: bool
    user_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat message through LangGraph."""

    # Create thread config for checkpointing
    thread_id = request.conversation_id or f"{request.user_id}:{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    # Build input state
    input_state = {
        "messages": [HumanMessage(content=request.message)],
        "user_id": request.user_id,
        "session_id": thread_id
    }

    try:
        # Run graph
        result = await _graph.ainvoke(input_state, config=config)

        return ChatResponse(
            response_text_geo=result.get("response_text_geo", ""),
            quick_replies=result.get("quick_replies", []),
            success=True,
            user_id=request.user_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 7. Infrastructure: MongoDB vs LangSmith

### Critical Clarification

| Component | MongoDB | LangSmith |
|-----------|---------|-----------|
| **Purpose** | Persistent Data Store | Observability & Tracing |
| **What it stores** | Products, users, checkpoints | Traces, evals, prompts |
| **Latency** | ~1-5ms (document fetch) | ~50-200ms (async upload) |
| **Cost Model** | Storage-based | Per-trace pricing |
| **Replaces** | Nothing - it's your database | Logging frameworks |

**LangSmith does NOT replace MongoDB.**

### Hybrid Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRODUCTION DATA                            │
│                       (MongoDB Atlas)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  Products   │  │   Users     │  │  LangGraph Checkpoints  │ │
│  │  (catalog)  │  │  (profiles) │  │  (conversation state)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Checkpointer reads/writes
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LangGraph Runtime                           │
│    graph.compile(checkpointer=MongoDBSaver(mongo_client))       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Async trace callbacks
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               OBSERVABILITY (LangSmith - Optional)              │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │  Traces  │  │   Datasets   │  │   Prompt Version Control   │ │
│  │  (debug) │  │   (evals)    │  │   (A/B testing)            │ │
│  └──────────┘  └──────────────┘  └────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Use Case Matrix

| Use Case | MongoDB | LangSmith |
|----------|---------|-----------|
| Product catalog | ✅ Required | ❌ |
| User profiles | ✅ Required | ❌ |
| Conversation history | ✅ Canonical | ✅ Traces for debugging |
| Shopping cart state | ✅ Required | ❌ |
| LLM call traces | ❌ | ✅ |
| Prompt A/B testing | ❌ | ✅ |
| Eval datasets | ❌ | ✅ |
| Production logging | ✅ Structured logs | ✅ Sampled traces |

### Cost Projection

| Scale | LangSmith Cost | Recommendation |
|-------|----------------|----------------|
| 1K conv/day | ~$50/month | Full tracing |
| 10K conv/day | ~$500/month | 20% sampling |
| 100K conv/day | ~$5,000/month | 5% sampling + structured logs |

**Recommendation:** Start with 10-20% trace sampling in production. Use structured logging (to MongoDB or CloudWatch) for the rest.

---

## 8. Migration Risks & Mitigations

### Risk Matrix

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| Increased latency | High | High | Cache intent classification, optimize node count |
| Higher LLM costs | Medium | High | Use Claude Haiku for classification, batch where possible |
| Complexity overhead | Medium | Medium | Keep node count minimal, document thoroughly |
| Georgian support regression | High | Low | Port existing prompts directly, comprehensive testing |
| Session state bugs | Medium | Medium | Extensive checkpoint testing, fallback to in-memory |
| Tool compatibility | Low | Medium | Maintain dual interface during migration |

### Migration Phases

```
Phase 1: Parallel Development (2-3 weeks)
├── Set up LangGraph project structure
├── Implement core nodes (guardrails, intent, search)
├── Port existing tools to LangChain format
└── Set up MongoDBSaver checkpointer

Phase 2: Feature Parity (2-3 weeks)
├── Port all Georgian prompts
├── Implement all response generators
├── Set up LangSmith integration
└── Performance testing

Phase 3: Gradual Rollout (1-2 weeks)
├── A/B test 10% traffic to LangGraph
├── Monitor latency and error rates
├── Gradual increase to 100%
└── Deprecate Claude SDK implementation

Phase 4: Advanced Features (ongoing)
├── Human-in-the-loop checkout
├── Multi-step guided workflows
└── Persistent cross-session memory
```

---

## 9. Decision Framework

### Should You Migrate?

Answer these questions:

1. **Do you need cyclic workflows?**
   - Cart confirmation flows
   - Multi-step checkout
   - "Are you sure?" interrupts

2. **Do you need persistent state?**
   - Conversations surviving Cloud Run restarts
   - Cross-device session continuity
   - Long-running multi-session flows

3. **Do you need complex branching?**
   - Beyond simple intent routing
   - Conditional sub-graphs
   - Dynamic workflow modification

4. **Is observability critical?**
   - LangSmith tracing integration
   - Prompt versioning
   - A/B testing infrastructure

### Decision Matrix

| Your Needs | Recommendation |
|------------|----------------|
| 0-1 Yes answers | Stay with Claude SDK |
| 2-3 Yes answers | Consider LangGraph |
| 4 Yes answers | Migrate to LangGraph |

### Current Scoop AI Assessment

| Question | Current State | Answer |
|----------|---------------|--------|
| Cyclic workflows needed? | No checkout flows | **No** |
| Persistent state needed? | 30-min TTL acceptable | **No** |
| Complex branching needed? | Intent routing via prompt | **No** |
| Observability critical? | Basic logging sufficient | **No** |

**Current Recommendation: Stay with Claude SDK**

Migrate when you add checkout flows or need persistent conversations.

---

## 10. Questions for Stakeholders

### 1. Cyclic Workflow Justification

> "What specific user journeys require cyclic graph execution? The current linear ReAct pattern handles 90% of e-commerce Q&A. Do we have concrete requirements for:
> - Multi-step checkout with confirmations?
> - Human-in-the-loop approval flows?
> - Complex branching conversation logic?"

### 2. State Persistence Requirements

> "Should conversation state survive Cloud Run instance restarts? Currently, sessions are in-memory with 30-min TTL. If persistence is required:
> - What's the expected p99 latency budget for checkpoint reads/writes?
> - Should state persist across user devices?
> - What's the maximum acceptable conversation history length?"

### 3. LangSmith Cost-Benefit

> "At current scale (~X conversations/day), full LangSmith tracing costs approximately $Y/month. Questions:
> - Is the observability ROI justified vs. structured logging?
> - Should we sample traces (e.g., 10%) to reduce costs?
> - Do we need prompt versioning and A/B testing capabilities?"

### 4. Fallback Strategy

> "If LLM latency exceeds 10s on a specific node, should the graph:
> - Short-circuit to a cached/default response?
> - Fail gracefully with error message?
> - Retry with exponential backoff?
> This affects edge routing logic and error handling."

### 5. Tool Migration Path

> "Current tools use in-process MCP server. LangGraph prefers LangChain Tool abstractions. Options:
> - Maintain dual interfaces (MCP for Claude SDK, LangChain for LangGraph)?
> - Fully migrate to LangChain tools?
> - Use adapter pattern to wrap MCP tools?"

### 6. Georgian Language Support

> "The current system has extensive Georgian support:
> - 235-line Georgian system prompt
> - Georgian→English query translation
> - Georgian response formatting
>
> How should this be distributed across LangGraph nodes? Options:
> - Single system prompt per node (duplicated)
> - Shared prompt fragments
> - Translation as dedicated node"

---

## Appendix A: Requirements Changes

### Current (`requirements.txt`)
```
anthropic>=0.40.0
claude-agent-sdk>=0.1.0
fastapi>=0.115.0
uvicorn>=0.32.0
motor>=3.6.0
pymongo>=4.10.0
python-dotenv>=1.0.0
pydantic>=2.10.0
google-generativeai>=0.8.0
```

### LangGraph Addition
```
# Existing
fastapi>=0.115.0
uvicorn>=0.32.0
motor>=3.6.0
pymongo>=4.10.0
python-dotenv>=1.0.0
pydantic>=2.10.0

# LangGraph Stack
langgraph>=0.2.0
langchain-anthropic>=0.3.0
langchain-core>=0.3.0
langchain-mongodb>=0.2.0

# Optional: LangSmith
langsmith>=0.1.0
```

---

## Appendix B: Environment Variables

### Additional Variables for LangGraph

```bash
# LangSmith (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls_xxx
LANGCHAIN_PROJECT=scoop-ai-production

# Checkpoint Configuration
CHECKPOINT_COLLECTION=langgraph_checkpoints
CHECKPOINT_TTL_HOURS=24
```

---

## Appendix C: Graph Visualization

```
                         ┌─────────────────┐
                         │     START       │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ security_check  │
                         └────────┬────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
               [BLOCKED]                   [CONTINUE]
                    │                           │
                    ▼                           ▼
               ┌────────┐              ┌─────────────────┐
               │  END   │              │ classify_intent │
               └────────┘              └────────┬────────┘
                                                │
              ┌─────────────────────────────────┼─────────────────────────────────┐
              │                                 │                                 │
         [GREETING]                    [RECOMMENDATION]                    [OFF_TOPIC]
              │                          [EXPLANATION]                           │
              │                                 │                                 │
              ▼                                 ▼                                 ▼
     ┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
     │ handle_greeting │              │ search_products │              │ handle_off_topic│
     └────────┬────────┘              └────────┬────────┘              └────────┬────────┘
              │                                 │                                 │
              │                    ┌────────────┴────────────┐                    │
              │                    │                         │                    │
              │           [RECOMMENDATION]            [EXPLANATION]               │
              │                    │                         │                    │
              │                    ▼                         ▼                    │
              │         ┌──────────────────┐    ┌──────────────────────┐          │
              │         │ generate_        │    │ generate_            │          │
              │         │ recommendation   │    │ explanation          │          │
              │         └────────┬─────────┘    └──────────┬───────────┘          │
              │                  │                         │                      │
              └──────────────────┴────────────┬────────────┴──────────────────────┘
                                              │
                                              ▼
                                         ┌────────┐
                                         │  END   │
                                         └────────┘
```

---

*Document prepared for Scoop AI LangGraph Migration Planning*
