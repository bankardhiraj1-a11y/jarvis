from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./jarvis2.db"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    CORS_ORIGINS: list = ["*"]

    # DhanHQ Integration
    DHAN_CLIENT_ID: str = ""
    DHAN_ACCESS_TOKEN: str = ""

    # ONDA Integration (Optional)
    ONDA_API_KEY: str = ""
    ONDA_ACCESS_TOKEN: str = ""

    # Paper Trading
    PAPER_TRADING_ENABLED: bool = True
    INITIAL_CAPITAL: float = 500000.0
    ALLOCATION_STOCKS: float = 100000.0
    ALLOCATION_SENSEX: float = 100000.0
    ALLOCATION_OPTIONS: float = 100000.0
    ALLOCATION_CANDLE: float = 100000.0
    ALLOCATION_XAUUSD: float = 100000.0

    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields from .env

@lru_cache()
def get_settings():
    return Settings()
