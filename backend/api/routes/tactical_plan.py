"""
Tactical Plan API - Automated recommendations with Redis caching (WhoScored data)
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
import httpx
from pydantic import BaseModel, Field

from services.match_analysis_service import get_match_analysis_service
from services.cache_service import get_cache_service
from services.tactical_recommendation_service import get_tactical_recommendation_service

router = APIRouter(prefix="/tactical-plan", tags=["Tactical Plan"])


class CurrentSeasonObservation(BaseModel):
    match_label: Optional[str] = None
    possession_percent: Optional[float] = Field(default=None, ge=0, le=100)
    shots_for: Optional[float] = Field(default=None, ge=0)
    goals_scored: Optional[float] = Field(default=None, ge=0)
    goals_conceded: Optional[float] = Field(default=None, ge=0)
    pressing_level: Optional[str] = None
    offensive_transitions_rating: Optional[float] = Field(default=None, ge=0, le=10)
    build_up_pattern: Optional[str] = None
    defensive_line_height: Optional[float] = Field(default=None, ge=0, le=100)
    set_piece_vulnerability: Optional[str] = None
    key_players: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class RecalibrationRequest(BaseModel):
    opponent_name: str
    current_season_observations: List[CurrentSeasonObservation] = Field(default_factory=list)


def _build_tactical_plan_payload(
    full_analysis: Dict[str, Any],
    opponent_name: str,
    customization: Dict[str, Any],
) -> Dict[str, Any]:
    ai_recs = full_analysis.get("ai_recommendations", {})
    advanced_stats = full_analysis.get("opponent_advanced_stats", {})
    opponent_form = full_analysis.get("opponent_form", {})

    subs_block = ai_recs.get("substitution_timing") or ai_recs.get("substitution_strategy") or {}
    if isinstance(subs_block, dict):
        subs_recs = subs_block.get("substitution_recommendations") or subs_block.get("recommendations") or []
    elif isinstance(subs_block, list):
        subs_recs = subs_block
    else:
        subs_recs = []

    switches_block = ai_recs.get("in_game_switches") or []
    if isinstance(switches_block, dict):
        switches_recs = switches_block.get("recommendations") or []
    elif isinstance(switches_block, list):
        switches_recs = switches_block
    else:
        switches_recs = []

    return {
        "opponent": opponent_name,
        "focus_team": full_analysis.get("focus_team", {}),
        "league": full_analysis.get("league"),
        "ml_insights": full_analysis.get("ml_insights", {}),
        "tactical_plan": {
            "formation_recommendations": {
                "suggested_changes": ai_recs.get("formation_changes", []),
                "supporting_evidence": {
                    "opponent_shape": advanced_stats.get("team_shape", {}),
                    "recent_form": opponent_form.get("form_summary", {}),
                },
            },
            "pressing_strategy": {
                "recommendation": ai_recs.get("pressing_adjustments", {}),
                "supporting_evidence": {
                    "opponent_pressing": advanced_stats.get("pressing_structure", {}),
                    "possession_stats": advanced_stats.get("possession_control", {}),
                },
            },
            "target_zones": {
                "priority_zones": ai_recs.get("target_zones", []),
                "supporting_evidence": {
                    "defensive_vulnerabilities": advanced_stats.get("defensive_actions", {}),
                    "weak_areas": [
                        w
                        for w in ai_recs.get("exploit_weaknesses", [])
                        if w.get("severity") in ["CRITICAL", "HIGH"]
                    ],
                },
            },
            "player_roles": {
                "role_changes": ai_recs.get("player_role_changes", []),
                "supporting_evidence": {
                    "opponent_width": advanced_stats.get("team_shape", {}).get("width_usage"),
                    "transition_speed": advanced_stats.get("transitions", {}),
                },
            },
            "game_phases": {
                "in_possession": ai_recs.get(
                    "in_possession_focus", "Build from the back, control tempo"
                ),
                "out_possession": ai_recs.get("out_possession_focus", "Compact defensive block"),
                "transitions": ai_recs.get("transition_strategy", "Quick counter-attacks"),
                "supporting_evidence": {
                    "goal_timing": opponent_form.get("goals_by_period", {}),
                    "defensive_timing": opponent_form.get("conceded_by_period", {}),
                },
            },
            "in_game_switches": {
                "recommendations": switches_recs,
                "supporting_evidence": {
                    "opponent_pressing": advanced_stats.get("pressing_structure", {}),
                    "possession_stats": advanced_stats.get("possession_control", {}),
                },
            },
            "substitution_strategy": {
                "recommendations": subs_recs,
                "supporting_evidence": {
                    "late_game_performance": opponent_form.get("late_game_record", {}),
                },
            },
            "critical_weaknesses": ai_recs.get("exploit_weaknesses", []),
        },
        "ai_confidence": ai_recs.get("ai_confidence", {}),
        "confidence_adjustment": customization.get("confidence_adjustment", {}),
        "historical_context": {
            "baseline_season": customization.get("baseline_season"),
            "validation_note": customization.get("validation_note"),
            "season_comparison": customization.get("season_comparison"),
        },
        "customized_suggestions": customization.get("customized_suggestions", {}),
        "language_generation": customization.get("language_generation", {}),
        "generated_at": full_analysis.get("generated_at"),
        "data_source": full_analysis.get("data_source", "whoscored"),
    }


@router.get("/{opponent_id}")
async def get_tactical_plan(
    opponent_id: str,
    opponent_name: str,
    team_id: Optional[str] = Query(default=None),
    team_name: Optional[str] = Query(default=None),
    league: Optional[str] = Query(default=None),
):
    """
    Get automated tactical plan with embedded statistical evidence sourced from WhoScored.

    Cached for 24 hours to avoid re-scraping.
    """
    cache = get_cache_service()
    cache_key = f"{league or 'default'}::{team_id or ''}::{team_name or ''}::{opponent_id}_{opponent_name}"

    cached_data = await cache.get("tactical_plan", cache_key)
    if cached_data:
        cached_data["data_source"] = "cache"
        cached_data["cache_info"] = "Tactical plan from cache (24h TTL)"
        return cached_data

    try:
        analysis_service = get_match_analysis_service()
        recommendation_service = get_tactical_recommendation_service()

        full_analysis = await analysis_service.analyze_match(
            opponent_id,
            opponent_name,
            team_id=team_id,
            team_name=team_name,
            league=league,
        )
        customization = await recommendation_service.build_customized_recommendations(
            opponent_name=opponent_name,
            opponent_advanced_stats=full_analysis.get("opponent_advanced_stats", {}),
            opponent_form=full_analysis.get("opponent_form", {}),
            ai_confidence=full_analysis.get("ai_recommendations", {}).get("ai_confidence", {}),
            current_season_observations=[],
        )
        result = _build_tactical_plan_payload(full_analysis, opponent_name, customization)
        result["cache_info"] = (
            "Fresh tactical plan from WhoScored data (cached for 24h)"
            if full_analysis.get("data_source") == "whoscored"
            else "Fresh tactical plan (cached for 24h)"
        )

        await cache.set("tactical_plan", cache_key, result)

        return result

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating tactical plan: {str(e)}")


@router.post("/{opponent_id}/recalibrate")
async def recalibrate_tactical_plan(
    opponent_id: str,
    payload: RecalibrationRequest,
    team_id: Optional[str] = Query(default=None),
    team_name: Optional[str] = Query(default=None),
    league: Optional[str] = Query(default=None),
):
    """Recalibrate tactical suggestions using manually observed current-season data."""
    try:
        analysis_service = get_match_analysis_service()
        recommendation_service = get_tactical_recommendation_service()
        full_analysis = await analysis_service.analyze_match(
            opponent_id,
            payload.opponent_name,
            team_id=team_id,
            team_name=team_name,
            league=league,
        )

        customization = await recommendation_service.build_customized_recommendations(
            opponent_name=payload.opponent_name,
            opponent_advanced_stats=full_analysis.get("opponent_advanced_stats", {}),
            opponent_form=full_analysis.get("opponent_form", {}),
            ai_confidence=full_analysis.get("ai_recommendations", {}).get("ai_confidence", {}),
            current_season_observations=[item.model_dump() for item in payload.current_season_observations],
        )

        result = _build_tactical_plan_payload(full_analysis, payload.opponent_name, customization)
        result["cache_info"] = "Manual recalibration (not cached)"
        result["data_source"] = "manual+historical"
        return result

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recalibrating tactical plan: {str(e)}")
