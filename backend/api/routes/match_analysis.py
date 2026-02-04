"""
Match Analysis API Routes
"""
from fastapi import APIRouter, HTTPException
import httpx
from services.match_analysis_service import get_match_analysis_service
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.get("/match-analysis/{opponent_id}")
async def get_match_analysis(opponent_id: str, opponent_name: str):
    """
    Get tactical analysis for Gil Vicente vs specific opponent
    
    Args:
        opponent_id: Opponent team ID from API
        opponent_name: Opponent team name
    """
    try:
        service = get_match_analysis_service()
        analysis = await service.analyze_match(opponent_id, opponent_name)
        return analysis
    except httpx.HTTPStatusError as e:
        status = getattr(e.response, "status_code", None)
        logger.error(f"Error generating match analysis: {e}")
        if status == 403:
            raise HTTPException(
                status_code=503,
                detail=(
                    "SofaScore denied this request (HTTP 403). This environment may be blocked."
                ),
            )
        raise HTTPException(status_code=502, detail=str(e))

    except Exception as e:
        logger.error(f"Error generating match analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
