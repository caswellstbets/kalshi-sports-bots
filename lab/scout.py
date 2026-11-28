"""Model C, "Scout": Claude's own full read of the game, done in session (no API key).

Unlike the current NBA bot, which writes a blind forecast from a no-price sheet and is then held
close to the market, the Scout reads everything at once, Kalshi prices included, the way a
careful bettor would: who is playing, how each team has really been playing, rest, and what the
price already assumes. Its job is to say what the price is missing, or pass. It never sees a
sportsbook line or the other lab models' numbers.

    python -m lab.scout read <game_id> --p-home 0.58 --margin 3.5 --total 229.5 \
        --pick "KXNBAGAME-26NOV16ORLBOS-BOS:yes" --confidence Mid \
        --why "two or three plain sentences" --missing "what the price is missing"
    python -m lab.scout read <game_id> ... --pick none --why "..."

A read is saved once and cannot be replaced. The code checks the pick against the Scout's own
numbers: the edge after the fee must clear the tier (High 8, Mid 5, Low 3 points); a tier the edge
does not support is lowered, and a pick under 3 points is not placed."""
from __future__ import annotations

import argparse
import json
import os
import sys

from core.util import iso, norm_cdf, now_utc, read_json, read_jsonl, append_jsonl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "data", "nba_scout")
SD_MARGIN, SD_TOTAL = 14.6, 19.1   # residual spread of NBA margins and totals (research/backtest_rotation.py)


def reads() -> dict[str, dict]:
    out = {}
    for r in read_jsonl(os.path.join(DIR, "reads.jsonl")):
        out.setdefault(r["game_id"], r)  # the first read is the one that counts
    return out


def sheets() -> dict:
    return read_json(os.path.join(DIR, "sheets.json"), {})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["read"])
    ap.add_argument("game_id")
    ap.add_argument("--p-home", type=float, required=True, help="home-win probability, 0-1")
    ap.add_argument("--margin", type=float, required=True, help="expected HOME margin")
    ap.add_argument("--total", type=float, required=True)
    ap.add_argument("--pick", required=True, help="TICKER:yes|no from the sheet, or none")
    ap.add_argument("--confidence", choices=["High", "Mid", "Low"])
    ap.add_argument("--why", required=True)
    ap.add_argument("--missing", default="", help="what the Kalshi price is missing")
    a = ap.parse_args(argv)
    sh = sheets().get(a.game_id)
    if not sh:
        print("no Scout sheet is waiting for that game; run `python3 run_lab.py` first"); return 1
    if a.game_id in reads():
        print("that game already has a Scout read; it cannot be replaced"); return 1
    if not (0.02 <= a.p_home <= 0.98) or not (170 <= a.total <= 300):
        print("rejected: probability or total out of range"); return 1
    implied = norm_cdf(a.margin / SD_MARGIN)
    if abs(implied - a.p_home) > 0.08:
        print(f"rejected: a home margin of {a.margin:+.1f} means about {implied:.0%} to win, not {a.p_home:.0%}; make them agree"); return 1
    pick = None
    if a.pick.lower() != "none":
        tk, _, side = a.pick.rpartition(":")
        offered = {(c["ticker"], c["side"]) for c in sh["contracts"]}
        if (tk, side) not in offered:
            print("rejected: that contract and side are not on the sheet"); return 1
        if not a.confidence or not a.missing:
            print("rejected: a pick needs --confidence and --missing"); return 1
        pick = {"ticker": tk, "side": side, "confidence": a.confidence}
    append_jsonl(os.path.join(DIR, "reads.jsonl"), [{
        "game_id": a.game_id, "game": sh["game"], "ts": iso(now_utc()), "p_home": a.p_home, "margin": a.margin,
        "total": a.total, "pick": pick, "why": a.why, "missing": a.missing, "sheet": sh, "model": "Claude, in session"}])
    print(f"saved Scout read for {sh['game']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
