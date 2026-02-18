# Gil Vicente Tactical Intelligence Platform

Projeto não oficial para análise tática do próximo adversário do Gil Vicente.

## Stack
- Backend: FastAPI (`backend/`)
- Frontend: React + Vite (`frontend/`)
- Cache: Redis
- Fonte de dados: WhoScored via `soccerdata`

## Estrutura (simplificada)
- `backend/api/routes/real_fixtures.py`: calendário e endpoints de adversários
- `backend/api/routes/opponent_stats.py`: estatísticas táticas agregadas
- `backend/api/routes/tactical_plan.py`: recomendações automáticas
- `backend/services/whoscored_service.py`: ingestão/normalização da fonte única
- `backend/services/match_analysis_service.py`: pipeline de análise

## Configuração
1. `cp .env.example .env`
2. Ajustar variáveis se necessário:
   - `WHOSCORED_ENABLED`
   - `WHOSCORED_LEAGUES`
   - `WHOSCORED_SEASONS`
   - `GIL_VICENTE_TEAM_NAME`

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

Login: `admin / GIL2025`

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
- `GET /api/v1/fixtures/all`
- `GET /api/v1/fixtures/upcoming?limit=1`
- `GET /api/v1/opponent-stats/{opponent_id}?opponent_name=...`
- `GET /api/v1/tactical-plan/{opponent_id}?opponent_name=...`
- `POST /api/v1/tactical-plan/{opponent_id}/recalibrate`
- `GET /api/v1/match-analysis/{opponent_id}?opponent_name=...`

## Documentação adicional
- Arquitetura + esquema de dados: `docs/TACTICAL_ARCHITECTURE.md`

## Notas
- Algumas métricas avançadas continuam `null` quando o feed não expõe o dado diretamente.
- O pipeline foi reduzido para uma única fonte e sem fallback de scraper local.
