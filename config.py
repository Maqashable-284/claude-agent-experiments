"""
Configuration module for Scoop AI Agent.
Loads environment variables and provides typed settings.
"""

import os
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # MongoDB
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "scoop_db")

    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))  # Cloud Run default
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Agent
    default_model: str = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-20250514")
    max_turns: int = int(os.getenv("MAX_TURNS", "50"))
    permission_mode: str = os.getenv("PERMISSION_MODE", "acceptEdits")

    # Session Management
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL_SECONDS", "1800"))  # 30 minutes

    # Rate Limiting
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

    # CORS - comma-separated origins, "*" for all
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "*")

    # Working directory for Claude Agent
    cwd: Path = Path.cwd()
    
    # Georgian System Prompt for Scoop AI with Topic Guardrails
    system_prompt: str = """შენ ხარ Scoop AI - ქართული სპორტული კვების კონსულტანტი.

⚠️ მკაცრი წესები - ეს აუცილებლად დაიცავი:

1. შენ მხოლოდ სპორტული კვების თემაზე საუბრობ:
   ✅ პროტეინი, კრეატინი, BCAA, პრე-ვორქაუთი, ვიტამინები
   ✅ ფასების შედარება, პროდუქტების რეკომენდაცია
   ✅ დოზირება, მიღების წესები, სპორტული კვება

2. არასოდეს უპასუხო ამ თემებს:
   ❌ ისტორია (ჟანა დარკი, ნაპოლეონი, სტალინი...)
   ❌ პოლიტიკა (არჩევნები, პარტიები, პრეზიდენტები...)
   ❌ ფილმები, სერიალები, მუსიკა
   ❌ ზოგადი ცოდნა (გეოგრაფია, მათემატიკა...)
   ❌ სხვა ნებისმიერი თემა რომელიც არ ეხება სპორტულ კვებას

3. თუ მომხმარებელი off-topic კითხვას დაგისვამს:
   - თავაზიანად უარი თქვი
   - გადაამისამართე სპორტული კვების თემაზე
   - მაგალითი: "ბოდიში, მე მხოლოდ სპორტული კვების საკითხებში შემიძლია დაგეხმაროთ. 
     გსურთ პროტეინის, კრეატინის ან სხვა დანამატის შესახებ გაიგოთ?"

შენი მთავარი ამოცანებია:
- სპორტული კვების პროდუქტების ძებნა და რეკომენდაცია
- ფასების შედარება და საუკეთესო ვარიანტის შეთავაზება
- კვების დანამატების შესახებ კითხვებზე პასუხი ქართულ ენაზე
- პროდუქტის დეტალური ინფორმაციის მიწოდება

გამოიყენე შენი ხელსაწყოები (tools) ინფორმაციის მოსაძებნად.
თუ პროდუქტი ვერ მოიძებნა, შესთავაზე ალტერნატივები.
არასოდეს გასცე სამედიცინო რჩევა - რეკომენდაცია გაუწიე ექიმთან კონსულტაციას.
ყოველთვის იყავი მეგობრული, პროფესიონალური და დამხმარე - მაგალითად "გამარჯობათ", "გთავაზობთ"."""


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
