#!/usr/bin/env python3
import glob
import os
import re
import sys
from datetime import datetime

export_dir = os.environ.get("SCRAPER_EXPORT_DIR", "data/scraper_exports")
stamp_dir = os.environ.get("STAMP_DIR", "data")
paths = glob.glob(os.path.join(export_dir, "gil_vicente_next_opponent_*_individual_*.json"))
if not paths:
    print("ERROR: No scraper exports found. Did the scraper finish successfully?")
    sys.exit(1)

latest = max(paths, key=os.path.getmtime)
name = os.path.basename(latest)
match = re.match(r"gil_vicente_next_opponent_(.+)_individual_\d{8}_\d{6}\.json", name)
if not match:
    print(f"ERROR: Could not parse opponent name from export: {name}")
    sys.exit(1)

raw = match.group(1)
slug = raw.strip().lower().replace(" ", "_")
slug = re.sub(r"[^a-z0-9_]+", "", slug)
slug = re.sub(r"_+", "_", slug).strip("_") or "opponent"

os.makedirs(stamp_dir, exist_ok=True)
stamp_path = os.path.join(stamp_dir, f".scrape_done_{slug}")
with open(stamp_path, "w", encoding="utf-8") as f:
    f.write(f"opponent={raw}\n")
    f.write(f"export={latest}\n")
    f.write(f"timestamp={datetime.now().isoformat()}\n")

print(f"OK: Scrape session recorded for '{raw}' -> {stamp_path}")
