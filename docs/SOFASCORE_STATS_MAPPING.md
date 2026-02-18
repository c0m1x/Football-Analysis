# Tactical Stats Mapping (WhoScored via soccerdata)

Este projeto mantém o schema de `recent_games_tactical` e `tactical_foundation`.
A origem passou para **WhoScored** (via `backend/services/whoscored_service.py`).

## Cobertura atual
- Preenchidos normalmente:
  - posse/passes
  - remates básicos
  - progressões por passe
  - ações defensivas base
  - PPDA proxy
  - corners
- Frequentemente `null` (depende do jogo/feed):
  - `xA`
  - `xG_from_open_play`
  - `xG_from_set_pieces`
  - métricas posicionais avançadas (heatmaps/zonas)

## Referências no código
- Normalização por jogo: `backend/services/whoscored_service.py`
- Agregação para painel: `backend/api/routes/opponent_stats.py`
- Consumo UI: `frontend/src/components/AdvancedStatsPanel.jsx`
