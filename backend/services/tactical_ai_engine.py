"""
Tactical Engine - Match-to-Tactic Recommendation Model
Generates Automated tactical recommendations based on match stats
"""
from typing import Dict, List


class TacticalAIEngine:
    """
    Automated tactical recommendation system
    Analyzes opponent stats and generates actionable tactical advice
    """

    def generate_recommendations(self, opponent_stats: Dict, gil_stats: Dict) -> Dict:
        recommendations = {
            "formation_changes": self._recommend_formation(opponent_stats),
            "pressing_adjustments": self._recommend_pressing(opponent_stats),
            "player_role_changes": self._recommend_player_roles(opponent_stats),
            "target_zones": self._identify_target_zones(opponent_stats),
            "substitution_timing": self._recommend_substitutions(opponent_stats),
            "in_game_switches": self._recommend_in_game_switches(opponent_stats),
            "exploit_weaknesses": self._identify_exploitable_weaknesses(opponent_stats),
            "ai_confidence": self._calculate_confidence(opponent_stats)
        }
        return recommendations

    # ------------------------------------------------------------------
    # FORMATIONS
    # ------------------------------------------------------------------
    def _recommend_formation(self, stats: Dict) -> Dict:
        pressing = stats.get('pressing_structure', {})
        defense = stats.get('defensive_actions', {})
        shape = stats.get('team_shape', {})

        try:
            ppda = float(pressing.get('PPDA', 12) or 12)
        except (TypeError, ValueError):
            ppda = 12.0

        defensive_rating = defense.get('defensive_rating', 'Average')

        recommendations = []

        # PPDA bands (lower = more intense press)
        # <8.5: elite | 8.5-10.5: high | 10.5-13.5: medium | 13.5-16: low | >16: passive
        if ppda < 8.5:
            recommendations.append({
                "formation": "4-4-2 Diamond",
                "reason": "Elite opponent press (PPDA < 8.5) - central overload + quicker/direct exits",
                "priority": "CRITICAL"
            })
        elif ppda < 10.5:
            recommendations.append({
                "formation": "4-4-2 Diamond",
                "reason": "High opponent press (PPDA 8.5-10.5) - bypass press through central overloads",
                "priority": "HIGH"
            })
        elif ppda > 16.0:
            recommendations.append({
                "formation": "4-2-3-1",
                "reason": "Passive opponent press (PPDA > 16) - dominate possession and tempo",
                "priority": "HIGH"
            })
        elif ppda > 13.5:
            recommendations.append({
                "formation": "4-2-3-1",
                "reason": "Low opponent press (PPDA 13.5-16) - patient build + controlled territory",
                "priority": "MEDIUM"
            })

        if defensive_rating == "Vulnerable":
            recommendations.append({
                "formation": "4-3-3 Attack",
                "reason": "Weak defensive structure - constant wide and central pressure",
                "priority": "CRITICAL"
            })

        if defensive_rating == "Solid":
            recommendations.append({
                "formation": "3-4-2-1",
                "reason": "Solid block - overload half-spaces behind midfield",
                "priority": "MEDIUM"
            })

        if shape.get('team_compactness') == 'Narrow':
            recommendations.append({
                "formation": "3-5-2 Wide",
                "reason": "Narrow block detected - stretch with wingbacks",
                "priority": "HIGH"
            })

        if shape.get('width_usage') == 'Central focus':
            recommendations.append({
                "formation": "4-3-3 Wide",
                "reason": "Opponent focuses centrally - attack flanks aggressively",
                "priority": "HIGH"
            })

        return {
            "recommendations": recommendations if recommendations else [
                {"formation": "4-2-3-1", "reason": "Balanced control and flexibility", "priority": "MEDIUM"}
            ],
            "current_formation": "4-2-3-1"
        }
    def _recommend_pressing(self, stats: Dict) -> Dict:
        pressing = stats.get('pressing_structure', {})
        possession = stats.get('possession_control', {})
        shooting = stats.get('shooting_finishing', {})

        try:
            ppda = float(pressing.get('PPDA', 12) or 12)
        except (TypeError, ValueError):
            ppda = 12.0

        try:
            pass_accuracy = float(possession.get('pass_accuracy', 75) or 75)
        except (TypeError, ValueError):
            pass_accuracy = 75.0

        try:
            shots = int(shooting.get('total_shots', 10) or 10)
        except (TypeError, ValueError):
            shots = 10

        recommendations = []

        # Pass accuracy bands (opponent build-up quality proxy)
        # <70: very poor | 70-75: poor | 75-80: ok | 80-85: good | >85: very good
        if pass_accuracy < 70:
            recommendations.append({
                "adjustment": "ULTRA HIGH PRESS",
                "target_line": "55-65m",
                "reason": f"Very low pass accuracy (<70%, got {pass_accuracy}%) - force turnovers aggressively",
                "priority": "CRITICAL"
            })
            recommendations.append({
                "adjustment": "TOUCHLINE TRAP",
                "target_line": "55-65m",
                "reason": "Lock play wide and collapse quickly on the receiver",
                "priority": "HIGH"
            })
        elif pass_accuracy < 75:
            recommendations.append({
                "adjustment": "HIGH PRESS",
                "target_line": "50-60m",
                "reason": f"Low pass accuracy (70-75%, got {pass_accuracy}%) - force errors under pressure",
                "priority": "CRITICAL"
            })
        elif pass_accuracy < 80:
            recommendations.append({
                "adjustment": "TRIGGER PRESS",
                "target_line": "45-55m",
                "reason": f"Average pass accuracy (75-80%, got {pass_accuracy}%) - press on cues (back-pass/poor touch)",
                "priority": "MEDIUM"
            })
        elif pass_accuracy <= 85:
            recommendations.append({
                "adjustment": "MID BLOCK + TRIGGERS",
                "target_line": "40-50m",
                "reason": f"Good pass accuracy (80-85%, got {pass_accuracy}%) - deny central lanes, press on cues",
                "priority": "MEDIUM"
            })
        else:
            recommendations.append({
                "adjustment": "MID/LOW BLOCK",
                "target_line": "35-45m",
                "reason": f"Very good pass accuracy (>85%, got {pass_accuracy}%) - block lanes instead of chasing",
                "priority": "HIGH"
            })

        # Shot volume context
        # <6: very low | 6-9: low | 10-13: good | 14-17: high | >=18: very high
        if shots >= 18:
            recommendations.append({
                "adjustment": "PROTECT BOX",
                "target_line": "35-45m",
                "reason": "Very high shot volume (>=18) - prioritize box protection and second balls",
                "priority": "HIGH"
            })
        elif shots >= 14:
            recommendations.append({
                "adjustment": "DENSIFY CENTRAL ZONE",
                "target_line": "38-48m",
                "reason": "High shot volume (14-17) - reduce shot quality by crowding zone 14",
                "priority": "MEDIUM"
            })

        # Opponent pressing style (PPDA) influences how risky our press should be
        if ppda < 8.5:
            recommendations.append({
                "adjustment": "PRESS CONTROL",
                "target_line": "40-50m",
                "reason": "Opponent is an elite press (PPDA < 8.5) - avoid chaotic pressing duels",
                "priority": "MEDIUM"
            })

        return {
            "pressing_recommendations": recommendations if recommendations else [
                {"adjustment": "STANDARD", "target_line": "45m", "reason": "No clear trigger", "priority": "LOW"}
            ]
        }
    def _recommend_player_roles(self, stats: Dict) -> List[Dict]:
        shape = stats.get('team_shape', {})
        set_pieces = stats.get('set_pieces', {})

        roles = []

        if shape.get('width_usage') == 'Wide flanks exploited':
            roles.append({
                "position": "Fullbacks",
                "role_change": "Inverted Fullbacks",
                "reason": "Protect central zones against wide overloads"
            })

        if shape.get('width_usage') == 'Central focus':
            roles.append({
                "position": "Wingers",
                "role_change": "Stay Wide",
                "reason": "Stretch compact midfield block"
            })

        if shape.get('defensive_line_height', 40) > 48:
            roles.append({
                "position": "Striker",
                "role_change": "False 9",
                "reason": "Exploit space behind high line"
            })

        if shape.get('defensive_line_height', 40) < 38:
            roles.append({
                "position": "Attacking Midfielder",
                "role_change": "Advanced Playmaker",
                "reason": "Unlock deep defensive block"
            })

        if set_pieces.get('defensive', {}).get('set_piece_weakness') == 'High':
            roles.append({
                "position": "Center Backs",
                "role_change": "Join Attacks on Set Pieces",
                "reason": "Exploit aerial weakness"
            })

        return roles

    # ------------------------------------------------------------------
    # TARGET ZONES
    # ------------------------------------------------------------------
    def _identify_target_zones(self, stats: Dict) -> Dict:
        shape = stats.get('team_shape', {})
        transitions = stats.get('transitions', {})

        zones = []

        if shape.get('team_compactness') == 'Narrow':
            zones.append({
                "zone": "Half-Spaces",
                "attack_method": "Interior runs",
                "priority": "CRITICAL",
                "expected_outcome": "High xG chances"
            })

        if shape.get('width_usage') == 'Central focus':
            zones.append({
                "zone": "Wide Flanks",
                "attack_method": "Overlaps and switches",
                "priority": "HIGH",
                "expected_outcome": "Crosses and cutbacks"
            })

        if transitions.get('defensive_transition', {}).get('recovery_time_after_loss') == 'Slow (>5s)':
            zones.append({
                "zone": "Counter-Attack Channels",
                "attack_method": "Vertical passes",
                "priority": "CRITICAL",
                "expected_outcome": "Numerical superiority"
            })

        return {
            "priority_zones": zones,
            "zone_heatmap_recommendation": " → ".join(z['zone'] for z in zones[:2])
        }

    # ------------------------------------------------------------------
    # SUBSTITUTIONS
    # ------------------------------------------------------------------
    def _recommend_substitutions(self, stats: Dict) -> Dict:
        context = stats.get('context', {})
        pressing = stats.get('pressing_structure', {})

        subs = []

        if context.get('fatigue_indicators') == 'High':
            subs.append({
                "timing": "60-65",
                "type": "Fast attackers",
                "reason": "Exploit tired defense"
            })

        if pressing.get('pressing_intensity') == 'High':
            subs.append({
                "timing": "70-75",
                "type": "Midfield controller",
                "reason": "Stabilize under pressure"
            })

        return {
            "substitution_recommendations": subs if subs else [
                {"timing": "70", "type": "Balanced", "reason": "No clear trigger"}
            ]
        }

    # ------------------------------------------------------------------
    # IN-GAME SWITCHES
    # ------------------------------------------------------------------
    def _recommend_in_game_switches(self, stats: Dict) -> List[Dict]:
        pressing = stats.get('pressing_structure', {})
        possession = stats.get('possession_control', {})

        try:
            ppda = float(pressing.get('PPDA', 12) or 12)
        except (TypeError, ValueError):
            ppda = 12.0

        try:
            poss = float(possession.get('possession_percent', 50) or 50)
        except (TypeError, ValueError):
            poss = 50.0

        switches = []

        # Possession bands
        # <40: very low | 40-45: low | 45-55: balanced | 55-60: high | >=60: very high
        if poss < 40:
            switches.append({
                "trigger": "Very low possession (<40%)",
                "switch": "Add extra midfielder",
                "timing": "Immediate",
                "reason": "Regain control and win second balls"
            })
        elif poss < 45:
            switches.append({
                "trigger": "Low possession (40-45%)",
                "switch": "Reduce risk in build-up",
                "timing": "10-15 minutes",
                "reason": "Stabilize possession before increasing tempo"
            })

        # Opponent press intensity (PPDA)
        if ppda < 8.5:
            switches.append({
                "trigger": "Elite opponent press (PPDA < 8.5)",
                "switch": "Direct play",
                "timing": "On press trigger",
                "reason": "Bypass pressure and avoid risky build-up"
            })
        elif ppda < 10.5:
            switches.append({
                "trigger": "High opponent press (PPDA 8.5-10.5)",
                "switch": "Wider outlets",
                "timing": "On press trigger",
                "reason": "Create safer escape routes"
            })

        return switches or [{
            "trigger": "None",
            "switch": "Maintain structure",
            "timing": "Monitor",
            "reason": "No tactical emergency"
        }]
    def _identify_exploitable_weaknesses(self, stats: Dict) -> List[Dict]:
        pressing = stats.get('pressing_structure', {})
        defense = stats.get('defensive_actions', {})
        set_pieces = stats.get('set_pieces', {})
        transitions = stats.get('transitions', {})

        try:
            ppda = float(pressing.get('PPDA', 12) or 12)
        except (TypeError, ValueError):
            ppda = 12.0

        try:
            tackle_success = float(defense.get('tackle_success_rate', 70) or 70)
        except (TypeError, ValueError):
            tackle_success = 70.0

        weaknesses = []

        # Pressing weakness (opponent passive / low press)
        if ppda > 16.0:
            weaknesses.append({
                "weakness": "Passive Press (PPDA > 16)",
                "severity": "CRITICAL",
                "exploitation": "Build patiently",
                "expected_impact": "Territorial dominance"
            })
        elif ppda > 13.5:
            weaknesses.append({
                "weakness": "Low Press (PPDA 13.5-16)",
                "severity": "HIGH",
                "exploitation": "Switch play quickly",
                "expected_impact": "Final-third entries"
            })

        if transitions.get('defensive_transition', {}).get('rest_defense_quality') == 'Poor':
            weaknesses.append({
                "weakness": "Poor Rest Defense",
                "severity": "HIGH",
                "exploitation": "Immediate counters",
                "expected_impact": "Clear chances"
            })

        if set_pieces.get('defensive', {}).get('set_piece_weakness') == 'High':
            weaknesses.append({
                "weakness": "Set Pieces",
                "severity": "CRITICAL",
                "exploitation": "Target aerial duels",
                "expected_impact": "Set-piece goals"
            })

        # Tackling quality bands
        if tackle_success < 55:
            weaknesses.append({
                "weakness": "Very Poor Tackling (<55%)",
                "severity": "HIGH",
                "exploitation": "Dribble and provoke fouls",
                "expected_impact": "Dangerous free kicks"
            })
        elif tackle_success < 60:
            weaknesses.append({
                "weakness": "Poor Tackling (55-60%)",
                "severity": "MEDIUM",
                "exploitation": "Dribble and provoke fouls",
                "expected_impact": "Dangerous free kicks"
            })

        return weaknesses
    def _calculate_confidence(self, stats: Dict) -> Dict:
        pressing = stats.get('pressing_structure', {})
        defense = stats.get('defensive_actions', {})
        possession = stats.get('possession_control', {})
        matches_analyzed = stats.get("matches_analyzed")
        try:
            matches_analyzed = int(matches_analyzed) if matches_analyzed is not None else 1
        except Exception:
            matches_analyzed = 1

        try:
            ppda = float(pressing.get('PPDA', 12) or 12)
        except (TypeError, ValueError):
            ppda = 12.0

        try:
            pass_accuracy = float(possession.get('pass_accuracy', 75) or 75)
        except (TypeError, ValueError):
            pass_accuracy = 75.0

        score = 70

        # Stronger signals when opponent profile is extreme
        if ppda < 8.5 or ppda > 16.0:
            score += 10
        elif ppda < 10.5 or ppda > 13.5:
            score += 5

        if pass_accuracy < 70 or pass_accuracy > 85:
            score += 5

        if defense.get('defensive_rating') in ['Vulnerable', 'Solid']:
            score += 10

        # More data -> more stable recommendations
        if matches_analyzed >= 8:
            score += 10
        elif matches_analyzed >= 5:
            score += 6
        elif matches_analyzed >= 3:
            score += 3

        is_estimated = bool(stats.get("estimated", False))
        if is_estimated:
            score -= 10

        return {
            "overall_confidence": min(95, score),
            "recommendation_reliability": "HIGH" if score >= 85 else "MEDIUM",
            "data_quality": (
                f"{'Estimated' if is_estimated else 'Observed'} - based on {matches_analyzed} match(es)"
            ),
        }


_tactical_ai_engine = None

def get_tactical_ai_engine():
    global _tactical_ai_engine
    if _tactical_ai_engine is None:
        _tactical_ai_engine = TacticalAIEngine()
    return _tactical_ai_engine
