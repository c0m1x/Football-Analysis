"""ML model endpoints: training and status."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.tactical_ml_service import get_tactical_ml_service

router = APIRouter(prefix="/ml", tags=["ML"])


class TrainMLRequest(BaseModel):
    leagues: List[str] = Field(default_factory=list)
    force: bool = False


@router.get("/status")
async def get_ml_status():
    service = get_tactical_ml_service()
    return service.get_status()


@router.post("/train")
async def train_ml_model(payload: Optional[TrainMLRequest] = None):
    service = get_tactical_ml_service()
    body = payload or TrainMLRequest()
    try:
        result = await service.train_model(
            leagues=body.leagues or None,
            force=bool(body.force),
        )
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
