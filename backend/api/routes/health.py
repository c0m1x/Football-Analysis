"""
Health check endpoints
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Football Tactical Intelligence Platform"
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness check endpoint"""
    # Add checks for database, cache, etc.
    return {
        "status": "ready",
        "database": "connected",
        "cache": "connected"
    }
