"""Join past Kalshi NBA winner markets to ESPN games and read the home team's price at fixed
times before tip-off. Research only.

    rows = load()  # one row per game: ESPN id, result, Kalshi home bid/ask at T-24h ... T-0"""
from __future__ import annotations

import json
import os

from core.kalshi import key_date
from core.util import ET, parse_iso
from lab import boxscores

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIAS = {"GS": "GSW", "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}
OFFSETS = {"t24": 24, "t12": 12, "t6": 6, "t3": 3, "t2": 2, "t1": 1, "t0": 0}


def code(espn_abbr: str) -> str:
    return ALIAS.get(espn_abbr, espn_abbr)


def price_at(candles: list, ts: float) -> dict | None:
    """Last hourly candle that ended at or before ts with a two-sided book."""
    best = None
    for c in candles:
        if c[0] <= ts and c[1] and c[2] and 0 < c[1] < c[2] < 1:
            best = c
        elif c[0] > ts:
            break
    if not best:
        return None
    return {"bid": best[1], "ask": best[2], "mid": (best[1] + best[2]) / 2, "age_h": (ts - best[0]) / 3600}


def load() -> list[dict]:
    k = json.load(open(os.path.join(ROOT, "data", "research", "kalshi_nba_games.json")))
    games = boxscores.load(ROOT)
    idx = {}
    for g in games:
        d = parse_iso(g["date"]).astimezone(ET).date()
        idx[(d.year, d.month, d.day, code(g["an"]), code(g["hn"]))] = g
    out = []
    for ev, row in k.items():
        ymd = key_date(ev.split("-", 1)[1])
        teams = ev.split("-", 1)[1][7:]
        g = None
        for m in row["markets"]:
            t = m["team"]
            if teams.endswith(t):
                g = idx.get((*ymd, teams[: -len(t)], t))
        if not g:
            continue
        home = [m for m in row["markets"] if m["team"] == code(g["hn"])]
        if not home or not home[0]["candles"]:
            continue
        hm = home[0]
        start = parse_iso(g["date"]).timestamp()
        cs = sorted(hm["candles"])
        r = {"id": g["id"], "event": ev, "date": g["date"], "season": g["season"], "stype": g["season_type"],
             "h": g["h"], "a": g["a"], "hn": code(g["hn"]), "an": code(g["an"]),
             "home_win": 1 if g["hs"] > g["as"] else 0, "margin": g["hs"] - g["as"], "total": g["hs"] + g["as"],
             "volume": hm.get("volume"), "line": g.get("line")}
        for key, h in OFFSETS.items():
            r[key] = price_at(cs, start - h * 3600)
        first = next((c for c in cs if c[1] and c[2] and 0 < c[1] < c[2] < 1), None)
        r["open"] = None if not first else {"mid": (first[1] + first[2]) / 2, "hours_before": (start - first[0]) / 3600}
        out.append(r)
    return sorted(out, key=lambda r: r["date"])


if __name__ == "__main__":
    rows = load()
    print(len(rows), sum(1 for r in rows if r["t2"]))
    print(rows[0])
