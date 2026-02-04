"""SofaScore Service

Fetches match/team statistics from SofaScore's public JSON endpoints and normalizes
into the same tactical stats shape used by `AdvancedStatsAnalyzer`.

Notes:
- This uses an *unofficial* SofaScore API surface.
- Be mindful of SofaScore's Terms of Service and rate-limit requests.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx

from config.settings import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()


_STAT_NAME_NORMALIZATION = {
    # possession
    "ball possession": "ball_possession",
    "possession": "ball_possession",
    # shooting
    "total shots": "total_shots",
    "shots": "total_shots",
    "shots on target": "shots_on_target",
    "shots off target": "shots_off_target",
    "shots inside box": "shots_inside_box",
    "shots outside box": "shots_outside_box",
    "blocked shots": "blocked_shots",
    "big chances": "big_chances",
    "big chances missed": "big_chances_missed",
    # expected
    "expected goals": "xg",
    "expected goals (xg)": "xg",
    "xg": "xg",
    # passing
    "total passes": "total_passes",
    "passes": "total_passes",
    "accurate passes": "accurate_passes",
    "pass accuracy": "pass_accuracy",
    "key passes": "key_passes",
    "crosses": "crosses",
    "accurate crosses": "accurate_crosses",
    "long balls": "long_balls",
    "accurate long balls": "accurate_long_balls",
    # set pieces / discipline
    "corner kicks": "corners",
    "corners": "corners",
    "fouls": "fouls",
    "offsides": "offsides",
    # defending
    "tackles": "tackles",
    "interceptions": "interceptions",
    "clearances": "clearances",
    "duels won": "duels_won",
    "ground duels won": "ground_duels_won",
    "aerial duels won": "aerial_duels_won",
    "saves": "saves",
}


def _slug(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _slug(a), _slug(b)).ratio()


def _unwrap_stat_value(value: Any) -> Any:
    """Unwrap SofaScore stat values that may come as dicts (new format)."""
    if value is None:
        return None
    if isinstance(value, list) and len(value) == 1:
        return _unwrap_stat_value(value[0])
    if isinstance(value, dict):
        for k in ("value", "displayValue", "formattedValue", "raw", "val"): 
            if k in value:
                return value.get(k)
    return value


def _parse_percent(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.endswith("%"):
            s = s[:-1].strip()
        try:
            return float(s)
        except Exception:
            return None
    return None


_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        m = _NUM_RE.search(s)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None
    return None


def _parse_count_and_percent(value: Any) -> Tuple[Optional[float], Optional[float]]:
    """Parse formats like '345 (82%)' into (345, 82)."""
    if value is None:
        return None, None
    if isinstance(value, (int, float)):
        return float(value), None
    if not isinstance(value, str):
        return None, None

    s = value.strip()
    if not s:
        return None, None

    # 345 (82%)
    parts = re.findall(r"-?\d+(?:\.\d+)?", s)
    if not parts:
        return None, None

    count = None
    pct = None

    try:
        count = float(parts[0])
    except Exception:
        count = None

    # heuristic: if there's a second number and the raw string contains '%', treat as percent
    if len(parts) >= 2 and "%" in s:
        try:
            pct = float(parts[1])
        except Exception:
            pct = None

    return count, pct


@dataclass(frozen=True)
class SofaScoreResolvedTeam:
    id: int
    name: str
    country: Optional[str] = None
    sport: Optional[str] = None


class SofaScoreService:
    def __init__(self):
        # Prefer api.sofascore.com (less likely to 403) with fallback to www.
        primary = getattr(settings, "SOFASCORE_BASE_URL", "https://api.sofascore.com/api/v1")
        fallbacks_raw = getattr(settings, "SOFASCORE_BASE_URLS", "") or ""
        fallback_list = [u.strip() for u in fallbacks_raw.split(",") if u.strip()]
        self.base_urls = [primary] + [u for u in fallback_list if u != primary]
        if "https://www.sofascore.com/api/v1" not in self.base_urls:
            self.base_urls.append("https://www.sofascore.com/api/v1")

        self.timeout = float(getattr(settings, "SOFASCORE_TIMEOUT_SECONDS", 20.0))
        self.enabled = bool(getattr(settings, "SOFASCORE_ENABLED", True))
        self.user_agent = getattr(settings, "SOFASCORE_USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        self.proxy = getattr(settings, "SOFASCORE_PROXY", None)
        try:
            self.extra_headers = json.loads(getattr(settings, "SOFASCORE_HEADERS_JSON", "") or "{}")
        except Exception:
            self.extra_headers = {}
        try:
            self.cookies = json.loads(getattr(settings, "SOFASCORE_COOKIES_JSON", "") or "{}")
        except Exception:
            self.cookies = {}

    def _client(self, base_url: str) -> httpx.AsyncClient:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.sofascore.com/",
            "Origin": "https://www.sofascore.com",
        }
        headers.update({k: v for k, v in (self.extra_headers or {}).items() if v is not None})

        return httpx.AsyncClient(
            base_url=base_url,
            timeout=self.timeout,
            headers=headers,
            cookies=self.cookies or None,
            follow_redirects=True,
            proxies=self.proxy or None,
        )

    async def _get(self, path: str) -> dict:
        """GET with fallback base URLs and clearer 403 guidance."""
        last_error = None
        for base_url in self.base_urls:
            try:
                async with self._client(base_url) as client:
                    resp = await client.get(path)
                    if resp.status_code == 404:
                        return {}
                    resp.raise_for_status()
                    return resp.json() or {}
            except httpx.HTTPStatusError as e:
                last_error = e
                status = getattr(e.response, "status_code", None)
                if status in (403, 429):
                    logger.warning(
                        "SofaScore request denied (%s). This environment may be blocked by SofaScore; use an authorized data source or adjust deployment accordingly.",
                        status,
                    )
                    continue
                raise
            except Exception as e:
                last_error = e
                continue
        if last_error:
            raise last_error
        return {}


    def _team_id_from_map(self, team_name: str) -> Optional[int]:
        raw = getattr(settings, "SOFASCORE_TEAM_ID_MAP_JSON", "") or ""
        if not str(raw).strip():
            return None

        try:
            data = json.loads(raw)
        except Exception as e:
            logger.warning(f"Invalid SOFASCORE_TEAM_ID_MAP_JSON: {e}")
            return None

        if not isinstance(data, dict):
            return None

        target = _slug(team_name)
        best_id: Optional[int] = None
        best_score = 0.0

        for key, value in data.items():
            candidate_name = str(key)
            score = 1.0 if _slug(candidate_name) == target else _similarity(candidate_name, team_name)
            if score < 0.85:
                continue

            if isinstance(value, dict):
                value = value.get("id")

            team_id: Optional[int] = None
            if isinstance(value, (int, float)) and int(value) > 0:
                team_id = int(value)
            elif isinstance(value, str) and value.strip().isdigit():
                team_id = int(value.strip())

            if team_id and score > best_score:
                best_score = score
                best_id = team_id

        return best_id

    async def search_teams(self, query: str, limit: int = 10) -> List[SofaScoreResolvedTeam]:
        if not self.enabled:
            return []

        q = str(query or "").strip()
        if not q:
            return []

        data = await self._get(f"/search/all?q={urllib.parse.quote(q)}")

        results: List[SofaScoreResolvedTeam] = []
        for item in (data.get("results") or []):
            entity = item.get("entity") or {}
            if (entity.get("type") or "").lower() != "team":
                continue

            team = entity.get("team") or {}
            team_id = team.get("id")
            name = team.get("name")
            if not team_id or not name:
                continue

            sport = (team.get("sport") or {}).get("name")
            country = (team.get("country") or {}).get("name")
            results.append(SofaScoreResolvedTeam(id=int(team_id), name=str(name), country=country, sport=sport))

        # rank by name similarity
        results.sort(key=lambda t: _similarity(t.name, q), reverse=True)
        return results[: max(0, int(limit))]

    async def resolve_team_id(self, team_name: str) -> Optional[int]:
        mapped = self._team_id_from_map(team_name)
        if mapped:
            return mapped

        teams = await self.search_teams(team_name, limit=5)
        if not teams:
            return None

        best = teams[0]
        # Conservative cutoff to avoid bad matches
        if _similarity(best.name, team_name) < 0.55:
            return None
        return best.id

    async def get_last_finished_events(self, team_id: int, limit: int = 5, max_pages: int = 3) -> List[Dict[str, Any]]:
        """Fetch last finished events for a team."""
        if not self.enabled:
            return []

        out: List[Dict[str, Any]] = []
        pages = max(1, int(max_pages))

        for page in range(pages):
            data = await self._get(f"/team/{int(team_id)}/events/last/{int(page)}")
            events = data.get("events") or []
            if not events:
                break
            for ev in events:
                status = (ev.get("status") or {})
                status_type = str(status.get("type") or "").lower()
                if status_type == "finished":
                    out.append(ev)
                    if len(out) >= int(limit):
                        return out

        return out[: int(limit)]

    async def get_upcoming_events(self, team_id: int, limit: int = 5, max_pages: int = 2) -> List[Dict[str, Any]]:
        """Fetch upcoming (not started) events for a team."""
        if not self.enabled:
            return []

        out: List[Dict[str, Any]] = []
        pages = max(1, int(max_pages))

        for page in range(pages):
            data = await self._get(f"/team/{int(team_id)}/events/next/{int(page)}")
            events = data.get("events") or []
            if not events:
                break
            for ev in events:
                status = (ev.get("status") or {})
                status_type = str(status.get("type") or "").lower()
                if status_type not in {"notstarted", "postponed", "cancelled", "inprogress"}:
                    continue
                out.append(ev)
                if len(out) >= int(limit):
                    return out

        return out[: int(limit)]

    async def get_team_events(self, team_id: int, past_limit: int = 30, upcoming_limit: int = 15) -> List[Dict[str, Any]]:
        """Helper to fetch both past finished and upcoming events for a team."""
        past = await self.get_last_finished_events(team_id, limit=past_limit)
        upcoming = await self.get_upcoming_events(team_id, limit=upcoming_limit)
        return past + upcoming

    async def get_event_statistics(self, event_id: int) -> Dict[str, Any]:
        if not self.enabled:
            return {}

        data = await self._get(f"/event/{int(event_id)}/statistics")
        return data or {}

    def _flatten_stats(self, raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Return a dict: normalized_name -> {home: raw, away: raw, originalName: str}.

        SofaScore has changed the shape of match statistics over time. This parser is
        intentionally tolerant:
        - raw["statistics"] can be a list or a dict
        - groups can appear under different keys
        - item values can be raw scalars or nested dicts like {value, displayValue}
        """
        out: Dict[str, Dict[str, Any]] = {}

        stats = raw.get("statistics")
        if isinstance(stats, list):
            blocks = stats
        elif isinstance(stats, dict):
            blocks = [stats]
        else:
            blocks = []

        for block in blocks:
            if not isinstance(block, dict):
                continue

            groups = block.get("groups") or block.get("statisticsGroups") or block.get("periods") or []
            if isinstance(groups, dict):
                groups = [groups]

            for group in (groups or []):
                if not isinstance(group, dict):
                    continue

                items = group.get("statisticsItems") or group.get("items") or group.get("statistics") or []
                if isinstance(items, dict):
                    items = [items]

                for item in (items or []):
                    if not isinstance(item, dict):
                        continue

                    name = item.get("name") or item.get("label") or item.get("title")
                    if not name:
                        continue

                    key = _STAT_NAME_NORMALIZATION.get(_slug(name), None)
                    if not key:
                        key = f"raw::{_slug(name)}"

                    home = item.get("home")
                    away = item.get("away")

                    # alternate keys across versions
                    if home is None and "homeValue" in item:
                        home = item.get("homeValue")
                    if away is None and "awayValue" in item:
                        away = item.get("awayValue")
                    if home is None and "homeTeamValue" in item:
                        home = item.get("homeTeamValue")
                    if away is None and "awayTeamValue" in item:
                        away = item.get("awayTeamValue")

                    home = _unwrap_stat_value(home)
                    away = _unwrap_stat_value(away)

                    out[key] = {"home": home, "away": away, "originalName": name}

        return out


    def _pick_side(self, stat: Dict[str, Any], is_home: bool) -> Any:
        return _unwrap_stat_value(stat.get("home") if is_home else stat.get("away"))

    def _pick_side_other(self, stat: Dict[str, Any], is_home: bool) -> Any:
        return _unwrap_stat_value(stat.get("away") if is_home else stat.get("home"))

    def normalize_event_tactical_stats(self, *, event: Dict[str, Any], team_id: int, stats_raw: Dict[str, Any]) -> Dict[str, Any]:
        home_team = event.get("homeTeam") or {}
        away_team = event.get("awayTeam") or {}

        is_home = int(home_team.get("id") or 0) == int(team_id)
        team_name = home_team.get("name") if is_home else away_team.get("name")
        opp_name = away_team.get("name") if is_home else home_team.get("name")

        home_score = (event.get("homeScore") or {}).get("current")
        away_score = (event.get("awayScore") or {}).get("current")
        try:
            hs = int(home_score)
        except Exception:
            hs = 0
        try:
            aws = int(away_score)
        except Exception:
            aws = 0

        team_score = hs if is_home else aws
        opp_score = aws if is_home else hs

        result = "W" if team_score > opp_score else "L" if team_score < opp_score else "D"

        start_ts = event.get("startTimestamp")
        # keep as epoch seconds if present; otherwise empty string
        date = start_ts if isinstance(start_ts, int) else ""

        flat = self._flatten_stats(stats_raw)

        ball_poss = _parse_percent(self._pick_side(flat.get("ball_possession", {}), is_home))

        total_shots = _parse_number(self._pick_side(flat.get("total_shots", {}), is_home))
        shots_on = _parse_number(self._pick_side(flat.get("shots_on_target", {}), is_home))
        shots_in = _parse_number(self._pick_side(flat.get("shots_inside_box", {}), is_home))
        shots_out = _parse_number(self._pick_side(flat.get("shots_outside_box", {}), is_home))

        big_chances = _parse_number(self._pick_side(flat.get("big_chances", {}), is_home))
        big_missed = _parse_number(self._pick_side(flat.get("big_chances_missed", {}), is_home))

        xg = _parse_number(self._pick_side(flat.get("xg", {}), is_home))

        passes_total = _parse_number(self._pick_side(flat.get("total_passes", {}), is_home))

        # accurate passes might be a plain count, while accuracy can be present separately.
        acc_passes_val = self._pick_side(flat.get("accurate_passes", {}), is_home)
        acc_passes, acc_pass_pct = _parse_count_and_percent(acc_passes_val)

        pass_acc = _parse_percent(self._pick_side(flat.get("pass_accuracy", {}), is_home))
        if pass_acc is None and acc_pass_pct is not None:
            pass_acc = acc_pass_pct
        if acc_passes is None and passes_total is not None and pass_acc is not None:
            acc_passes = round((passes_total * pass_acc) / 100.0, 0)

        long_balls_val = self._pick_side(flat.get("long_balls", {}), is_home)
        long_attempted, _ = _parse_count_and_percent(long_balls_val)
        acc_long_val = self._pick_side(flat.get("accurate_long_balls", {}), is_home)
        long_completed, _ = _parse_count_and_percent(acc_long_val)

        corners = _parse_number(self._pick_side(flat.get("corners", {}), is_home))
        corners_conceded = _parse_number(self._pick_side_other(flat.get("corners", {}), is_home))

        tackles = _parse_number(self._pick_side(flat.get("tackles", {}), is_home))
        interceptions = _parse_number(self._pick_side(flat.get("interceptions", {}), is_home))
        clearances = _parse_number(self._pick_side(flat.get("clearances", {}), is_home))
        blocks = _parse_number(self._pick_side(flat.get("blocked_shots", {}), is_home))

        duels_won = _parse_number(self._pick_side(flat.get("duels_won", {}), is_home))
        duels_total = None
        # If we only have duels won, don't fake total.

        shot_conv = None
        if total_shots is not None and total_shots > 0:
            shot_conv = round((float(team_score) / float(total_shots)) * 100.0, 1)

        xg_per_shot = None
        if xg is not None and total_shots is not None and total_shots > 0:
            xg_per_shot = round(float(xg) / float(total_shots), 3)

        # Derived convenience
        passes_per_min = None
        if passes_total is not None:
            passes_per_min = round(float(passes_total) / 90.0, 2)

        tempo_rating = None
        if passes_per_min is not None:
            tempo_rating = "High" if passes_per_min >= 4.2 else "Medium" if passes_per_min >= 3.4 else "Low"

        possession_insight = None
        if ball_poss is not None and passes_per_min is not None:
            if ball_poss >= 60 and passes_per_min >= 4.0:
                possession_insight = "High possession + high tempo → opponent likely controls territory and rhythm"
            elif ball_poss <= 40 and passes_per_min <= 3.2:
                possession_insight = "Low possession + low tempo → opponent likely sits deep and plays transitions"

        shooting_insight = None
        if total_shots is not None and xg is not None:
            if total_shots >= 14 and xg < 1.2:
                shooting_insight = "High shot volume but low xG → many low-quality shots; protect zone 14 + force wide shots"
            elif total_shots <= 8 and xg >= 1.3:
                shooting_insight = "Low shot volume but high xG → efficient chance creation; avoid cheap turnovers"

        return {
            "estimated": False,
            "match_info": {
                "event_id": int(event.get("id") or 0) or None,
                "team": team_name,
                "opponent": opp_name,
                "score": f"{team_score}-{opp_score}",
                "result": result,
                "location": "Home" if is_home else "Away",
                "date": date,
            },
            "possession_control": {
                "possession_percent": ball_poss,
                "time_in_opponent_half": None,
                "pass_accuracy": pass_acc,
                "passes_per_minute": passes_per_min,
                "long_balls_attempted": long_attempted,
                "long_balls_completed": long_completed,
                "tempo_rating": tempo_rating,
                "tactical_insight": possession_insight,
            },
            "shooting_finishing": {
                "total_shots": total_shots,
                "shots_on_target": shots_on,
                "shot_conversion_rate": shot_conv,
                "shots_inside_box": shots_in,
                "shots_outside_box": shots_out,
                "big_chances_created": big_chances,
                "big_chances_missed": big_missed,
                "tactical_insight": shooting_insight,
            },
            "expected_metrics": {
                "xG": xg,
                "xG_per_shot": xg_per_shot,
                "xG_from_open_play": None,
                "xG_from_set_pieces": None,
                "xA": None,
                "performance_rating": None,
            },
            "chance_creation": {
                "key_passes": _parse_number(self._pick_side(flat.get("key_passes", {}), is_home)),
                "progressive_passes": None,
                "passes_into_final_third": None,
                "passes_into_penalty_area": None,
                "crosses_attempted": _parse_number(self._pick_side(flat.get("crosses", {}), is_home)),
                "crosses_accurate": _parse_number(self._pick_side(flat.get("accurate_crosses", {}), is_home)),
                "cutbacks": None,
                "creation_quality": None,
            },
            "defensive_actions": {
                "tackles_attempted": tackles,
                "tackles_won": None,
                "tackle_success_rate": None,
                "interceptions": interceptions,
                "blocks": blocks,
                "clearances": clearances,
                "defensive_duels_won_percent": None,
                "defensive_rating": None,
                "duels_won": duels_won,
                "duels_total": duels_total,
            },
            "pressing_structure": {
                "PPDA": None,
                "pressing_intensity": None,
                "high_turnovers_won": None,
                "counter_press_recoveries": None,
                "pressing_zones": None,
                "tactical_insight": None,
            },
            "team_shape": {
                "avg_team_line_height": None,
                "defensive_line_height": None,
                "distance_between_lines": None,
                "team_compactness": None,
                "width_usage": None,
                "formation_detected": None,
            },
            "transitions": None,
            "set_pieces": {
                "attacking": {
                    "corners_taken": corners,
                    "xG_from_corners": None,
                    "first_contact_success": None,
                    "second_ball_recoveries": None,
                    "set_piece_goals": None,
                },
                "defensive": {
                    "corners_conceded": corners_conceded,
                    "marking_type": None,
                    "clearances_under_pressure": None,
                    "shots_conceded_after_set_pieces": None,
                    "set_piece_weakness": None,
                },
            },
            "context": {
                "scoreline_state": "Winning" if result == "W" else "Losing" if result == "L" else "Drawing",
                "game_momentum": None,
                "pressure_handling": None,
                "fatigue_indicators": None,
                "mental_strength": None,
            },
        }

    async def get_recent_games_tactical(self, team_name: str, limit: int = 5, team_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Resolve a team by name (or use an explicit team_id) and return normalized tactical stats for its last games."""
        if not self.enabled:
            return []

        resolved_id = int(team_id) if team_id else await self.resolve_team_id(team_name)
        if not resolved_id:
            return []

        events = await self.get_last_finished_events(resolved_id, limit=limit)
        if not events:
            return []

        out: List[Dict[str, Any]] = []
        for ev in events:
            ev_id = ev.get("id")
            if not ev_id:
                continue
            try:
                stats_raw = await self.get_event_statistics(int(ev_id))
                if not stats_raw:
                    continue
                out.append(self.normalize_event_tactical_stats(event=ev, team_id=int(resolved_id), stats_raw=stats_raw))
            except Exception as e:
                logger.warning(f"SofaScore normalize failed for event={ev_id}: {e}")

        return out


_sofascore_service: Optional[SofaScoreService] = None


def get_sofascore_service() -> SofaScoreService:
    global _sofascore_service
    if _sofascore_service is None:
        _sofascore_service = SofaScoreService()
    return _sofascore_service
