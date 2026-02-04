"""SofaScore connectivity diagnosis.

Runs a couple of lightweight requests and prints actionable hints.
Intended for manual debugging (not as a CI test).

Usage (inside container):
  python scripts/sofascore_diagnose.py

Env controls (optional):
- SOFASCORE_BASE_URL / SOFASCORE_BASE_URLS
- SOFASCORE_HEADERS_JSON
- SOFASCORE_COOKIES_JSON
- SOFASCORE_PROXY
- GIL_VICENTE_TEAM_ID
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure `/app` (backend root) is on sys.path when executed as a script.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from services.sofascore_service import SofaScoreService  # noqa: E402


async def main() -> int:
    team_id = int(os.getenv("GIL_VICENTE_TEAM_ID", "9764"))
    svc = SofaScoreService()

    print("SofaScore base urls:")
    for u in getattr(svc, "base_urls", []):
        print(f"- {u}")

    try:
        last = await svc.get_last_finished_events(team_id, limit=1, max_pages=1)
        print(f"last_finished_events: OK (count={len(last)})")
    except Exception as e:
        print(f"last_finished_events: ERROR: {type(e).__name__}: {e}")

    try:
        nxt = await svc.get_upcoming_events(team_id, limit=1, max_pages=1)
        print(f"upcoming_events: OK (count={len(nxt)})")
    except Exception as e:
        print(f"upcoming_events: ERROR: {type(e).__name__}: {e}")

    if os.getenv("SOFASCORE_COOKIES_JSON") or os.getenv("SOFASCORE_PROXY"):
        print("Hint: cookies/proxy are configured.")
    else:
        print(
            "Hint: this environment appears to be blocked (403). "
            "Consider using an authorized data provider or running in an environment with permitted access."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
