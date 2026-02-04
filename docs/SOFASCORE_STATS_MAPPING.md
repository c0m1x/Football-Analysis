# SofaScore stats mapping (project integration)

This project’s frontend consumes aggregated tactical statistics from `GET /api/v1/opponent-stats/{opponent_id}`.
Historically those values were **estimated** (heuristics) because the upstream match feed lacked detailed stats.

The backend now supports **SofaScore** as a higher-fidelity source for the same fields.

## Current stats used by the project (and how they map)

These are the fields used by the UI (`frontend/src/components/AdvancedStatsPanel.jsx`) via:
- `statistics.tactical_foundation.*` (aggregates)
- `statistics.recent_games_tactical[*].*` (per-match)

### Possession & control
Project field (per match) -> SofaScore statistic label (typical)
- `possession_control.possession_percent` -> `Ball possession`
- `possession_control.pass_accuracy` -> `Pass accuracy` (or derived from `Accurate passes`)
- `possession_control.passes_per_minute` -> derived from `Total passes / 90`
- `possession_control.long_balls_attempted` -> `Long balls` (if present)
- `possession_control.long_balls_completed` -> `Accurate long balls` (if present)

### Shooting & finishing
- `shooting_finishing.total_shots` -> `Total shots`
- `shooting_finishing.shots_on_target` -> `Shots on target`
- `shooting_finishing.shots_inside_box` -> `Shots inside box` (if present)
- `shooting_finishing.shots_outside_box` -> `Shots outside box` (if present)
- `shooting_finishing.big_chances_created` -> `Big chances` (if present)
- `shooting_finishing.big_chances_missed` -> `Big chances missed` (if present)
- `shooting_finishing.shot_conversion_rate` -> derived: `goals / total_shots * 100`

### Expected metrics
- `expected_metrics.xG` -> `Expected goals (xG)` / `xG`
- `expected_metrics.xG_per_shot` -> derived: `xG / total_shots`

Not consistently available from SofaScore’s standard match statistics endpoint (kept as `null`):
- `expected_metrics.xA`
- `expected_metrics.xG_from_open_play`
- `expected_metrics.xG_from_set_pieces`

### Chance creation
Commonly available:
- `chance_creation.key_passes` -> `Key passes`
- `chance_creation.crosses_attempted` -> `Crosses`
- `chance_creation.crosses_accurate` -> `Accurate crosses`

Often not available in the basic endpoint (kept as `null`):
- `chance_creation.progressive_passes`
- `chance_creation.passes_into_final_third`
- `chance_creation.passes_into_penalty_area`
- `chance_creation.cutbacks`

### Defensive actions
- `defensive_actions.tackles_attempted` -> `Tackles`
- `defensive_actions.interceptions` -> `Interceptions`
- `defensive_actions.clearances` -> `Clearances`
- `defensive_actions.blocks` -> `Blocked shots`

Not consistently available in the basic endpoint (kept as `null`):
- `defensive_actions.tackles_won`
- `defensive_actions.defensive_duels_won_percent`

### Set pieces
- `set_pieces.attacking.corners_taken` -> `Corner kicks`
- `set_pieces.defensive.corners_conceded` -> derived from opponent’s `Corner kicks`

## Additional SofaScore stats worth integrating later (future)

These are often present in SofaScore match stats and can unlock better tactical features beyond the current UI:
- Discipline: fouls, yellow/red cards
- Offside counts
- Goalkeeper: saves
- Passing depth: long pass accuracy, through balls (varies)
- Duels: aerial/ground duels won (varies)

For event-level/timeline features (pressing triggers, counter-press recoveries, PPDA, zones, heatmaps), you’ll generally need richer event feeds than the basic match statistics endpoint.

## Implementation notes

- The normalization is implemented in `backend/services/sofascore_service.py`.
- Aggregation into `tactical_foundation`, `set_piece_analytics`, `contextual_psychological` happens in `backend/api/routes/opponent_stats.py`.
- The backend prefers SofaScore tactical stats when available, otherwise falls back to heuristic estimation.
- If team search is blocked (403), set `SOFASCORE_TEAM_ID_MAP_JSON` in `.env` to map team names to SofaScore team IDs.
