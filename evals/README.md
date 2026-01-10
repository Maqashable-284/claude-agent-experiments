# Scoop AI Evaluation System

Gemini-based LLM-as-Judge for evaluating Scoop AI agent responses.

## 🎯 რას აკეთებს?

1. გაგზავნის ტესტ კითხვებს Scoop AI-ზე
2. Gemini აფასებს პასუხებს (0-10 ქულა)
3. ინახავს შედეგებს JSON-ში

## 📋 Test Categories

| Category | Count | Description |
|----------|-------|-------------|
| greeting | 3 | მისალმებები (სწრაფი, no tool) |
| product_search | 3 | პროდუქტის ძებნა (URLs) |
| recommendation | 3 | რეკომენდაციები (Quick-Buy) |
| science | 3 | მეცნიერება (Bio-Bridge) |
| edge_case | 3 | რთული შემთხვევები |

## 🚀 Usage

```bash
# Set API keys
export GEMINI_API_KEY="your-gemini-key"
export SCOOP_API_URL="https://scoop-ai-sdk-xxx.run.app"

# Run all tests
python evaluate.py

# Run specific category
python evaluate.py --category greeting

# Dry run (show scenarios)
python evaluate.py --dry-run

# Without saving results
python evaluate.py --no-save
```

## 📊 Grading Criteria

| Criteria | Points | Description |
|----------|--------|-------------|
| LANGUAGE | 0-2 | 100% ქართული? |
| RELEVANCE | 0-2 | კითხვას პასუხობს? |
| PRODUCTS | 0-2 | ფასი + URL აქვს? |
| FORMAT | 0-2 | სწორი ფორმატი? |
| NO_HALLUCINATION | 0-2 | არ მოიგონა? |

**Pass threshold:** >= 7/10 + time limit passed

## 📁 Files

```
evals/
├── evaluate.py      # Main runner
├── scenarios.json   # Test cases
├── README.md        # This file
└── results/         # JSON outputs (gitignored)
```
