"""Run all three bots once, then rebuild the scorecard.

    python run_all.py            normal run (saves trades, grades, scorecard)
    python run_all.py --dry-run  look only
    python run_all.py --quiet-hours-check   exit immediately if nothing is near

A game that is close to a trade but has no AI review yet is held: its sheet is
written to data/<bot>/review_sheets.json. Review it, save a note with
`python -m core.notes ...`, and run again to act on it."""
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
    ap.add_argument("--no-ai", action="store_true")
    ap.add_argument("--only", choices=["nba", "nfl", "cfb"])
    a = ap.parse_args()
    failed, pending = [], {}
    for mod in (nba, nfl, cfb):
        cfg = mod.CONFIG
        if a.only and cfg.name != a.only:
            continue
        try:  # one sport's data problem must not stop the other two
            out = engine.run(cfg, ROOT, dry=a.dry_run, use_ai=not a.no_ai)
            if out["sheets"]:
                pending[cfg.name] = out["sheets"]
        except Exception:
            failed.append(cfg.name)
            traceback.print_exc()
    if not a.dry_run:
        report.build(ROOT)
    if pending:
        print("\nREVIEWS NEEDED (save each with: python -m core.notes <bot> <game_id> ...):")
        for bot, sheets in pending.items():
            for gid, s in sheets.items():
                print(f"--- {bot} {gid} {s['game']}")
                print(json.dumps({k: v for k, v in s.items() if k not in ("game", "game_id", "adjustment_caps", "sport")},
                                 separators=(",", ":")))
    if failed:
        print("FAILED:", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
