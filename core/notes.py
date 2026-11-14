"""Record an AI review of one game. This is how Claude, running the bots in a
session, supplies the judgment step without any API key:

    python -m core.notes nba 401909980 --margin -1.0 --total 0 --confidence medium \\
        --reason "Star guard ruled out an hour ago; line has not moved."

Adjustments are clamped to the bot's caps exactly as an API answer would be."""
from __future__ import annotations

import argparse
import importlib
import os

from . import engine
from .util import iso, now_utc, read_json, write_json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("bot", choices=["nba", "nfl", "cfb"])
    ap.add_argument("game_id")
    ap.add_argument("--margin", type=float, default=0.0, help="points added to the expected HOME margin")
    ap.add_argument("--total", type=float, default=0.0, help="points added to the expected total")
    ap.add_argument("--veto", action="store_true", help="do not trade this game")
    ap.add_argument("--confidence", choices=["low", "medium", "high"], default="medium")
    ap.add_argument("--reason", required=True)
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args()
    cfg = importlib.import_module(f"bots.{a.bot}").CONFIG
    p = engine.paths(cfg, a.root)
    cache = read_json(p["ai_cache"], {})
    clamp = lambda x, c: max(-c, min(c, x))
    cache[a.game_id] = {
        "status": "ok", "model": "Claude (in session)", "ts": iso(now_utc()),
        "margin_adj": clamp(a.margin, cfg.ai_margin_cap), "total_adj": clamp(a.total, cfg.ai_total_cap),
        "veto": a.veto, "confidence": a.confidence, "reason": a.reason[:600],
    }
    write_json(p["ai_cache"], cache)
    print(f"saved review for {a.bot} game {a.game_id}")


if __name__ == "__main__":
    main()
