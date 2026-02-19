"""
API Status and monitoring endpoints (WhoScored-only)
"""
from fastapi import APIRouter

from services.cache_service import get_cache_service
from services.tactical_ml_service import get_tactical_ml_service
from config.settings import get_settings

router = APIRouter()
cache = get_cache_service()
settings = get_settings()
ml_service = get_tactical_ml_service()


@router.get("/api-usage")
async def get_api_usage():
    """Expose data-source health and cache stats."""
    cache_stats = await cache.get_stats()
    ml_status = ml_service.get_status()

    return {
        "status": "ok",
        "data_source": "whoscored",
        "default_league": getattr(settings, "WHOSCORED_DEFAULT_LEAGUE", "ENG-Premier League"),
        "training_baseline_league": getattr(settings, "PORTUGUESE_TRAINING_LEAGUE", "POR-Liga Portugal"),
        "historical_baseline_season": getattr(settings, "HISTORICAL_BASELINE_SEASON", "2023/24"),
        "anthropic_enabled": bool(getattr(settings, "ANTHROPIC_API_KEY", "")),
        "ml": ml_status,
        "cache": cache_stats,
        "notes": [
            "Using WhoScored data via soccerdata",
            "Responses are cached to reduce upstream load",
            "Cache TTLs: fixtures 1h, opponent_stats 24h, tactical_plan 24h",
        ],
    }
