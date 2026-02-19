"""Football Tactical Intelligence Platform - Main Application Entry Point."""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import api_status, health, match_analysis, ml_model, opponent_stats, real_fixtures, tactical_plan
from config.settings import get_settings
from utils.logger import setup_logger

settings = get_settings()
logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Football Tactical Intelligence Platform...")
    logger.info("Real-time match analysis enabled")
    logger.info("Using WhoScored data via soccerdata")
    logger.info("Enhanced opponent statistics available")
    logger.info("Automated tactical planning available")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="Football Tactical Intelligence Platform",
    description="Tactical analysis and opponent intelligence platform with multi-league and multi-team support.",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS middleware - MUST be before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "CORS_ORIGINS", ["*"]) or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(api_status.router, prefix="/api/v1", tags=["API Status"])
app.include_router(real_fixtures.router, prefix="/api/v1", tags=["Fixtures"])
app.include_router(opponent_stats.router, prefix="/api/v1", tags=["Opponent Statistics"])
app.include_router(tactical_plan.router, prefix="/api/v1", tags=["Tactical Plan"])
app.include_router(match_analysis.router, prefix="/api/v1", tags=["Match Analysis"])
app.include_router(ml_model.router, prefix="/api/v1", tags=["ML"])


@app.get("/")
async def root():
    """Root endpoint with platform information."""
    return {
        "name": "Football Tactical Intelligence Platform",
        "version": "4.0.0",
        "status": "operational",
        "features": [
            "League and team discovery",
            "Real-time fixture tracking",
            "Automated match analysis",
            "Comprehensive opponent statistics",
            "Tactical plan generation with evidence",
            "Form analysis and predictions",
            "WhoScored-driven tactical data pipeline",
        ],
        "endpoints": {
            "health": "/api/v1/health",
            "leagues": "/api/v1/leagues",
            "teams": "/api/v1/teams?league=ENG-Premier League",
            "fixtures": "/api/v1/fixtures/all?league=ENG-Premier League&team_id=...",
            "opponent_stats": "/api/v1/opponent-stats/{opponent_id}",
            "tactical_plan": "/api/v1/tactical-plan/{opponent_id}",
            "match_analysis": "/api/v1/match-analysis/{opponent_id}",
            "ml_status": "/api/v1/ml/status",
            "ml_train": "/api/v1/ml/train",
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
