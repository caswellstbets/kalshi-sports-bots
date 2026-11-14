"""Walk-forward back-test of the STATS forecast only.

    python backtest.py            all three sports, writes BACKTEST.md
    python backtest.py --only nfl

For every finished game this season, the ratings are refit using only games that
started before that game's day, the stats forecast is made, and it is compared
with the result and with the sportsbook's closing line (ESPN, DraftKings).

What this does NOT show:
  - Anything about the AI forecast. That is only tested forward.
  - Trading profit on Kalshi. No historical Kalshi quotes are used.
  - A clean out-of-sample result. The model settings in bots/ were tuned on this
    same season, so these numbers flatter the stats model somewhat.
The closing line is used as the yardstick, never as an input."""
from __future__ import annotations

import argparse
import math
import os
from collections import defaultdict
from datetime import timedelta

from bots import cfb, nba, nfl
from core import engine, espn, pricing, ratings
from core.util import ET, get_json, iso, now_utc, parse_iso, read_json, write_json

ROOT = os.path.dirname(os.path.abspath(__file__))
LEAGUE = {"cfb": "football/leagues/college-football", "nfl": "football/leagues/nfl", "nba": "basketball/leagues/nba"}


def closing_line(sport: str, gid: str, cache: dict) -> dict | None:
    if gid in cache:
        return cache[gid]
    out = None
    try:
        d = get_json(f"https://sports.core.api.espn.com/v2/sports/{LEAGUE[sport]}/events/{gid}/competitions/{gid}/odds",
                     min_gap=0.15, tries=2)
        for it in d.get("items", []):
            if it.get("spread") is not None and it.get("overUnder") is not None:
                out = {"home_margin": -float(it["spread"]), "total": float(it["overUnder"]),
                       "provider": (it.get("provider") or {}).get("name")}
                break
    except RuntimeError:
        pass
    cache[gid] = out
    return out


def walk_forward(cfg, results: list[dict]) -> list[dict]:
    by_day = defaultdict(list)
    for r in results:
        if r.get("hs") is not None and r.get("as") is not None:
            by_day[parse_iso(r["date"]).astimezone(ET).date()].append(r)
    out = []
    for day in sorted(by_day):
        games = by_day[day]
        as_of = min(parse_iso(g["date"]) for g in games) - timedelta(minutes=1)
        kw = dict(hfa=cfg.hfa, ridge=cfg.ridge, margin_cap=cfg.margin_cap, min_games=cfg.min_games, as_of=as_of)
        rt = ratings.fit(results, half_life_days=cfg.half_life_days, **kw)
        rt_form = ratings.fit(results, half_life_days=cfg.form_half_life_days, **kw)
        if not rt["n"]:
            continue
        for r in games:
            g = {"id": r["id"], "start": r["date"], "neutral": r.get("neutral", False),
                 "home": {"id": r["h"], "abbr": r.get("hn", "")}, "away": {"id": r["a"], "abbr": r.get("an", "")}}
            st = engine.stats_forecast(cfg, g, rt, rt_form)
            if st["margin"] is None:
                continue
            out.append({"id": r["id"], "day": str(day), "stats_margin": st["margin"], "stats_total": st["total"],
                        "margin": r["hs"] - r["as"], "total": r["hs"] + r["as"]})
    return out


def summarize(cfg, rows: list[dict]) -> dict:
    n = len(rows)

    def mae(a, b):
        return sum(abs(r[a] - r[b]) for r in rows) / n

    def brier(key):
        return sum((pricing.p_margin_over(r[key], 0, cfg.sd_margin) - (1 if r["margin"] > 0 else 0)) ** 2
                   for r in rows if r["margin"] != 0) / max(1, sum(r["margin"] != 0 for r in rows))
    # Best single weight w on the stats forecast in  line + w * (stats - line), by least squares.
    num = sum((r["stats_margin"] - r["line_margin"]) * (r["margin"] - r["line_margin"]) for r in rows)
    den = sum((r["stats_margin"] - r["line_margin"]) ** 2 for r in rows)
    numt = sum((r["stats_total"] - r["line_total"]) * (r["total"] - r["line_total"]) for r in rows)
    dent = sum((r["stats_total"] - r["line_total"]) ** 2 for r in rows)
    ats = {}
    for gap in (0, 3, 6):
        sub = [r for r in rows if abs(r["stats_margin"] - r["line_margin"]) >= gap and r["margin"] != r["line_margin"]]
        wins = sum((r["stats_margin"] > r["line_margin"]) == (r["margin"] > r["line_margin"]) for r in sub)
        ats[gap] = (wins, len(sub))
    ou = {}
    for gap in (0, 3, 6):
        sub = [r for r in rows if abs(r["stats_total"] - r["line_total"]) >= gap and r["total"] != r["line_total"]]
        wins = sum((r["stats_total"] > r["line_total"]) == (r["total"] > r["line_total"]) for r in sub)
        ou[gap] = (wins, len(sub))
    return {"n": n, "mae_stats": mae("stats_margin", "margin"), "mae_line": mae("line_margin", "margin"),
            "tmae_stats": mae("stats_total", "total"), "tmae_line": mae("line_total", "total"),
            "brier_stats": brier("stats_margin"), "brier_line": brier("line_margin"),
            "w_margin": num / den if den else None, "w_total": numt / dent if dent else None, "ats": ats, "ou": ou}


def rate(w, n):
    if not n:
        return "n/a"
    p = w / n
    return f"{w}-{n - w} ({p * 100:.1f}%, coin-flip range ±{196 * math.sqrt(0.25 / n):.0f})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["nba", "nfl", "cfb"])
    a = ap.parse_args()
    os.makedirs(os.path.join(ROOT, "data", "backtest"), exist_ok=True)
    L = ["# Back-test of the stats forecast", "",
         f"Generated {iso(now_utc())} by `python backtest.py`. Walk-forward: each game is forecast from ratings fit "
         "only on games that started before that day, then compared with the final score and with the sportsbook "
         "closing line (ESPN, DraftKings).", "",
         "**Read this first.**", "",
         "- This tests the numbers-only forecast. It says nothing about the AI forecast, which is tested forward.",
         "- It is not a Kalshi trading back-test. No historical Kalshi prices are used.",
         "- The model settings were tuned on this same season, so the stats model looks a little better here than it would on new data.",
         "- The closing line is the yardstick. A real bet is placed hours earlier at a different price.",
         "- 52.4% is the break-even rate against a standard sportsbook spread. The ± is the 95% range for a coin flip at that sample size.", ""]
    for mod in (nba, nfl, cfb):
        cfg = mod.CONFIG
        if a.only and cfg.name != a.only:
            continue
        results = espn.season_results(cfg.name, os.path.join(ROOT, "data", cfg.name, "results_cache.json"),
                                      season_start=cfg.season_start, groups=cfg.espn_groups, save=False)
        rows = walk_forward(cfg, results)
        if cfg.name == "cfb":  # closing lines are fetched for top-division games only
            cache_r = read_json(os.path.join(ROOT, "data", "cfb", "results_cache.json"), {})
            fbs = {g["id"] for k, v in cache_r.items() if k.endswith("g80") for g in v["games"]}
            rows = [r for r in rows if r["id"] in fbs]
        lpath = os.path.join(ROOT, "data", "backtest", f"lines_{cfg.name}.json")
        cache = read_json(lpath, {})
        for r in rows:
            ln = closing_line(cfg.name, r["id"], cache)
            if ln:
                r["line_margin"], r["line_total"] = ln["home_margin"], ln["total"]
        write_json(lpath, cache)
        have = [r for r in rows if "line_margin" in r]
        write_json(os.path.join(ROOT, "data", "backtest", f"forecasts_{cfg.name}.json"), rows)
        L += [f"## {cfg.title}", ""]
        if len(have) < 20:
            L += [f"Only {len(have)} of {len(rows)} forecast games have a closing line. Not enough to report.", ""]
            continue
        s = summarize(cfg, have)
        L += [f"{s['n']} games with both a stats forecast and a closing line ({len(rows)} forecast in all).", "",
              "| Measure | Stats forecast | Closing line |", "| --- | --- | --- |",
              f"| Average miss on the margin, points | {s['mae_stats']:.2f} | {s['mae_line']:.2f} |",
              f"| Average miss on the total, points | {s['tmae_stats']:.2f} | {s['tmae_line']:.2f} |",
              f"| Winner probability, Brier score (lower is better) | {s['brier_stats']:.4f} | {s['brier_line']:.4f} |", "",
              "When the stats forecast disagreed with the closing line, how often was its side right?", "",
              "| Disagreement of at least | Against the spread | Over/under |", "| --- | --- | --- |"]
        for gap in (0, 3, 6):
            L.append(f"| {gap} points | {rate(*s['ats'][gap])} | {rate(*s['ou'][gap])} |")
        L += ["", f"Best single weight on the stats forecast when mixed with the closing line: "
              f"**{s['w_margin']:.2f}** for the margin and **{s['w_total']:.2f}** for the total "
              "(0 means the line alone is best, 1 means the stats alone). This is fit on the same games it is "
              "reported on, so it is an upper estimate.", ""]
        print(cfg.name, s)
    if not a.only:
        with open(os.path.join(ROOT, "BACKTEST.md"), "w") as f:
            f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
