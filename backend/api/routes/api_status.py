"""
API Status and monitoring endpoints (WhoScored-only)
"""
from fastapi import APIRouter

from services.cache_service import get_cache_service
from config.settings import get_settings

router = APIRouter()
cache = get_cache_service()
settings = get_settings()


@router.get("/api-usage")
async def get_api_usage():
    """Expose data-source health and cache stats."""
    cache_stats = await cache.get_stats()

    return {
        "status": "ok",
        "data_source": "whoscored",
        "historical_baseline_season": getattr(settings, "HISTORICAL_BASELINE_SEASON", "2023/24"),
        "anthropic_enabled": bool(getattr(settings, "ANTHROPIC_API_KEY", "")),
        "cache": cache_stats,
        "notes": [
            "Using WhoScored data via soccerdata",
            "Responses are cached to reduce upstream load",
            "Cache TTLs: fixtures 1h, opponent_stats 24h, tactical_plan 24h",
        ],
    }
