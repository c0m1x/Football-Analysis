# Tactical Analysis System

**Last Updated:** December 23, 2025  
**Status:** FULLY INTEGRATED

## System Overview

Gil Vicente Football Analysis is a tactical intelligence platform designed for coaching staff. The system provides comprehensive pre-match analysis including:

- Tactical Recommendations (formations, pressing, player roles)
- Advanced Statistics (possession, xG, PPDA, pressing intensity)
- Exploitable Weaknesses (identified vulnerabilities)
- Game Phase Planning (minute-by-minute tactical plan)
- Player Instructions (position-specific coaching points)

---

## Core Features

### 1. Tactical Engine
**File:** `backend/services/tactical_ai_engine.py`

**Capabilities:**
- Formation recommendations (4-4-2, 4-3-3, 3-5-2 based on opponent patterns)
- Pressing adjustments (high/mid/low block with line height specifications)
- Player role changes (inverted fullbacks, false 9, target man)
- Target zone identification (half-spaces, flanks, counter-attack spaces)
- Substitution timing (optimal windows: 60-65min, 70-75min)
- In-game tactical switches
- Exploitable weakness detection (CRITICAL/HIGH/MEDIUM severity)
- Confidence scoring (75-95% reliability)

**Example Output:**
```json
{
  "formation_changes": [
    {
      "formation": "4-3-3 Attack",
      "reason": "Opponent weak in wide areas - overload flanks"
    }
  ],
  "pressing_adjustments": {
    "style": "HIGH PRESS",
    "line_height": "50-60m from own goal",
    "rationale": "Opponent pass accuracy below 75% - force turnovers"
  },
  "target_zones": [
    {
      "zone": "Half-spaces (between CB and FB)",
      "priority": "PRIMARY",
      "exploitation": "Progressive passes into Mboula/Fujimoto"
    }
  ],
  "player_role_changes": [
    {
      "position": "RB",
      "new_role": "Inverted Fullback",
      "reason": "Opponent LW tracks poorly - create 3-2 build-up overload"
    }
  ],
  "exploitable_weaknesses": [
    {
      "weakness": "Slow center-backs vulnerable to pace",
      "severity": "CRITICAL",
      "tactical_response": "Direct balls in behind for Fujimoto runs"
    }
  ],
  "confidence_score": 87
}
```

---

### 2. Advanced Stats Analyzer
**File:** `backend/services/advanced_stats_analyzer.py`

**Metrics Extracted:**
- **Possession & Control**: Pass completion %, possession %, tempo rating
- **Attacking Intelligence**: xG, xG per shot, key passes, progressive passes
- **Defensive Metrics**: Tackles won %, interceptions, PPDA (passes allowed per defensive action)
- **Pressing Structure**: Pressing intensity (high/low), high turnovers, recovery time
- **Spatial Analysis**: Team shape (compact/stretched), defensive line height, compactness score
- **Transitions**: Counter-attack threat level, transition quality
- **Set-Pieces**: xG from corners/free kicks, set-piece defensive rating
- **Contextual Data**: Scoreline pressure, fatigue indicators (late-game drop-off)

**Example Output:**
```json
{
  "possession_control": {
    "avg_possession": 58.2,
    "pass_accuracy": 82.5,
    "tempo": "MEDIUM-HIGH"
  },
  "attacking_intelligence": {
    "xg_total": 1.8,
    "xg_per_shot": 0.12,
    "key_passes_per_game": 12.4,
    "progressive_passes": 38.6
  },
  "defensive_metrics": {
    "tackles_won_pct": 68.3,
    "interceptions_per_game": 11.2,
    "ppda": 8.7,
    "rating": "AGGRESSIVE"
  },
  "pressing_structure": {
    "intensity": "HIGH",
    "high_turnovers_per_game": 6.8,
    "press_success_rate": 31.4
  },
  "exploitable_patterns": [
    "Struggles under high press (pass accuracy drops to 71%)",
    "Vulnerable on counter-attacks (slow transition defense)",
    "Weak left flank (LB caught high 4.2 times/game)"
  ]
}
```

---

### 3. Tactical Recommendation Engine
**File:** `backend/services/tactical_ai_engine.py`

**Features:**
- Formation suggestions based on opponent weaknesses
- Pressing strategy recommendations
- Attacking approach guidelines
- Defensive setup instructions
- Player-specific role assignments
- In-game adjustment triggers

**Rule-Based Logic (example):**
- IF opponent PPDA < 10 → Recommend controlled possession build-up
- IF opponent pass accuracy < 75% → Recommend high pressing
- IF opponent allows > 1.5 xG/game → Recommend aggressive attacking approach
- IF opponent concedes from set-pieces → Highlight set-piece opportunities

---

### 4. Match Analysis Service
**File:** `backend/services/match_analysis_service.py`

**Complete Workflow:**
1. Fetch opponent's last 5 matches
2. Extract advanced statistics
3. Identify patterns and trends
4. Generate tactical recommendations
5. Create match brief with actionable insights

**Match Brief Includes:**
- Opponent tactical profile
- Formation analysis
- Key player threats
- Exploitable weaknesses (prioritized by severity)
- Recommended Gil Vicente setup
- Minute-by-minute game plan
- Substitution windows
- In-game trigger conditions

---

## API Integration

### Generate Tactical Plan
**Endpoint:** `POST /api/v1/tactical-plan/{team_id}`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/tactical-plan/123" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "opponent": {
    "team_id": 123,
    "name": "Opponent FC",
    "recent_form": "W-D-L-W-D"
  },
  "advanced_stats": { ... },
  "tactical_recommendations": { ... },
  "match_brief": {
    "summary": "Opponent plays possession-based football...",
    "key_instructions": [
      "Press aggressively in wide areas",
      "Exploit half-spaces with Mboula/Fujimoto",
      "Target slow CBs with direct runs"
    ]
  },
  "game_plan": {
    "0-15min": "Start compact, absorb pressure",
    "15-30min": "Increase pressing intensity",
    "30-45min": "Maintain structure, exploit transitions",
    "45-60min": "Assess opponent adjustments",
    "60-75min": "Consider tactical switch if needed",
    "75-90min": "Manage game state (protect lead or push for goal)"
  }
}
```

**Caching:** Results cached for 24 hours to prevent API token waste

---

## Frontend Integration

### Display Components

**Advanced Stats Panel**
- Visual gauges for key metrics
- Color-coded severity indicators
- Comparison charts

**Tactical Recommendations Card**
- Formation diagram
- Pressing zones heatmap
- Player role assignments
- Confidence scores

**Match Brief Section**
- Executive summary
- Phase-by-phase game plan
- Key instructions checklist
- Exploitable weaknesses list

---

## Data Flow

```
User Request
    ↓
API Endpoint (tactical_plan.py)
    ↓
Match Analysis Service
    ↓
├─→ SofaScore Service / Scraper Export (fetch matches)
├─→ Advanced Stats Analyzer (process data)
├─→ Tactical Engine (generate recommendations)
└─→ Recommendation Engine (create match brief)
    ↓
Cache Result (Redis, 24h TTL)
    ↓
Return JSON Response
    ↓
Frontend Display
```

---

## Configuration

### Pattern Rules
**File:** `backend/config/pattern_rules.json`

Defines thresholds and rules for tactical pattern detection:
```json
{
  "pressing_intensity": {
    "high": {"ppda": "<10"},
    "medium": {"ppda": "10-12"},
    "low": {"ppda": ">12"}
  },
  "possession_style": {
    "dominant": {">": 55},
    "balanced": {"40-55": true},
    "reactive": {"<": 40}
  }
}
```

### Customization
- Adjust thresholds in `pattern_rules.json`
- Modify recommendation logic in `tactical_ai_engine.py`
- Add new metrics in `advanced_stats_analyzer.py`

---

## Usage Example

### Complete Analysis Workflow

1. **Fetch Upcoming Fixture**
```bash
GET /api/v1/fixtures/upcoming
```

2. **Generate Tactical Plan**
```bash
POST /api/v1/tactical-plan/123
```

3. **Review Analysis**
- Advanced statistics
- Tactical recommendations
- Match brief

4. **Export for Coaching Staff**
- PDF generation
- Email delivery
- Print-friendly format

---

## Performance

- **Analysis Time**: 15-25 seconds (uncached)
- **Cache Hit Rate**: ~70% for repeated requests
- **API Calls**: 5-10 per analysis (rate-limited)
- **Memory Usage**: ~50MB per analysis

---

## Future Enhancements

### Planned Features
- Video clip integration
- Live match tracking
- Historical trend analysis
- Multi-match pattern detection
- Predictive outcome modeling

### Data Sources
- Current: SofaScore scraping + scraper export fallback
- Future: Event-level data providers
- Goal: Real-time tracking data

---

## Technical Details

### Dependencies
```
- pandas: Data processing
- numpy: Numerical calculations
- httpx: Async API calls
- redis: Caching layer
- fastapi: API framework
```

### Error Handling
- API rate limit protection
- Graceful degradation (missing data)
- Retry logic with exponential backoff
- Comprehensive logging

### Testing
- Unit tests for each analyzer
- Integration tests for full workflow
- Mock data for offline testing

---

## Best Practices

### For Developers
1. Always cache expensive API calls
2. Use async operations for data fetching
3. Validate input data thoroughly
4. Log all analysis parameters
5. Handle missing data gracefully

### For Users
1. Generate analysis 2-3 days before match
2. Review cached results for quick access
3. Export reports for offline viewing
4. Provide feedback on recommendation accuracy

---

## Troubleshooting

### Common Issues

**Slow Analysis**
- Check API rate limits
- Verify cache service running
- Monitor network latency

**Inaccurate Recommendations**
- Review pattern rule thresholds
- Check data quality
- Validate opponent ID

**Missing Statistics**
- Verify API subscription active
- Check opponent has recent matches
- Ensure league coverage available

---

## Support

For technical issues or feature requests:
- Review logs in `backend/logs/`
- Check API status at provider dashboard
- Contact development team

---

**Built for Gil Vicente FC**
