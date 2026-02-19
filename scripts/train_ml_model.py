#!/usr/bin/env python3
"""Train tactical ML model from available league data."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


def _bootstrap_backend_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    backend_root = repo_root / "backend"
    sys.path.insert(0, str(backend_root))
    os.chdir(str(backend_root))


async def _run(leagues: list[str], force: bool) -> int:
    from services.tactical_ml_service import get_tactical_ml_service

    service = get_tactical_ml_service()
    result = await service.train_model(leagues=leagues or None, force=force)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result.get("ok") else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Train tactical ML model")
    parser.add_argument(
        "--league",
        action="append",
        default=[],
        help="League code (repeatable), e.g. --league POR-Liga Portugal",
    )
    parser.add_argument("--force", action="store_true", help="Retrain even if model already exists")
    args = parser.parse_args()

    _bootstrap_backend_path()
    return asyncio.run(_run(args.league, args.force))


if __name__ == "__main__":
    raise SystemExit(main())
