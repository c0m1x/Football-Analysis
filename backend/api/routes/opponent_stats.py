"""Opponent Statistics API - Comprehensive deep analytics with Redis caching.

This endpoint primarily supports tactical scouting:
- Possession & control
- Shooting & finishing
- Expected metrics + chance creation
- Defensive intelligence + pressing structure
- Spatial/positional proxies (limited by upstream data)

Important: the upstream API used in this project does not provide event-level
tracking (touches per zone, heatmaps, overloads, etc.). Those fields are either
inferred or returned as unavailable.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from utils.logger import setup_logger

from services.match_analysis_service import get_match_analysis_service
from services.cache_service import get_cache_service
from services.advanced_stats_analyzer import get_advanced_stats_analyzer
from config.settings import get_settings

router = APIRouter()
logger = setup_logger(__name__)
settings = get_settings()


def _safe_div(n: float, d: float, default: float = 0.0) -> float:
    try:
        if d == 0:
            return default
        return n / d
    except Exception:
        return default


def _mean(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _aggregate_tactical(recent_analyzed):
    """Aggregate a list of per-match tactical stats into team-level averages."""
    if not recent_analyzed:
        return {
            "estimated": True,
            "matches_analyzed": 0,
        }

    possession = [
        (m.get("possession_control", {}) or {}).get("possession_percent")
        for m in recent_analyzed
    ]
    time_opp_half = [
        (m.get("possession_control", {}) or {}).get("time_in_opponent_half")
        for m in recent_analyzed
    ]
    pass_acc = [
        (m.get("possession_control", {}) or {}).get("pass_accuracy")
        for m in recent_analyzed
    ]
    passes_per_min = [
        (m.get("possession_control", {}) or {}).get("passes_per_minute")
        for m in recent_analyzed
    ]

    long_attempted = [
        (m.get("possession_control", {}) or {}).get("long_balls_attempted")
        for m in recent_analyzed
    ]
    long_completed = [
        (m.get("possession_control", {}) or {}).get("long_balls_completed")
        for m in recent_analyzed
    ]

    shots = [(m.get("shooting_finishing", {}) or {}).get("total_shots") for m in recent_analyzed]
    shots_on = [
        (m.get("shooting_finishing", {}) or {}).get("shots_on_target")
        for m in recent_analyzed
    ]
    conv = [
        (m.get("shooting_finishing", {}) or {}).get("shot_conversion_rate")
        for m in recent_analyzed
    ]
    inside = [
        (m.get("shooting_finishing", {}) or {}).get("shots_inside_box")
        for m in recent_analyzed
    ]
    outside = [
        (m.get("shooting_finishing", {}) or {}).get("shots_outside_box")
        for m in recent_analyzed
    ]
    big_created = [
        (m.get("shooting_finishing", {}) or {}).get("big_chances_created")
        for m in recent_analyzed
    ]
    big_missed = [
        (m.get("shooting_finishing", {}) or {}).get("big_chances_missed")
        for m in recent_analyzed
    ]

    xg = [(m.get("expected_metrics", {}) or {}).get("xG") for m in recent_analyzed]
    xg_shot = [
        (m.get("expected_metrics", {}) or {}).get("xG_per_shot")
        for m in recent_analyzed
    ]
    xg_open = [
        (m.get("expected_metrics", {}) or {}).get("xG_from_open_play")
        for m in recent_analyzed
    ]
    xg_set = [
        (m.get("expected_metrics", {}) or {}).get("xG_from_set_pieces")
        for m in recent_analyzed
    ]
    xa = [(m.get("expected_metrics", {}) or {}).get("xA") for m in recent_analyzed]

    key_passes = [
        (m.get("chance_creation", {}) or {}).get("key_passes")
        for m in recent_analyzed
    ]
    prog_passes = [
        (m.get("chance_creation", {}) or {}).get("progressive_passes")
        for m in recent_analyzed
    ]
    final_third = [
        (m.get("chance_creation", {}) or {}).get("passes_into_final_third")
        for m in recent_analyzed
    ]
    pen_area = [
        (m.get("chance_creation", {}) or {}).get("passes_into_penalty_area")
        for m in recent_analyzed
    ]
    crosses = [
        (m.get("chance_creation", {}) or {}).get("crosses_attempted")
        for m in recent_analyzed
    ]
    crosses_acc = [
        (m.get("chance_creation", {}) or {}).get("crosses_accurate")
        for m in recent_analyzed
    ]
    cutbacks = [(m.get("chance_creation", {}) or {}).get("cutbacks") for m in recent_analyzed]

    tackles_att = [
        (m.get("defensive_actions", {}) or {}).get("tackles_attempted")
        for m in recent_analyzed
    ]
    tackles_won = [
        (m.get("defensive_actions", {}) or {}).get("tackles_won")
        for m in recent_analyzed
    ]
    interceptions = [
        (m.get("defensive_actions", {}) or {}).get("interceptions")
        for m in recent_analyzed
    ]
    blocks = [(m.get("defensive_actions", {}) or {}).get("blocks") for m in recent_analyzed]
    clearances = [
        (m.get("defensive_actions", {}) or {}).get("clearances")
        for m in recent_analyzed
    ]
    duels = [
        (m.get("defensive_actions", {}) or {}).get("defensive_duels_won_percent")
        for m in recent_analyzed
    ]

    ppda = [(m.get("pressing_structure", {}) or {}).get("PPDA") for m in recent_analyzed]
    high_turnovers = [
        (m.get("pressing_structure", {}) or {}).get("high_turnovers_won")
        for m in recent_analyzed
    ]
    counter_press = [
        (m.get("pressing_structure", {}) or {}).get("counter_press_recoveries")
        for m in recent_analyzed
    ]

    # Team shape proxies (strings)
    avg_line = [
        (m.get("team_shape", {}) or {}).get("avg_team_line_height")
        for m in recent_analyzed
    ]
    def_line = [
        (m.get("team_shape", {}) or {}).get("defensive_line_height")
        for m in recent_analyzed
    ]
    between = [
        (m.get("team_shape", {}) or {}).get("distance_between_lines")
        for m in recent_analyzed
    ]
    compact = [
        (m.get("team_shape", {}) or {}).get("team_compactness")
        for m in recent_analyzed
    ]
    width = [(m.get("team_shape", {}) or {}).get("width_usage") for m in recent_analyzed]

    # Simple mode for categorical strings
    def _mode_str(values):
        values = [v for v in values if isinstance(v, str) and v]
        if not values:
            return None
        counts = {}
        for v in values:
            counts[v] = counts.get(v, 0) + 1
        return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    return {
        "estimated": any(bool(m.get('estimated', True)) for m in recent_analyzed),
        "matches_analyzed": len(recent_analyzed),
        "possession_control": {
            "possession_percent_avg": _mean(possession),
            "time_in_opponent_half_avg": _mean(time_opp_half),
            "pass_accuracy_avg": _mean(pass_acc),
            "passes_per_minute_avg": _mean(passes_per_min),
            "long_balls_attempted_avg": _mean(long_attempted),
            "long_balls_completed_avg": _mean(long_completed),
        },
        "shooting_finishing": {
            "total_shots_avg": _mean(shots),
            "shots_on_target_avg": _mean(shots_on),
            "shot_conversion_rate_avg": _mean(conv),
            "shots_inside_box_avg": _mean(inside),
            "shots_outside_box_avg": _mean(outside),
            "big_chances_created_avg": _mean(big_created),
            "big_chances_missed_avg": _mean(big_missed),
        },
        "expected_metrics": {
            "xG_avg": _mean(xg),
            "xG_per_shot_avg": _mean(xg_shot),
            "xG_from_open_play_avg": _mean(xg_open),
            "xG_from_set_pieces_avg": _mean(xg_set),
            "xA_avg": _mean(xa),
        },
        "chance_creation": {
            "key_passes_avg": _mean(key_passes),
            "progressive_passes_avg": _mean(prog_passes),
            "passes_into_final_third_avg": _mean(final_third),
            "passes_into_penalty_area_avg": _mean(pen_area),
            "crosses_attempted_avg": _mean(crosses),
            "crosses_accurate_avg": _mean(crosses_acc),
            "cutbacks_avg": _mean(cutbacks),
        },
        "defensive_actions": {
            "tackles_attempted_avg": _mean(tackles_att),
            "tackles_won_avg": _mean(tackles_won),
            "interceptions_avg": _mean(interceptions),
            "blocks_avg": _mean(blocks),
            "clearances_avg": _mean(clearances),
            "defensive_duels_won_percent_avg": _mean(duels),
        },
        "pressing_structure": {
            "PPDA_avg": _mean(ppda),
            "high_turnovers_won_avg": _mean(high_turnovers),
            "counter_press_recoveries_avg": _mean(counter_press),
            # zone-level pressing is unavailable without event data
            "pressing_intensity_zones": None,
        },
        "team_shape": {
            "avg_team_line_height_mode": _mode_str(avg_line),
            "defensive_line_height_avg": _mean(def_line),
            "distance_between_lines_mode": _mode_str(between),
            "team_compactness_mode": _mode_str(compact),
            "width_usage_mode": _mode_str(width),
            # event/positional tracking unavailable
            "touches_per_zone": None,
            "half_space_occupation": None,
            "heatmaps": None,
            "overloads": None,
        },
    }




def _clamp(v: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return lo


def _parse_percent(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if s.endswith('%'):
            s = s[:-1].strip()
        try:
            return float(s)
        except Exception:
            return None
    return None


def _mode_str(values):
    values = [v for v in values if isinstance(v, str) and v]
    if not values:
        return None
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _aggregate_set_pieces(recent_analyzed):
    # Aggregate set-piece analytics from per-match analyzer output
    if not recent_analyzed:
        return {'estimated': True, 'matches_analyzed': 0}

    corners_taken = []
    xg_corners = []
    first_contact_pct = []
    second_balls = []
    set_piece_goals = []

    corners_conceded = []
    marking_types = []
    clear_under_pressure = []
    shots_conceded_sp = []
    weaknesses = []

    short_share = []

    for m in recent_analyzed:
        sp = (m.get('set_pieces', {}) or {})
        att = (sp.get('attacking', {}) or {})
        deff = (sp.get('defensive', {}) or {})
        pc = (m.get('possession_control', {}) or {})

        corners_taken.append(att.get('corners_taken'))
        xg_corners.append(att.get('xG_from_corners'))
        first_contact_pct.append(_parse_percent(att.get('first_contact_success')))
        second_balls.append(att.get('second_ball_recoveries'))
        set_piece_goals.append(att.get('set_piece_goals'))

        corners_conceded.append(deff.get('corners_conceded'))
        marking_types.append(deff.get('marking_type'))
        clear_under_pressure.append(deff.get('clearances_under_pressure'))
        shots_conceded_sp.append(deff.get('shots_conceded_after_set_pieces'))
        weaknesses.append(deff.get('set_piece_weakness'))

        poss = pc.get('possession_percent')
        if poss is not None:
            share = 0.35 + 0.005 * (float(poss) - 45.0)
            short_share.append(_clamp(share, 0.2, 0.7))

    first_contact_avg = _mean(first_contact_pct)
    short_share_avg = _mean(short_share)
    if short_share_avg is None:
        short_share_avg = 0.4

    short_success = None
    long_success = None
    if first_contact_avg is not None:
        short_success = _clamp(first_contact_avg * 0.9, 0.0, 100.0)
        long_success = _clamp(first_contact_avg * 1.05, 0.0, 100.0)

    marking_mode = _mode_str(marking_types)
    weakness_mode = _mode_str(weaknesses)

    shots_sp_avg = _mean(shots_conceded_sp)
    defensive_success_rating = None
    if shots_sp_avg is not None:
        base = 100.0 - float(shots_sp_avg) * 10.0
        if weakness_mode == 'High':
            base -= 20.0
        elif weakness_mode == 'Low':
            base += 10.0
        defensive_success_rating = _clamp(base, 0.0, 100.0)

    return {
        'estimated': any(bool(m.get('estimated', True)) for m in recent_analyzed),
        'matches_analyzed': len(recent_analyzed),
        'attacking_set_pieces': {
            'corners_taken_avg': _mean(corners_taken),
            'xG_from_corners_avg': _mean(xg_corners),
            'first_contact_success_percent_avg': first_contact_avg,
            'second_ball_recoveries_avg': _mean(second_balls),
            'set_piece_goals_avg': _mean(set_piece_goals),
            'short_corners_share_avg': short_share_avg * 100.0,
            'long_corners_share_avg': (1.0 - short_share_avg) * 100.0,
            'short_corners_success_percent_avg': short_success,
            'long_corners_success_percent_avg': long_success,
        },
        'defensive_set_pieces': {
            'corners_conceded_avg': _mean(corners_conceded),
            'marking_type_mode': marking_mode,
            'zone_vs_man_marking_success_rating': defensive_success_rating,
            'clearances_under_pressure_avg': _mean(clear_under_pressure),
            'shots_conceded_after_set_pieces_avg': shots_sp_avg,
        },
        'limitations': {
            'short_vs_long_corner_success': 'Estimated proxy (no event data)',
            'zone_vs_man_marking_success': 'Estimated proxy (no event data)',
        },
    }


def _aggregate_contextual(recent_analyzed):
    # Aggregate contextual & psychological variables from analyzer output
    if not recent_analyzed:
        return {'estimated': True, 'matches_analyzed': 0}

    scoreline = []
    momentum = []
    pressure = []
    fatigue = []
    mental = []
    location = []

    for m in recent_analyzed:
        ctx = (m.get('context', {}) or {})
        mi = (m.get('match_info', {}) or {})
        scoreline.append(ctx.get('scoreline_state'))
        momentum.append(ctx.get('game_momentum'))
        pressure.append(ctx.get('pressure_handling'))
        fatigue.append(ctx.get('fatigue_indicators'))
        mental.append(ctx.get('mental_strength'))
        location.append(mi.get('location'))

    def _dist(values):
        out = {}
        for v in values:
            if not isinstance(v, str) or not v:
                continue
            out[v] = out.get(v, 0) + 1
        return out

    loc_dist = _dist(location)
    total_loc = sum(loc_dist.values())

    return {
        'estimated': any(bool(m.get('estimated', True)) for m in recent_analyzed),
        'matches_analyzed': len(recent_analyzed),
        'scoreline_state_distribution': _dist(scoreline),
        'home_away_distribution': loc_dist,
        'home_share_percent': round((loc_dist.get('Home', 0) / total_loc) * 100, 1) if total_loc else None,
        'away_share_percent': round((loc_dist.get('Away', 0) / total_loc) * 100, 1) if total_loc else None,
        'momentum_mode': _mode_str(momentum),
        'pressure_handling_mode': _mode_str(pressure),
        'fatigue_indicators_mode': _mode_str(fatigue),
        'mental_strength_mode': _mode_str(mental),
        'minute_of_match': None,
        'substitutions_impact': None,
        'referee_foul_tendencies': None,
        'limitations': {
            'minute_of_match': 'Unavailable without event timeline',
            'substitutions_impact': 'Unavailable without lineup/substitution events',
            'referee_foul_tendencies': 'Unavailable without referee + foul event data',
        },
    }


@router.get("/opponent-stats/{opponent_id}")
async def get_opponent_statistics(
    opponent_id: str,
    opponent_name: str = Query(..., description="Opponent team name"),
):
    """Get comprehensive opponent statistics with deep analytics.

    Cached for 24 hours to prevent API token waste.
    """

    cache = get_cache_service()
    cache_key = f"v3:{opponent_id}_{opponent_name}"

    cached_data = await cache.get("opponent_stats", cache_key)
    if cached_data:
        cached_data["data_source"] = "cache"
        cached_data["cache_info"] = "Statistics from cache (24h TTL)"
        return cached_data

    service = get_match_analysis_service()

    try:
        full_analysis = await service.analyze_match(opponent_id, opponent_name)
        opponent_form = full_analysis.get("opponent_form", {}) or {}
        form_summary = opponent_form.get("form_summary", {}) or {}
        recent_matches = opponent_form.get("recent_matches", []) or []

        # Transform to existing frontend-expected format
        overall_performance = {
            "form_string": form_summary.get("form_string", "N/A"),
            "goals_per_game": form_summary.get("avg_goals_scored", 0),
            "conceded_per_game": form_summary.get("avg_goals_conceded", 0),
            "points_per_game": round(
                _safe_div(form_summary.get("points", 0), max(form_summary.get("games_played", 1), 1), 0.0),
                2,
            ),
        }

        # Split matches by home/away
        home_matches = [m for m in recent_matches if str((m.get("home", {}) or {}).get("id")) == str(opponent_id)]
        away_matches = [m for m in recent_matches if str((m.get("away", {}) or {}).get("id")) == str(opponent_id)]

        def calc_perf(matches, team_id):
            if not matches:
                return {"matches": 0, "form": "N/A", "goals_per_game": 0, "conceded_per_game": 0}

            wins = draws = losses = 0
            goals_scored = goals_conceded = 0

            for m in matches:
                home = m.get("home", {}) or {}
                away = m.get("away", {}) or {}
                is_home_local = str(home.get("id")) == str(team_id)

                team_score = home.get("score") if is_home_local else away.get("score")
                opp_score = away.get("score") if is_home_local else home.get("score")

                try:
                    team_score = int(team_score)
                except Exception:
                    team_score = 0
                try:
                    opp_score = int(opp_score)
                except Exception:
                    opp_score = 0

                goals_scored += team_score
                goals_conceded += opp_score

                if team_score > opp_score:
                    wins += 1
                elif team_score == opp_score:
                    draws += 1
                else:
                    losses += 1

            return {
                "matches": len(matches),
                "form": f"{wins}W-{draws}D-{losses}L",
                "goals_per_game": round(_safe_div(goals_scored, len(matches), 0.0), 2),
                "conceded_per_game": round(_safe_div(goals_conceded, len(matches), 0.0), 2),
            }

        home_performance = calc_perf(home_matches, opponent_id)
        away_performance = calc_perf(away_matches, opponent_id)

        # Match breakdown (keep structure)
        match_breakdown = []
        for idx, match in enumerate(recent_matches[:5], start=1):
            home = match.get("home", {}) or {}
            away = match.get("away", {}) or {}

            is_home_local = str(home.get("id")) == str(opponent_id)
            team_score = home.get("score") if is_home_local else away.get("score")
            opp_score = away.get("score") if is_home_local else home.get("score")
            try:
                team_score = int(team_score)
            except Exception:
                team_score = 0
            try:
                opp_score = int(opp_score)
            except Exception:
                opp_score = 0

            opp_name = (away.get("name") if is_home_local else home.get("name")) or "Unknown"
            result = "W" if team_score > opp_score else ("D" if team_score == opp_score else "L")

            utc_time = (match.get("status", {}) or {}).get("utcTime", "N/A")
            match_breakdown.append(
                {
                    "game_number": idx,
                    "date": str(utc_time)[:10] if isinstance(utc_time, str) else "N/A",
                    "opponent": opp_name,
                    "location": "Home" if is_home_local else "Away",
                    "score": f"{team_score}-{opp_score}",
                    "result": result,
                }
            )

        # Psychological profile (existing)
        wins = form_summary.get("wins", 0)
        games = max(form_summary.get("games_played", 1), 1)
        psychological_profile = {
            "mental_strength": "Strong" if wins >= games * 0.6 else "Average" if wins >= games * 0.3 else "Weak",
            "resilience_score": min(100, int((_safe_div(wins, games, 0.0) * 100) + 20)),
            "handles_pressure": "Well" if form_summary.get("goal_difference", 0) >= 0 else "Poorly",
            "momentum": "Positive" if wins > form_summary.get("losses", 0) else "Negative",
        }

        # Form trends
        form_trends = {
            "trend": "Upward" if wins > form_summary.get("losses", 0) else "Downward",
            "recent_form_points": form_summary.get("points", 0),
        }

        # Tactical foundation stats (NEW)
        analyzer = get_advanced_stats_analyzer()
        recent_games_tactical = full_analysis.get("recent_games_tactical") or []
        if not recent_games_tactical:
            recent_games_tactical = analyzer.analyze_recent_games(recent_matches, opponent_name, limit=5)
        tactical_foundation = _aggregate_tactical(recent_games_tactical)
        set_piece_analytics = _aggregate_set_pieces(recent_games_tactical)
        contextual_psychological = _aggregate_contextual(recent_games_tactical)

        result = {
            "opponent": opponent_name,
            "opponent_id": opponent_id,
            "historical_context": {
                "baseline_season": getattr(settings, "HISTORICAL_BASELINE_SEASON", "2023/24"),
                "validation_note": getattr(
                    settings,
                    "HISTORICAL_VALIDATION_NOTE",
                    "Baseado em dados da época 2023/24 — validar com observação recente do adversário.",
                ),
            },
            "data_quality": {
                "matches_analyzed": len(recent_matches),
                "time_period": "Last 5 matches",
            },
            "overall_performance": overall_performance,
            "home_performance": home_performance,
            "away_performance": away_performance,
            "match_breakdown": match_breakdown,
            "psychological_profile": psychological_profile,
            "form_trends": form_trends,
            "opponent_form": opponent_form,
            # Existing (last-game) advanced stats from the analysis pipeline
            "opponent_advanced_stats": full_analysis.get("opponent_advanced_stats", {}),
            # NEW: per-match tactical stats + aggregates
            "recent_games_tactical": recent_games_tactical,
            "tactical_foundation": tactical_foundation,
            "set_piece_analytics": set_piece_analytics,
            "contextual_psychological": contextual_psychological,
            "data_source": full_analysis.get("data_source", "whoscored"),
            "cache_info": (
                "Fresh data from WhoScored (cached for 24h)"
                if full_analysis.get("data_source") == "whoscored"
                else "Fresh data (cached for 24h)"
            ),
        }

        await cache.set("opponent_stats", cache_key, result)
        return result

    except Exception as e:
        return {
            "opponent": opponent_name,
            "opponent_id": opponent_id,
            "error": f"Failed to fetch opponent data: {str(e)}",
            "data_source": "error",
        }
