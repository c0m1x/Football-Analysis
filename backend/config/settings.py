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
    
    # Redis Cache
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    CACHE_TTL: int = 3600  # 1 hour
    
    # WhoScored via soccerdata
    WHOSCORED_ENABLED: bool = True
    WHOSCORED_LEAGUES: str = "POR-Liga Portugal,POR-Primeira Liga,POR-Liga NOS"
    WHOSCORED_SEASONS: str = ""
    WHOSCORED_CACHE_SECONDS: int = 1800
    WHOSCORED_NO_CACHE: bool = False
    WHOSCORED_DATA_DIR: str = ""
    
    # Historical baseline control
    HISTORICAL_BASELINE_SEASON: str = "2023/24"
    HISTORICAL_VALIDATION_NOTE: str = (
        "Baseado em dados da época 2023/24 — validar com observação recente do adversário."
    )

    # Anthropic (optional natural language generation)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    ANTHROPIC_TIMEOUT_SECONDS: int = 12

    # Gil Vicente Configuration
    GIL_VICENTE_TEAM_ID: int = 9764
    GIL_VICENTE_TEAM_NAME: str = "Gil Vicente"
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
