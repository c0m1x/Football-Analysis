# Gil Vicente Tactical Intelligence Platform

## Disclaimer / Aviso

**PT:** Este é um projeto **não oficial**, criado por um adepto. O **Gil Vicente FC** **não** solicitou, não aprovou/endossou, não está afiliado e **não** remunerou este trabalho.

**EN:** This is an **unofficial fan-made** project. **Gil Vicente FC** did **not** request or endorse it, is **not** affiliated with it, and **no** remuneration was provided.

A comprehensive software system that integrates with football data APIs to analyze opponents of Gil Vicente FC and provide tactical insights and formation suggestions tailored to each upcoming match.

## Project Overview

## Data Sources & Accuracy Notes

This project mixes **real fixture data** with **derived/estimated tactical metrics**.

- **Real data**: fixtures/results are fetched from SofaScore scraping and local scraper exports.
- **Estimated/heuristic data**: many advanced metrics (e.g. xG/xA/PPDA proxies, pressing/shape proxies) are computed because the upstream sources used here do **not** provide full event-level tracking.
- **How to detect it**: several API responses include an `estimated: true` flag and/or a note like "Estimated proxy (no event data)".
- **Unavailable fields**: event/positional outputs such as zone heatmaps, touches-per-zone, overloads, and minute-by-minute timelines are returned as `null` unless you integrate an event feed or video tracking.

The Gil Vicente Tactical Intelligence Platform helps coaches and analysts by:

- **Automatically identifying** Gil Vicente's upcoming opponents
- **Collecting and processing** relevant match and team data
- **Generating tactical recommendations** based on opponent tendencies
- **Presenting insights** in a clear, actionable format

## Live Deployment

The platform is currently deployed and accessible online.

## Key Features

### Core Capabilities
- API integration with football data providers
- Opponent filtering and tracking
- Tactical summaries
- Formation analysis
- Playing style metrics
- Strength/weakness identification

### Advanced Features
- Advanced pattern detection
- Rule-based tactical recommendations
- Interactive visual dashboards
- Historical performance tracking

### Future Enhancements
- Predictive models
- Match outcome simulations
- Custom tactical profiles per coach

## Architecture

```
├── backend/                 # Python FastAPI backend
│   ├── api/                # API routes and endpoints
│   ├── models/             # Database models
│   ├── services/           # Business logic services
│   ├── config/             # Configuration
│   └── utils/              # Utility functions
├── frontend/               # React frontend dashboard
│   ├── src/
│   │   ├── components/    # Reusable components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API services
│   │   └── utils/         # Utility functions
├── database/              # Database schemas and migrations
├── docs/                  # Additional documentation
└── config/                # Configuration files
```

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Database**: PostgreSQL
- **Cache**: Redis
- **API Integration**: httpx, requests
- **Data Processing**: pandas, numpy

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: TailwindCSS
- **State Management**: React Query
- **Routing**: React Router
- **Charts**: Recharts

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Database**: PostgreSQL 15
- **Cache**: Redis 7

## Setup Instructions

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### Quick Start with Docker

1. **Clone the repository**
```bash
cd "Football Analysis"
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env
```

3. **Start the services**
```bash
docker-compose up -d
```

4. **Access the applications**
- Frontend Dashboard: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Local Development Setup

#### Backend Setup

1. **Create virtual environment**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp ../.env.example .env
# Edit .env with your configuration
```

4. **Run database migrations**
```bash
# Ensure PostgreSQL is running
psql -U gil_vicente_user -d gil_vicente_tactical -f ../database/schemas/001_initial_schema.sql
```

5. **Start the backend**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

1. **Install dependencies**
```bash
cd frontend
npm install
```

2. **Start development server**
```bash
npm run dev
```

3. **Build for production**
```bash
npm run build
```

## API Documentation

### Core Endpoints

#### Health Check
```
GET /api/v1/health
```

#### Fixtures
```
GET /api/v1/fixtures/upcoming?limit=5
GET /api/v1/fixtures/{fixture_id}
```

#### Opponents
```
GET /api/v1/opponents/{team_id}/matches?limit=10
GET /api/v1/opponents/{team_id}/statistics
GET /api/v1/opponents/{team_id}/head-to-head?last=5
```

#### Tactical Analysis
```
POST /api/v1/tactical/analyze
POST /api/v1/tactical/recommendations
POST /api/v1/tactical/match-brief
```

For detailed API documentation, visit: http://localhost:8000/docs

## Usage Examples

### Analyzing an Opponent

1. **Fetch opponent's recent matches**
```bash
curl http://localhost:8000/api/v1/opponents/123/matches?limit=10
```

2. **Analyze tactical patterns**
```bash
curl -X POST http://localhost:8000/api/v1/tactical/analyze \
  -H "Content-Type: application/json" \
  -d @matches.json
```

3. **Generate recommendations**
```bash
curl -X POST http://localhost:8000/api/v1/tactical/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "opponent_analysis": {...},
    "gil_vicente_formation": "4-3-3"
  }'
```

### Complete Match Brief
```bash
curl -X POST http://localhost:8000/api/v1/tactical/match-brief \
  -H "Content-Type: application/json" \
  -d '{
    "opponent_team_id": 123,
    "matches": [...],
    "gil_vicente_formation": "4-3-3"
  }'
```

## Database Schema

### Teams
- Core team information
- Gil Vicente flagged with `is_gil_vicente=1`

### Matches
- Match details and statistics
- Formations and tactical data
- Home/away performance metrics

### Tactical Profiles
- Analyzed tactical tendencies
- Formation frequencies
- Playing style metrics
- Strengths and weaknesses

## Configuration

Key configuration options in `.env`:

```env
# SofaScore
SOFASCORE_ENABLED=True
GIL_VICENTE_TEAM_ID=9764
GIL_VICENTE_LEAGUE_ID=61

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/gil_vicente_tactical

# Cache
REDIS_HOST=localhost
CACHE_TTL=3600
```

## Deployment

### Production Environment Variables

```env
DEBUG=False
HOST=0.0.0.0
PORT=8000
DATABASE_URL=postgresql://production_user:production_pass@db_host:5432/production_db
REDIS_HOST=production_redis_host
CORS_ORIGINS=["https://your-production-url.com"]
LOG_LEVEL=INFO
```

## Monitoring & Logging

- Structured JSON logging
- Request/response logging
- Error tracking
- Performance metrics

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Contributing

This is a professional project for Gil Vicente FC. For contributions:

1. Follow the existing code structure
2. Write tests for new features
3. Update documentation
4. Follow Python PEP 8 and ESLint standards

## License

Proprietary - Gil Vicente FC

## Data Source

This project uses SofaScore scraping with an optional local scraper export fallback.

## Support

For issues or questions, contact the development team.

---

**Built for Gil Vicente FC**
