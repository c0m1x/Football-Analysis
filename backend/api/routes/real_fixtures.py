"""
Real Fixtures API - Gil Vicente fixtures with Redis caching
"""
from fastapi import APIRouter, HTTPException
from utils.api_client import get_api_client
from utils.logger import setup_logger
from services.cache_service import get_cache_service
from services.match_analysis_service import get_match_analysis_service
from services.advanced_stats_analyzer import get_advanced_stats_analyzer
from typing import Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

router = APIRouter()
logger = setup_logger(__name__)

LISBON_TZ = ZoneInfo('Europe/Lisbon')

def _utc_to_lisbon(utc_iso: str) -> tuple[str, str, str]:
    # Accepts '...Z' or '+00:00'
    dt_utc = datetime.fromisoformat(utc_iso.replace('Z', '+00:00'))
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_local = dt_utc.astimezone(LISBON_TZ)
    date_str = dt_local.date().isoformat()
    time_str = dt_local.time().replace(microsecond=0).isoformat()
    iso_local = dt_local.replace(microsecond=0).isoformat()
    return date_str, time_str, iso_local

def _normalize_fixture(f: dict) -> dict:
    # Backward/forward compatible fixture shape for frontend
    if 'id' not in f and 'match_id' in f:
        f['id'] = f.get('match_id')
    if 'match_id' not in f and 'id' in f:
        f['match_id'] = f.get('id')
    if 'is_home' not in f and 'gil_vicente_home' in f:
        f['is_home'] = bool(f.get('gil_vicente_home'))
    if 'gil_vicente_home' not in f and 'is_home' in f:
        f['gil_vicente_home'] = bool(f.get('is_home'))    # Ensure date/time are local (Europe/Lisbon) and parseable
    utc_iso = f.get('utc_time')
    if isinstance(utc_iso, str) and 'T' in utc_iso:
        d, t, iso_local = _utc_to_lisbon(utc_iso)
        f['date'] = d
        f['time'] = t
        f['datetime'] = iso_local
    else:
        # Fall back: if datetime has offset/Z, convert; if naive, keep as-is
        dt = f.get('datetime')
        if isinstance(dt, str) and 'T' in dt and (dt.endswith('Z') or '+' in dt or '-' in dt[10:]):
            try:
                d, t, iso_local = _utc_to_lisbon(dt)
                f['date'] = d
                f['time'] = t
                f['datetime'] = iso_local
            except Exception:
                pass
        if not f.get('time') or f.get('time') == 'TBD':
            f['time'] = '00:00:00'

    # Add a display score + result for finished matches if missing
    if f.get('status') == 'finished':
        hs = f.get('home_score')
        aw = f.get('away_score')
        if hs is not None and aw is not None:
            if isinstance(f.get('score'), dict) and 'display' in f['score']:
                pass
            else:
                f['score'] = {'home': hs, 'away': aw, 'display': f"{hs}-{aw}"}
            # Result from Gil Vicente perspective
            is_home = bool(f.get('is_home'))
            gil = hs if is_home else aw
            opp = aw if is_home else hs
            if 'result' not in f:
                f['result'] = 'W' if gil > opp else ('D' if gil == opp else 'L')

    return f

# --- Opponent profile helpers ---

def _mean(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _mode_str(values):
    values = [v for v in values if isinstance(v, str) and v]
    if not values:
        return None
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _team_name_from_fixtures(fixtures: list[dict], team_id: str) -> Optional[str]:
    tid = str(team_id)
    for f in fixtures:
        if str(f.get('opponent_id')) == tid:
            name = f.get('opponent_name')
            if isinstance(name, str) and name:
                return name
    return None


def _result_letter(match: dict, team_id: str) -> str:
    tid = str(team_id)
    home = match.get('home', {}) or {}
    away = match.get('away', {}) or {}

    is_home = str(home.get('id')) == tid
    team_score = home.get('score') if is_home else away.get('score')
    opp_score = away.get('score') if is_home else home.get('score')

    try:
        team_score = int(team_score)
    except Exception:
        team_score = 0
    try:
        opp_score = int(opp_score)
    except Exception:
        opp_score = 0

    if team_score > opp_score:
        return 'W'
    if team_score < opp_score:
        return 'L'
    return 'D'


def _simplify_recent_match(match: dict, team_id: str, team_name: str) -> dict:
    home = match.get('home', {}) or {}
    away = match.get('away', {}) or {}
    status = match.get('status', {}) or {}

    is_home = str(home.get('id')) == str(team_id)
    team_score = home.get('score') if is_home else away.get('score')
    opp_score = away.get('score') if is_home else home.get('score')

    opponent_name = away.get('name') if is_home else home.get('name')

    return {
        'date': status.get('utcTime', ''),
        'home_team': team_name if is_home else opponent_name,
        'away_team': opponent_name if is_home else team_name,
        'score': f"{team_score}-{opp_score}",
        'result': _result_letter(match, team_id),
    }


def _build_tactical_profile(recent_analyzed: list[dict], form_summary: dict) -> dict:
    poss = _mean([(m.get('possession_control', {}) or {}).get('possession_percent') for m in recent_analyzed])
    ppda = _mean([(m.get('pressing_structure', {}) or {}).get('PPDA') for m in recent_analyzed])
    xg = _mean([(m.get('expected_metrics', {}) or {}).get('xG') for m in recent_analyzed])
    conv = _mean([(m.get('shooting_finishing', {}) or {}).get('shot_conversion_rate') for m in recent_analyzed])
    long_balls = _mean([(m.get('possession_control', {}) or {}).get('long_balls_attempted') for m in recent_analyzed])

    conceded_rate = form_summary.get('avg_goals_conceded')
    scored_rate = form_summary.get('avg_goals_scored')

    formation = _mode_str([(m.get('team_shape', {}) or {}).get('formation_detected') for m in recent_analyzed])

    if poss is not None and poss >= 55:
        style = 'Possession-based control'
    elif poss is not None and poss <= 45:
        style = 'Direct / counter-attacking'
    else:
        style = 'Balanced'

    if long_balls is not None and long_balls >= 18:
        style = f"{style} (vertical / long-ball tendency)"

    strengths = []
    weaknesses = []
    recommendations = []

    if ppda is not None and ppda < 11:
        strengths.append('Aggressive pressing (low PPDA)')
    if xg is not None and xg >= 1.4:
        strengths.append('Creates high-quality chances (xG)')
    if conv is not None and conv >= 14:
        strengths.append('Efficient finishing')
    if conceded_rate is not None and conceded_rate <= 1.0:
        strengths.append('Defensive solidity (low goals conceded)')

    if conv is not None and conv <= 10:
        weaknesses.append('Low shot conversion (finishing efficiency)')
    if poss is not None and poss >= 55 and (xg is not None and xg <= 1.0):
        weaknesses.append('Sterile possession (low penetration)')
    if conceded_rate is not None and conceded_rate >= 1.5:
        weaknesses.append('Concedes frequently (defensive fragility)')
    if ppda is not None and ppda < 11 and (conceded_rate is not None and conceded_rate >= 1.5):
        weaknesses.append('High press can be exploited behind the first line')

    if poss is not None and poss >= 55:
        recommendations.append('Stay compact, force wide circulation, counter into half-spaces')
    if ppda is not None and ppda < 12:
        recommendations.append('Use quick bounce passes and third-man runs to escape the press')
    if long_balls is not None and long_balls >= 18:
        recommendations.append('Win aerial duels and attack second balls; protect central channels')
    if conv is not None and conv <= 10:
        recommendations.append('Protect the box and allow low-quality shots from distance')
    if conceded_rate is not None and conceded_rate >= 1.5:
        recommendations.append('Attack transitions quickly; isolate defenders 1v1')

    if not formation:
        formation = '4-2-3-1'
    if not strengths:
        strengths = ['No clear strengths detected (limited data).']
    if not weaknesses:
        weaknesses = ['No clear weaknesses detected (limited data).']
    if not recommendations:
        recommendations = ['Collect more matches for stronger tactical recommendations.']

    return {
        'formation': formation,
        'playing_style': style,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'recommendations': recommendations,
        'estimated': True,
        'inputs': {
            'possession_avg': poss,
            'ppda_avg': ppda,
            'xg_avg': xg,
            'conversion_avg': conv,
            'avg_goals_scored': scored_rate,
            'avg_goals_conceded': conceded_rate,
        },
    }


@router.get("/fixtures/all")
async def get_all_fixtures():
    """
    Get all Gil Vicente fixtures (past and upcoming)
    
    🔄 CACHED: Results cached for 1 hour to minimize API token usage
    """
    # Check cache first
    cache = get_cache_service()
    cached_data = await cache.get("fixtures", "all_gil_vicente")
    
    if cached_data:
        logger.info("🎯 Returning cached fixtures")
        fixtures = cached_data.get('fixtures') or []
        if isinstance(fixtures, list):
            cached_data['fixtures'] = [_normalize_fixture(f) if isinstance(f, dict) else f for f in fixtures]
        cached_data["data_source"] = "cache"
        cached_data["cache_info"] = "Fixtures from cache (1h TTL)"
        return cached_data
    
    # Cache miss - fetch from API
    logger.info("❌ Cache miss - fetching fixtures from API")
    
    try:
        api_client = get_api_client()
        
        # Fetch all matches for Liga Portugal
        data = await api_client.get(
            "/football-get-all-matches-by-league",
            params={"leagueid": 61}
        )
        
        if not data or ('matches' not in data and 'response' not in data):
            raise HTTPException(status_code=500, detail="Failed to fetch fixtures")
        
        # Handle both response formats
        all_matches = data.get('response', {}).get('matches', data.get('matches', []))
        
        # Filter Gil Vicente matches
        gil_vicente_fixtures = []
        for match in all_matches:
            # Check if Gil Vicente is involved (ID: 9764)
            home_id = str(match.get('home', {}).get('id', ''))
            away_id = str(match.get('away', {}).get('id', ''))
            
            if '9764' in [home_id, away_id]:
                is_home = home_id == '9764'
                opponent = match.get('away') if is_home else match.get('home')
                
                # Extract status info
                status_obj = match.get('status', {})
                utc_time = status_obj.get('utcTime', '')
                is_finished = status_obj.get('finished', False)
                
                # Convert UTC time to Europe/Lisbon local time
                if utc_time and 'T' in utc_time:
                    match_date, match_time, iso_local = _utc_to_lisbon(utc_time)
                else:
                    match_date, match_time, iso_local = 'Unknown', '00:00:00', None
                
                # Flatten structure for frontend compatibility
                home_score = match.get('home', {}).get('score') if is_finished else None
                away_score = match.get('away', {}).get('score') if is_finished else None

                fixture = {
                    # IDs
                    "id": match.get('id'),
                    "match_id": match.get('id'),

                    # Date/time
                    "utc_time": utc_time or None,
                    "datetime": iso_local,
                    "date": match_date,
                    "time": match_time if match_time != 'TBD' else '00:00:00',

                    # Status + location
                    "status": "finished" if is_finished else "upcoming",
                    "is_home": is_home,
                    "gil_vicente_home": is_home,

                    # Opponent
                    "opponent_id": str(opponent.get('id')),
                    "opponent_name": opponent.get('name'),

                    # Scores
                    "home_score": home_score,
                    "away_score": away_score,
                }

                if is_finished and home_score is not None and away_score is not None:
                    fixture["score"] = {"home": home_score, "away": away_score, "display": f"{home_score}-{away_score}"}
                    # Result from Gil Vicente perspective
                    gil = home_score if is_home else away_score
                    opp = away_score if is_home else home_score
                    fixture["result"] = "W" if gil > opp else ("D" if gil == opp else "L")

                fixture = _normalize_fixture(fixture)
                
                gil_vicente_fixtures.append(fixture)
        
        # Sort by date
        gil_vicente_fixtures.sort(key=lambda x: x['date'])
        
        # Separate past and upcoming
        now = datetime.now().strftime("%Y-%m-%d")
        past_fixtures = [f for f in gil_vicente_fixtures if f['date'] < now or f['status'] == 'finished']
        upcoming_fixtures = [f for f in gil_vicente_fixtures if f['date'] >= now and f['status'] == 'upcoming']
        
        result = {
            "total_fixtures": len(gil_vicente_fixtures),
            "past_fixtures": len(past_fixtures),
            "upcoming_fixtures": len(upcoming_fixtures),
            "fixtures": gil_vicente_fixtures,
            "data_source": "api",
            "cache_info": "Fresh fixtures from API (cached for 1h)"
        }
        
        # Cache for 1 hour
        await cache.set("fixtures", "all_gil_vicente", result, ttl=3600)
        logger.info(f"💾 Cached {len(gil_vicente_fixtures)} fixtures")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching fixtures: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fixtures/upcoming")

@router.get("/opponents")
async def get_opponents():
    """
    Get list of opponents from fixtures
    
    🔄 CACHED: Extracted from fixtures data
    """
    # Get all fixtures (will use cache if available)
    all_data = await get_all_fixtures()
    
    # Extract unique opponents
    opponents_dict = {}
    for fixture in all_data['fixtures']:
        opponent_id = fixture['opponent_id']
        opponent_name = fixture['opponent_name']
        
        if opponent_id not in opponents_dict:
            opponents_dict[opponent_id] = {
                "id": opponent_id,
                "name": opponent_name
            }
    
    # Convert to list and sort
    opponents = list(opponents_dict.values())
    opponents.sort(key=lambda x: x['name'])
    
    return {
        "season": 2025,
        "opponents": opponents,
        "count": len(opponents),
        "source": "Extracted from fixtures",
        "data_source": all_data.get('data_source', 'api'),
        "cache_info": "Opponents from fixtures data"
    }


# --- Opponent profile endpoints ---

@router.get('/opponents/{team_id}/recent')
async def get_opponent_recent_form(team_id: str, limit: int = 5):
    all_data = await get_all_fixtures()
    fixtures = all_data.get('fixtures') or []

    team_name = _team_name_from_fixtures(fixtures, team_id)
    if not team_name:
        raise HTTPException(status_code=404, detail='Opponent not found in fixtures')

    analysis_service = get_match_analysis_service()
    analysis = await analysis_service.analyze_match(str(team_id), team_name)

    opp_form = analysis.get('opponent_form', {}) or {}
    recent_matches = opp_form.get('recent_matches') or []
    form_summary = opp_form.get('form_summary', {}) or {}

    recent_sorted = list(recent_matches)
    recent_sorted.sort(key=lambda m: (m.get('status', {}) or {}).get('utcTime', ''), reverse=True)
    letters = [_result_letter(m, team_id) for m in recent_sorted[: max(0, int(limit))]]
    form_letters = ''.join(letters)

    wins = int(form_summary.get('wins', 0) or 0)
    draws = int(form_summary.get('draws', 0) or 0)
    losses = int(form_summary.get('losses', 0) or 0)
    games = int(form_summary.get('games_played', len(letters)) or 0)
    goals_scored = int(form_summary.get('goals_scored', 0) or 0)
    goals_conceded = int(form_summary.get('goals_conceded', 0) or 0)

    form_percentage = round((wins / games) * 100) if games > 0 else 0

    simplified = [_simplify_recent_match(m, team_id, team_name) for m in recent_sorted[: max(0, int(limit))]]

    return {
        'team': {'id': str(team_id), 'name': team_name},
        'form': form_letters or (form_summary.get('form_string') or ''),
        'recent_matches': simplified,
        'statistics': {
            'goals_scored': goals_scored,
            'goals_conceded': goals_conceded,
            'wins': wins,
            'draws': draws,
            'losses': losses,
            'form_percentage': form_percentage,
        },
        'source': 'Derived from league matches',
        'data_source': analysis.get('data_source', 'api'),
    }


@router.get('/opponents/{team_id}/tactical')
async def get_opponent_tactical_profile(team_id: str, limit: int = 5):
    all_data = await get_all_fixtures()
    fixtures = all_data.get('fixtures') or []

    team_name = _team_name_from_fixtures(fixtures, team_id)
    if not team_name:
        raise HTTPException(status_code=404, detail='Opponent not found in fixtures')

    analysis_service = get_match_analysis_service()
    analysis = await analysis_service.analyze_match(str(team_id), team_name)

    opp_form = analysis.get('opponent_form', {}) or {}
    recent_matches = opp_form.get('recent_matches') or []
    form_summary = opp_form.get('form_summary', {}) or {}

    stats_analyzer = get_advanced_stats_analyzer()
    recent_analyzed = stats_analyzer.analyze_recent_games(recent_matches, team_name, limit=int(limit))

    profile = _build_tactical_profile(recent_analyzed, form_summary)

    return {
        'team': {'id': str(team_id), 'name': team_name},
        'formation': profile.get('formation'),
        'playing_style': profile.get('playing_style'),
        'strengths': profile.get('strengths') or [],
        'weaknesses': profile.get('weaknesses') or [],
        'recommendations': profile.get('recommendations') or [],
        'estimated': profile.get('estimated', True),
        'inputs': profile.get('inputs', {}),
        'source': 'Heuristic profile from recent matches',
    }
