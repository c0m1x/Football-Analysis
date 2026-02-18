"""Tactical recommendation service with historical confidence adjustment.

This service combines:
- Historical baseline metrics (previous season data)
- Optional manually observed current-season samples
- Optional Anthropic narrative generation
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from config.settings import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()

DEFAULT_BASELINE_SEASON = "2023/24"
DEFAULT_VALIDATION_NOTE = (
    "Baseado em dados da época 2023/24 — validar com observação recente do adversário."
)


def _safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def _to_float(value: Any) -> Optional[float]:
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
    return sum(nums) / len(nums)


def _mode(values: List[str]) -> Optional[str]:
    cleaned = [str(v).strip() for v in values if isinstance(v, str) and str(v).strip()]
    if not cleaned:
        return None
    counts: Dict[str, int] = {}
    for v in cleaned:
        counts[v] = counts.get(v, 0) + 1
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0][0]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class TacticalRecommendationService:
    """Builds customized tactical suggestions and confidence calibration."""

    def __init__(self) -> None:
        self.baseline_season = str(
            getattr(settings, "HISTORICAL_BASELINE_SEASON", DEFAULT_BASELINE_SEASON)
            or DEFAULT_BASELINE_SEASON
        )
        configured_note = str(
            getattr(settings, "HISTORICAL_VALIDATION_NOTE", DEFAULT_VALIDATION_NOTE)
            or DEFAULT_VALIDATION_NOTE
        )
        self.validation_note = configured_note.replace("2023/24", self.baseline_season)

    def _extract_historical_profile(
        self,
        opponent_advanced_stats: Dict[str, Any],
        opponent_form: Dict[str, Any],
    ) -> Dict[str, Any]:
        form = opponent_form.get("form_summary", {}) if isinstance(opponent_form, dict) else {}
        profile = {
            "possession_percent": _to_float(
                _safe_get(opponent_advanced_stats, "possession_control", "possession_percent")
            ),
            "shots_per_game": _to_float(
                _safe_get(opponent_advanced_stats, "shooting_finishing", "total_shots")
            ),
            "goals_scored_per_game": _to_float(form.get("avg_goals_scored")),
            "goals_conceded_per_game": _to_float(form.get("avg_goals_conceded")),
            "ppda": _to_float(_safe_get(opponent_advanced_stats, "pressing_structure", "PPDA")),
            "defensive_line_height": _to_float(
                _safe_get(opponent_advanced_stats, "team_shape", "defensive_line_height")
            ),
            "width_usage": _safe_get(opponent_advanced_stats, "team_shape", "width_usage"),
            "set_piece_weakness": _safe_get(
                opponent_advanced_stats, "set_pieces", "defensive", "set_piece_weakness"
            ),
            "matches_analyzed": int(opponent_advanced_stats.get("matches_analyzed", 5) or 5),
            "estimated": bool(opponent_advanced_stats.get("estimated", True)),
        }
        return profile

    def _aggregate_current_observations(self, observations: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not observations:
            return {}

        possessions = [_to_float(o.get("possession_percent")) for o in observations]
        shots = [_to_float(o.get("shots_for")) for o in observations]
        goals_scored = [_to_float(o.get("goals_scored")) for o in observations]
        goals_conceded = [_to_float(o.get("goals_conceded")) for o in observations]
        transition_ratings = [_to_float(o.get("offensive_transitions_rating")) for o in observations]
        defensive_line = [_to_float(o.get("defensive_line_height")) for o in observations]
        press_levels = [str(o.get("pressing_level") or "").strip().lower() for o in observations]
        build_patterns = [str(o.get("build_up_pattern") or "").strip() for o in observations]
        set_piece_flags = [str(o.get("set_piece_vulnerability") or "").strip() for o in observations]

        key_players: List[str] = []
        for o in observations:
            players = o.get("key_players")
            if isinstance(players, list):
                key_players.extend([str(p).strip() for p in players if str(p).strip()])
            elif isinstance(players, str) and players.strip():
                key_players.append(players.strip())

        return {
            "sample_size": len(observations),
            "possession_percent": _mean(possessions),
            "shots_per_game": _mean(shots),
            "goals_scored_per_game": _mean(goals_scored),
            "goals_conceded_per_game": _mean(goals_conceded),
            "offensive_transitions_rating": _mean(transition_ratings),
            "defensive_line_height": _mean(defensive_line),
            "pressing_level": _mode([p for p in press_levels if p]),
            "build_up_pattern": _mode([b for b in build_patterns if b]),
            "set_piece_vulnerability": _mode([s for s in set_piece_flags if s]),
            "key_players": sorted(set(key_players)),
        }

    def _blend_profiles(self, historical: Dict[str, Any], observed: Dict[str, Any]) -> Dict[str, Any]:
        if not observed:
            return dict(historical)

        sample_size = int(observed.get("sample_size", 0) or 0)
        observed_weight = _clamp(0.18 * sample_size, 0.0, 0.54)
        historical_weight = 1.0 - observed_weight

        def blended_num(field: str) -> Optional[float]:
            h = _to_float(historical.get(field))
            o = _to_float(observed.get(field))
            if h is None:
                return o
            if o is None:
                return h
            return (h * historical_weight) + (o * observed_weight)

        blended = {
            "possession_percent": blended_num("possession_percent"),
            "shots_per_game": blended_num("shots_per_game"),
            "goals_scored_per_game": blended_num("goals_scored_per_game"),
            "goals_conceded_per_game": blended_num("goals_conceded_per_game"),
            "ppda": blended_num("ppda"),
            "defensive_line_height": blended_num("defensive_line_height"),
            "offensive_transitions_rating": blended_num("offensive_transitions_rating"),
            "width_usage": observed.get("build_up_pattern") or historical.get("width_usage"),
            "set_piece_weakness": observed.get("set_piece_vulnerability")
            or historical.get("set_piece_weakness"),
            "matches_analyzed": int(historical.get("matches_analyzed", 5) or 5),
            "historical_weight": round(historical_weight, 2),
            "observed_weight": round(observed_weight, 2),
        }
        return blended

    def _confidence_adjustment(
        self,
        base_ai_confidence: Dict[str, Any],
        historical: Dict[str, Any],
        observed: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            base_score = float(base_ai_confidence.get("overall_confidence", 70) or 70)
        except Exception:
            base_score = 70.0

        sample_size = int(observed.get("sample_size", 0) or 0)
        completeness_signals = [
            observed.get("possession_percent"),
            observed.get("shots_per_game"),
            observed.get("goals_scored_per_game"),
            observed.get("goals_conceded_per_game"),
            observed.get("pressing_level"),
            observed.get("build_up_pattern"),
        ]
        completeness = sum(1 for s in completeness_signals if s is not None and s != "") / max(
            len(completeness_signals), 1
        )

        # Historical-only recommendations are penalized due season drift.
        seasonal_drift_penalty = 14.0
        manual_boost = sample_size * 3.5
        quality_boost = completeness * 8.0

        divergence_penalty = 0.0
        if observed:
            for field, threshold, penalty in (
                ("possession_percent", 10.0, 4.0),
                ("shots_per_game", 4.0, 3.0),
                ("goals_conceded_per_game", 0.8, 3.0),
            ):
                hv = _to_float(historical.get(field))
                ov = _to_float(observed.get(field))
                if hv is None or ov is None:
                    continue
                if abs(hv - ov) >= threshold:
                    divergence_penalty += penalty

        adjusted = base_score - seasonal_drift_penalty + manual_boost + quality_boost - divergence_penalty
        adjusted = _clamp(adjusted, 30.0, 92.0)

        if adjusted >= 80:
            reliability = "ALTA"
        elif adjusted >= 60:
            reliability = "MÉDIA"
        else:
            reliability = "BAIXA"

        return {
            "baseline_ai_confidence": round(base_score, 1),
            "adjusted_confidence": round(adjusted, 1),
            "recommendation_reliability": reliability,
            "seasonal_drift_penalty": seasonal_drift_penalty,
            "manual_observation_boost": round(manual_boost + quality_boost, 1),
            "divergence_penalty": round(divergence_penalty, 1),
            "observation_sample_size": sample_size,
            "basis": f"Histórico {self.baseline_season} + observações atuais",
        }

    def _rule_based_suggestions(self, profile: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        poss = _to_float(profile.get("possession_percent"))
        ppda = _to_float(profile.get("ppda"))
        shots = _to_float(profile.get("shots_per_game"))
        conceded = _to_float(profile.get("goals_conceded_per_game"))
        line_height = _to_float(profile.get("defensive_line_height"))
        width = str(profile.get("width_usage") or "").lower()
        set_piece_weakness = str(profile.get("set_piece_weakness") or "").lower()
        transitions_rating = _to_float(profile.get("offensive_transitions_rating"))

        system = []
        if ppda is not None and ppda < 10.5:
            system.append(
                {
                    "title": "4-2-3-1 com saída vertical",
                    "detail": "Duplo pivô para controlar a 2.ª bola e ultrapassar pressão alta.",
                    "note": self.validation_note,
                }
            )
        elif poss is not None and poss > 54:
            system.append(
                {
                    "title": "4-1-4-1 em bloco médio",
                    "detail": "Fechar corredor central e forçar circulação exterior do adversário.",
                    "note": self.validation_note,
                }
            )
        else:
            system.append(
                {
                    "title": "4-3-3 equilibrado",
                    "detail": "Pressão orientada e ocupação de meio-campo para controlar transições.",
                    "note": self.validation_note,
                }
            )

        zones = []
        if "central" in width:
            zones.append(
                {
                    "title": "Explorar corredores laterais",
                    "detail": "Criar 2x1 com lateral + extremo e atacar zona de cruzamento atrasado.",
                    "note": self.validation_note,
                }
            )
        if line_height is not None and line_height >= 47:
            zones.append(
                {
                    "title": "Atacar profundidade nas costas",
                    "detail": "Movimentos de rutura do avançado entre central e lateral.",
                    "note": self.validation_note,
                }
            )
        if ppda is not None and ppda < 10:
            zones.append(
                {
                    "title": "Meio-espaços após 1.º passe",
                    "detail": "Receção entre linhas após atrair pressão no primeiro passe.",
                    "note": self.validation_note,
                }
            )
        if not zones:
            zones.append(
                {
                    "title": "Ataque entre lateral e central",
                    "detail": "Priorizar entradas na área por combinação curta no corredor forte.",
                    "note": self.validation_note,
                }
            )

        vulnerabilities = []
        if conceded is not None and conceded >= 1.4:
            vulnerabilities.append(
                {
                    "title": "Fragilidade na proteção da área",
                    "detail": "Acelerar último passe após recuperação em zona intermédia.",
                    "note": self.validation_note,
                }
            )
        if shots is not None and shots >= 13:
            vulnerabilities.append(
                {
                    "title": "Espaço para remate na zona 14",
                    "detail": "Criar remates frontais com apoio do médio ofensivo.",
                    "note": self.validation_note,
                }
            )
        if "high" in set_piece_weakness or "alta" in set_piece_weakness:
            vulnerabilities.append(
                {
                    "title": "Defesa de bola parada vulnerável",
                    "detail": "Atacar primeiro poste com bloqueio no melhor cabeceador adversário.",
                    "note": self.validation_note,
                }
            )
        if not vulnerabilities:
            vulnerabilities.append(
                {
                    "title": "Vulnerabilidade moderada em transição defensiva",
                    "detail": "Aumentar ritmo após perda ofensiva do adversário.",
                    "note": self.validation_note,
                }
            )

        neutralize = []
        if poss is not None and poss >= 55:
            neutralize.append(
                {
                    "title": "Neutralizar posse alta",
                    "detail": "Compactar 4-1-4-1 e bloquear linha de passe interior para o pivot.",
                    "note": self.validation_note,
                }
            )
        if shots is not None and shots >= 12:
            neutralize.append(
                {
                    "title": "Reduzir volume de remate",
                    "detail": "Proteger zona frontal da área e orientar ataque para zonas exteriores.",
                    "note": self.validation_note,
                }
            )
        if transitions_rating is not None and transitions_rating >= 7:
            neutralize.append(
                {
                    "title": "Controlo de transições rápidas",
                    "detail": "Manter rest-defense 3+2 na fase ofensiva.",
                    "note": self.validation_note,
                }
            )
        if not neutralize:
            neutralize.append(
                {
                    "title": "Neutralização geral",
                    "detail": "Evitar perdas centrais e controlar ritmo com circulação curta.",
                    "note": self.validation_note,
                }
            )

        set_piece = []
        if "high" in set_piece_weakness or "alta" in set_piece_weakness:
            set_piece.append(
                {
                    "title": "Cantos ofensivos ao 1.º poste",
                    "detail": "Bloqueio frontal + ataque agressivo ao primeiro contacto.",
                    "note": self.validation_note,
                }
            )
        else:
            set_piece.append(
                {
                    "title": "Variar curto/longo nas bolas paradas",
                    "detail": "Alternar canto curto para arrastar marcação e cruzamento no 2.º momento.",
                    "note": self.validation_note,
                }
            )
        set_piece.append(
            {
                "title": "Defesa de livres laterais",
                "detail": "Linha mista com proteção da zona de finalização entre penalty spot e 2.º poste.",
                "note": self.validation_note,
            }
        )

        return {
            "recommended_system": system,
            "attack_zones": zones,
            "defensive_vulnerabilities": vulnerabilities,
            "neutralize_strengths": neutralize,
            "set_piece_adjustments": set_piece,
        }

    async def _anthropic_enrichment(
        self,
        opponent_name: str,
        profile: Dict[str, Any],
        suggestions: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        api_key = str(getattr(settings, "ANTHROPIC_API_KEY", "") or "").strip()
        model = str(getattr(settings, "ANTHROPIC_MODEL", "claude-3-5-sonnet-latest") or "").strip()
        if not api_key:
            return {
                "provider": "rule_engine",
                "enabled": False,
                "narrative": None,
            }

        prompt = (
            "Gera uma narrativa curta em português de Portugal para o treinador.\n"
            "Devolve JSON puro com o formato:"
            '{"summary": "...", "alerts": ["...","..."], "training_focus": ["...","..."]}.\n'
            f"Adversário: {opponent_name}\n"
            f"Perfil combinado: {json.dumps(profile, ensure_ascii=False)}\n"
            f"Sugestões estruturadas: {json.dumps(suggestions, ensure_ascii=False)}\n"
            "Máximo 120 palavras no total."
        )

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": 500,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            timeout = float(getattr(settings, "ANTHROPIC_TIMEOUT_SECONDS", 12) or 12)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                resp.raise_for_status()
                body = resp.json()

            content = body.get("content", [])
            text = ""
            if isinstance(content, list) and content:
                text = str(content[0].get("text", "") or "")

            parsed = None
            if text:
                cleaned = text.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.strip("`")
                    cleaned = cleaned.replace("json", "", 1).strip()
                try:
                    parsed = json.loads(cleaned)
                except Exception:
                    parsed = {"summary": cleaned, "alerts": [], "training_focus": []}

            return {
                "provider": "anthropic",
                "enabled": True,
                "narrative": parsed,
            }
        except Exception as exc:
            logger.warning("Anthropic enrichment failed, using fallback narrative: %s", exc)
            return {
                "provider": "rule_engine",
                "enabled": False,
                "narrative": None,
                "error": str(exc),
            }

    async def build_customized_recommendations(
        self,
        *,
        opponent_name: str,
        opponent_advanced_stats: Dict[str, Any],
        opponent_form: Dict[str, Any],
        ai_confidence: Dict[str, Any],
        current_season_observations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        observations = list(current_season_observations or [])
        historical = self._extract_historical_profile(opponent_advanced_stats, opponent_form)
        observed = self._aggregate_current_observations(observations)
        blended = self._blend_profiles(historical, observed)
        confidence = self._confidence_adjustment(ai_confidence, historical, observed)
        suggestions = self._rule_based_suggestions(blended)
        enrichment = await self._anthropic_enrichment(opponent_name, blended, suggestions)

        return {
            "baseline_season": self.baseline_season,
            "validation_note": self.validation_note,
            "season_comparison": {
                "historical_profile": historical,
                "current_observed_profile": observed or None,
                "blended_profile": blended,
            },
            "confidence_adjustment": confidence,
            "customized_suggestions": suggestions,
            "language_generation": enrichment,
        }


_tactical_recommendation_service: Optional[TacticalRecommendationService] = None


def get_tactical_recommendation_service() -> TacticalRecommendationService:
    global _tactical_recommendation_service
    if _tactical_recommendation_service is None:
        _tactical_recommendation_service = TacticalRecommendationService()
    return _tactical_recommendation_service
