#!/usr/bin/env python3

"""Fetch recent match statistics from SofaScore and write normalized JSON.

Outputs the same per-match tactical stats shape used by the backend endpoint:
`GET /api/v1/opponent-stats/{opponent_id}` under `recent_games_tactical`.

Usage examples:
  python scripts/sofascore_sync.py --team "Gil Vicente" --limit 5 --out /tmp/gil.json
  python scripts/sofascore_sync.py --team "FC Porto" --limit 10 --pretty
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


def _bootstrap_import_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    backend_dir = repo_root / "backend"
    sys.path.insert(0, str(backend_dir))


async def _run(team: str, limit: int, team_id: int | None) -> list[dict]:
    from services.sofascore_service import get_sofascore_service

    svc = get_sofascore_service()
    return await svc.get_recent_games_tactical(team, limit=limit, team_id=team_id)


def main() -> int:
    _bootstrap_import_path()

    parser = argparse.ArgumentParser(description="Fetch SofaScore match stats and normalize to project schema")
    parser.add_argument("--team", required=True, help="Team name as it appears on SofaScore (best-effort search) OR a numeric SofaScore team id")
    parser.add_argument("--team-id", type=int, default=None, help="Optional SofaScore team id (bypasses /search/all)")
    parser.add_argument("--limit", type=int, default=5, help="How many finished matches to fetch")
    parser.add_argument("--out", default="", help="Output JSON file path (defaults to stdout)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    args = parser.parse_args()

    # Convenience: allow passing a numeric team id in --team
    if args.team_id is None and str(args.team).strip().isdigit():
        args.team_id = int(str(args.team).strip())

    try:
        data = asyncio.run(_run(args.team, args.limit, args.team_id))
    except Exception as e:
        msg = str(e)
        print(f"Error fetching SofaScore data: {msg}", file=sys.stderr)
        print(
            "Tip: SofaScore may block search (403). Use --team-id (from the team URL on sofascore.com), pass a numeric team id via --team, or set SOFASCORE_TEAM_ID_MAP_JSON in .env to bypass /search/all.",
            file=sys.stderr,
        )
        return 2

    payload = {
        "team": args.team,
        "limit": args.limit,
        "matches": data,
        "matches_found": len(data),
    }

    indent = 2 if args.pretty else None
    text = json.dumps(payload, ensure_ascii=False, indent=indent)

    if args.out:
        out_path = Path(args.out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
