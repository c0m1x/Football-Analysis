# Football Tactical Intelligence Platform

Plataforma para análise tática do próximo adversário com suporte multi-liga e multi-equipa.

## Stack
- Backend: FastAPI (`backend/`)
- Frontend: React + Vite (`frontend/`)
- Cache: Redis
- Fonte de dados: WhoScored via `soccerdata` (Python)

## O que mudou
- Removido acoplamento a um clube fixo.
- Seleção de **liga** e **equipa** no frontend.
- A API identifica o **próximo adversário** da equipa escolhida.
- Sugestões táticas baseadas no adversário (últimos `OPPONENT_MATCH_HISTORY_LIMIT`, por defeito 10 jogos).
- Base portuguesa mantida como referência de treino (`PORTUGUESE_TRAINING_LEAGUE=POR-Liga Portugal`).

## Configuração
1. `cp .env.example .env`
2. Ajustar variáveis principais se necessário:
   - `WHOSCORED_LEAGUES`
   - `WHOSCORED_DEFAULT_LEAGUE`
   - `PORTUGUESE_TRAINING_LEAGUE`
   - `OPPONENT_MATCH_HISTORY_LIMIT`
   - `ML_TRAINING_LEAGUES`
   - `ML_MIN_SAMPLES`

## Como Rodar
### Opção 1: Docker (recomendado)
```bash
cp .env.example .env
docker compose up --build
```

Também podes usar:
```bash
make up
```

URLs:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

Login: `admin / FOOTBALL2026`

### Opção 2: Local (sem Docker)
Terminal 1 (backend):
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 (frontend):
```bash
cd frontend
npm install
npm run dev -- --host --port 3000
```

## Endpoints principais
- `GET /api/v1/leagues`
- `GET /api/v1/teams?league=ENG-Premier League`
- `GET /api/v1/fixtures/all?league=...&team_id=...`
- `GET /api/v1/fixtures/upcoming?league=...&team_id=...&limit=1`
- `GET /api/v1/next-opponent?league=...&team_id=...`
- `GET /api/v1/opponent-stats/{opponent_id}?opponent_name=...&team_id=...&league=...`
- `GET /api/v1/tactical-plan/{opponent_id}?opponent_name=...&team_id=...&league=...`
- `POST /api/v1/tactical-plan/{opponent_id}/recalibrate?team_id=...&league=...`
- `GET /api/v1/ml/status`
- `POST /api/v1/ml/train`

## Treino ML
Treinar modelo tático via script:
```bash
python3 scripts/train_ml_model.py --league POR-Liga Portugal --league ENG-Premier League --force
```

Ou via API:
```bash
curl -X POST http://localhost:8000/api/v1/ml/train \
  -H 'content-type: application/json' \
  -d '{"leagues":["POR-Liga Portugal","ENG-Premier League"],"force":true}'
```

Modelo guardado em `ML_MODEL_PATH` (por defeito `data/models/tactical_model.joblib`; com fallback automático para `../data/models` se necessário).

## Notas
- Algumas métricas avançadas podem aparecer `null` quando o feed não expõe o dado diretamente.
- A validação histórica continua baseada em época de referência (configurável).
