No root do projeto, corre: docker compose up --build (ou docker-compose up --build)
make scrape
make run TEAM="Moreirense"
Abre: http://localhost:3000
Login: admin / GIL2025
Para modo offline (sem SofaScore), corre: `python3 scrapper/scrapper.py` para gerar `data/scraper_exports/gil_vicente_fixtures_*.json`
