from pydantic_settings import BaseSettings
from typing import List, Dict, Any

class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    DATABASE_URL: str = "sqlite:///./data/finpilot.db"

    # Provider setting: "none" | "ollama" | "gemini" | "groq" | "anthropic"
    LLM_PROVIDER: str = "none"

    # Ollama (Local - Free)
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # Gemini (Google AI Studio - Free Tier)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"

    # Groq (Groq Cloud - Free Tier)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # Anthropic (Optional Paid Cloud)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"
    ANTHROPIC_MODEL_FAST: str = "claude-haiku-4-5-20251001"
    ANTHROPIC_MODEL_SMART: str = "claude-sonnet-5"
    USE_SMART_MODEL: bool = False

    # Mode & Rate Limiting
    LLM_MODE: str = "cheap"  # "off" | "cheap" | "full"
    USD_TO_INR_RATE: float = 84.0
    RATE_LIMIT_RPM: int = 30
    CIRCUIT_BREAKER_COOLDOWN_SECONDS: int = 60

    # Pricing per 1M tokens (USD) - only applicable for paid providers like Anthropic
    MODEL_PRICES: Dict[str, Dict[str, float]] = {
        "claude-haiku-4-5-20251001": {
            "input": 1.00,
            "output": 5.00,
            "cache_read": 0.10,
            "cache_write": 1.25,
        },
        "claude-sonnet-5": {
            "input": 3.00,
            "output": 15.00,
            "cache_read": 0.30,
            "cache_write": 3.75,
        },
        "claude-sonnet-4-5": {
            "input": 3.00,
            "output": 15.00,
            "cache_read": 0.30,
            "cache_write": 3.75,
        },
    }

    UPLOADS_DIR: str = "./data/uploads"
    DEFAULT_CURRENCY: str = "INR"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    DEFAULT_USER_ID: int = 1
    USE_OCR: bool = False

settings = Settings()
