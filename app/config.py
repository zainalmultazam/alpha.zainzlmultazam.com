import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "AlphaSwing IDX"
    APP_DOMAIN: str = os.getenv("APP_DOMAIN", "alpha.zainalmultazam.com")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    
    # Risk Management Defaults
    DEFAULT_CAPITAL: float = float(os.getenv("DEFAULT_CAPITAL", 50000000.0))  # Rp 50 Juta
    DEFAULT_MAX_RISK_PCT: float = float(os.getenv("DEFAULT_MAX_RISK_PCT", 1.0)) # 1% per trade
    MIN_RR_RATIO: float = 2.0  # Minimal Risk to Reward 1:2
    
    # Security PIN
    ACCESS_PIN: str = os.getenv("ACCESS_PIN", "311294")
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    ENABLE_TELEGRAM_ALERTS: bool = os.getenv("ENABLE_TELEGRAM_ALERTS", "false").lower() == "true"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
