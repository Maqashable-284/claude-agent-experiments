# Scoop AI Agent 🥤🤖

**ქართული სპორტული კვების AI კონსულტანტი** - Claude Agent SDK + MongoDB

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Claude Agent SDK](https://img.shields.io/badge/Claude-Agent%20SDK-orange.svg)](https://docs.anthropic.com/en/docs/agents-and-tools)

## 🎯 რა არის?

Scoop AI არის აგენტური ჩატბოტი რომელიც იყენებს **Claude Agent SDK**-ს სპორტული კვების პროდუქტების საძიებლად და რჩევების მისაცემად ქართულ ენაზე.

## ✨ ფუნქციონალი

- 🔍 **პროდუქტების ძებნა** - MongoDB-დან real-time
- 💬 **ქართული ენა** - სრული Georgian support
- 🧠 **Conversation Memory** - ახსოვს საუბრის ისტორია
- 🛡️ **Security Hooks** - ბლოკავს საშიშ მოთხოვნებს
- ⚡ **MCP Tools** - Claude თვითონ წყვეტს რა tool გამოიძახოს

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
├── requirements.txt
└── app/
    ├── agent.py         # ClaudeSDKClient wrapper
    ├── tools.py         # MCP Tools (@tool decorator)
    ├── hooks.py         # Security guardrails
    ├── database.py      # MongoDB connection
    └── product_service.py # Product queries
```

## 🚀 გაშვება

### 1. დააინსტალირე dependencies
```bash
pip install -r requirements.txt
```

### 2. შექმენი .env ფაილი
```bash
cp .env.example .env
# დაამატე შენი API keys
```

### 3. გაუშვი სერვერი
```bash
python main.py
```

### 4. ტესტი
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "მაჩვენე პროტეინები"}'
```

## 🔧 Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `MONGODB_URI` | MongoDB connection string |
| `MONGODB_DATABASE` | Database name |
| `DEFAULT_MODEL` | Claude model (default: claude-haiku-3-5) |

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | მთავარი ჩატი |
| `/health` | GET | Health check |
| `/sessions` | GET | აქტიური სესიები |
| `/session/clear` | POST | სესიის გასუფთავება |
| `/db/status` | GET | MongoDB სტატუსი |

## 🛡️ Security

- Blocked keywords (steroids, hack, etc.)
- Prompt injection detection
- Input length validation
- Audit logging

## 📄 License

MIT
