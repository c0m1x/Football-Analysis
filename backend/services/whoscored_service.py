"""WhoScored service via soccerdata.

This module provides a single free data source for:
- fixtures (past + upcoming)
- recent team tactical snapshots
- lightweight match/event-derived tactical metrics

It intentionally normalizes outputs to the existing project schema so the
frontend and tactical engine keep working.
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from config.settings import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()


def _slug(s: Any) -> str:
    return " ".join(str(s or "").strip().lower().split())


def _to_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return None


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        try:
            txt = str(v).replace("%", "").replace(",", ".").strip()
            return float(txt)
        except Exception:
            return None


def _safe_mean(values: Iterable[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return sum(nums) / len(nums)


def _safe_div(n: float, d: float, default: float = 0.0) -> float:
    if not d:
        return default
    return n / d


def _stable_team_id(name: str) -> int:
    h = hashlib.md5(_slug(name).encode("utf-8")).hexdigest()[:8]
    return int(h, 16)


def _parse_datetime_any(value: Any, fallback_time: Any = None) -> Optional[datetime]:
    if value is None:
        return None

    # pandas Timestamp support without importing pandas here
    if hasattr(value, "to_pydatetime"):
        try:
            dt = value.to_pydatetime()
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    s = str(value).strip()
    if not s:
        return None

    if fallback_time is not None:
        t = str(fallback_time).strip()
        if t and "T" not in s and len(s) <= 10:
            s = f"{s}T{t}"

    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    for parser in (datetime.fromisoformat,):
        try:
            dt = parser(s)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue

    return None


def _qual_text(qualifiers: Any) -> str:
    if qualifiers is None:
        return ""

    if isinstance(qualifiers, str):
        return _slug(qualifiers)

    parts: List[str] = []

    if isinstance(qualifiers, dict):
        qualifiers = [qualifiers]

    if isinstance(qualifiers, list):
        for q in qualifiers:
            if isinstance(q, str):
                parts.append(q)
                continue
            if not isinstance(q, dict):
                continue
            t = q.get("displayName")
            if not t and isinstance(q.get("type"), dict):
                t = q["type"].get("displayName")
            if not t:
                t = q.get("value")
            if t:
                parts.append(str(t))

    return _slug(" ".join(parts))


@dataclass(frozen=True)
class _TeamFilter:
    team_id: Optional[int]
    team_name: Optional[str]


class WhoScoredService:
    def __init__(self):
        self.enabled = bool(getattr(settings, "WHOSCORED_ENABLED", True))

        leagues_raw = str(getattr(settings, "WHOSCORED_LEAGUES", "") or "").strip()
        self.league_candidates = [x.strip() for x in leagues_raw.split(",") if x.strip()]
        if not self.league_candidates:
            self.league_candidates = [
                "ENG-Premier League",
                "ESP-La Liga",
                "ITA-Serie A",
                "GER-Bundesliga",
                "FRA-Ligue 1",
                "POR-Liga Portugal",
            ]
        self.default_league = str(
            getattr(settings, "WHOSCORED_DEFAULT_LEAGUE", self.league_candidates[0]) or self.league_candidates[0]
        ).strip()
        if self.default_league not in self.league_candidates:
            self.default_league = self.league_candidates[0]

        seasons_raw = str(getattr(settings, "WHOSCORED_SEASONS", "") or "").strip()
        self.season_candidates = [x.strip() for x in seasons_raw.split(",") if x.strip()]
        if not self.season_candidates:
            year = datetime.now(timezone.utc).year
            self.season_candidates = [str(year), str(year - 1)]

        self.cache_seconds = int(getattr(settings, "WHOSCORED_CACHE_SECONDS", 1800) or 1800)
        self.no_cache = bool(getattr(settings, "WHOSCORED_NO_CACHE", False))
        self.data_dir = str(getattr(settings, "WHOSCORED_DATA_DIR", "") or "").strip() or None

        self._reader_cache: Dict[str, Any] = {}
        self._schedule_cache: Dict[str, tuple[float, Any]] = {}
        self._events_cache: Dict[str, tuple[float, Any]] = {}

    def _import_sd(self):
        try:
            import soccerdata as sd  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Dependency `soccerdata` is missing. Run `pip install -r backend/requirements.txt`."
            ) from e
        return sd

    def _new_reader(self, league: str, season: str):
        sd = self._import_sd()
        season_value: Any = int(season) if str(season).isdigit() else season
        kwargs: Dict[str, Any] = {
            "leagues": league,
            "seasons": season_value,
            "no_cache": self.no_cache,
        }
        if self.data_dir:
            kwargs["data_dir"] = self.data_dir
        return sd.WhoScored(**kwargs)

    def get_available_leagues(self) -> List[str]:
        return list(self.league_candidates)

    def _reader_cache_key(self, league: str, season: str) -> str:
        return f"{league}::{season}"

    def _normalize_schedule_df(self, df: Any) -> Any:
        if df is None:
            return df
        if hasattr(df, "reset_index"):
            idx_names = [n for n in (getattr(df.index, "names", None) or []) if n]
            if idx_names:
                df = df.reset_index()
            elif "game" not in list(getattr(df, "columns", [])):
                df = df.reset_index().rename(columns={"index": "game"})
        return df

    def _resolve_reader_for_league(self, league: Optional[str] = None) -> tuple[Any, str, str]:
        if not self.enabled:
            raise RuntimeError("WhoScored integration is disabled")

        league_order: List[str]
        if league and league.strip():
            requested = league.strip()
            league_order = [requested]
        else:
            league_order = [self.default_league] + [x for x in self.league_candidates if x != self.default_league]

        last_error: Optional[Exception] = None
        for lg in league_order:
            for season in self.season_candidates:
                key = self._reader_cache_key(lg, season)
                reader = self._reader_cache.get(key)
                if reader is None:
                    try:
                        reader = self._new_reader(lg, season)
                        self._reader_cache[key] = reader
                    except Exception as e:
                        last_error = e
                        continue
                try:
                    df = reader.read_schedule()
                    if df is None or len(df) == 0:
                        continue
                    return reader, lg, season
                except Exception as e:
                    last_error = e
                    continue

        raise RuntimeError(
            f"Unable to initialize WhoScored reader for league={league or self.default_league} "
            f"with seasons={self.season_candidates}. Last error: {last_error}"
        )

    def _schedule_df(self, league: Optional[str] = None):
        reader, active_league, active_season = self._resolve_reader_for_league(league)
        cache_key = self._reader_cache_key(active_league, active_season)
        now = time.time()
        cached = self._schedule_cache.get(cache_key)
        if cached and (now - cached[0]) <= self.cache_seconds:
            return cached[1]

        df = reader.read_schedule()
        if df is None:
            raise RuntimeError("WhoScored returned empty schedule")
        df = self._normalize_schedule_df(df)

        self._schedule_cache[cache_key] = (now, df)
        return df

    @staticmethod
    def _row_get(row: Any, keys: List[str]) -> Any:
        for k in keys:
            if k in row and row.get(k) is not None:
                return row.get(k)
        return None

    def _team_filter_from_name_or_id(
        self,
        *,
        team_id: Optional[int],
        team_name: Optional[str],
        league: Optional[str] = None,
    ) -> _TeamFilter:
        if team_id is not None:
            return _TeamFilter(team_id=team_id, team_name=team_name)

        if team_name:
            resolved = self.resolve_team_id(team_name, league=league)
            return _TeamFilter(team_id=resolved, team_name=team_name)

        return _TeamFilter(team_id=None, team_name=None)

    def _row_matches_team(self, row: Any, filt: _TeamFilter) -> bool:
        hid = _to_int(self._row_get(row, ["home_team_id", "home_id"]))
        aid = _to_int(self._row_get(row, ["away_team_id", "away_id"]))
        hname = str(self._row_get(row, ["home_team", "home"]) or "")
        aname = str(self._row_get(row, ["away_team", "away"]) or "")

        if filt.team_id is not None and (hid == filt.team_id or aid == filt.team_id):
            return True

        if filt.team_name:
            target = _slug(filt.team_name)
            if target and (target == _slug(hname) or target == _slug(aname)):
                return True

        return False

    def _row_to_event(self, row: Any) -> Dict[str, Any]:
        game_id = self._row_get(row, ["game", "match_id", "id", "event_id"])
        game_id = _to_int(game_id) if _to_int(game_id) is not None else str(game_id)

        home_name = str(self._row_get(row, ["home_team", "home"]) or "Home")
        away_name = str(self._row_get(row, ["away_team", "away"]) or "Away")

        home_id = _to_int(self._row_get(row, ["home_team_id", "home_id"]))
        away_id = _to_int(self._row_get(row, ["away_team_id", "away_id"]))
        if home_id is None:
            home_id = _stable_team_id(home_name)
        if away_id is None:
            away_id = _stable_team_id(away_name)

        home_score = _to_int(self._row_get(row, ["home_score", "score_home"]))
        away_score = _to_int(self._row_get(row, ["away_score", "score_away"]))

        dt = _parse_datetime_any(
            self._row_get(row, ["date", "datetime", "kickoff", "start_time", "utc_time"]),
            fallback_time=self._row_get(row, ["time"]),
        )
        if dt is None:
            dt = datetime.now(timezone.utc)
        ts = int(dt.timestamp())

        status_txt = _slug(self._row_get(row, ["status", "match_status", "state"]))
        finished = home_score is not None and away_score is not None
        if "postpon" in status_txt:
            status_type = "postponed"
        elif "cancel" in status_txt:
            status_type = "cancelled"
        elif finished or status_txt in {"ft", "finished"}:
            status_type = "finished"
        else:
            status_type = "notstarted"

        ev = {
            "id": game_id,
            "startTimestamp": ts,
            "homeTeam": {"id": int(home_id), "name": home_name},
            "awayTeam": {"id": int(away_id), "name": away_name},
            "status": {"type": status_type},
        }

        if home_score is not None:
            ev["homeScore"] = {"current": int(home_score)}
        if away_score is not None:
            ev["awayScore"] = {"current": int(away_score)}

        return ev

    def resolve_team_id(self, team_name: str, league: Optional[str] = None) -> Optional[int]:
        if not team_name:
            return None

        target = _slug(team_name)
        df = self._schedule_df(league=league)

        best_id = None
        for _, row in df.iterrows():
            home_name = str(self._row_get(row, ["home_team", "home"]) or "")
            away_name = str(self._row_get(row, ["away_team", "away"]) or "")

            if _slug(home_name) == target:
                best_id = _to_int(self._row_get(row, ["home_team_id", "home_id"])) or _stable_team_id(home_name)
                break
            if _slug(away_name) == target:
                best_id = _to_int(self._row_get(row, ["away_team_id", "away_id"])) or _stable_team_id(away_name)
                break

        if best_id is None:
            best_id = _stable_team_id(team_name)
        return int(best_id)

    def resolve_team_name(self, team_id: int, league: Optional[str] = None) -> Optional[str]:
        try:
            target_id = int(team_id)
        except Exception:
            return None

        df = self._schedule_df(league=league)
        for _, row in df.iterrows():
            hid = _to_int(self._row_get(row, ["home_team_id", "home_id"]))
            aid = _to_int(self._row_get(row, ["away_team_id", "away_id"]))
            if hid == target_id:
                name = self._row_get(row, ["home_team", "home"])
                return str(name) if name else None
            if aid == target_id:
                name = self._row_get(row, ["away_team", "away"])
                return str(name) if name else None
        return None

    def list_teams(self, league: Optional[str], search: Optional[str] = None, limit: int = 250) -> List[Dict[str, Any]]:
        df = self._schedule_df(league=league)
        teams: Dict[int, str] = {}
        query = _slug(search or "")

        for _, row in df.iterrows():
            home_name = str(self._row_get(row, ["home_team", "home"]) or "")
            away_name = str(self._row_get(row, ["away_team", "away"]) or "")
            home_id = _to_int(self._row_get(row, ["home_team_id", "home_id"])) or _stable_team_id(home_name)
            away_id = _to_int(self._row_get(row, ["away_team_id", "away_id"])) or _stable_team_id(away_name)

            if home_name:
                teams[int(home_id)] = home_name
            if away_name:
                teams[int(away_id)] = away_name

        out = [
            {"id": str(team_id), "name": name}
            for team_id, name in teams.items()
            if name and (not query or query in _slug(name))
        ]
        out.sort(key=lambda t: _slug(t.get("name")))
        return out[: max(1, int(limit))]

    def get_team_events(
        self,
        team_id: int,
        past_limit: int = 30,
        upcoming_limit: int = 15,
        team_name: Optional[str] = None,
        league: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        df = self._schedule_df(league=league)
        filt = self._team_filter_from_name_or_id(team_id=team_id, team_name=team_name, league=league)

        rows = [row for _, row in df.iterrows() if self._row_matches_team(row, filt)]
        events = [self._row_to_event(r) for r in rows]

        events.sort(key=lambda e: int(e.get("startTimestamp") or 0), reverse=True)

        past = [e for e in events if _slug((e.get("status") or {}).get("type")) == "finished"]
        upcoming = [e for e in events if _slug((e.get("status") or {}).get("type")) != "finished"]
        upcoming.sort(key=lambda e: int(e.get("startTimestamp") or 0))

        return past[: max(0, int(past_limit))] + upcoming[: max(0, int(upcoming_limit))]

    def get_last_finished_events(
        self,
        team_id: int,
        limit: int = 5,
        max_pages: int = 3,
        league: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        _ = max_pages  # compatibility parameter
        events = self.get_team_events(
            team_id,
            past_limit=max(20, int(limit) * 4),
            upcoming_limit=0,
            league=league,
        )
        return [e for e in events if _slug((e.get("status") or {}).get("type")) == "finished"][: max(0, int(limit))]

    def get_upcoming_events(
        self,
        team_id: int,
        limit: int = 5,
        max_pages: int = 2,
        league: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        _ = max_pages  # compatibility parameter
        events = self.get_team_events(
            team_id,
            past_limit=0,
            upcoming_limit=max(10, int(limit) * 2),
            league=league,
        )
        out = [e for e in events if _slug((e.get("status") or {}).get("type")) != "finished"]
        out.sort(key=lambda e: int(e.get("startTimestamp") or 0))
        return out[: max(0, int(limit))]

    def _read_events(self, game_id: Any, league: Optional[str] = None):
        key = f"{league or self.default_league}::{game_id}"
        now = time.time()

        cached = self._events_cache.get(key)
        if cached and (now - cached[0]) <= self.cache_seconds:
            return cached[1]

        reader, _, _ = self._resolve_reader_for_league(league)

        last_error = None
        for kwargs in ({"match_id": game_id}, {"game_id": game_id}, {"game": game_id}):
            try:
                df = reader.read_events(**kwargs)
                self._events_cache[key] = (now, df)
                return df
            except TypeError as e:
                last_error = e
                continue
            except Exception as e:
                last_error = e
                continue

        if last_error:
            raise RuntimeError(f"Unable to read events for game={game_id}: {last_error}")
        raise RuntimeError(f"Unable to read events for game={game_id}")

    @staticmethod
    def _normalize_event_type(v: Any) -> str:
        if isinstance(v, dict):
            for k in ("displayName", "value", "name"):
                if v.get(k):
                    return _slug(v.get(k))
            return ""
        return _slug(v)

    def _build_time_seconds(self, row: Any) -> int:
        minute = _to_int(self._row_get(row, ["minute", "expanded_minute", "event_minute"])) or 0
        second = _to_int(self._row_get(row, ["second", "event_second"])) or 0
        return minute * 60 + second

    def _normalize_tactical_from_events(
        self,
        *,
        event: Dict[str, Any],
        team_id: int,
        team_name: str,
        events_df: Any,
        formation_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        if events_df is None or len(events_df) == 0:
            return {
                "estimated": True,
                "match_info": {
                    "event_id": event.get("id"),
                    "team": team_name,
                    "opponent": None,
                    "score": None,
                    "result": None,
                    "location": None,
                    "date": event.get("startTimestamp"),
                },
            }

        if hasattr(events_df, "reset_index") and any(getattr(events_df.index, "names", []) or []):
            events_df = events_df.reset_index()

        # Ensure fast row-level access for heterogeneous schemas.
        rows = []
        for _, row in events_df.iterrows():
            if hasattr(row, "to_dict"):
                rows.append(row.to_dict())
            else:
                rows.append(dict(row))

        home = event.get("homeTeam") or {}
        away = event.get("awayTeam") or {}
        is_home = int(home.get("id") or 0) == int(team_id)
        opp_name = away.get("name") if is_home else home.get("name")

        hs = _to_int(((event.get("homeScore") or {}).get("current"))) or 0
        aws = _to_int(((event.get("awayScore") or {}).get("current"))) or 0
        team_score = hs if is_home else aws
        opp_score = aws if is_home else hs
        result = "W" if team_score > opp_score else "L" if team_score < opp_score else "D"

        def row_team_match(r: Dict[str, Any]) -> bool:
            rid = _to_int(r.get("team_id") or r.get("teamId"))
            if rid is not None:
                return rid == int(team_id)
            rteam = _slug(r.get("team") or r.get("team_name") or r.get("teamName"))
            return bool(rteam) and rteam == _slug(team_name)

        team_rows = [r for r in rows if row_team_match(r)]
        opp_rows = [r for r in rows if not row_team_match(r)]

        def rtype(r: Dict[str, Any]) -> str:
            return self._normalize_event_type(r.get("type") or r.get("event_type"))

        def outcome(r: Dict[str, Any]) -> str:
            return self._normalize_event_type(r.get("outcome_type") or r.get("outcomeType") or r.get("outcome"))

        def quals(r: Dict[str, Any]) -> str:
            return _qual_text(r.get("qualifiers"))

        def x(r: Dict[str, Any]) -> Optional[float]:
            return _to_float(r.get("x"))

        def y(r: Dict[str, Any]) -> Optional[float]:
            return _to_float(r.get("y"))

        def end_x(r: Dict[str, Any]) -> Optional[float]:
            return _to_float(r.get("end_x") or r.get("endX"))

        def end_y(r: Dict[str, Any]) -> Optional[float]:
            return _to_float(r.get("end_y") or r.get("endY"))

        pass_rows = [r for r in team_rows if "pass" in rtype(r)]
        succ_pass_rows = [r for r in pass_rows if "successful" in outcome(r)]

        total_passes = len(pass_rows)
        accurate_passes = len(succ_pass_rows)
        pass_accuracy = round(_safe_div(accurate_passes, total_passes, 0.0) * 100.0, 1) if total_passes else None

        long_balls = [r for r in pass_rows if "long" in quals(r)]
        long_balls_ok = [r for r in long_balls if "successful" in outcome(r)]

        crosses = [r for r in pass_rows if "cross" in quals(r)]
        crosses_ok = [r for r in crosses if "successful" in outcome(r)]

        key_passes = [r for r in pass_rows if "key pass" in quals(r)]

        progressive_passes = []
        final_third_passes = []
        penalty_passes = []
        cutbacks = []
        for r in pass_rows:
            sx, sy, ex, ey = x(r), y(r), end_x(r), end_y(r)
            if sx is None or ex is None:
                continue
            if (ex - sx) >= 25:
                progressive_passes.append(r)
            if (sx < 66 and ex >= 66) or "final third" in quals(r):
                final_third_passes.append(r)
            if (ex >= 83 and ey is not None and 21 <= ey <= 79) or "penalty area" in quals(r):
                penalty_passes.append(r)
            if sx >= 85 and sy is not None and (sy <= 20 or sy >= 80) and ex >= 80 and ey is not None and 24 <= ey <= 76:
                cutbacks.append(r)

        def is_shot_row(r: Dict[str, Any]) -> bool:
            if r.get("is_shot") is True:
                return True
            t = rtype(r)
            return any(k in t for k in ["shot", "goal", "miss", "saved", "attempt"])

        shot_rows = [r for r in team_rows if is_shot_row(r)]

        shots_on_target = []
        shots_inside = []
        shots_outside = []
        xg_values = []

        for r in shot_rows:
            qtxt = quals(r)
            t = rtype(r)
            on_target = bool(r.get("is_goal")) or ("on target" in qtxt) or ("saved" in t)
            if on_target:
                shots_on_target.append(r)

            sx = x(r)
            sy = y(r)
            inside = ("inside box" in qtxt) or (sx is not None and sx >= 83 and sy is not None and 18 <= sy <= 82)
            if inside:
                shots_inside.append(r)
            else:
                shots_outside.append(r)

            if sx is not None and sy is not None:
                d1 = math.sqrt((100 - sx) ** 2 + (50 - sy) ** 2)
                d2 = math.sqrt((sx - 0) ** 2 + (50 - sy) ** 2)
                d = min(d1, d2)
                xg = 1.0 / (1.0 + math.exp((d - 18.0) / 4.5))
                xg_values.append(max(0.01, min(0.85, xg)))

        xg_total = round(sum(xg_values), 2) if xg_values else None
        xg_per_shot = round(_safe_div(sum(xg_values), len(shot_rows), 0.0), 3) if shot_rows else None
        shot_conv = round(_safe_div(team_score, len(shot_rows), 0.0) * 100.0, 1) if shot_rows else None

        tackles = [r for r in team_rows if "tackle" in rtype(r)]
        tackles_won = [r for r in tackles if "successful" in outcome(r)]
        interceptions = [r for r in team_rows if "interception" in rtype(r)]
        clearances = [r for r in team_rows if "clearance" in rtype(r)]
        blocks = [r for r in team_rows if "block" in rtype(r)]

        duel_rows = [r for r in team_rows if any(k in rtype(r) for k in ["duel", "aerial", "ground"]) ]
        duel_won = [r for r in duel_rows if "successful" in outcome(r)]
        duel_pct = round(_safe_div(len(duel_won), len(duel_rows), 0.0) * 100.0, 1) if duel_rows else None

        opp_pass_rows = [r for r in opp_rows if "pass" in rtype(r)]
        high_actions = [r for r in team_rows if any(k in rtype(r) for k in ["tackle", "interception", "foul"])]

        def high_zone_count(rset: List[Dict[str, Any]]) -> int:
            right = 0
            left = 0
            for r in rset:
                xv = x(r)
                if xv is None:
                    continue
                if xv >= 60:
                    right += 1
                if xv <= 40:
                    left += 1
            return max(right, left)

        high_actions_n = high_zone_count(high_actions)
        opp_passes_n = len(opp_pass_rows)
        ppda = round(_safe_div(opp_passes_n, max(1, high_actions_n), 0.0), 2) if opp_passes_n else None

        turnover_recoveries = [r for r in team_rows if any(k in rtype(r) for k in ["interception", "tackle", "ball recovery"]) ]
        high_turnovers_won = high_zone_count(turnover_recoveries)

        losses = []
        recoveries = []
        for r in team_rows:
            t = rtype(r)
            out = outcome(r)
            ts = self._build_time_seconds(r)
            if ("pass" in t and "successful" not in out) or any(k in t for k in ["dispossessed", "bad touch", "miscontrol"]):
                losses.append(ts)
            if any(k in t for k in ["interception", "tackle", "ball recovery"]) and ("successful" in out or "interception" in t):
                recoveries.append(ts)

        counter_press = 0
        if losses and recoveries:
            losses_sorted = sorted(losses)
            for rt in sorted(recoveries):
                # recovery shortly after a loss
                if any((0 <= rt - lt <= 8) for lt in losses_sorted):
                    counter_press += 1

        xs = [x(r) for r in team_rows if x(r) is not None]
        ys = [y(r) for r in team_rows if y(r) is not None]
        avg_x = _safe_mean(xs)
        avg_y_abs = _safe_mean([abs(v - 50.0) for v in ys])

        if avg_x is None:
            line_height_label = None
            def_line_height = None
        else:
            def_line_height = round(avg_x, 1)
            if avg_x >= 55:
                line_height_label = "High"
            elif avg_x <= 45:
                line_height_label = "Low"
            else:
                line_height_label = "Medium"

        spread_x = _safe_mean([abs(v - (avg_x or 50.0)) for v in xs])
        spread_y = _safe_mean([abs(v - 50.0) for v in ys])

        if spread_x is None:
            distance_between_lines = None
        elif spread_x <= 12:
            distance_between_lines = "Compact (15-20m)"
        elif spread_x <= 18:
            distance_between_lines = "Standard (20-25m)"
        else:
            distance_between_lines = "Stretched (>25m)"

        if spread_y is None:
            compactness = None
        elif spread_y <= 14:
            compactness = "Narrow"
        elif spread_y <= 20:
            compactness = "Balanced"
        else:
            compactness = "Wide"

        if avg_y_abs is None:
            width_usage = None
        elif avg_y_abs >= 18:
            width_usage = "Wide flanks exploited"
        elif avg_y_abs <= 13:
            width_usage = "Central focus"
        else:
            width_usage = "Balanced"

        possession = None
        total_team_actions = len(team_rows)
        total_opp_actions = len(opp_rows)
        if total_team_actions and total_opp_actions:
            possession = round(_safe_div(total_team_actions, total_team_actions + total_opp_actions, 0.0) * 100.0, 1)

        passes_per_min = round(_safe_div(total_passes, 90.0, 0.0), 2) if total_passes else None
        tempo_rating = None
        if passes_per_min is not None:
            tempo_rating = "High" if passes_per_min >= 4.2 else "Medium" if passes_per_min >= 3.4 else "Low"

        possession_insight = None
        if possession is not None and passes_per_min is not None:
            if possession >= 60 and passes_per_min >= 4.0:
                possession_insight = "High possession + high tempo -> likely controls territory and rhythm"
            elif possession <= 40 and passes_per_min <= 3.2:
                possession_insight = "Low possession + low tempo -> likely deeper block and transitions"

        shooting_insight = None
        if len(shot_rows) >= 14 and (xg_total or 0) < 1.2:
            shooting_insight = "High shot volume but low xG -> low-quality shooting profile"
        elif len(shot_rows) <= 8 and (xg_total or 0) >= 1.3:
            shooting_insight = "Low shot volume but high xG -> efficient chance creation"

        corners_for = len([r for r in team_rows if "corner" in rtype(r)])
        corners_against = len([r for r in opp_rows if "corner" in rtype(r)])

        return {
            "estimated": False,
            "match_info": {
                "event_id": event.get("id"),
                "team": team_name,
                "opponent": opp_name,
                "score": f"{team_score}-{opp_score}",
                "result": result,
                "location": "Home" if is_home else "Away",
                "date": datetime.fromtimestamp(int(event.get("startTimestamp") or 0), tz=timezone.utc).isoformat(),
            },
            "possession_control": {
                "possession_percent": possession,
                "time_in_opponent_half": None,
                "pass_accuracy": pass_accuracy,
                "passes_per_minute": passes_per_min,
                "long_balls_attempted": float(len(long_balls)) if long_balls else None,
                "long_balls_completed": float(len(long_balls_ok)) if long_balls_ok else None,
                "tempo_rating": tempo_rating,
                "tactical_insight": possession_insight,
            },
            "shooting_finishing": {
                "total_shots": float(len(shot_rows)) if shot_rows else None,
                "shots_on_target": float(len(shots_on_target)) if shots_on_target else None,
                "shot_conversion_rate": shot_conv,
                "shots_inside_box": float(len(shots_inside)) if shots_inside else None,
                "shots_outside_box": float(len(shots_outside)) if shots_outside else None,
                "big_chances_created": None,
                "big_chances_missed": None,
                "tactical_insight": shooting_insight,
            },
            "expected_metrics": {
                "xG": xg_total,
                "xG_per_shot": xg_per_shot,
                "xG_from_open_play": None,
                "xG_from_set_pieces": None,
                "xA": None,
                "performance_rating": None,
            },
            "chance_creation": {
                "key_passes": float(len(key_passes)) if key_passes else None,
                "progressive_passes": float(len(progressive_passes)) if progressive_passes else None,
                "passes_into_final_third": float(len(final_third_passes)) if final_third_passes else None,
                "passes_into_penalty_area": float(len(penalty_passes)) if penalty_passes else None,
                "crosses_attempted": float(len(crosses)) if crosses else None,
                "crosses_accurate": float(len(crosses_ok)) if crosses_ok else None,
                "cutbacks": float(len(cutbacks)) if cutbacks else None,
                "creation_quality": None,
            },
            "defensive_actions": {
                "tackles_attempted": float(len(tackles)) if tackles else None,
                "tackles_won": float(len(tackles_won)) if tackles_won else None,
                "tackle_success_rate": round(_safe_div(len(tackles_won), len(tackles), 0.0) * 100.0, 1) if tackles else None,
                "interceptions": float(len(interceptions)) if interceptions else None,
                "blocks": float(len(blocks)) if blocks else None,
                "clearances": float(len(clearances)) if clearances else None,
                "defensive_duels_won_percent": duel_pct,
                "defensive_rating": None,
                "duels_won": float(len(duel_won)) if duel_won else None,
                "duels_total": float(len(duel_rows)) if duel_rows else None,
            },
            "pressing_structure": {
                "PPDA": ppda,
                "pressing_intensity": "High" if ppda is not None and ppda < 10 else "Medium" if ppda is not None and ppda < 14 else "Low" if ppda is not None else None,
                "high_turnovers_won": float(high_turnovers_won) if high_turnovers_won else None,
                "counter_press_recoveries": float(counter_press) if counter_press else None,
                "pressing_zones": None,
                "tactical_insight": None,
            },
            "team_shape": {
                "avg_team_line_height": line_height_label,
                "defensive_line_height": def_line_height,
                "distance_between_lines": distance_between_lines,
                "team_compactness": compactness,
                "width_usage": width_usage,
                "formation_detected": formation_hint,
            },
            "transitions": None,
            "set_pieces": {
                "attacking": {
                    "corners_taken": float(corners_for) if corners_for else None,
                    "xG_from_corners": None,
                    "first_contact_success": None,
                    "second_ball_recoveries": None,
                    "set_piece_goals": None,
                },
                "defensive": {
                    "corners_conceded": float(corners_against) if corners_against else None,
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

    def get_recent_games_tactical(
        self,
        team_name: str,
        limit: int = 5,
        team_id: Optional[int] = None,
        league: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        resolved_id = int(team_id) if team_id is not None else self.resolve_team_id(team_name, league=league)
        if resolved_id is None:
            return []

        events = self.get_last_finished_events(
            int(resolved_id),
            limit=max(1, int(limit) * 3),
            league=league,
        )
        out: List[Dict[str, Any]] = []

        for ev in events:
            if len(out) >= int(limit):
                break
            game_id = ev.get("id")
            if game_id is None:
                continue
            try:
                events_df = self._read_events(game_id, league=league)
                out.append(
                    self._normalize_tactical_from_events(
                        event=ev,
                        team_id=int(resolved_id),
                        team_name=team_name,
                        events_df=events_df,
                        formation_hint=None,
                    )
                )
            except Exception as e:
                logger.warning("WhoScored normalize failed for game=%s: %s", game_id, e)

        return out


_whoscored_service: Optional[WhoScoredService] = None


def get_whoscored_service() -> WhoScoredService:
    global _whoscored_service
    if _whoscored_service is None:
        _whoscored_service = WhoScoredService()
    return _whoscored_service
