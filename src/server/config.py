import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BITBANK_API_KEY: str = os.getenv("BITBANK_API_KEY", "")
    BITBANK_API_SECRET: str = os.getenv("BITBANK_API_SECRET", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    POLLING_INTERVAL_MINUTES: int = int(os.getenv("POLLING_INTERVAL_MINUTES", "15"))
    LOG_RETENTION_DAYS: int = int(os.getenv("LOG_RETENTION_DAYS", "365"))
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8080"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")
    DB_PATH: str = os.getenv("DB_PATH", "/app/data/trading.db")
    CONFIG_PATH: str = os.getenv("CONFIG_PATH", "/app/config/trading_rules.md")
    WEB_PATH: str = os.getenv("WEB_PATH", "/app/web")


config = Config()
