"""
Scoop AI Evaluation System
==========================
Uses Google Gemini as LLM-as-Judge to evaluate Scoop AI agent responses.

Usage:
    python evaluate.py                    # Run all scenarios
    python evaluate.py --category greeting # Run specific category
    python evaluate.py --dry-run          # Show scenarios without running

Environment Variables:
    GEMINI_API_KEY     - Google Gemini API key
    SCOOP_API_URL      - Scoop AI API endpoint (default: Cloud Run URL)
"""

import os
import json
import time
import asyncio
import argparse
from datetime import datetime
from typing import Optional

import httpx
import google.generativeai as genai

# ==================== Configuration ====================

SCOOP_API_URL = os.getenv(
    "SCOOP_API_URL", 
    "https://scoop-ai-sdk-358331686110.europe-west1.run.app"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SCENARIOS_FILE = os.path.join(os.path.dirname(__file__), "scenarios.json")

# ==================== Grading Prompt ====================

GRADING_PROMPT = """
შეაფასე Scoop AI-ს პასუხი შემდეგი კრიტერიუმებით.

## INPUT
მომხმარებლის კითხ
: {user_input}

## RESPONSE  
აგენტის პასუხი:
{agent_response}

## EXPECTED BEHAVIOR
{expected_behavior}

## კრიტერიუმები (0-10 ქულიანი სისტემა)

1. **LANGUAGE (0-2 ქულა):** 
   - პასუხი 100% ქართულია? 
   - ინგლისური სიტყვები/წინადადებები = 0 ქულა

2. **RELEVANCE (0-2 ქულა):**
   - კითხვას პასუხობს?
   - თემასთან შესაბამისია?

3. **PRODUCTS (0-2 ქულა):**
   - პროდუქტებს აქვს ფასი?
   - პროდუქტებს აქვს URL ლინკი (🛒)?
   - თუ პროდუქტის ძებნა არ იყო საჭირო, 2 ქულა ავტომატურად

4. **FORMAT (0-2 ქულა):**
   - სწორი ფორმატი გამოიყენა? (Quick-Buy: 🥇🥈🥉 ან Bio-Bridge)
   - მოწესრიგებული და წაკითხვადი?

5. **NO_HALLUCINATION (0-2 ქულა):**
   - არ მოიგონა არარსებული პროდუქტი?
   - არ მოიგონა ფასი ან URL?

## პასუხის ფორმატი

დააბრუნე ᲛᲮᲝᲚᲝᲓ JSON, სხვა ტექსტი არ დაწერო:
{{
  "scores": {{
    "language": 2,
    "relevance": 2,
    "products": 2,
    "format": 2,
    "hallucination": 2
  }},
  "total_score": 10,
  "issues": ["issue 1", "issue 2"],
  "passed": true
}}

passed = true თუ total_score >= 7
"""


# ==================== Eval Runner ====================

class ScoopEvaluator:
    """Evaluates Scoop AI agent using Gemini as judge."""
    
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.scenarios = self._load_scenarios()
        self.results = []
    
    def _load_scenarios(self) -> list:
        """Load test scenarios from JSON file."""
        with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["scenarios"]
    
    async def call_scoop_api(self, message: str) -> tuple[str, float]:
        """Call Scoop AI API and return response with elapsed time."""
        start = time.time()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{SCOOP_API_URL}/chat",
                    json={
                        "user_id": f"eval_{int(time.time())}",
                        "message": message
                    }
                )
                response.raise_for_status()
                data = response.json()
                agent_response = data.get("response_text_geo", "")
            except Exception as e:
                agent_response = f"ERROR: {str(e)}"
        
        elapsed = time.time() - start
        return agent_response, elapsed
    
    def grade_response(
        self, 
        user_input: str, 
        agent_response: str, 
        expected_behavior: str
    ) -> dict:
        """Use Gemini to grade the agent's response."""
        prompt = GRADING_PROMPT.format(
            user_input=user_input,
            agent_response=agent_response,
            expected_behavior=expected_behavior
        )
        
        try:
            result = self.model.generate_content(prompt)
            # Extract JSON from response
            text = result.text.strip()
            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            grade = json.loads(text)
        except Exception as e:
            grade = {
                "scores": {"language": 0, "relevance": 0, "products": 0, "format": 0, "hallucination": 0},
                "total_score": 0,
                "issues": [f"Grading error: {str(e)}"],
                "passed": False
            }
        
        return grade
    
    async def run_scenario(self, scenario: dict) -> dict:
        """Run a single evaluation scenario."""
        print(f"  Testing: {scenario['id']}...", end=" ", flush=True)
        
        # Call Scoop AI
        agent_response, elapsed = await self.call_scoop_api(scenario["input"])
        
        # Check time limit
        time_passed = elapsed < scenario["max_time_seconds"]
        
        # Grade with Gemini
        grade = self.grade_response(
            user_input=scenario["input"],
            agent_response=agent_response,
            expected_behavior=scenario["expected_behavior"]
        )
        
        # Combine results
        result = {
            "id": scenario["id"],
            "category": scenario["category"],
            "input": scenario["input"],
            "response": agent_response[:500],  # Truncate for storage
            "elapsed_seconds": round(elapsed, 2),
            "max_time_seconds": scenario["max_time_seconds"],
            "time_passed": time_passed,
            "grade": grade,
            "passed": grade.get("passed", False) and time_passed
        }
        
        # Print result
        status = "✅" if result["passed"] else "❌"
        print(f"{status} Score: {grade.get('total_score', 0)}/10 | Time: {elapsed:.1f}s")
        
        if not result["passed"] and grade.get("issues"):
            for issue in grade["issues"][:2]:
                print(f"      ⚠️  {issue}")
        
        return result
    
    async def run_all(self, category: Optional[str] = None) -> list:
        """Run all scenarios or filter by category."""
        scenarios = self.scenarios
        if category:
            scenarios = [s for s in scenarios if s["category"] == category]
        
        print(f"\n🧪 Scoop AI Evaluation")
        print(f"=" * 50)
        print(f"API: {SCOOP_API_URL}")
        print(f"Scenarios: {len(scenarios)}")
        print(f"=" * 50 + "\n")
        
        self.results = []
        for scenario in scenarios:
            result = await self.run_scenario(scenario)
            self.results.append(result)
        
        return self.results
    
    def print_summary(self):
        """Print evaluation summary."""
        if not self.results:
            print("No results to summarize.")
            return
        
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)
        avg_score = sum(r["grade"].get("total_score", 0) for r in self.results) / total
        avg_time = sum(r["elapsed_seconds"] for r in self.results) / total
        
        print(f"\n{'=' * 50}")
        print(f"📊 SUMMARY")
        print(f"{'=' * 50}")
        print(f"Passed: {passed}/{total} ({100*passed/total:.0f}%)")
        print(f"Average Score: {avg_score:.1f}/10")
        print(f"Average Time: {avg_time:.1f}s")
        
        # By category
        print(f"\n📈 By Category:")
        categories = set(r["category"] for r in self.results)
        for cat in sorted(categories):
            cat_results = [r for r in self.results if r["category"] == cat]
            cat_passed = sum(1 for r in cat_results if r["passed"])
            print(f"  {cat}: {cat_passed}/{len(cat_results)}")
        
        print(f"{'=' * 50}\n")
    
    def save_results(self, filename: Optional[str] = None):
        """Save results to JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(
                os.path.dirname(__file__), 
                "results", 
                f"eval_{timestamp}.json"
            )
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "api_url": SCOOP_API_URL,
                "results": self.results,
                "summary": {
                    "total": len(self.results),
                    "passed": sum(1 for r in self.results if r["passed"]),
                    "avg_score": sum(r["grade"].get("total_score", 0) for r in self.results) / len(self.results),
                    "avg_time": sum(r["elapsed_seconds"] for r in self.results) / len(self.results)
                }
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Results saved to: {filename}")


# ==================== CLI ====================

def main():
    parser = argparse.ArgumentParser(description="Scoop AI Evaluation System")
    parser.add_argument("--category", type=str, help="Run specific category only")
    parser.add_argument("--dry-run", action="store_true", help="Show scenarios without running")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to file")
    args = parser.parse_args()
    
    evaluator = ScoopEvaluator()
    
    if args.dry_run:
        print("\n📋 Available Scenarios:")
        for s in evaluator.scenarios:
            print(f"  [{s['category']}] {s['id']}: {s['input']}")
        return
    
    # Run evaluation
    asyncio.run(evaluator.run_all(category=args.category))
    
    # Print summary
    evaluator.print_summary()
    
    # Save results
    if not args.no_save:
        evaluator.save_results()


if __name__ == "__main__":
    main()
