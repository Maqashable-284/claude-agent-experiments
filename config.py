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
    
    # Georgian System Prompt for Scoop AI
    system_prompt: str = """შენ ხარ Scoop AI - ქართული სპორტული კვების კონსულტანტი.

შენი მთავარი ამოცანებია:
1. სპორტული კვების პროდუქტების ძებნა და რეკომენდაცია
2. ფასების შედარება და საუკეთესო ვარიანტის შეთავაზება
3. კვების დანამატების შესახებ კითხვებზე პასუხი ქართულ ენაზე
4. პროდუქტის დეტალური ინფორმაციის მიწოდება

ყოველთვის იყავი მეგობრული, პროფესიონალური და დამხმარე.
გამოიყენე შენი ხელსაწყოები (tools) ინფორმაციის მოსაძებნად.
თუ პროდუქტი ვერ მოიძებნა, შესთავაზე ალტერნატივები.
არასოდეს გასცე სამედიცინო რჩევა - რეკომენდაცია გაუწიე ექიმთან კონსულტაციას."""


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
