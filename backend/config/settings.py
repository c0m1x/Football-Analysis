"""
Configuration settings for the application
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Gil Vicente Tactical Intelligence Platform"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/gil_vicente_tactical"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis Cache
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    CACHE_TTL: int = 3600  # 1 hour
    
    # SofaScore Configuration
    SOFASCORE_ENABLED: bool = True
    SOFASCORE_BASE_URL: str = "https://www.sofascore.com/api/v1"
    SOFASCORE_TIMEOUT_SECONDS: float = 20.0
    SOFASCORE_USER_AGENT: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    SOFASCORE_BASE_URLS: str = ""  # comma-separated fallbacks
    SOFASCORE_HEADERS_JSON: str = ""  # optional extra headers for scraping
    SOFASCORE_COOKIES_JSON: str = ""  # optional cookies for scraping
    SOFASCORE_PROXY: str = ""  # optional http/https proxy URL
    SOFASCORE_TEAM_ID_MAP_JSON: str = ""  # optional: {"Gil Vicente": 12345, "FC Porto": 67890}

    # Local Scraper Export Fallback
    # Directory where `scrapper/scrapper.py` writes JSON exports (repo root by default).
    SCRAPER_EXPORT_DIR: str = ""

    # Gil Vicente Configuration
    GIL_VICENTE_TEAM_ID: int = 9764  # SofaScore team ID
    GIL_VICENTE_LEAGUE_ID: int = 61  # Liga Portugal
    OPPONENT_MATCH_HISTORY_LIMIT: int = 10
    
    # CORS - Allow all origins in development
    CORS_ORIGINS: List[str] = ["*"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
