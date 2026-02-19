"""Match analysis API routes."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
import httpx
from services.match_analysis_service import get_match_analysis_service
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.get("/match-analysis/{opponent_id}")
async def get_match_analysis(
    opponent_id: str,
    opponent_name: str,
    team_id: Optional[str] = Query(default=None),
    team_name: Optional[str] = Query(default=None),
    league: Optional[str] = Query(default=None),
):
    """
    Get tactical analysis for selected team vs specific opponent.
    
    Args:
        opponent_id: Opponent team ID
        opponent_name: Opponent team name
        team_id/team_name: Optional selected team context
        league: Optional league code (e.g. ENG-Premier League)
    """
    try:
        service = get_match_analysis_service()
        analysis = await service.analyze_match(
            opponent_id,
            opponent_name,
            team_id=team_id,
            team_name=team_name,
            league=league,
        )
        return analysis
    except httpx.HTTPStatusError as e:
        logger.error(f"Error generating match analysis: {e}")
        raise HTTPException(status_code=502, detail=str(e))

    except Exception as e:
        logger.error(f"Error generating match analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
