import os

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        class BaseSettings:
            pass

class Settings(BaseSettings):
    APP_NAME: str = "Alpha"
    APP_DOMAIN: str = os.getenv("APP_DOMAIN", "alpha.zainalmultazam.com")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    
    # Risk Management Defaults
    DEFAULT_CAPITAL: float = float(os.getenv("DEFAULT_CAPITAL", 50000000.0))  # Rp 50 Juta
    DEFAULT_MAX_RISK_PCT: float = float(os.getenv("DEFAULT_MAX_RISK_PCT", 1.0)) # 1% per trade
    MIN_RR_RATIO: float = 2.0  # Minimal Risk to Reward 1:2
    
    # Security PIN
    ACCESS_PIN: str = os.getenv("ACCESS_PIN", "311294")
    
    # Universal Multi-Provider LLM Settings (Tier 1 Primary)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")  # gemini, openai, deepseek, groq, openrouter, custom
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("GEMINI_API_KEY", os.getenv("OPENAI_API_KEY", "")))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-flash-latest")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")  # Optional custom base URL for OpenAI-compatible proxies

    # Smart Auto-Failover LLM Settings (Tier 2 Secondary)
    LLM_BACKUP_PROVIDER: str = os.getenv("LLM_BACKUP_PROVIDER", "groq")
    LLM_BACKUP_API_KEY: str = os.getenv("LLM_BACKUP_API_KEY", os.getenv("GROQ_API_KEY", ""))
    LLM_BACKUP_MODEL: str = os.getenv("LLM_BACKUP_MODEL", "qwen/qwen3.8-27b")
    LLM_BACKUP_BASE_URL: str = os.getenv("LLM_BACKUP_BASE_URL", "")
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    ENABLE_TELEGRAM_ALERTS: bool = os.getenv("ENABLE_TELEGRAM_ALERTS", "false").lower() == "true"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
