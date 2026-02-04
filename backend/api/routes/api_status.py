"""
API Status and monitoring endpoints (SofaScore-only)
"""
from fastapi import APIRouter

from services.cache_service import get_cache_service

router = APIRouter()
cache = get_cache_service()


@router.get("/api-usage")
async def get_api_usage():
    """Expose scraper health and cache stats (no external API tokens)."""
    cache_stats = await cache.get_stats()

    return {
        "status": "ok",
        "data_source": "sofascore_scraper",
        "cache": cache_stats,
        "notes": [
            "Using SofaScore scraping only; no external API keys required",
            "Responses are cached to reduce scraping load",
            "Cache TTLs: fixtures 1h, opponent_stats 24h, tactical_plan 24h",
        ],
    }
