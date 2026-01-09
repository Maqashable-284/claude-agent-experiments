# Scoop AI Agent SDK 🥤🤖

**ქართული სპორტული კვების AI კონსულტანტი** - Standard Anthropic SDK + MongoDB

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Anthropic SDK](https://img.shields.io/badge/Anthropic-SDK%20Standard-orange.svg)](https://docs.anthropic.com/)
[![Cloud Run](https://img.shields.io/badge/Google-Cloud%20Run-blue.svg)](https://cloud.google.com/run)

---

## 🎯 რა არის?

Scoop AI Agent SDK არის **სტანდარტული Anthropic SDK**-ზე დაფუძნებული აგენტური ჩატბოტი სპორტული კვების პროდუქტებისთვის. მიგრირებულია Claude Agent SDK-დან Cloud Run თავსებადობისთვის.

## ✨ ფუნქციონალი

- 🔍 **პროდუქტების ძებნა** - MongoDB + Georgian→English translation
- 💬 **ქართული ენა** - სრული Georgian support
- 🧠 **Conversation Memory** - ახსოვს საუბრის ისტორია
- 🛡️ **Security Guards** - Prompt injection & blocked keywords
- ⚡ **Tool Use** - Claude თვითონ წყვეტს რა tool გამოიძახოს
- 🚀 **Cloud Run** - Production deployment europe-west1

---

## ⚠️ მნიშვნელოვანი: MongoDB Databases

```
⚡ PRODUCTION DATABASE: scoop_db ← გამოიყენე ეს!
❌ არ გამოიყენო: scoop_ai (მხოლოდ conversations)
```

| Database | Collections | Products | გამოყენება |
|----------|-------------|----------|------------|
| `scoop_db` | 9 | ✅ 315 | **Production** |
| `scoop_ai` | 1 | ❌ 0 | არ გამოიყენო |

---

## 🏗️ არქიტექტურა

```
User Request
    ↓
FastAPI (/chat)
    ↓
ScoopAgent (Anthropic SDK)
    ↓ tool_use
Execute Tools (search_products, get_product_details)
    ↓
MongoDB (scoop_db.products)
    ↓
Return Response to User
```

**Agentic Loop:** Claude აანალიზებს მოთხოვნას → თვითონ წყვეტს tool-ის გამოძახებას → ასრულებს tools-ს → აბრუნებს საბოლოო პასუხს.

---

## 📁 პროექტის სტრუქტურა

```
scoop_ai_agent/
├── main.py              # FastAPI server + lifespan
├── config.py            # Settings + System Prompt
├── Dockerfile           # Cloud Run (Python 3.11)
├── requirements.txt     # anthropic, fastapi, motor
└── app/
    ├── __init__.py
    ├── agent.py         # ScoopAgent + Tool Definitions + Security
    ├── database.py      # MongoDB connection manager
    └── product_service.py # Product queries + QUERY_MAP
```

---

## 🚀 Deployment

### Cloud Run Deploy

```bash
gcloud run deploy scoop-ai-sdk \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "ANTHROPIC_API_KEY=sk-ant-api03-...,MONGODB_URI=mongodb+srv://scoop_admin:W6AuJLLnYrPnq.3@scoop.xbbeory.mongodb.net/?appName=Scoop,MONGODB_DATABASE=scoop_db,DEFAULT_MODEL=claude-3-5-haiku-20241022"
```

### Service URL
```
https://scoop-ai-sdk-358331686110.europe-west1.run.app
```

---

## 🔧 Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` | Anthropic API key |
| `MONGODB_URI` | `mongodb+srv://...` | MongoDB Atlas connection |
| `MONGODB_DATABASE` | `scoop_db` | ⚠️ **არა scoop_ai!** |
| `DEFAULT_MODEL` | `claude-3-5-haiku-20241022` | Claude model |

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check + DB status |
| `/chat` | POST | Chat with agent |
| `/session/clear` | POST | Clear session history |
| `/sessions` | GET | List active sessions |

### Chat Request
```bash
curl -X POST https://scoop-ai-sdk-xxx.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","message":"პროტეინი მაინტერესებს"}'
```

### Response Format (Botpress Compatible)
```json
{
  "user_id": "user123",
  "response": "მოიძებნა 5 პროდუქტი...",
  "text": "მოიძებნა 5 პროდუქტი...",
  "success": true,
  "choices": ["პროტეინი", "კრეატინი"]
}
```

---

## 🛡️ Security Features

**Blocked Keywords:**
- Illegal substances: steroid, anabolic, hgh, sarm
- Prompt injection: "ignore instructions", "you are now"
- Dangerous: overdose, suicide

**Input Validation:**
- Max message length: 5000 chars
- Prompt injection pattern detection

---

## 🔄 Migration Notes

**Claude Agent SDK → Standard Anthropic SDK**

| Feature | Agent SDK | Standard SDK |
|---------|-----------|--------------|
| Tool calling | @tool decorator | tool_use API |
| Hooks | PreToolUse/PostToolUse | Manual check |
| MCP Server | create_sdk_mcp_server | Not used |
| Node.js | Required (CLI) | Not required |

**Why:**
- Agent SDK had `Server.__init__()` bug on Cloud Run
- Standard SDK is more stable and simpler

---

## 📄 License

MIT
