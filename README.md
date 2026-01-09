# Scoop AI Agent SDK 🥤🤖

**ქართული სპორტული კვების AI კონსულტანტი** - Claude Agent SDK V3.1

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Claude Agent SDK](https://img.shields.io/badge/Claude-Agent%20SDK-purple.svg)](https://docs.anthropic.com/)
[![Cloud Run](https://img.shields.io/badge/Google-Cloud%20Run-blue.svg)](https://cloud.google.com/run)

---

## 🎯 რა არის?

Scoop AI Agent V3.1 არის **Claude Agent SDK**-ზე დაფუძნებული აგენტური ჩატბოტი სპორტული კვების პროდუქტებისთვის.

### ✨ V3.1 გაუმჯობესებები

- 🤖 **Automatic Tool Orchestration** - Claude SDK თვითონ მართავს ყველაფერს
- 🔄 **Built-in Conversation Memory** - არ გჭირდება manual history management
- 🛡️ **Security via Hooks** - PreToolUse/PostToolUse ვალიდაცია
- ⚡ **MCP Server** - In-process tool server architecture
- 🚦 **Rate Limiting** - 30 request/minute (configurable)
- ⏰ **Session TTL** - 30 წუთის შემდეგ auto-cleanup
- 🎯 **Topic Guardrails** - Off-topic კითხვების ფილტრაცია

---

## ✨ ფუნქციონალი

- 🔍 **პროდუქტების ძებნა** - MongoDB + Georgian→English translation
- 💬 **ქართული ენა** - სრული Georgian support
- 🧠 **Conversation Memory** - SDK მართავს საუბრის ისტორიას
- 🛡️ **Security Hooks** - Prompt injection & blocked keywords
- ⚡ **Auto Tool Use** - Claude აირჩევს tool-ს ავტომატურად
- 🚀 **Cloud Run** - Production deployment europe-west1
- 🎯 **Topic Focus** - მხოლოდ სპორტული კვება, off-topic უარყოფა

---

## 🛡️ Topic Guardrails

ბოტი **მხოლოდ სპორტული კვების** თემაზე პასუხობს:

| ნებადართული ✅ | აკრძალული ❌ |
|---------------|-------------|
| პროტეინი, კრეატინი, BCAA | ისტორია (ჟანა დარკი...) |
| ფასების შედარება | პოლიტიკა |
| დოზირება, მიღების წესები | ფილმები, მუსიკა |
| სპორტული დანამატები | ზოგადი ცოდნა |

**Off-topic კითხვაზე პასუხი:**
> "ბოდიში, მე მხოლოდ სპორტული კვების საკითხებზე ვარ სპეციალიზებული..."

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
Rate Limiter (30 req/min)
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

---

## 📁 პროექტის სტრუქტურა

```
claude-agent-experiments/
├── main.py              # FastAPI server + Rate Limiting + Lifespan
├── config.py            # Settings + System Prompt + Guardrails
├── Dockerfile           # Cloud Run (Python 3.11 + Node.js)
├── requirements.txt     # claude-agent-sdk, mcp, fastapi
└── app/
    ├── __init__.py      # Exports + Custom Exceptions
    ├── agent.py         # ScoopAgent + Session TTL
    ├── tools.py         # MCP Tools (@tool decorator)
    ├── hooks.py         # Security hooks
    ├── database.py      # MongoDB + DatabaseConnectionError
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

---

## 🔧 Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` | Anthropic API key |
| `MONGODB_URI` | `mongodb+srv://...` | MongoDB Atlas connection |
| `MONGODB_DATABASE` | `scoop_db` | Production database |
| `DEFAULT_MODEL` | `claude-sonnet-4-20250514` | Claude model |
| `SESSION_TTL_SECONDS` | `1800` | Session timeout (30 min) |
| `RATE_LIMIT_PER_MINUTE` | `30` | Rate limit per user |
| `ALLOWED_ORIGINS` | `*` | CORS origins |

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
  "success": true
}
```

### Rate Limit Response (HTTP 429)
```json
{
  "response_text_geo": "ძალიან ბევრი მოთხოვნა. გთხოვთ მოიცადოთ ერთი წუთი.",
  "success": false,
  "error": "Rate limit exceeded"
}
```

---

## 🛡️ Security Features

### Hooks-based Security
- `validate_user_prompt` - Input validation before processing
- `validate_tool_use` - Tool authorization check
- `log_tool_result` - Result logging

### Blocked Keywords
- Illegal substances: steroid, anabolic, hgh, sarm
- Prompt injection: "ignore instructions", "you are now"

### Custom Exceptions
- `AgentError` - General agent failures
- `SessionError` - Session management issues
- `DatabaseConnectionError` - MongoDB connection failures

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

### 4. `Off-topic responses (Joan of Arc bug)`
**Problem:** Bot was answering questions about history, politics, movies
**Solution:** Added strict topic guardrails to system prompt - now refuses off-topic and redirects to sports nutrition

### 5. `No rate limiting`
**Problem:** Users could spam unlimited requests
**Solution:** Added `RateLimiter` class with 30 req/min default

### 6. `Session memory leak`
**Problem:** Sessions stayed in memory forever
**Solution:** Added session TTL with 30-minute auto-cleanup

---

## 📄 License

MIT

