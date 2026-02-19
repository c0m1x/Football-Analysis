"""Tactical ML service: training + inference for tactical suggestions."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config.settings import get_settings
from services.whoscored_service import get_whoscored_service
from utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()


FEATURE_NAMES = [
    "possession_percent",
    "pass_accuracy",
    "passes_per_minute",
    "long_balls_attempted",
    "long_balls_completed",
    "total_shots",
    "shots_on_target",
    "shot_conversion_rate",
    "shots_inside_box",
    "shots_outside_box",
    "xg",
    "xg_per_shot",
    "key_passes",
    "progressive_passes",
    "passes_into_final_third",
    "passes_into_penalty_area",
    "crosses_attempted",
    "crosses_accurate",
    "cutbacks",
    "tackles_attempted",
    "tackles_won",
    "interceptions",
    "blocks",
    "clearances",
    "defensive_duels_won_percent",
    "ppda",
    "high_turnovers_won",
    "counter_press_recoveries",
    "defensive_line_height",
    "corners_taken",
    "corners_conceded",
    "form_points_per_game",
    "form_win_rate",
    "form_goals_for_avg",
    "form_goals_against_avg",
]


def _safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _mean(values: List[Optional[float]]) -> Optional[float]:
    nums = [float(v) for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return float(sum(nums) / len(nums))


def _parse_score(score: Any) -> Tuple[Optional[int], Optional[int]]:
    if isinstance(score, str) and "-" in score:
        parts = score.split("-", 1)
        try:
            return int(parts[0].strip()), int(parts[1].strip())
        except Exception:
            return None, None
    return None, None


def _result_to_points(result: Any) -> int:
    r = str(result or "").strip().upper()
    if r == "W":
        return 3
    if r == "D":
        return 1
    return 0


class TacticalMLService:
    """Lifecycle and usage of tactical ML model."""

    def __init__(self) -> None:
        self.enabled = bool(getattr(settings, "ML_ENABLED", True))
        self.model_path = self._resolve_model_path(str(getattr(settings, "ML_MODEL_PATH", "data/models/tactical_model.joblib")))
        self.window_size = max(3, int(getattr(settings, "ML_WINDOW_SIZE", 5) or 5))
        self.min_samples = max(30, int(getattr(settings, "ML_MIN_SAMPLES", 120) or 120))
        self.max_teams_per_league = max(4, int(getattr(settings, "ML_MAX_TEAMS_PER_LEAGUE", 20) or 20))
        self.matches_per_team = max(10, int(getattr(settings, "ML_MATCHES_PER_TEAM", 28) or 28))
        self.default_training_leagues = [
            x.strip()
            for x in str(getattr(settings, "ML_TRAINING_LEAGUES", "POR-Liga Portugal") or "").split(",")
            if x.strip()
        ] or ["POR-Liga Portugal"]

        self._model_bundle: Optional[Dict[str, Any]] = None
        self._last_error: Optional[str] = None
        self._train_lock = asyncio.Lock()

        self._load_model()

    def _resolve_model_path(self, path_str: str) -> Path:
        path = Path(path_str).expanduser()
        if path.is_absolute():
            return path
        return (Path.cwd() / path).resolve()

    def _ensure_parent_dir(self) -> None:
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            fallback = (Path.cwd().parent / "data" / "models" / self.model_path.name).resolve()
            fallback.parent.mkdir(parents=True, exist_ok=True)
            self.model_path = fallback

    def _load_model(self) -> None:
        if not self.model_path.exists():
            self._model_bundle = None
            return
        try:
            import joblib

            self._model_bundle = joblib.load(self.model_path)
            self._last_error = None
        except Exception as e:
            self._model_bundle = None
            self._last_error = f"Failed loading model: {e}"
            logger.warning(self._last_error)

    def is_model_available(self) -> bool:
        return self._model_bundle is not None

    def get_status(self) -> Dict[str, Any]:
        bundle = self._model_bundle or {}
        meta = bundle.get("metadata", {}) if isinstance(bundle, dict) else {}
        return {
            "ml_enabled": self.enabled,
            "model_available": self.is_model_available(),
            "model_path": str(self.model_path),
            "model_version": meta.get("model_version"),
            "trained_at": meta.get("trained_at"),
            "sample_count": meta.get("sample_count"),
            "training_leagues": meta.get("training_leagues", []),
            "metrics": meta.get("metrics", {}),
            "window_size": self.window_size,
            "last_error": self._last_error,
        }

    def _extract_match_features(self, match: Dict[str, Any]) -> Dict[str, Optional[float]]:
        return {
            "possession_percent": _safe_float(_safe_get(match, "possession_control", "possession_percent")),
            "pass_accuracy": _safe_float(_safe_get(match, "possession_control", "pass_accuracy")),
            "passes_per_minute": _safe_float(_safe_get(match, "possession_control", "passes_per_minute")),
            "long_balls_attempted": _safe_float(_safe_get(match, "possession_control", "long_balls_attempted")),
            "long_balls_completed": _safe_float(_safe_get(match, "possession_control", "long_balls_completed")),
            "total_shots": _safe_float(_safe_get(match, "shooting_finishing", "total_shots")),
            "shots_on_target": _safe_float(_safe_get(match, "shooting_finishing", "shots_on_target")),
            "shot_conversion_rate": _safe_float(_safe_get(match, "shooting_finishing", "shot_conversion_rate")),
            "shots_inside_box": _safe_float(_safe_get(match, "shooting_finishing", "shots_inside_box")),
            "shots_outside_box": _safe_float(_safe_get(match, "shooting_finishing", "shots_outside_box")),
            "xg": _safe_float(_safe_get(match, "expected_metrics", "xG")),
            "xg_per_shot": _safe_float(_safe_get(match, "expected_metrics", "xG_per_shot")),
            "key_passes": _safe_float(_safe_get(match, "chance_creation", "key_passes")),
            "progressive_passes": _safe_float(_safe_get(match, "chance_creation", "progressive_passes")),
            "passes_into_final_third": _safe_float(_safe_get(match, "chance_creation", "passes_into_final_third")),
            "passes_into_penalty_area": _safe_float(_safe_get(match, "chance_creation", "passes_into_penalty_area")),
            "crosses_attempted": _safe_float(_safe_get(match, "chance_creation", "crosses_attempted")),
            "crosses_accurate": _safe_float(_safe_get(match, "chance_creation", "crosses_accurate")),
            "cutbacks": _safe_float(_safe_get(match, "chance_creation", "cutbacks")),
            "tackles_attempted": _safe_float(_safe_get(match, "defensive_actions", "tackles_attempted")),
            "tackles_won": _safe_float(_safe_get(match, "defensive_actions", "tackles_won")),
            "interceptions": _safe_float(_safe_get(match, "defensive_actions", "interceptions")),
            "blocks": _safe_float(_safe_get(match, "defensive_actions", "blocks")),
            "clearances": _safe_float(_safe_get(match, "defensive_actions", "clearances")),
            "defensive_duels_won_percent": _safe_float(
                _safe_get(match, "defensive_actions", "defensive_duels_won_percent")
            ),
            "ppda": _safe_float(_safe_get(match, "pressing_structure", "PPDA")),
            "high_turnovers_won": _safe_float(_safe_get(match, "pressing_structure", "high_turnovers_won")),
            "counter_press_recoveries": _safe_float(_safe_get(match, "pressing_structure", "counter_press_recoveries")),
            "defensive_line_height": _safe_float(_safe_get(match, "team_shape", "defensive_line_height")),
            "corners_taken": _safe_float(_safe_get(match, "set_pieces", "attacking", "corners_taken")),
            "corners_conceded": _safe_float(_safe_get(match, "set_pieces", "defensive", "corners_conceded")),
        }

    def _aggregate_history_window(self, history: List[Dict[str, Any]]) -> Dict[str, float]:
        values_by_feature: Dict[str, List[Optional[float]]] = {k: [] for k in FEATURE_NAMES}
        points: List[float] = []
        goals_for: List[float] = []
        goals_against: List[float] = []

        for match in history:
            base = self._extract_match_features(match)
            for key, value in base.items():
                values_by_feature[key].append(value)

            result = _safe_get(match, "match_info", "result", default="")
            points.append(float(_result_to_points(result)))

            score = _safe_get(match, "match_info", "score")
            gf, ga = _parse_score(score)
            goals_for.append(float(gf) if gf is not None else None)
            goals_against.append(float(ga) if ga is not None else None)

        out: Dict[str, float] = {}
        for feature in FEATURE_NAMES:
            if feature in ("form_points_per_game", "form_win_rate", "form_goals_for_avg", "form_goals_against_avg"):
                continue
            out[feature] = _mean(values_by_feature.get(feature, []))

        n = max(1, len(history))
        out["form_points_per_game"] = float(sum(points) / n) if points else None
        out["form_win_rate"] = float(sum(1.0 for p in points if p >= 3.0) / n) if points else None
        out["form_goals_for_avg"] = _mean(goals_for)
        out["form_goals_against_avg"] = _mean(goals_against)
        return out

    def _target_from_match(self, match: Dict[str, Any]) -> Tuple[Optional[str], Optional[float], Optional[float]]:
        result = str(_safe_get(match, "match_info", "result", default="")).upper()
        if result not in {"W", "D", "L"}:
            return None, None, None
        score = _safe_get(match, "match_info", "score")
        gf, ga = _parse_score(score)
        if gf is None or ga is None:
            return None, None, None
        return result, float(gf), float(ga)

    def _sort_matches_chronological(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def _sort_key(match: Dict[str, Any]) -> float:
            value = str(_safe_get(match, "match_info", "date", default="") or "")
            if not value:
                return 0.0
            text = value.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(text).timestamp()
            except Exception:
                return 0.0

        return sorted(matches, key=_sort_key)

    def _build_samples_for_team(
        self,
        matches: List[Dict[str, Any]],
    ) -> Tuple[List[List[float]], List[str], List[float], List[float]]:
        ordered = self._sort_matches_chronological(matches)
        if len(ordered) <= self.window_size:
            return [], [], [], []

        x_rows: List[List[float]] = []
        y_result: List[str] = []
        y_goals_for: List[float] = []
        y_goals_against: List[float] = []

        for idx in range(self.window_size, len(ordered)):
            history = ordered[idx - self.window_size : idx]
            target = ordered[idx]
            target_result, target_gf, target_ga = self._target_from_match(target)
            if target_result is None or target_gf is None or target_ga is None:
                continue

            agg = self._aggregate_history_window(history)
            row = [float(agg.get(name)) if agg.get(name) is not None else np.nan for name in FEATURE_NAMES]
            x_rows.append(row)
            y_result.append(target_result)
            y_goals_for.append(float(target_gf))
            y_goals_against.append(float(target_ga))

        return x_rows, y_result, y_goals_for, y_goals_against

    async def _collect_dataset(self, leagues: List[str]) -> Dict[str, Any]:
        ws = get_whoscored_service()

        x_rows: List[List[float]] = []
        y_result: List[str] = []
        y_goals_for: List[float] = []
        y_goals_against: List[float] = []

        total_teams = 0
        used_teams = 0

        for league in leagues:
            try:
                teams = ws.list_teams(league=league, limit=self.max_teams_per_league)
            except Exception as e:
                logger.warning("ML dataset: failed to list teams for %s: %s", league, e)
                continue

            teams = teams[: self.max_teams_per_league]
            total_teams += len(teams)

            for team in teams:
                team_id = int(team.get("id"))
                team_name = str(team.get("name") or "")
                if not team_name:
                    continue
                try:
                    recent = await asyncio.to_thread(
                        ws.get_recent_games_tactical,
                        team_name,
                        self.matches_per_team,
                        team_id,
                        league,
                    )
                except Exception as e:
                    logger.debug("ML dataset: team fetch failed for %s (%s): %s", team_name, team_id, e)
                    continue

                team_x, team_y_r, team_y_gf, team_y_ga = self._build_samples_for_team(recent or [])
                if not team_x:
                    continue

                used_teams += 1
                x_rows.extend(team_x)
                y_result.extend(team_y_r)
                y_goals_for.extend(team_y_gf)
                y_goals_against.extend(team_y_ga)

        return {
            "X": np.asarray(x_rows, dtype=float),
            "y_result": np.asarray(y_result, dtype=object),
            "y_goals_for": np.asarray(y_goals_for, dtype=float),
            "y_goals_against": np.asarray(y_goals_against, dtype=float),
            "total_teams_seen": total_teams,
            "teams_with_samples": used_teams,
        }

    def _train_estimators(
        self,
        x_all: np.ndarray,
        y_result: np.ndarray,
        y_goals_for: np.ndarray,
        y_goals_against: np.ndarray,
    ) -> Dict[str, Any]:
        try:
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            from sklearn.impute import SimpleImputer
            from sklearn.metrics import accuracy_score, mean_absolute_error
            from sklearn.model_selection import train_test_split
            from sklearn.pipeline import Pipeline
        except Exception as e:
            raise RuntimeError(
                "scikit-learn is required for ML training. Install backend dependencies first."
            ) from e

        def build_result_model():
            return Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        RandomForestClassifier(
                            n_estimators=300,
                            min_samples_leaf=2,
                            random_state=42,
                            class_weight="balanced_subsample",
                        ),
                    ),
                ]
            )

        def build_reg_model():
            return Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        RandomForestRegressor(
                            n_estimators=300,
                            min_samples_leaf=2,
                            random_state=42,
                        ),
                    ),
                ]
            )

        metrics: Dict[str, Any] = {}
        n_samples = int(x_all.shape[0])

        can_eval = n_samples >= 80 and len(set(y_result.tolist())) >= 2
        if can_eval:
            try:
                classes, counts = np.unique(y_result, return_counts=True)
                stratify = y_result if counts.min() >= 2 else None
                split = train_test_split(
                    x_all,
                    y_result,
                    y_goals_for,
                    y_goals_against,
                    test_size=0.2,
                    random_state=42,
                    stratify=stratify,
                )
                x_train, x_test, y_train_res, y_test_res, y_train_gf, y_test_gf, y_train_ga, y_test_ga = split

                result_eval = build_result_model()
                gf_eval = build_reg_model()
                ga_eval = build_reg_model()
                result_eval.fit(x_train, y_train_res)
                gf_eval.fit(x_train, y_train_gf)
                ga_eval.fit(x_train, y_train_ga)

                res_pred = result_eval.predict(x_test)
                gf_pred = gf_eval.predict(x_test)
                ga_pred = ga_eval.predict(x_test)

                metrics = {
                    "result_accuracy": round(float(accuracy_score(y_test_res, res_pred)), 4),
                    "goals_for_mae": round(float(mean_absolute_error(y_test_gf, gf_pred)), 4),
                    "goals_against_mae": round(float(mean_absolute_error(y_test_ga, ga_pred)), 4),
                    "holdout_samples": int(x_test.shape[0]),
                }
            except Exception as e:
                logger.warning("ML evaluation step failed: %s", e)
                metrics = {}

        result_model = build_result_model()
        goals_for_model = build_reg_model()
        goals_against_model = build_reg_model()
        result_model.fit(x_all, y_result)
        goals_for_model.fit(x_all, y_goals_for)
        goals_against_model.fit(x_all, y_goals_against)

        return {
            "result_model": result_model,
            "goals_for_model": goals_for_model,
            "goals_against_model": goals_against_model,
            "metrics": metrics,
        }

    async def train_model(self, leagues: Optional[List[str]] = None, force: bool = False) -> Dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "reason": "ML disabled by configuration"}

        async with self._train_lock:
            if self.is_model_available() and not force:
                return {
                    "ok": True,
                    "skipped": True,
                    "reason": "Model already exists. Use force=true to retrain.",
                    "status": self.get_status(),
                }

            use_leagues = [x.strip() for x in (leagues or self.default_training_leagues) if x and x.strip()]
            if not use_leagues:
                use_leagues = list(self.default_training_leagues)

            dataset = await self._collect_dataset(use_leagues)
            x_all = dataset["X"]
            y_result = dataset["y_result"]
            y_goals_for = dataset["y_goals_for"]
            y_goals_against = dataset["y_goals_against"]

            n_samples = int(x_all.shape[0]) if hasattr(x_all, "shape") else 0
            if n_samples < self.min_samples:
                msg = (
                    f"Not enough samples for ML training: got {n_samples}, "
                    f"need at least {self.min_samples}."
                )
                self._last_error = msg
                return {
                    "ok": False,
                    "reason": msg,
                    "dataset": {
                        "samples": n_samples,
                        "teams_with_samples": dataset["teams_with_samples"],
                        "total_teams_seen": dataset["total_teams_seen"],
                        "training_leagues": use_leagues,
                    },
                }

            trained = self._train_estimators(x_all, y_result, y_goals_for, y_goals_against)
            trained_at = datetime.now(timezone.utc).isoformat()
            model_version = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

            bundle = {
                "feature_names": FEATURE_NAMES,
                "result_model": trained["result_model"],
                "goals_for_model": trained["goals_for_model"],
                "goals_against_model": trained["goals_against_model"],
                "metadata": {
                    "model_version": model_version,
                    "trained_at": trained_at,
                    "sample_count": n_samples,
                    "window_size": self.window_size,
                    "training_leagues": use_leagues,
                    "teams_with_samples": dataset["teams_with_samples"],
                    "total_teams_seen": dataset["total_teams_seen"],
                    "metrics": trained["metrics"],
                },
            }

            self._ensure_parent_dir()
            try:
                import joblib

                joblib.dump(bundle, self.model_path)
            except Exception as e:
                self._last_error = f"Failed saving model: {e}"
                return {"ok": False, "reason": self._last_error}

            self._model_bundle = bundle
            self._last_error = None
            return {
                "ok": True,
                "model_path": str(self.model_path),
                "metadata": bundle["metadata"],
            }

    def _build_features_from_profile(
        self,
        opponent_stats: Dict[str, Any],
        recent_games_tactical: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Optional[float]]:
        features = {
            "possession_percent": _safe_float(_safe_get(opponent_stats, "possession_control", "possession_percent")),
            "pass_accuracy": _safe_float(_safe_get(opponent_stats, "possession_control", "pass_accuracy")),
            "passes_per_minute": _safe_float(_safe_get(opponent_stats, "possession_control", "passes_per_minute")),
            "long_balls_attempted": _safe_float(_safe_get(opponent_stats, "possession_control", "long_balls_attempted")),
            "long_balls_completed": _safe_float(_safe_get(opponent_stats, "possession_control", "long_balls_completed")),
            "total_shots": _safe_float(_safe_get(opponent_stats, "shooting_finishing", "total_shots")),
            "shots_on_target": _safe_float(_safe_get(opponent_stats, "shooting_finishing", "shots_on_target")),
            "shot_conversion_rate": _safe_float(_safe_get(opponent_stats, "shooting_finishing", "shot_conversion_rate")),
            "shots_inside_box": _safe_float(_safe_get(opponent_stats, "shooting_finishing", "shots_inside_box")),
            "shots_outside_box": _safe_float(_safe_get(opponent_stats, "shooting_finishing", "shots_outside_box")),
            "xg": _safe_float(_safe_get(opponent_stats, "expected_metrics", "xG")),
            "xg_per_shot": _safe_float(_safe_get(opponent_stats, "expected_metrics", "xG_per_shot")),
            "key_passes": _safe_float(_safe_get(opponent_stats, "chance_creation", "key_passes")),
            "progressive_passes": _safe_float(_safe_get(opponent_stats, "chance_creation", "progressive_passes")),
            "passes_into_final_third": _safe_float(_safe_get(opponent_stats, "chance_creation", "passes_into_final_third")),
            "passes_into_penalty_area": _safe_float(_safe_get(opponent_stats, "chance_creation", "passes_into_penalty_area")),
            "crosses_attempted": _safe_float(_safe_get(opponent_stats, "chance_creation", "crosses_attempted")),
            "crosses_accurate": _safe_float(_safe_get(opponent_stats, "chance_creation", "crosses_accurate")),
            "cutbacks": _safe_float(_safe_get(opponent_stats, "chance_creation", "cutbacks")),
            "tackles_attempted": _safe_float(_safe_get(opponent_stats, "defensive_actions", "tackles_attempted")),
            "tackles_won": _safe_float(_safe_get(opponent_stats, "defensive_actions", "tackles_won")),
            "interceptions": _safe_float(_safe_get(opponent_stats, "defensive_actions", "interceptions")),
            "blocks": _safe_float(_safe_get(opponent_stats, "defensive_actions", "blocks")),
            "clearances": _safe_float(_safe_get(opponent_stats, "defensive_actions", "clearances")),
            "defensive_duels_won_percent": _safe_float(
                _safe_get(opponent_stats, "defensive_actions", "defensive_duels_won_percent")
            ),
            "ppda": _safe_float(_safe_get(opponent_stats, "pressing_structure", "PPDA")),
            "high_turnovers_won": _safe_float(_safe_get(opponent_stats, "pressing_structure", "high_turnovers_won")),
            "counter_press_recoveries": _safe_float(_safe_get(opponent_stats, "pressing_structure", "counter_press_recoveries")),
            "defensive_line_height": _safe_float(_safe_get(opponent_stats, "team_shape", "defensive_line_height")),
            "corners_taken": _safe_float(_safe_get(opponent_stats, "set_pieces", "attacking", "corners_taken")),
            "corners_conceded": _safe_float(_safe_get(opponent_stats, "set_pieces", "defensive", "corners_conceded")),
            "form_points_per_game": None,
            "form_win_rate": None,
            "form_goals_for_avg": None,
            "form_goals_against_avg": None,
        }

        if recent_games_tactical:
            history = recent_games_tactical[: self.window_size]
            agg = self._aggregate_history_window(history)
            for key in ("form_points_per_game", "form_win_rate", "form_goals_for_avg", "form_goals_against_avg"):
                features[key] = agg.get(key)

            # If any sparse field is missing in aggregate profile, fallback to recent history average
            for key in FEATURE_NAMES:
                if features.get(key) is None and key in agg:
                    features[key] = agg.get(key)

        return features

    def predict(
        self,
        *,
        opponent_stats: Dict[str, Any],
        recent_games_tactical: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "reason": "ML disabled"}
        if not self.is_model_available():
            return {"enabled": False, "reason": "Model not trained"}

        bundle = self._model_bundle or {}
        result_model = bundle.get("result_model")
        goals_for_model = bundle.get("goals_for_model")
        goals_against_model = bundle.get("goals_against_model")
        meta = bundle.get("metadata", {})
        if not result_model or not goals_for_model or not goals_against_model:
            return {"enabled": False, "reason": "Invalid model bundle"}

        features = self._build_features_from_profile(opponent_stats, recent_games_tactical=recent_games_tactical)
        row = np.asarray([[float(features.get(name)) if features.get(name) is not None else np.nan for name in FEATURE_NAMES]])

        try:
            result_pred = result_model.predict(row)[0]
            proba = result_model.predict_proba(row)[0]
            classes = [str(c) for c in result_model.named_steps["model"].classes_]
            prob_map = {classes[i]: float(proba[i]) for i in range(len(classes))}
            goals_for = float(goals_for_model.predict(row)[0])
            goals_against = float(goals_against_model.predict(row)[0])
        except Exception as e:
            return {"enabled": False, "reason": f"ML inference failed: {e}"}

        p_win = prob_map.get("W", 0.0)
        p_draw = prob_map.get("D", 0.0)
        p_loss = prob_map.get("L", 0.0)
        risk_score = max(0.0, min(100.0, (p_win * 100.0) + (goals_for * 15.0) - (goals_against * 7.5)))

        if risk_score >= 62:
            risk_level = "high"
            formation_hint = "4-1-4-1"
            pressing_hint = "MID/LOW BLOCK"
            attack_focus = "transitions_and_set_pieces"
            game_state = "control_risk_first"
        elif risk_score >= 42:
            risk_level = "medium"
            formation_hint = "4-2-3-1"
            pressing_hint = "MID BLOCK + TRIGGERS"
            attack_focus = "balanced_channels"
            game_state = "balanced_plan"
        else:
            risk_level = "low"
            formation_hint = "4-3-3 Attack"
            pressing_hint = "HIGH PRESS"
            attack_focus = "sustained_pressure"
            game_state = "proactive_dominance"

        confidence = max(prob_map.values()) if prob_map else 0.0

        return {
            "enabled": True,
            "model_version": meta.get("model_version"),
            "confidence": round(confidence * 100.0, 1),
            "predictions": {
                "result_probabilities": {k: round(v, 4) for k, v in sorted(prob_map.items())},
                "most_likely_result": str(result_pred),
                "expected_goals_for": round(goals_for, 2),
                "expected_goals_against": round(goals_against, 2),
                "opponent_risk_score": round(risk_score, 1),
                "opponent_risk_level": risk_level,
            },
            "recommendations": {
                "formation_hint": formation_hint,
                "pressing_hint": pressing_hint,
                "attack_focus_hint": attack_focus,
                "game_state_hint": game_state,
            },
        }


_ml_service: Optional[TacticalMLService] = None


def get_tactical_ml_service() -> TacticalMLService:
    global _ml_service
    if _ml_service is None:
        _ml_service = TacticalMLService()
    return _ml_service
