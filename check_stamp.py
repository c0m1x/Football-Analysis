#!/usr/bin/env python3
import glob
import os
import re
import sys

stamp_dir = os.environ.get("STAMP_DIR", "data")
team = os.environ.get("TEAM", "").strip()

def slugify(value):
    s = value.strip().lower().replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "opponent"

if team:
    slug = slugify(team)
    stamp = os.path.join(stamp_dir, f".scrape_done_{slug}")
    if not os.path.isfile(stamp):
        print(f"ERROR: No scrape session found for team '{team}'. Run: make scrape")
        sys.exit(1)
else:
    stamps = glob.glob(os.path.join(stamp_dir, ".scrape_done_*"))
    if not stamps:
        print("ERROR: No scrape session found. Run: make scrape")
        sys.exit(1)
