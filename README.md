# Scoop AI Agent 🥤🤖

**ქართული სპორტული კვების AI კონსულტანტი** - Claude Agent SDK + MongoDB

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Claude Agent SDK](https://img.shields.io/badge/Claude-Agent%20SDK-orange.svg)](https://docs.anthropic.com/en/docs/agents-and-tools)
[![Cloud Run](https://img.shields.io/badge/Google-Cloud%20Run-blue.svg)](https://cloud.google.com/run)

## 🎯 რა არის?

Scoop AI არის აგენტური ჩატბოტი რომელიც იყენებს **Claude Agent SDK**-ს სპორტული კვების პროდუქტების საძიებლად და რჩევების მისაცემად ქართულ ენაზე.

## ✨ ფუნქციონალი

- 🔍 **პროდუქტების ძებნა** - MongoDB-დან real-time
- 💬 **ქართული ენა** - სრული Georgian support
- 🧠 **Conversation Memory** - ახსოვს საუბრის ისტორია
- 🛡️ **Security Hooks** - ბლოკავს საშიშ მოთხოვნებს
- ⚡ **MCP Tools** - Claude თვითონ წყვეტს რა tool გამოიძახოს
- 🚀 **Cloud Run** - Production-ready deployment

## 🏗️ არქიტექტურა

```
User → FastAPI → ScoopAgent → ClaudeSDKClient → Claude API
                                    ↓
                              MCP Tools → MongoDB
```

## 📁 სტრუქტურა

```
scoop_ai_agent/
├── main.py              # FastAPI server
├── config.py            # Settings
├── Dockerfile           # Cloud Run deployment
├── requirements.txt
└── app/
    ├── agent.py         # ClaudeSDKClient wrapper
    ├── tools.py         # MCP Tools (@tool decorator)
    ├── hooks.py         # Security guardrails
    ├── database.py      # MongoDB connection
    └── product_service.py # Product queries
```

## 🚀 გაშვება

### ლოკალურად
```bash
pip install -r requirements.txt
cp .env.example .env
# დაამატე API keys
python main.py
```

### Cloud Run Deploy
```bash
gcloud run deploy scoop-ai-sdk \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "ANTHROPIC_API_KEY=...,MONGODB_URI=..."
```

## 🔧 Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `MONGODB_URI` | MongoDB connection string |
| `MONGODB_DATABASE` | Database name |
| `DEFAULT_MODEL` | Claude model (default: claude-3-5-haiku-20241022) |

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | მთავარი ჩატი |
| `/health` | GET | Health check |
| `/sessions` | GET | აქტიური სესიები |
| `/db/status` | GET | MongoDB სტატუსი |

## 🤖 Botpress Integration

Botpress-თან დასაკავშირებლად გამოიყენე Cloud Run URL:
```
POST https://scoop-ai-sdk-xxxxx.run.app/chat
Body: {"user_id": "botpress_user", "message": "..."}
```

## 📄 License

MIT
