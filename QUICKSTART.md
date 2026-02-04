# Quick Start Guide

## Disclaimer / Aviso

**PT:** Este é um projeto **não oficial**, criado por um adepto. O **Gil Vicente FC** **não** solicitou, não aprovou/endossou, não está afiliado e **não** remunerou este trabalho.

**EN:** This is an **unofficial fan-made** project. **Gil Vicente FC** did **not** request or endorse it, is **not** affiliated with it, and **no** remuneration was provided.

## Gil Vicente Tactical Intelligence Platform

Get up and running in 5 minutes.

---

## Prerequisites

- **Docker** & **Docker Compose** installed
- No API keys are required for the default SofaScore scraping mode

---

## Installation Steps

### 1. Setup Environment

```bash
# Navigate to project directory
cd "Football Analysis"

# Copy environment template
cp .env.example .env

# Edit .env
nano .env  # or use your preferred editor
```

**Optional: enable SofaScore tactical stats (recommended):**
```env
SOFASCORE_ENABLED=True
```

If SofaScore search is blocked (403), you can pin team IDs and skip the search step:

```env
SOFASCORE_TEAM_ID_MAP_JSON={"Gil Vicente": 12345}
```

(You can usually find the team id in the sofascore.com team URL: `.../team/football/<slug>/<id>`.)

If SofaScore match statistics are blocked (HTTP 403), you can also use the Selenium scraper export fallback:

1. Run the scraper to generate JSON exports:
```bash
python3 scrapper/scrapper.py
```

2. (Optional) Point the backend to the folder containing those exports (defaults to `data/scraper_exports/`):
```env
SCRAPER_EXPORT_DIR=/path/to/Football Analysis/data/scraper_exports
```


### 2. Start Services

```bash
# Using the setup script (recommended)
./scripts/setup.sh

# OR manually with Docker Compose
docker-compose up -d
```

### 3. Access the Platform

**Local Development:**
- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

**Production:**
The platform is deployed and accessible online.

---

## Using the Platform

### Dashboard
View upcoming matches, opponent tracking status, and recent activity.

### Fixtures
- View Gil Vicente's upcoming matches
- Check opponent details
- Schedule analysis

### Opponents
- Track opponent teams
- View match history
- Access statistics

### Tactical Analysis
- Generate opponent analysis
- Get tactical recommendations
- View match briefs

---

## Development Setup

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

---

## API Quick Examples

### Get Upcoming Fixtures
```bash
curl http://localhost:8000/api/v1/fixtures/upcoming?limit=5
```

### Get Opponent Statistics
```bash
curl http://localhost:8000/api/v1/opponents/123/statistics
```

### Generate Tactical Analysis
```bash
curl -X POST http://localhost:8000/api/v1/tactical/analyze \
  -H "Content-Type: application/json" \
  -d @matches.json
```


### Export SofaScore stats (JSON)
```bash
python3 scripts/sofascore_sync.py --team "Gil Vicente" --limit 5 --pretty
python3 scripts/sofascore_sync.py --team "Gil Vicente" --team-id 12345 --limit 5 --pretty
```

---

## Key Features

**Opponent Tracking** - Automatically identify Gil Vicente's opponents  
**Tactical Analysis** - Analyze formations, playing style, strengths/weaknesses  
**Match Recommendations** - Get tactical suggestions for each match  
**Data Visualization** - Clear, actionable insights dashboard  
**Data Sources** - SofaScore scraping with optional local scraper export fallback  

---

## Sample Workflow

1. **Check Upcoming Fixtures**
   - Navigate to Fixtures page
   - View Gil Vicente's next matches

2. **Select Opponent**
   - Click on opponent team
   - View recent match history

3. **Generate Analysis**
   - Click "Analyze Opponent"
   - Review tactical patterns
   - View formation tendencies

4. **Get Recommendations**
   - Request tactical brief
   - Review suggested formations
   - Export match preparation notes

---

## Troubleshooting

### Services won't start
```bash
# Check if ports are available
netstat -tulpn | grep -E '3000|8000|5432|6379'

# Check Docker logs
docker-compose logs -f
```

### SofaScore 403 (blocked)
- Run `docker compose exec backend python scripts/sofascore_diagnose.py`
- Use the Selenium scraper export fallback (`python3 scrapper/scrapper.py`)
- Optionally set `SOFASCORE_ENABLED=False` to force offline fixtures mode

### Database Connection
```bash
# Check PostgreSQL is running
docker-compose ps

# Reset database
docker-compose down -v
docker-compose up -d
```

---

## Next Steps

- Review [API Documentation](docs/API_DOCUMENTATION.md)
- Explore [Tactical Features](TACTICAL_FEATURES.md)
- Check [Project Summary](PROJECT_SUMMARY.md)

---

## Ready to Analyze

You're all set! Start by viewing upcoming fixtures and analyzing your next opponent.

For detailed information, see the full README.md

---

**Built for Gil Vicente FC**
