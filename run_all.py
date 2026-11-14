"""Run all three bots once, then rebuild the scorecard.

    python run_all.py            normal run (saves trades, grades, scorecard)
    python run_all.py --dry-run  look only

A run prints two kinds of request. BLIND FORECAST NEEDED: a game sheet with no prices
in it; answer with `python -m core.forecast blind ...`. MARKET CHECK NEEDED: the prices
for a game already forecast; answer with `python -m core.forecast check ...`. Run again
to act on the answers. A game with no forecast or no check is never traded."""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback

from bots import cfb, nba, nfl
from core import engine, report

ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-ai", action="store_true", help="do not request new AI forecasts")
    ap.add_argument("--only", choices=["nba", "nfl", "cfb"])
    a = ap.parse_args()
    failed, pending = [], {}
    for mod in (nba, nfl, cfb):
        cfg = mod.CONFIG
        if a.only and cfg.name != a.only:
            continue
        try:  # one sport's data problem must not stop the other two
            out = engine.run(cfg, ROOT, dry=a.dry_run, use_ai=not a.no_ai)
            if out["sheets"] or out["reveals"]:
                pending[cfg.name] = out
        except Exception:
            failed.append(cfg.name)
            traceback.print_exc()
    if not a.dry_run:
        report.build(ROOT)
    for bot, out in pending.items():
        for gid, sh in out["sheets"].items():
            print(f"--- BLIND FORECAST NEEDED {bot} {gid} {sh['game']}")
            print(json.dumps(sh, separators=(",", ":")))
        for gid, sh in out["reveals"].items():
            print(f"--- MARKET CHECK NEEDED {bot} {gid} {sh['game']}")
            print(json.dumps(sh, separators=(",", ":")))
    if failed:
        print("FAILED:", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
