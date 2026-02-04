# API Documentation

##  Disclaimer / Aviso

**PT:** Este é um projeto **não oficial**, criado por um adepto. O **Gil Vicente FC** **não** solicitou, não aprovou/endossou, não está afiliado e **não** remunerou este trabalho.

**EN:** This is an **unofficial fan-made** project. **Gil Vicente FC** did **not** request or endorse it, is **not** affiliated with it, and **no** remuneration was provided.

## Gil Vicente Tactical Intelligence Platform - API Reference

Base URL: `http://localhost:8000/api/v1`

---

## Data Source (SofaScore)

- All fixtures/opponents/stats are sourced via **SofaScore scraping** (unofficial endpoints).
- If you see `503 Service Unavailable` with a message like "SofaScore denied this request (HTTP 403)", this deployment environment is likely blocked by SofaScore.

**Scraper env vars** (see `.env`):
- `SOFASCORE_BASE_URL` / `SOFASCORE_BASE_URLS`
- `SOFASCORE_TIMEOUT_SECONDS` / `SOFASCORE_USER_AGENT`

**Diagnose inside Docker**:
```bash
docker compose exec backend python scripts/sofascore_diagnose.py
```

**Optional live test** (fails if blocked):
```bash
docker compose exec -e RUN_LIVE_SOFASCORE_TESTS=1 backend python -m unittest -v tests/test_sofascore_live.py
```

---

## Authentication

Currently, the API does not require authentication for development purposes. Production deployment should implement API key authentication.

---

## Endpoints

### Health Check

#### GET /health
Check API health status

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-21T10:30:00Z",
  "service": "Gil Vicente Tactical Intelligence Platform"
}
```

#### GET /health/ready
Check service readiness (database, cache connections)

**Response:**
```json
{
  "status": "ready",
  "database": "connected",
  "cache": "connected"
}
```

---

### Fixtures

#### GET /fixtures/upcoming
Get Gil Vicente's upcoming fixtures

**Query Parameters:**
- `limit` (optional, default: 5): Number of fixtures to return

**Response:**
```json
{
  "team": "Gil Vicente",
  "fixtures": [
    {
      "fixture_id": 12345,
      "date": "2024-12-28T20:00:00Z",
      "home_team": "Gil Vicente",
      "away_team": "Opponent Team",
      "venue": "Estádio Cidade de Barcelos"
    }
  ],
  "count": 5
}
```

#### GET /fixtures/{fixture_id}
Get detailed fixture information

**Path Parameters:**
- `fixture_id`: Fixture ID

**Response:**
```json
{
  "fixture": {
    "id": 12345,
    "date": "2024-12-28T20:00:00Z",
    "home_team": {...},
    "away_team": {...}
  },
  "statistics": [...]
}
```

---

### Opponents

#### GET /opponents/{team_id}/matches
Get opponent's recent match history

**Path Parameters:**
- `team_id`: Opponent team ID

**Query Parameters:**
- `limit` (optional, default: 10): Number of matches to return

**Response:**
```json
{
  "team_id": 123,
  "matches": [
    {
      "fixture_id": 12345,
      "date": "2024-12-20T18:00:00Z",
      "result": "W",
      "home_team": "...",
      "away_team": "...",
      "score": "2-1",
      "formation": "4-3-3"
    }
  ],
  "count": 10
}
```

#### GET /opponents/{team_id}/statistics
Get opponent's season statistics

**Path Parameters:**
- `team_id`: Opponent team ID

**Response:**
```json
{
  "team_id": 123,
  "statistics": {
    "matches_played": 15,
    "wins": 8,
    "draws": 4,
    "losses": 3,
    "goals_scored": 24,
    "goals_conceded": 15,
    "formations": {...}
  }
}
```

#### GET /opponents/{team_id}/head-to-head
Get head-to-head history

**Path Parameters:**
- `team_id`: Opponent team ID

**Query Parameters:**
- `last` (optional, default: 5): Number of H2H matches

**Response:**
```json
{
  "gil_vicente_id": 228,
  "opponent_id": 123,
  "matches": [...],
  "count": 5
}
```

---

### Opponent Deep Stats (Scouting)

#### GET /opponent-stats/{opponent_id}
Returns deep tactical aggregates used by the frontend's Advanced Stats Panel.

**Path Parameters:**
- `opponent_id`: Opponent team ID (from the existing fixtures feed)

**Query Parameters:**
- `opponent_name` (required): Opponent team name

**Data sources:**
- Tactical stats prefer SofaScore when enabled and available.
- Falls back to heuristic estimation when SofaScore is unavailable.
- If team search is blocked (403), set `SOFASCORE_TEAM_ID_MAP_JSON` in `.env` to map names to SofaScore team IDs.

**Response (shape):**
```json
{
  "opponent": "Team Name",
  "opponent_id": "123",
  "tactical_foundation": {
    "estimated": false,
    "matches_analyzed": 5
  },
  "recent_games_tactical": [
    {
      "estimated": false,
      "possession_control": {
        "possession_percent": 55.0
      }
    }
  ]
}
```

---

### Tactical Analysis

#### POST /tactical/analyze
Analyze opponent tactical patterns

**Request Body:**
```json
[
  {
    "formation": "4-3-3",
    "statistics": {
      "possession": 58.5,
      "shots": 15,
      "passes": 450
    },
    "goals_scored": 2,
    "goals_conceded": 1,
    "result": "W",
    "is_home": true
  }
]
```

**Response:**
```json
{
  "analysis": {
    "formations": {
      "primary_formation": "4-3-3",
      "formation_distribution": {
        "4-3-3": 70.0,
        "4-4-2": 30.0
      },
      "formation_flexibility": 2
    },
    "playing_style": {
      "avg_possession": 56.2,
      "possession_style": "possession-based",
      "attacking_intensity": "high"
    },
    "strengths": ["possession_control", "clinical_finishing"],
    "weaknesses": ["defensive_vulnerability"],
    "performance": {
      "wins": 7,
      "draws": 2,
      "losses": 1,
      "win_rate": 70.0,
      "form": "excellent"
    },
    "confidence_score": 0.9
  },
  "matches_analyzed": 10
}
```

#### POST /tactical/recommendations
Generate tactical recommendations

**Request Body:**
```json
{
  "opponent_analysis": {
    // Result from /tactical/analyze
  },
  "gil_vicente_formation": "4-3-3"
}
```

**Response:**
```json
{
  "recommendations": {
    "recommended_formation": "4-3-3",
    "pressing_strategy": {
      "intensity": "high",
      "description": "Opponent likes possession - press high to disrupt build-up"
    },
    "key_zones_to_exploit": ["wide_areas", "central_penetration"],
    "defensive_focus": {
      "priority": "limit_chances",
      "description": "Opponent is clinical - minimize clear goal-scoring opportunities"
    },
    "risk_factors": [
      "High conversion rate - must limit shots",
      "Opponent in good form - expect strong performance"
    ],
    "tactical_adjustments": [
      "Stay compact when defending - don't chase the ball",
      "Be ready for quick transitions - counter-attack opportunities"
    ]
  },
  "opponent_formation": "4-3-3"
}
```

#### POST /tactical/match-brief
Generate complete pre-match tactical brief

**Request Body:**
```json
{
  "opponent_team_id": 123,
  "matches": [
    // Array of match data
  ],
  "gil_vicente_formation": "4-3-3"
}
```

**Response:**
```json
{
  "opponent_team_id": 123,
  "analysis": {
    // Complete opponent analysis
  },
  "recommendations": {
    // Tactical recommendations
  },
  "summary": {
    "opponent_formation": "4-3-3",
    "recommended_formation": "4-3-3",
    "key_focus": "Press high to disrupt build-up",
    "main_threats": ["possession_control", "clinical_finishing"],
    "areas_to_exploit": ["defensive_vulnerability"]
  }
}
```

---

## Error Responses

All endpoints follow consistent error response format:

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

- `200 OK`: Successful request
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## Rate Limiting

SofaScore scraping should be treated as a best-effort source. Use caching and avoid high-frequency requests in production.

---

## Data Models

### Match Data Format
```json
{
  "formation": "4-3-3",
  "statistics": {
    "possession": 58.5,
    "shots": 15,
    "shots_on_target": 8,
    "passes": 450
  },
  "goals_scored": 2,
  "goals_conceded": 1,
  "result": "W",
  "is_home": true
}
```

### Tactical Analysis Format
See POST /tactical/analyze response for complete format.

---

## Best Practices

1. **Cache responses** when possible to reduce API calls
2. **Batch requests** for multiple opponents when analyzing fixtures
3. **Handle errors gracefully** with retry logic
4. **Monitor API usage** to stay within rate limits
5. **Validate data** before sending to analysis endpoints

---

## Interactive API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation with:
- Try-it-out functionality
- Request/response examples
- Schema definitions
- Authentication testing

---

For additional support or questions, contact the development team.
