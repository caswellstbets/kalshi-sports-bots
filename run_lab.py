"""Run the three lab NBA models once, then rebuild NBA_MODELS.md. Paper only.

    python3 run_lab.py            normal run
    python3 run_lab.py --dry-run  look only

Prints SCOUT READ NEEDED <game_id> with a game sheet for each game that needs Claude's read;
answer with `python3 -m lab.scout read ...` (see lab/scout.py) and run again."""
from __future__ import annotations

import argparse
import json
import os
import sys

from lab import report, run

ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    out = run.run(ROOT, dry=a.dry_run)
    if not a.dry_run:
        report.build(ROOT)
    for gid, sh in out["sheets"].items():
        print(f"--- SCOUT READ NEEDED {gid} {sh['game']}")
        print(json.dumps(sh, separators=(",", ":")))
    if out["errors"]:
        print("FAILED:", ", ".join(out["errors"]))
    return 1 if out["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
