# Arquitetura da Aplicação Tática

## 1) Arquitetura do projeto

### Backend (FastAPI)
- `backend/api/routes/opponent_stats.py`
  - Dashboard estatístico do adversário.
  - Expõe `historical_context` com época base e nota de validação.
- `backend/api/routes/tactical_plan.py`
  - `GET /tactical-plan/{opponent_id}`: plano base com sugestões táticas.
  - `POST /tactical-plan/{opponent_id}/recalibrate`: recalibração com dados manuais da época atual.
- `backend/services/match_analysis_service.py`
  - Pipeline de análise histórica e agregação de métricas.
- `backend/services/tactical_ai_engine.py`
  - Recomendações base por regras.
- `backend/services/tactical_ml_service.py`
  - Treino do modelo ML (classificação de risco + regressão de golos esperados).
  - Inferência online para ajuste tático.
  - Fallback automático para regras quando não existe modelo treinado.
- `backend/services/tactical_recommendation_service.py`
  - Combina histórico + observações atuais.
  - Ajusta confiança devido ao drift temporal.
  - Gera categorias táticas finais.
  - Integração opcional Anthropic para texto natural.

### Frontend (React)
- `frontend/src/pages/NextOpponent.jsx`
  - Seleção de liga + equipa.
  - Resolução automática do próximo adversário.
  - Formulário de observações atuais (até 3 jogos).
  - Recalibração do plano tático via endpoint `POST`.
- `frontend/src/components/AdvancedStatsPanel.jsx`
  - Dashboard de métricas históricas.
- `frontend/src/components/TacticalPlanPanel.jsx`
  - Exibição das 5 categorias táticas obrigatórias.
- `frontend/src/utils/exportAnalysis.js`
  - Exportação JSON/TXT + Word (`.doc`) + PDF (print dialog).

## 2) Esquema de dados

### 2.1 Dados históricos (época base)
Fonte: WhoScored (`soccerdata`) normalizado no backend.

Campos principais usados:
- `possession_percent`
- `shots_per_game`
- `goals_scored_per_game`
- `goals_conceded_per_game`
- `ppda`
- `defensive_line_height`
- `width_usage`
- `set_piece_weakness`

### 2.2 Observações manuais da época atual (input treinador)
Request de recalibração:

```json
{
  "opponent_name": "Sporting CP",
  "current_season_observations": [
    {
      "match_label": "Jogo 1",
      "possession_percent": 58,
      "shots_for": 14,
      "goals_scored": 2,
      "goals_conceded": 1,
      "pressing_level": "high",
      "offensive_transitions_rating": 8,
      "build_up_pattern": "central",
      "defensive_line_height": 49,
      "set_piece_vulnerability": "high",
      "key_players": ["Gyokeres", "Pedro Gonçalves"],
      "notes": "Acelera após recuperação"
    }
  ]
}
```

### 2.3 Resposta tática recalibrada
Campos novos:
- `historical_context.baseline_season`
- `historical_context.validation_note`
- `historical_context.season_comparison`
  - `historical_profile`
  - `current_observed_profile`
  - `blended_profile`
- `confidence_adjustment`
  - `adjusted_confidence`
  - `recommendation_reliability`
  - penalizações/boosts
- `customized_suggestions`
  - `recommended_system`
  - `attack_zones`
  - `defensive_vulnerabilities`
  - `neutralize_strengths`
  - `set_piece_adjustments`

## 3) Regras de confiança

- Base histórica sofre penalização fixa por drift temporal (época anterior).
- Observações atuais aumentam confiança conforme:
  - `sample_size`
  - completude dos campos.
- Divergência forte entre histórico e observado reduz confiança final.

## 5) Pipeline ML

- Dataset: janelas históricas por equipa (últimos `ML_WINDOW_SIZE` jogos) para prever jogo seguinte.
- Labels reais: resultado (`W/D/L`), golos marcados e sofridos.
- Modelos:
  - `RandomForestClassifier` para tendência de resultado.
  - `RandomForestRegressor` para golos esperados (marcados/sofridos).
- Artefacto: `ML_MODEL_PATH`.
- Endpoints:
  - `GET /api/v1/ml/status`
  - `POST /api/v1/ml/train`

## 4) Nota obrigatória por sugestão

Todas as sugestões carregam:

`Baseado em dados da época 2023/24 — validar com observação recente do adversário.`

(ajustada automaticamente se `HISTORICAL_BASELINE_SEASON` mudar).
