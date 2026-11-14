"""The AI forecast store. Two stages, saved as separate append-only events in
data/<bot>/forecasts.jsonl so neither can overwrite the other:

  blind  Claude's own margin and total for a game, written from a sheet that
         contains no Kalshi price and no sportsbook line.
  check  after the prices are revealed: stands, shrink or drop, with the reason.

    python -m core.forecast blind cfb 401234 --margin 6.5 --total 48 \
        --reason "stat|3|Rating inflated by two blowouts of weak teams" \
        --reason "soft|1|Third straight road game" --summary "..." --unknowns "QB status"
    python -m core.forecast check cfb 401234 --outcome shrink --why "..."

A reason is type|points|text. Types: hard (a verifiable fact), stat (a read of
the numbers), soft (judgment). points is roughly how far that reason moved the
margin away from the stats forecast, in absolute points."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

from .util import append_jsonl, iso, now_utc, read_json, read_jsonl

PROMPT_VERSION = "blind-v1"
MODEL = "claude-fable-5-2 (in session)"
TYPES = {"hard": "hard_fact", "stat": "stat_read", "soft": "soft_judgment"}


def latest(path: str) -> dict:
    """game_id -> {"blind": first blind forecast, "check": latest check}. A blind forecast is
    never replaced: the first one recorded for a game is the one that gets graded."""
    out: dict[str, dict] = {}
    for ev in read_jsonl(path):
        g = out.setdefault(ev["game_id"], {})
        if ev["type"] == "blind":
            g.setdefault("blind", ev)
        elif ev["type"] == "check" and "blind" in g:
            g["check"] = ev
    return {k: v for k, v in out.items() if "blind" in v}


def validate_blind(cfg, sheet: dict, margin: float, total: float, reasons: list[dict]) -> str | None:
    st = sheet["stats_forecast"]
    dev = abs(margin - st["home_margin"])
    pts = {k: sum(r["points"] for r in reasons if r["type"] == k) for k in TYPES.values()}
    if dev > 0.5 and not reasons:
        return "a forecast that differs from the stats needs at least one reason"
    firm = pts["hard_fact"] + pts["stat_read"]
    if dev > cfg.soft_reason_cap + firm + 1e-9:
        return (f"forecast is {dev:.1f} points from the stats but hard and stat-based reasons only cover {firm:.1f}; "
                f"soft judgment alone may move it at most {cfg.soft_reason_cap}")
    if dev > cfg.hard_reason_gap and firm <= 0:
        return f"more than {cfg.hard_reason_gap} points from the stats needs a hard fact or stat-based reason"
    if not (20 <= total <= 320):
        return "total out of range"
    return None


def main(argv=None) -> int:
    from bots import cfb, nba, nfl
    cfgs = {m.CONFIG.name: m.CONFIG for m in (nba, nfl, cfb)}
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["blind", "check"])
    ap.add_argument("bot", choices=list(cfgs))
    ap.add_argument("game_id")
    ap.add_argument("--margin", type=float, help="expected HOME margin")
    ap.add_argument("--total", type=float)
    ap.add_argument("--reason", action="append", default=[])
    ap.add_argument("--summary", default="")
    ap.add_argument("--unknowns", default="")
    ap.add_argument("--outcome", choices=["stands", "shrink", "drop"])
    ap.add_argument("--why", default="")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv)
    cfg = cfgs[a.bot]
    d = os.path.join(a.root, "data", a.bot)
    path = os.path.join(d, "forecasts.jsonl")
    have = latest(path).get(a.game_id) or {}
    if a.stage == "blind":
        sheet = read_json(os.path.join(d, "blind_sheets.json"), {}).get(a.game_id)
        if not sheet:
            print("no blind sheet is waiting for that game; run the bot first"); return 1
        if "blind" in have:
            print("that game already has a blind forecast; it cannot be replaced"); return 1
        if a.margin is None or a.total is None:
            print("--margin and --total are required"); return 1
        reasons = []
        for r in a.reason:
            t, pts, text = r.split("|", 2)
            reasons.append({"type": TYPES[t], "points": abs(float(pts)), "text": text.strip()})
        err = validate_blind(cfg, sheet, a.margin, a.total, reasons)
        if err:
            print("rejected:", err); return 1
        append_jsonl(path, [{
            "type": "blind", "game_id": a.game_id, "game": sheet["game"], "ts": iso(now_utc()),
            "margin": a.margin, "total": a.total, "reasons": reasons, "summary": a.summary, "unknowns": a.unknowns,
            "stats_margin": sheet["stats_forecast"]["home_margin"], "stats_total": sheet["stats_forecast"]["total"],
            "selected": sheet["picked_for_review_because"],
            "sheet_sha": hashlib.sha256(json.dumps(sheet, sort_keys=True).encode()).hexdigest()[:16],
            "sheet": sheet, "prompt_version": PROMPT_VERSION, "model": MODEL, "strategy_version": cfg.strategy_version}])
        print(f"saved blind forecast for {a.bot} {a.game_id}")
    else:
        reveal = read_json(os.path.join(d, "reveal_sheets.json"), {}).get(a.game_id)
        if "blind" not in have:
            print("no blind forecast for that game yet"); return 1
        if not reveal and "check" not in have:
            print("no market check is waiting for that game; run the bot first"); return 1
        if not a.outcome or not a.why:
            print("--outcome and --why are required"); return 1
        append_jsonl(path, [{"type": "check", "game_id": a.game_id, "ts": iso(now_utc()), "outcome": a.outcome,
                             "why": a.why, "auto": False, "seen": reveal, "model": MODEL}])
        print(f"saved market check for {a.bot} {a.game_id}: {a.outcome}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
