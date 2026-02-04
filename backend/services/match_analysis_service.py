"""Match Analysis Service driven by SofaScore data (no external paid API)."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from config.settings import get_settings
from services.advanced_stats_analyzer import get_advanced_stats_analyzer
from services.scraper_export_service import get_scraper_export_service
from services.sofascore_service import get_sofascore_service
from services.tactical_ai_engine import get_tactical_ai_engine
from utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()


def _safe_get(d: Dict, *keys, default=None):
    cur = d
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


class MatchAnalysisService:
    def __init__(self):
        self.stats_analyzer = get_advanced_stats_analyzer()
        self.ai_engine = get_tactical_ai_engine()
        self.sofa = get_sofascore_service()
        self.scraper_exports = get_scraper_export_service()

    def _profile_from_recent_games(self, recent_games_tactical: List[Dict]) -> Dict:
        """Build a stable opponent profile by averaging per-match tactical stats."""
        if not recent_games_tactical:
            return {}

        def _mean(values):
            values = [v for v in values if isinstance(v, (int, float))]
            if not values:
                return None
            return sum(values) / len(values)

        possession = [_safe_get(m, "possession_control", "possession_percent") for m in recent_games_tactical]
        pass_acc = [_safe_get(m, "possession_control", "pass_accuracy") for m in recent_games_tactical]
        ppm = [_safe_get(m, "possession_control", "passes_per_minute") for m in recent_games_tactical]

        shots = [_safe_get(m, "shooting_finishing", "total_shots") for m in recent_games_tactical]
        shots_on = [_safe_get(m, "shooting_finishing", "shots_on_target") for m in recent_games_tactical]
        big = [_safe_get(m, "shooting_finishing", "big_chances_created") for m in recent_games_tactical]
        xg = [_safe_get(m, "expected_metrics", "xG") for m in recent_games_tactical]
        xg_shot = [_safe_get(m, "expected_metrics", "xG_per_shot") for m in recent_games_tactical]

        corners = [_safe_get(m, "set_pieces", "attacking", "corners_taken") for m in recent_games_tactical]
        corners_conc = [_safe_get(m, "set_pieces", "defensive", "corners_conceded") for m in recent_games_tactical]

        interceptions = [_safe_get(m, "defensive_actions", "interceptions") for m in recent_games_tactical]
        clearances = [_safe_get(m, "defensive_actions", "clearances") for m in recent_games_tactical]
        blocks = [_safe_get(m, "defensive_actions", "blocks") for m in recent_games_tactical]

        latest = recent_games_tactical[0] if isinstance(recent_games_tactical[0], dict) else {}

        profile = {
            "estimated": any(bool(m.get("estimated", True)) for m in recent_games_tactical),
            "matches_analyzed": len(recent_games_tactical),
            "possession_control": {
                "possession_percent": _mean(possession),
                "pass_accuracy": _mean(pass_acc),
                "passes_per_minute": _mean(ppm),
            },
            "shooting_finishing": {
                "total_shots": _mean(shots),
                "shots_on_target": _mean(shots_on),
                "big_chances_created": _mean(big),
            },
            "expected_metrics": {
                "xG": _mean(xg),
                "xG_per_shot": _mean(xg_shot),
            },
            "defensive_actions": {
                "interceptions": _mean(interceptions),
                "clearances": _mean(clearances),
                "blocks": _mean(blocks),
            },
            "set_pieces": {
                "attacking": {"corners_taken": _mean(corners)},
                "defensive": {"corners_conceded": _mean(corners_conc)},
            },
        }

        # Keep non-numeric/categorical structures from the latest match (best available signal).
        for key in ("pressing_structure", "team_shape", "transitions", "context", "match_info"):
            if key in latest:
                profile[key] = latest.get(key)

        return profile

    async def analyze_match(self, opponent_id: str, opponent_name: str) -> Dict:
        """Generate comprehensive match analysis using only SofaScore data."""
        try:
            gil_id = str(getattr(settings, "GIL_VICENTE_TEAM_ID", 9764) or 9764)

            gil_events = await self.sofa.get_last_finished_events(int(gil_id), limit=10)
            opp_events = await self.sofa.get_last_finished_events(int(opponent_id), limit=10)

            gil_matches = [self._event_to_match(ev) for ev in gil_events if ev]
            opp_matches = [self._event_to_match(ev) for ev in opp_events if ev]

            gil_matches = [m for m in gil_matches if m]
            opp_matches = [m for m in opp_matches if m]

            gil_form = self._build_form(gil_matches, gil_id, "Gil Vicente")
            opp_form = self._build_form(opp_matches, opponent_id, opponent_name)

            opponent_advanced_stats: Dict[str, any] = {}
            if opp_matches:
                opponent_advanced_stats = self.stats_analyzer.analyze_last_game(opp_matches, opponent_name)

            recent_games_tactical = await self.sofa.get_recent_games_tactical(
                opponent_name, limit=5, team_id=int(opponent_id)
            )
            data_source = "sofascore"
            if not recent_games_tactical:
                recent_games_tactical = self.scraper_exports.load_recent_games_tactical(opponent_name, limit=5)
                if recent_games_tactical:
                    data_source = "scraper_export"

            if recent_games_tactical:
                opponent_advanced_stats = self._profile_from_recent_games(recent_games_tactical) or recent_games_tactical[0]

            ai_recommendations = self.ai_engine.generate_recommendations(
                opponent_advanced_stats,
                None,
            )

            return {
                "match": f"Gil Vicente vs {opponent_name}",
                "gil_vicente_form": gil_form,
                "opponent_form": opp_form,
                "defensive_vulnerabilities": self._analyze_defensive_vulnerabilities(opp_form),
                "gil_attacking_analysis": self._analyze_gil_attacking(gil_form),
                "tactical_game_plan": self._generate_game_plan(gil_form, opp_form),
                "opponent_advanced_stats": opponent_advanced_stats,
                "recent_games_tactical": recent_games_tactical,
                "data_source": data_source,
                "ai_recommendations": ai_recommendations,
                "generated_at": self._get_timestamp(),
            }

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            raise

    def _event_to_match(self, event: Dict) -> Optional[Dict]:
        """Convert a SofaScore event into the lightweight match shape used by analyzers."""
        if not isinstance(event, dict):
            return None

        home = event.get("homeTeam") or {}
        away = event.get("awayTeam") or {}
        status = event.get("status") or {}

        start_ts = event.get("startTimestamp")
        utc_iso = None
        if isinstance(start_ts, (int, float)):
            utc_iso = datetime.fromtimestamp(float(start_ts), tz=timezone.utc).isoformat()

        home_score = (event.get("homeScore") or {}).get("current")
        away_score = (event.get("awayScore") or {}).get("current")

        status_type = str(status.get("type") or "").lower()
        finished = status_type == "finished"

        try:
            home_id = int(home.get("id")) if home.get("id") is not None else None
            away_id = int(away.get("id")) if away.get("id") is not None else None
        except Exception:
            return None

        return {
            "id": event.get("id"),
            "home": {
                "id": home_id,
                "name": home.get("name"),
                "score": home_score if home_score is not None else 0,
            },
            "away": {
                "id": away_id,
                "name": away.get("name"),
                "score": away_score if away_score is not None else 0,
            },
            "status": {
                "utcTime": utc_iso or "",
                "finished": finished,
            },
        }

    def _build_form(self, matches: List[Dict], team_id: str, team_name: str) -> Dict:
        matches_sorted = list(matches)
        matches_sorted.sort(key=lambda x: (x.get("status", {}) or {}).get("utcTime", ""), reverse=True)
        recent_matches = matches_sorted[:5]
        form = self._calculate_form(recent_matches, team_id)
        return {
            "team_name": team_name,
            "recent_matches": recent_matches,
            "form_summary": form,
        }

    def _calculate_form(self, matches: List[Dict], team_id: str) -> Dict:
        wins = draws = losses = 0
        goals_scored = goals_conceded = 0

        for match in matches:
            home = match.get("home", {})
            away = match.get("away", {})

            is_home = str(home.get("id")) == str(team_id)
            team_score = home.get("score") if is_home else away.get("score")
            opp_score = away.get("score") if is_home else home.get("score")

            goals_scored += int(team_score or 0)
            goals_conceded += int(opp_score or 0)

            if int(team_score or 0) > int(opp_score or 0):
                wins += 1
            elif int(team_score or 0) < int(opp_score or 0):
                losses += 1
            else:
                draws += 1

        total_games = len(matches)

        return {
            "form_string": f"{wins}W-{draws}D-{losses}L",
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
            "goal_difference": goals_scored - goals_conceded,
            "points": wins * 3 + draws,
            "games_played": total_games,
            "avg_goals_scored": round(goals_scored / total_games, 2) if total_games > 0 else 0,
            "avg_goals_conceded": round(goals_conceded / total_games, 2) if total_games > 0 else 0,
        }

    def _analyze_defensive_vulnerabilities(self, opponent_form: Dict) -> Dict:
        form = opponent_form.get("form_summary", {})

        return {
            "conceding_rate": form.get("avg_goals_conceded", 0),
            "clean_sheets": sum(
                1
                for m in opponent_form.get("recent_matches", [])
                if self._team_kept_clean_sheet(m, opponent_form.get("team_name", ""))
            ),
            "vulnerability_rating": "High"
            if form.get("avg_goals_conceded", 0) > 1.5
            else "Medium"
            if form.get("avg_goals_conceded", 0) > 1
            else "Low",
        }

    def _team_kept_clean_sheet(self, match: Dict, team_name: str) -> bool:
        home = match.get("home", {})
        away = match.get("away", {})
        is_home = str(home.get("name")) == str(team_name)
        goals_conceded = away.get("score") if is_home else home.get("score")
        return int(goals_conceded or 0) == 0

    def _analyze_gil_attacking(self, gil_form: Dict) -> Dict:
        form = gil_form.get("form_summary", {})

        return {
            "scoring_rate": form.get("avg_goals_scored", 0),
            "recent_form": form.get("form_string", ""),
            "attack_rating": "Strong"
            if form.get("avg_goals_scored", 0) >= 1.5
            else "Average"
            if form.get("avg_goals_scored", 0) >= 1
            else "Weak",
        }

    def _generate_game_plan(self, gil_form: Dict, opp_form: Dict) -> Dict:
        gil_attack = gil_form.get("form_summary", {}).get("avg_goals_scored", 0)
        opp_defense = opp_form.get("form_summary", {}).get("avg_goals_conceded", 0)

        if opp_defense > 1.5:
            approach = "Aggressive - Opponent is defensively weak"
            formation = "4-3-3 or 4-2-4"
        elif gil_attack >= 1.5:
            approach = "Balanced - Capitalize on good form"
            formation = "4-2-3-1"
        else:
            approach = "Cautious - Build confidence"
            formation = "4-4-2 or 4-5-1"

        return {
            "recommended_approach": approach,
            "suggested_formation": formation,
            "key_focus": "Exploit defensive vulnerabilities"
            if opp_defense > 1.5
            else "Maintain defensive solidity",
        }

    def _get_timestamp(self) -> str:
        return datetime.utcnow().isoformat() + "Z"


_service: Optional[MatchAnalysisService] = None


def get_match_analysis_service() -> MatchAnalysisService:
    global _service
    if _service is None:
        _service = MatchAnalysisService()
    return _service
