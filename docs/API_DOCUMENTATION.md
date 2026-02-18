# API Documentation

Base URL: `http://localhost:8000/api/v1`

## Data Source
- WhoScored via `soccerdata`.
- A API devolve `data_source` (`whoscored`, `cache`, `manual`, `error`) em vários endpoints.

## Endpoints

### Health
- `GET /health`
- `GET /health/ready`

### Fixtures
- `GET /fixtures/all`
- `GET /fixtures/upcoming?limit=5`

### Opponents
- `GET /opponents`
- `GET /opponents/{team_id}/recent?limit=5`
- `GET /opponents/{team_id}/tactical?limit=5`

### Deep Stats
- `GET /opponent-stats/{opponent_id}?opponent_name=...`

### Tactical Plan
- `GET /tactical-plan/{opponent_id}?opponent_name=...`
- `POST /tactical-plan/{opponent_id}/recalibrate`
  - body: `opponent_name` + `current_season_observations[]`
  - recalibra confiança e sugestões usando observação manual da época atual

### Match Analysis
- `GET /match-analysis/{opponent_id}?opponent_name=...`

## Notas de resposta
- O schema de `recent_games_tactical` mantém compatibilidade com o frontend.
- Campos indisponíveis no feed de origem podem aparecer como `null`.
- As sugestões táticas incluem contexto histórico (`historical_context`) e nota de validação.
