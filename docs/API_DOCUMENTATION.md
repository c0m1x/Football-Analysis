# API Documentation

Base URL: `http://localhost:8000/api/v1`

## Data Source
- WhoScored via `soccerdata` (Python).
- A API devolve `data_source` (`whoscored`, `cache`, `manual`, `error`) em vários endpoints.

## Endpoints

### Health
- `GET /health`
- `GET /health/ready`

### Discovery
- `GET /leagues`
- `GET /teams?league=ENG-Premier League`

### Fixtures
- `GET /fixtures/all?league=...&team_id=...`
- `GET /fixtures/upcoming?league=...&team_id=...&limit=1`
- `GET /next-opponent?league=...&team_id=...`

### Deep Stats
- `GET /opponent-stats/{opponent_id}?opponent_name=...&team_id=...&team_name=...&league=...`

### Tactical Plan
- `GET /tactical-plan/{opponent_id}?opponent_name=...&team_id=...&team_name=...&league=...`
- `POST /tactical-plan/{opponent_id}/recalibrate?team_id=...&team_name=...&league=...`
  - body: `opponent_name` + `current_season_observations[]`

### Match Analysis
- `GET /match-analysis/{opponent_id}?opponent_name=...&team_id=...&team_name=...&league=...`

### ML Model
- `GET /ml/status`
- `POST /ml/train`
  - body opcional: `leagues[]`, `force`

## Notas
- As sugestões táticas usam histórico do adversário (últimos 10 jogos por defeito).
- A referência portuguesa para treino pode ser mantida via `PORTUGUESE_TRAINING_LEAGUE`.
- Campos indisponíveis no feed de origem podem aparecer como `null`.
- O motor tático usa modelo ML quando disponível; sem modelo treinado, cai para regras heurísticas.
