# Scoop AI Agent SDK 🥤🤖

**ქართული სპორტული კვების AI კონსულტანტი** - Claude Agent SDK V3

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Claude Agent SDK](https://img.shields.io/badge/Claude-Agent%20SDK-purple.svg)](https://docs.anthropic.com/)
[![Cloud Run](https://img.shields.io/badge/Google-Cloud%20Run-blue.svg)](https://cloud.google.com/run)

---

## 🎯 რა არის?

Scoop AI Agent V3 არის **Claude Agent SDK**-ზე დაფუძნებული აგენტური ჩატბოტი სპორტული კვების პროდუქტებისთვის.

### ✨ V3 გაუმჯობესებები

- 🤖 **Automatic Tool Orchestration** - Claude SDK თვითონ მართავს ყველაფერს
- 🔄 **Built-in Conversation Memory** - არ გჭირდება manual history management
- 🛡️ **Security via Hooks** - PreToolUse/PostToolUse ვალიდაცია
- ⚡ **MCP Server** - In-process tool server architecture

---

## ✨ ფუნქციონალი

- 🔍 **პროდუქტების ძებნა** - MongoDB + Georgian→English translation
- 💬 **ქართული ენა** - სრული Georgian support
- 🧠 **Conversation Memory** - SDK მართავს საუბრის ისტორიას
- 🛡️ **Security Hooks** - Prompt injection & blocked keywords
- ⚡ **Auto Tool Use** - Claude აირჩევს tool-ს ავტომატურად
- 🚀 **Cloud Run** - Production deployment europe-west1

---

## ⚠️ მნიშვნელოვანი: MongoDB Database

```
⚡ PRODUCTION DATABASE: scoop_db ← გამოიყენე ეს!
```

---

## 🏗️ არქიტექტურა

```
User Request
    ↓
FastAPI (/chat)
    ↓
ScoopAgent (Claude Agent SDK)
    ↓
ClaudeSDKClient + MCP Server
    ↓ automatic tool orchestration
Execute Tools (search_products, get_product_details)
    ↓
MongoDB (scoop_db.products)
    ↓
Return Response to User
```

**V3 Agentic Loop:** Claude SDK ავტომატურად მართავს tool calls → hooks ვალიდაციისთვის → საბოლოო პასუხი.

---

## 📁 პროექტის სტრუქტურა

```
claude-agent-experiments/
├── main.py              # FastAPI server + lifespan
├── config.py            # Settings + System Prompt
├── Dockerfile           # Cloud Run (Python 3.11 + Node.js)
├── requirements.txt     # claude-agent-sdk, mcp, fastapi
└── app/
    ├── __init__.py
    ├── agent.py         # ScoopAgent + ClaudeSDKClient
    ├── tools.py         # MCP Tools (@tool decorator)
    ├── hooks.py         # Security hooks
    ├── database.py      # MongoDB connection manager
    └── product_service.py # Product queries
```

---

## 🚀 Deployment

### Cloud Run Requirements

⚠️ **მნიშვნელოვანი:** Claude Agent SDK მოითხოვს:
- **Memory: 2 GiB** (მინიმუმ!)
- **Node.js 18+** (Dockerfile-ში)

### Deploy Command

```bash
gcloud run deploy scoop-ai-sdk \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --set-env-vars "ANTHROPIC_API_KEY=...,MONGODB_URI=...,MONGODB_DATABASE=scoop_db"
```

### Service URL
```
https://scoop-ai-sdk-358331686110.europe-west1.run.app
```

---

## 📦 Dependencies

```txt
# Core SDK
claude-agent-sdk>=0.1.0
mcp>=1.0.0                  # Required for Server version compatibility
anthropic>=0.18.1

# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0

# MongoDB
pymongo==4.6.1
motor==3.3.2

# Utilities
pydantic>=2.11.0            # mcp 1.x requires >=2.11.0
python-dotenv==1.0.1
aiohttp==3.9.3
```

### ⚠️ Version Compatibility Notes

| Package | Requirement | Reason |
|---------|-------------|--------|
| `mcp` | `>=1.0.0` | `Server.__init__()` version param support |
| `pydantic` | `>=2.11.0` | Required by mcp 1.x |
| Memory | `2 GiB` | Claude Code CLI subprocess |

---

## 🔧 Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` | Anthropic API key |
| `MONGODB_URI` | `mongodb+srv://...` | MongoDB Atlas connection |
| `MONGODB_DATABASE` | `scoop_db` | Production database |
| `DEFAULT_MODEL` | `claude-3-5-haiku-20241022` | Claude model |

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info (sdk: claude-agent-sdk) |
| `/health` | GET | Health check + DB status |
| `/chat` | POST | Chat with agent |

### Chat Request
```bash
curl -X POST https://scoop-ai-sdk-xxx.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","message":"პროტეინი მაინტერესებს"}'
```

### Response Format (V7 Compatible)
```json
{
  "response_text_geo": "მოიძებნა 5 პროდუქტი...",
  "current_state": "CHAT",
  "user_id": "user123",
  "response": "მოიძებნა 5 პროდუქტი...",
  "text": "მოიძებნა 5 პროდუქტი...",
  "success": true,
  "quick_replies": [
    {"title": "რომელია საუკეთესო?", "payload": "რომელია საუკეთესო?"}
  ]
}
```

---

## 🛡️ Security Features

**Hooks-based Security:**
- `validate_user_prompt` - Input validation before processing
- `validate_tool_use` - Tool authorization check
- `log_tool_result` - Result logging

**Blocked Keywords:**
- Illegal substances: steroid, anabolic, hgh, sarm
- Prompt injection: "ignore instructions", "you are now"

---

## 🐛 Resolved Issues

### 1. `Server.__init__() version error`
**Problem:** `mcp 0.9.x` doesn't support `version` parameter
**Solution:** Added `mcp>=1.0.0` to requirements.txt

### 2. `pydantic conflict`
**Problem:** `mcp 1.x` requires `pydantic>=2.11.0`
**Solution:** Updated pydantic constraint from `==2.6.1` to `>=2.11.0`

### 3. `Memory limit exceeded`
**Problem:** Claude Agent SDK uses ~525 MiB (exceeds 512 MiB limit)
**Solution:** Increased Cloud Run memory to **2 GiB**

---

## 📄 License

MIT
