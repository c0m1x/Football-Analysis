## Como correr o projeto

### Opção A: Docker (recomendado)
No root do projeto:

1. `cp .env.example .env`
2. `docker compose up --build`
3. Abre `http://localhost:3000`

Também podes usar `make up`.

Login: `admin / FOOTBALL2026`

### Opção B: Local (sem Docker)
Terminal 1 (backend):

1. `cd backend`
2. `python3 -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `uvicorn main:app --reload --host 0.0.0.0 --port 8000`

Terminal 2 (frontend):

1. `cd frontend`
2. `npm install`
3. `npm run dev -- --host --port 3000`

URLs:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Fluxo novo
1. Escolhe a liga.
2. Escolhe a equipa.
3. A plataforma identifica o próximo adversário.
4. A análise tática usa os últimos 10 jogos do adversário (configurável em `OPPONENT_MATCH_HISTORY_LIMIT`).

## Treino do modelo ML
- Estado do modelo: `GET http://localhost:8000/api/v1/ml/status`
- Treinar modelo (API): `POST http://localhost:8000/api/v1/ml/train`
- Treinar modelo (script):
  1. `source backend/.venv/bin/activate` (se usares venv local)
  2. `python3 scripts/train_ml_model.py --league POR-Liga Portugal --force`
