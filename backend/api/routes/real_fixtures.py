"""Fixtures and discovery endpoints backed by WhoScored (via soccerdata)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query

from config.settings import get_settings
from services.cache_service import get_cache_service
from services.whoscored_service import get_whoscored_service
from utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)
settings = get_settings()

LISBON_TZ = ZoneInfo("Europe/Lisbon")


def _to_int(v) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


def _utc_to_lisbon(utc_iso: str) -> tuple[str, str, str]:
    dt_utc = datetime.fromisoformat(utc_iso.replace("Z", "+00:00"))
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_local = dt_utc.astimezone(LISBON_TZ)
    date_str = dt_local.date().isoformat()
    time_str = dt_local.time().replace(microsecond=0).isoformat()
    iso_local = dt_local.replace(microsecond=0).isoformat()
    return date_str, time_str, iso_local


def _fixture_from_event(event: dict, focus_team_id: int, focus_team_name: str) -> dict | None:
    if not isinstance(event, dict):
        return None

    home = event.get("homeTeam") or {}
    away = event.get("awayTeam") or {}
    status = event.get("status") or {}
    start_ts = event.get("startTimestamp")

    try:
        home_id_raw = home.get("id")
        away_id_raw = away.get("id")
        home_id = int(home_id_raw) if home_id_raw is not None else None
        away_id = int(away_id_raw) if away_id_raw is not None else None
    except Exception:
        return None

    if start_ts is None:
        return None

    dt_utc = datetime.fromtimestamp(float(start_ts), tz=timezone.utc)
    utc_iso = dt_utc.isoformat()
    match_date, match_time, iso_local = _utc_to_lisbon(utc_iso)

    status_type = str(status.get("type") or "").lower()
    is_finished = status_type == "finished"
    is_home = bool(home_id) and int(home_id) == int(focus_team_id)

    opponent = away if is_home else home

    home_score = (event.get("homeScore") or {}).get("current") if is_finished else None
    away_score = (event.get("awayScore") or {}).get("current") if is_finished else None

    fixture = {
        "id": event.get("id"),
        "match_id": event.get("id"),
        "utc_time": utc_iso,
        "datetime": iso_local,
        "date": match_date,
        "time": match_time,
        "status": "finished" if is_finished else "upcoming",
        "league": None,
        "team_id": str(focus_team_id),
        "team_name": focus_team_name,
        "is_home": is_home,
        "opponent_id": str(opponent.get("id")),
        "opponent_name": opponent.get("name"),
        "home_team_id": str(home_id) if home_id is not None else None,
        "home_team_name": home.get("name"),
        "away_team_id": str(away_id) if away_id is not None else None,
        "away_team_name": away.get("name"),
        "home_score": home_score,
        "away_score": away_score,
    }

    if is_finished and home_score is not None and away_score is not None:
        fixture["score"] = {"home": home_score, "away": away_score, "display": f"{home_score}-{away_score}"}
        team_score = home_score if is_home else away_score
        opp_score = away_score if is_home else home_score
        fixture["result"] = "W" if team_score > opp_score else ("D" if team_score == opp_score else "L")

    return fixture


def _sort_fixtures(fixtures: list[dict]) -> list[dict]:
    fixtures.sort(key=lambda x: (x.get("date") or "", x.get("time") or ""))
    return fixtures


async def _resolve_focus_team(league: str, team_id: Optional[str], team_name: Optional[str]) -> tuple[int, str]:
    ws = get_whoscored_service()

    resolved_id = _to_int(team_id)
    if resolved_id is None and team_name:
        resolved_id = ws.resolve_team_id(team_name, league=league)

    if resolved_id is None:
        raise HTTPException(status_code=400, detail="Provide a valid team_id or team_name")

    resolved_name = str(team_name or "").strip()
    if not resolved_name:
        resolved_name = ws.resolve_team_name(int(resolved_id), league=league) or f"Team {resolved_id}"

    return int(resolved_id), resolved_name


async def _get_fixtures_payload(
    *,
    league: str,
    team_id: Optional[str],
    team_name: Optional[str],
    past_limit: int,
    upcoming_limit: int,
) -> dict:
    cache = get_cache_service()
    ws = get_whoscored_service()

    focus_team_id, focus_team_name = await _resolve_focus_team(league, team_id, team_name)

    cache_key = f"fixtures::{league}::{focus_team_id}::{past_limit}::{upcoming_limit}"
    cached_data = await cache.get("fixtures", cache_key)
    if cached_data:
        cached_data["data_source"] = "cache"
        cached_data["cache_info"] = cached_data.get("cache_info") or "Fixtures from cache"
        return cached_data

    try:
        events = ws.get_team_events(
            int(focus_team_id),
            past_limit=int(past_limit),
            upcoming_limit=int(upcoming_limit),
            team_name=focus_team_name,
            league=league,
        )
        fixtures = []
        for ev in events:
            fixture = _fixture_from_event(ev, int(focus_team_id), focus_team_name)
            if fixture:
                fixture["league"] = league
                fixtures.append(fixture)

        _sort_fixtures(fixtures)

        now = datetime.now().strftime("%Y-%m-%d")
        past_fixtures = [f for f in fixtures if f.get("date", "") < now or f.get("status") == "finished"]
        upcoming_fixtures = [f for f in fixtures if f.get("date", "") >= now and f.get("status") != "finished"]

        result = {
            "league": league,
            "team": {"id": str(focus_team_id), "name": focus_team_name},
            "total_fixtures": len(fixtures),
            "past_fixtures": len(past_fixtures),
            "upcoming_fixtures": len(upcoming_fixtures),
            "fixtures": fixtures,
            "data_source": "whoscored",
            "cache_info": "Fixtures from WhoScored (cached for 1h)",
        }

        await cache.set("fixtures", cache_key, result, ttl=3600)
        return result

    except Exception as e:
        logger.error("Error fetching fixtures from WhoScored: %s", e)
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/leagues")
async def get_leagues():
    ws = get_whoscored_service()
    leagues = ws.get_available_leagues()
    training_league = str(getattr(settings, "PORTUGUESE_TRAINING_LEAGUE", "POR-Liga Portugal") or "POR-Liga Portugal")
    default_league = str(getattr(settings, "WHOSCORED_DEFAULT_LEAGUE", leagues[0] if leagues else "") or "")

    return {
        "leagues": [
            {
                "code": lg,
                "name": lg,
                "is_training_baseline": lg == training_league,
            }
            for lg in leagues
        ],
        "default_league": default_league,
        "training_baseline_league": training_league,
        "data_source": "whoscored",
    }


@router.get("/teams")
async def get_teams(
    league: str = Query(..., description="League code, e.g. ENG-Premier League"),
    search: Optional[str] = Query(default=None, description="Optional team name filter"),
    limit: int = Query(default=200, ge=1, le=500),
):
    ws = get_whoscored_service()
    try:
        teams = ws.list_teams(league=league, search=search, limit=limit)
        return {
            "league": league,
            "teams": teams,
            "count": len(teams),
            "data_source": "whoscored",
        }
    except Exception as e:
        logger.error("Error fetching teams for league %s: %s", league, e)
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/fixtures/all")
async def get_all_fixtures(
    league: str = Query(default=str(getattr(settings, "WHOSCORED_DEFAULT_LEAGUE", "ENG-Premier League"))),
    team_id: Optional[str] = Query(default=None),
    team_name: Optional[str] = Query(default=None),
    past_limit: int = Query(default=60, ge=1, le=200),
    upcoming_limit: int = Query(default=20, ge=1, le=100),
):
    return await _get_fixtures_payload(
        league=league,
        team_id=team_id,
        team_name=team_name,
        past_limit=past_limit,
        upcoming_limit=upcoming_limit,
    )


@router.get("/fixtures/upcoming")
async def get_upcoming_fixtures(
    league: str = Query(default=str(getattr(settings, "WHOSCORED_DEFAULT_LEAGUE", "ENG-Premier League"))),
    team_id: Optional[str] = Query(default=None),
    team_name: Optional[str] = Query(default=None),
    limit: int = Query(default=5, ge=1, le=50),
):
    all_data = await _get_fixtures_payload(
        league=league,
        team_id=team_id,
        team_name=team_name,
        past_limit=60,
        upcoming_limit=max(10, int(limit) * 2),
    )
    fixtures = all_data.get("fixtures") or []

    upcoming = [f for f in fixtures if (f.get("status") != "finished")]
    upcoming.sort(key=lambda x: (x.get("date") or "", x.get("time") or ""))

    sliced = upcoming[: int(limit)]
    return {
        "league": league,
        "team": all_data.get("team"),
        "fixtures": sliced,
        "count": len(sliced),
        "data_source": all_data.get("data_source", "whoscored"),
        "cache_info": all_data.get("cache_info", ""),
    }


@router.get("/next-opponent")
async def get_next_opponent(
    league: str = Query(default=str(getattr(settings, "WHOSCORED_DEFAULT_LEAGUE", "ENG-Premier League"))),
    team_id: Optional[str] = Query(default=None),
    team_name: Optional[str] = Query(default=None),
):
    data = await get_upcoming_fixtures(league=league, team_id=team_id, team_name=team_name, limit=1)
    fixture = (data.get("fixtures") or [None])[0]
    return {
        "league": data.get("league"),
        "team": data.get("team"),
        "next_fixture": fixture,
        "data_source": data.get("data_source", "whoscored"),
        "cache_info": data.get("cache_info", ""),
    }
