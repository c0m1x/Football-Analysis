"""Scraper Export Service

Provides a fallback data source when SofaScore's public endpoints are blocked (HTTP 403).

It reads JSON exports produced by `scrapper/scrapper.py` and converts them into the
same per-match tactical stats shape used across the backend:
  - `recent_games_tactical[*]`

This keeps the frontend + AI pipeline working even when direct API scraping is denied.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import datetime, timedelta
from dataclasses import dataclass
from glob import glob
from typing import Any, Dict, List, Optional

from config.settings import get_settings

settings = get_settings()


def _slug(text: str) -> str:
    """Lowercase + strip accents + keep alnum/spaces for fuzzy matching."""
    text = str(text or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_percent(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("%"):
        s = s[:-1].strip()
    try:
        return float(s)
    except Exception:
        return None


_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    match = _NUM_RE.search(s.replace(",", "."))
    if not match:
        return None
    try:
        return float(match.group(0))
    except Exception:
        return None


def _extract_event_id(match_url: str) -> Optional[int]:
    if not match_url:
        return None
    match = re.search(r"#id:(\d+)", str(match_url))
    if match:
        return int(match.group(1))
    return None


def _parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    s = str(value).strip()
    if not s:
        return None
    m = re.search(r"-?\d+", s)
    if not m:
        return None
    try:
        return int(m.group(0))
    except Exception:
        return None


_MONTH_MAP = {
    "jan": 1,
    "janeiro": 1,
    "feb": 2,
    "fev": 2,
    "fevereiro": 2,
    "mar": 3,
    "marco": 3,
    "abril": 4,
    "abr": 4,
    "mai": 5,
    "maio": 5,
    "jun": 6,
    "junho": 6,
    "jul": 7,
    "julho": 7,
    "ago": 8,
    "agosto": 8,
    "sep": 9,
    "set": 9,
    "setembro": 9,
    "oct": 10,
    "out": 10,
    "outubro": 10,
    "nov": 11,
    "novembro": 11,
    "dec": 12,
    "dez": 12,
    "dezembro": 12,
}


def _parse_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    m = re.match(r"^(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?$", s)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year_raw = m.group(3)
        year = datetime.now().year if not year_raw else int(year_raw)
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).date().isoformat()
        except Exception:
            return None

    m = re.match(r"^(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s*(\d{2,4})?$", s)
    if m:
        day = int(m.group(1))
        month_text = _slug(m.group(2))
        year_raw = m.group(3)
        month = _MONTH_MAP.get(month_text)
        if month:
            year = datetime.now().year if not year_raw else int(year_raw)
            if year < 100:
                year += 2000
            try:
                return datetime(year, month, day).date().isoformat()
            except Exception:
                return None

    lowered = _slug(s)
    if lowered in {"hoje"}:
        return datetime.now().date().isoformat()
    if lowered in {"ontem"}:
        return (datetime.now().date() - timedelta(days=1)).isoformat()
    if lowered in {"amanha"}:
        return (datetime.now().date() + timedelta(days=1)).isoformat()

    return None


def _parse_time(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    m = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", s)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2))
        second = int(m.group(3)) if m.group(3) else 0
        return f"{hour:02d}:{minute:02d}:{second:02d}"
    m = re.search(r"(\d{1,2})h(\d{2})", s)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2))
        return f"{hour:02d}:{minute:02d}:00"
    return None


@dataclass(frozen=True)
class ScraperExportMatch:
    raw: Dict[str, Any]
    opponent_name: str

    @property
    def home_team(self) -> str:
        return str(self.raw.get("home_team") or "")

    @property
    def away_team(self) -> str:
        return str(self.raw.get("away_team") or "")

    @property
    def match_url(self) -> str:
        return str(self.raw.get("match_url") or "")

    @property
    def is_opponent_home(self) -> Optional[bool]:
        opp = _slug(self.opponent_name)
        home = _slug(self.home_team)
        away = _slug(self.away_team)
        if opp and home and opp in home:
            return True
        if opp and away and opp in away:
            return False
        return None

    def _side(self) -> str:
        # Default to away when unknown; we'll still try to populate.
        return "home" if self.is_opponent_home else "away"

    def _other_side(self) -> str:
        return "away" if self._side() == "home" else "home"

    def _pick(self, base_keys: List[str], *, other_team: bool = False) -> Any:
        side = self._other_side() if other_team else self._side()
        for base in base_keys:
            key = f"{base}_{side}"
            if key in self.raw and self.raw.get(key) not in (None, ""):
                return self.raw.get(key)
        return None

    def to_tactical_stats(self) -> Dict[str, Any]:
        # Match opponent + determine context
        is_home = self.is_opponent_home
        location = "Home" if is_home else "Away" if is_home is not None else None
        opp_name = self.away_team if is_home else self.home_team if is_home is not None else None

        # Core metrics (best-effort mapping from Portuguese exports)
        possession = _parse_percent(
            self._pick(["posse_de_bola", "ball_possession", "possession", "match_overview_ball_possession"])
        )

        total_passes = _parse_number(self._pick(["passes", "total_passes", "match_overview_passes"]))
        accurate_passes = _parse_number(self._pick(["passes_precisos", "passes_accurate_passes", "accurate_passes"]))

        pass_accuracy = _parse_percent(self._pick(["pass_accuracy", "precisao_de_passe", "precisão_de_passe"]))
        if pass_accuracy is None and total_passes is not None and total_passes > 0 and accurate_passes is not None:
            pass_accuracy = round((float(accurate_passes) / float(total_passes)) * 100.0, 1)

        passes_per_min = None
        if total_passes is not None:
            passes_per_min = round(float(total_passes) / 90.0, 2)

        total_shots = _parse_number(
            self._pick(["total_de_remates", "total_shots", "shots_total_shots"])
        )
        shots_on = _parse_number(
            self._pick(["remates_enquadrados", "shots_on_target", "shots_shots_on_target"])
        )
        shots_in = _parse_number(self._pick(["remates_dentro_da_área", "shots_inside_box", "shots_shots_inside_box"]))
        shots_out = _parse_number(self._pick(["remates_fora_da_área", "shots_outside_box", "shots_shots_outside_box"]))

        big_chances = _parse_number(self._pick(["grandes_oportunidades", "big_chances", "match_overview_big_chances"]))
        big_missed = _parse_number(self._pick(["grandes_oportunidades_falhadas", "big_chances_missed"]))

        xg = _parse_number(self._pick(["golos_esperados_xg", "xg", "expected_goals_xg"]))

        corners = _parse_number(self._pick(["cantos", "corner_kicks", "match_overview_corner_kicks"]))
        corners_conceded = _parse_number(
            self._pick(["cantos", "corner_kicks", "match_overview_corner_kicks"], other_team=True)
        )

        interceptions = _parse_number(self._pick(["interceções", "interceptions", "defending_interceptions"]))
        clearances = _parse_number(self._pick(["cortes", "clearances", "defending_clearances", "alívios"]))
        blocks = _parse_number(self._pick(["remates_bloqueados", "blocked_shots", "defending_blocks"]))

        xg_per_shot = None
        if xg is not None and total_shots is not None and total_shots > 0:
            xg_per_shot = round(float(xg) / float(total_shots), 3)

        # Lightweight textual insights (frontend shows latest match insights)
        possession_insight = None
        if possession is not None:
            if possession >= 60:
                possession_insight = "High possession (>=60%) → likely comfortable controlling tempo and territory"
            elif possession <= 40:
                possession_insight = "Low possession (<=40%) → likely deeper block and transition/counter focus"

        shooting_insight = None
        if total_shots is not None and xg is not None:
            if total_shots >= 14 and xg < 1.2:
                shooting_insight = "High shot volume but low xG → shot quality may be poor; protect zone 14 + force wide shots"
            elif total_shots <= 8 and xg >= 1.3:
                shooting_insight = "Low shot volume but high xG → efficient chance creation; avoid cheap turnovers"

        return {
            "estimated": False,
            "match_info": {
                "event_id": _extract_event_id(self.match_url),
                "team": self.opponent_name,
                "opponent": opp_name,
                "score": None,
                "result": None,
                "location": location,
                "date": self.raw.get("date"),
            },
            "possession_control": {
                "possession_percent": possession,
                "time_in_opponent_half": None,
                "pass_accuracy": pass_accuracy,
                "passes_per_minute": passes_per_min,
                "long_balls_attempted": None,
                "long_balls_completed": None,
                "tempo_rating": None,
                "tactical_insight": possession_insight,
            },
            "shooting_finishing": {
                "total_shots": total_shots,
                "shots_on_target": shots_on,
                "shot_conversion_rate": None,
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
                "key_passes": None,
                "progressive_passes": None,
                "passes_into_final_third": None,
                "passes_into_penalty_area": None,
                "crosses_attempted": None,
                "crosses_accurate": None,
                "cutbacks": None,
                "creation_quality": None,
            },
            "defensive_actions": {
                "tackles_attempted": None,
                "tackles_won": None,
                "tackle_success_rate": None,
                "interceptions": interceptions,
                "blocks": blocks,
                "clearances": clearances,
                "defensive_duels_won_percent": None,
                "defensive_rating": None,
                "duels_won": None,
                "duels_total": None,
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
                "scoreline_state": None,
                "game_momentum": None,
                "pressure_handling": None,
                "fatigue_indicators": None,
                "mental_strength": None,
            },
        }


class ScraperExportService:
    """Find and parse `scrapper/scrapper.py` exports as a backend data source."""

    def __init__(self):
        self.export_dir = str(getattr(settings, "SCRAPER_EXPORT_DIR", "") or "").strip()

    def _default_export_dir(self) -> str:
        # Default to a dedicated data folder if present, otherwise repo root.
        here = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(here, "..", ".."))
        preferred = os.path.join(repo_root, "data", "scraper_exports")
        return preferred if os.path.isdir(preferred) else repo_root

    def _candidate_paths(self, opponent_name: str) -> List[str]:
        if self.export_dir:
            base_dirs = [self.export_dir]
        else:
            here = os.path.dirname(os.path.abspath(__file__))
            repo_root = os.path.abspath(os.path.join(here, "..", ".."))
            base_dirs = [
                os.path.join(repo_root, "data", "scraper_exports"),
                repo_root,  # backwards-compat: older exports were written to repo root
            ]

        slug = str(opponent_name or "").replace(" ", "_")
        paths: List[str] = []
        for export_dir in base_dirs:
            patterns = [
                os.path.join(export_dir, f"gil_vicente_next_opponent_{slug}_individual_*.json"),
                os.path.join(export_dir, f"*{slug}*individual*.json"),
            ]
            for pattern in patterns:
                paths.extend(glob(pattern))
        # Newest first (filenames include timestamp)
        paths.sort(reverse=True)
        return paths

    def _fixture_paths(self) -> List[str]:
        if self.export_dir:
            base_dirs = [self.export_dir]
        else:
            here = os.path.dirname(os.path.abspath(__file__))
            repo_root = os.path.abspath(os.path.join(here, "..", ".."))
            base_dirs = [
                os.path.join(repo_root, "data", "scraper_exports"),
                repo_root,
            ]

        paths: List[str] = []
        for export_dir in base_dirs:
            pattern = os.path.join(export_dir, "gil_vicente_fixtures_*.json")
            paths.extend(glob(pattern))

        paths.sort(reverse=True)
        return paths

    def _normalize_fixture(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, dict):
            return None

        match_url = raw.get("match_url") or raw.get("url")
        match_id = raw.get("match_id") or raw.get("id") or _extract_event_id(str(match_url or ""))
        if match_id is None and match_url:
            match_id = str(match_url)

        home_team = raw.get("home_team") or raw.get("home")
        away_team = raw.get("away_team") or raw.get("away")

        is_home = raw.get("gil_vicente_home")
        if is_home is None:
            if home_team and _slug(home_team).find("gil vicente") != -1:
                is_home = True
            elif away_team and _slug(away_team).find("gil vicente") != -1:
                is_home = False

        opponent_name = raw.get("opponent_name")
        if not opponent_name and home_team and away_team and is_home is not None:
            opponent_name = away_team if is_home else home_team

        home_score = _parse_int(raw.get("home_score"))
        away_score = _parse_int(raw.get("away_score"))

        status_raw = str(raw.get("status") or "").strip().lower()
        if status_raw in {"finished", "ft", "tr", "terminado", "ended"}:
            status = "finished"
        elif status_raw in {"upcoming", "scheduled", "notstarted", "ns"}:
            status = "upcoming"
        elif status_raw in {"postponed", "cancelled", "canceled"}:
            status = status_raw
        else:
            status = "finished" if home_score is not None and away_score is not None else "upcoming"

        date = _parse_date(raw.get("date")) or raw.get("date")
        time = _parse_time(raw.get("time")) or raw.get("time")
        datetime_raw = raw.get("datetime") or raw.get("utc_time")

        fixture: Dict[str, Any] = {
            "id": match_id,
            "match_id": match_id,
            "match_url": match_url,
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
            "status": status,
            "is_home": is_home,
            "gil_vicente_home": is_home,
            "opponent_name": opponent_name,
            "opponent_id": raw.get("opponent_id"),
            "date": date,
            "time": time,
        }

        if datetime_raw:
            fixture["datetime"] = datetime_raw
            if isinstance(datetime_raw, str) and ("Z" in datetime_raw or "+" in datetime_raw or "-" in datetime_raw[10:]):
                fixture["utc_time"] = datetime_raw

        return fixture

    def load_fixtures(self, limit: int = 100) -> List[Dict[str, Any]]:
        paths = self._fixture_paths()
        if not paths:
            return []

        path = paths[0]
        try:
            raw = json.loads(open(path, "r", encoding="utf-8").read())
        except Exception:
            return []

        if isinstance(raw, dict):
            fixtures_raw = raw.get("fixtures") or []
        elif isinstance(raw, list):
            fixtures_raw = raw
        else:
            fixtures_raw = []

        out: List[Dict[str, Any]] = []
        for item in fixtures_raw[: max(0, int(limit))]:
            fixture = self._normalize_fixture(item)
            if fixture:
                out.append(fixture)

        return out

    def load_recent_games_tactical(self, opponent_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        paths = self._candidate_paths(opponent_name)
        if not paths:
            return []

        # Pick newest export
        path = paths[0]
        try:
            raw = json.loads(open(path, "r", encoding="utf-8").read())
        except Exception:
            return []

        if not isinstance(raw, list):
            return []

        out: List[Dict[str, Any]] = []
        for item in raw[: max(0, int(limit))]:
            if not isinstance(item, dict):
                continue
            out.append(ScraperExportMatch(raw=item, opponent_name=opponent_name).to_tactical_stats())

        return out


_svc: Optional[ScraperExportService] = None


def get_scraper_export_service() -> ScraperExportService:
    global _svc
    if _svc is None:
        _svc = ScraperExportService()
    return _svc
