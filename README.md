# Scoop AI Agent SDK 🥤🤖

**ქართული სპორტული კვების AI კონსულტანტი** - Claude Agent SDK V4.0

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Claude Agent SDK](https://img.shields.io/badge/Claude-Agent%20SDK-purple.svg)](https://docs.anthropic.com/)
[![Cloud Run](https://img.shields.io/badge/Google-Cloud%20Run-blue.svg)](https://cloud.google.com/run)

---

## 🎯 რა არის?

Scoop AI Agent V4.0 არის **Claude Agent SDK**-ზე დაფუძნებული აგენტური ჩატბოტი სპორტული კვების პროდუქტებისთვის.

### 🏛️ Unified Sales & Science v4.0

ბოტს აქვს უნიკალური მიდგომა - **70% გაყიდვა / 30% მეცნიერება**:

| ატრიბუტი | მნიშვნელობა |
|----------|-------------|
| **როლი** | Senior Consultant |
| **გაყიდვა (70%)** | მოკლე აღწერები, ფასები, "შეძენა" ლინკები |
| **მეცნიერება (30%)** | Bio-Bridge მეთოდი (მექანიზმი → შედეგი) |
| **ფილოსოფია** | "Scoop Truth Code" - არ ყიდის მაგიას |

### ✨ V4.0 ცვლილებები

- 🎯 **No Hallucination Rule** - მხოლოდ ბაზაში არსებული პროდუქტები
- 🛒 **Link Mandate** - URL-ის გარეშე პროდუქტი არ ჩანს
- 📋 **Quick-Buy Format** - 🥇🥈🥉 შედარების ფორმატი
- 🔬 **Bio-Bridge Explanation** - მექანიზმი + შედეგი
- 🗣️ **First Person Voice** - პირდაპირი მიმართვა (არა "ქოუჩი გირჩევთ")

---

## ✨ ფუნქციონალი

- 🔍 **პროდუქტების ძებნა** - MongoDB + Georgian→English translation
- 🔗 **პროდუქტის URL** - ბმულები scoop.ge-ზე
- 💬 **ქართული ენა** - სრული Georgian support
- 🧠 **Conversation Memory** - SDK მართავს საუბრის ისტორიას
- 🛡️ **Security Hooks** - Prompt injection & blocked keywords
- ⚡ **Auto Tool Use** - Claude აირჩევს tool-ს ავტომატურად
- 🚀 **Cloud Run** - Production deployment europe-west1
- 🚦 **Rate Limiting** - 30 request/minute

---

## 🚀 Performance Optimizations (v4.1)

### პრობლემა
პასუხის დრო იყო **15-30 წამი**. სამიზნე: **<10 წამი**.

### გადაწყვეტა - 4 ოპტიმიზაცია

| # | ცვლილება | ეფექტი | ფაილი/კონფიგი |
|---|----------|--------|---------------|
| 1 | **Min Instances = 1** | Cold Start: 0 წამი | Cloud Run |
| 2 | **Prompt Caching** | -30-50% latency | `agent.py` |
| 3 | **Speed Rules** | Tool calls -50% | `config.py` |
| 4 | **max_turns = 5** | Loop limit | `agent.py` |

### 1. Min Instances (Cloud Run)
```bash
gcloud run services update scoop-ai-sdk --min-instances=1 --region=europe-west1
```
- **ეფექტი:** Cold start = 0 (იყო: 3-5 წამი)
- **ფასი:** ~$15/თვე

### 2. Prompt Caching (Automatic)

Claude API ავტომატურად აკეთებს system prompt-ის ქეშირებას.
- **ეფექტი:** System prompt ქეშირდება Anthropic-ზე
- **შედეგი:** -30-50% tokens processing

### 3. Speed Optimization Rules (`config.py`)
```xml
<speed_optimization>
  TOOL USAGE DECISION:
  - გამარჯობა → NO TOOL
  - რა არის პროტეინი? → NO TOOL  
  - რა პროტეინები გაქვთ? → USE tool
</speed_optimization>
```
- **ეფექტი:** Greetings: 2-3 წამი (იყო: 15 წამი)

### 4. max_turns Limit (`agent.py`)
```python
max_turns=5  # იყო: unlimited
```
- **ეფექტი:** აგენტი არ ჩერდება უსასრულო loop-ში

### მოსალოდნელი შედეგი

| Request Type | წინ | ახლა |
|--------------|-----|------|
| Greeting | 15 წამი | 2-3 წამი |
| General Question | 20 წამი | 5-8 წამი |
| Product Search | 25-30 წამი | 8-12 წამი |

---

## 🔧 v4.2 Updates (2026-01-11)

### New Tool: get_all_categories

**პრობლემა:** "რა გაქვს მარაგში?" იწვევდა timeout (4+ tool calls × 20s = 80s+)

**გადაწყვეტა:** ერთი `get_all_categories` tool - ყველა კატეგორია ერთ ბრძანებაში:

```python
# app/tools.py
@mcp_tool(name="get_all_categories")
def get_all_categories(products_per_category: int = 3):
    """Returns all products grouped by category in a single call."""
```

### MongoDB Query Fix

**პრობლემა:** Aggregation pipeline 0 results აბრუნებდა.

**გადაწყვეტა:** Python-based grouping (უფრო reliable):

```python
# app/product_service.py
all_products = await self.collection.find({}).to_list(length=100)
# Group by category in Python
for p in all_products:
    category = p.get("category", "other")
    result[category].append(p)
```

### Debug Logging

Agent response tracking:
```python
logger.info(f"Total messages received: {msg_count}, response length: {len(full_response)}")
```

### Performance Results (v4.2)

| Query Type | დრო |
|------------|-----|
| მარტივი კითხვა (NO TOOL) | **9-14 წამი** ⚡ |
| პროდუქტის ძებნა (WITH TOOL) | **20-40 წამი** |
| "რა გაქვს მარაგში?" | **25-30 წამი** ✅ (იყო: TIMEOUT) |

### Database Stats
- **100 პროდუქტი**
- **13 კატეგორია**

## 🔘 LLM-Generated Quick Replies

Backend აბრუნებს კონტექსტურ quick_replies-ს:

### Sales Intent (პროდუქტების პასუხზე)
```
• 🔄 Whey vs Isolate შეადარე
• 💰 100₾-მდე ვარიანტები
• 🏋️ აღდგენისთვის რომელია საუკეთესო?
```

### Science Intent (მეცნიერულ პასუხზე)
```
• 📊 რა დოზა მჭირდება?
• ⏰ როდის მივიღო?
• 🔬 როგორ მუშაობს ორგანიზმში?
```

---

## 🧪 Evaluation System

`evals/` folder შეიცავს Gemini-based LLM-as-Judge სისტემას:

```bash
cd evals/
export GEMINI_API_KEY="your-key"
python evaluate.py
```

- **15 test scenarios** (greeting, product, recommendation, science, edge cases)
- **Gemini Flash** როგორც მოსამართლე (იაფი: $0.125/1M tokens)
- შედეგები `evals/results/`-ში

---

## 📋 Output Formats

### Quick-Buy Comparison (გაყიდვა)

```markdown
გთავაზობთ 3 საუკეთესო ვარიანტს:

### 🥇 Product Name
**💰 ფასი:** 140 ₾ | **📦 მოცულობა:** 67 პორცია
**⚡ შეფასება:** რატომ საუკეთესო
**🛒 [პროდუქტის ნახვა და შეძენა](URL)**
```

### Bio-Bridge Explanation (მეცნიერება)

```markdown
### 🔬 მოკლედ მოქმედების პრინციპი: კრეატინი

**1. მექანიზმი:**
ავსებს კუნთს ენერგიით (ATP სინთეზი)

**2. შედეგი ვარჯიშზე:**
შეძლებთ 2-3 ზედმეტი გამეორების გაკეთებას
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
MongoDB (scoop_db.products) → Returns URL!
    ↓
Return Response to User
```

---

## 📁 პროექტის სტრუქტურა

```
claude-agent-experiments/
├── main.py              # FastAPI server + Rate Limiting
├── config.py            # Settings + System Prompt v4.0
├── Dockerfile           # Cloud Run
├── requirements.txt     # claude-agent-sdk, mcp, fastapi
└── app/
    ├── agent.py         # ScoopAgent + Session TTL
    ├── tools.py         # MCP Tools + URL output
    ├── hooks.py         # Security hooks
    ├── database.py      # MongoDB connection
    └── product_service.py # Product queries
```

---

## 🚀 Deployment

### Cloud Run Requirements

⚠️ **მნიშვნელოვანი:** Claude Agent SDK მოითხოვს:
- **Memory: 2 GiB** (მინიმუმ!)
- **Node.js 18+** (Dockerfile-ში)

### Auto-Deploy

GitHub push → ავტომატური Cloud Run deploy

### Service URL
```
https://scoop-ai-sdk-358331686110.europe-west1.run.app
```

---

## 📦 Dependencies

```txt
claude-agent-sdk>=0.1.0
mcp>=1.0.0
anthropic>=0.18.1
fastapi==0.109.0
uvicorn[standard]==0.27.0
pymongo==4.6.1
motor==3.3.2
pydantic>=2.11.0
python-dotenv==1.0.1
```

---

## 🔧 Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `MONGODB_URI` | MongoDB Atlas connection |
| `MONGODB_DATABASE` | `scoop_db` |
| `DEFAULT_MODEL` | `claude-sonnet-4-20250514` |
| `SESSION_TTL_SECONDS` | Session timeout (default 1800) |
| `RATE_LIMIT_PER_MINUTE` | Rate limit (default 30) |

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check + DB status |
| `/chat` | POST | Chat with agent (full response) |
| `/chat/stream` | POST | **Streaming** chat (SSE) |
| `/session/clear` | POST | Clear user session |
| `/sessions` | GET | List active sessions |

### Chat Request
```bash
curl -X POST https://scoop-ai-sdk-xxx.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","message":"პროტეინი მაინტერესებს"}'
```

### Streaming Request (SSE)
```bash
curl -X POST https://scoop-ai-sdk-xxx.run.app/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user123","message":"პროტეინი მაინტერესებს"}'

# Response: Server-Sent Events
data: გთა
data: ვაზობთ
data: 3 საუკეთესო...
event: done
data: {}
```

### Response Format
```json
{
  "response_text_geo": "გთავაზობთ 3 საუკეთესო ვარიანტს...",
  "current_state": "CHAT",
  "quick_replies": [
    {"title": "რომელია საუკეთესო?", "payload": "..."}
  ],
  "success": true
}
```

---

## 🔗 Related Repositories

- [scoop-widget](https://github.com/Maqashable-284/scoop-widget) - React Chat Widget (Streaming)
- [scoop-chainlit](https://github.com/Maqashable-284/scoop-chainlit) - Chainlit Web UI

---

## 📄 License

MIT
