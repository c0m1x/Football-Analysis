"""
Configuration settings for the application
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Football Tactical Intelligence Platform"
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
    WHOSCORED_LEAGUES: str = (
        "ENG-Premier League,ESP-La Liga,ITA-Serie A,GER-Bundesliga,"
        "FRA-Ligue 1,POR-Liga Portugal"
    )
    WHOSCORED_SEASONS: str = ""
    WHOSCORED_CACHE_SECONDS: int = 1800
    WHOSCORED_NO_CACHE: bool = False
    WHOSCORED_DATA_DIR: str = ""
    WHOSCORED_DEFAULT_LEAGUE: str = "ENG-Premier League"
    PORTUGUESE_TRAINING_LEAGUE: str = "POR-Liga Portugal"
    
    # Historical baseline control
    HISTORICAL_BASELINE_SEASON: str = "2023/24"
    HISTORICAL_VALIDATION_NOTE: str = (
        "Baseado em dados da época 2023/24 — validar com observação recente do adversário."
    )

    # Anthropic (optional natural language generation)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    ANTHROPIC_TIMEOUT_SECONDS: int = 12

    # Analysis configuration
    DEFAULT_FOCUS_TEAM_ID: Optional[int] = None
    DEFAULT_FOCUS_TEAM_NAME: str = ""
    OPPONENT_MATCH_HISTORY_LIMIT: int = 10

    # ML Tactical Model
    ML_ENABLED: bool = True
    ML_MODEL_PATH: str = "data/models/tactical_model.joblib"
    ML_AUTO_TRAIN_IF_MISSING: bool = False
    ML_TRAINING_LEAGUES: str = "POR-Liga Portugal,ENG-Premier League,ESP-La Liga"
    ML_WINDOW_SIZE: int = 5
    ML_MIN_SAMPLES: int = 120
    ML_MAX_TEAMS_PER_LEAGUE: int = 20
    ML_MATCHES_PER_TEAM: int = 28
    
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
