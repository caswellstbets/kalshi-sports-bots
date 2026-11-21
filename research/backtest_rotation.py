"""Walk-forward back-test of the Rotation model, and the fit of its frozen coefficients.

    python -m research.backtest_rotation

Each day, player impacts are refit on games before that day; the forecast uses the players who
played in each team's previous game as the expected rotation (no pre-game news, so this is a
conservative stand-in for the injury report used live). Coefficients are fit on 2025-26 regular
season games from Nov 20 on, then frozen and scored on 2026-27 games, which the fit never saw.
Writes lab/rotation_params.json and data/research/rotation_backtest.json."""
from __future__ import annotations

import json
import os
from collections import defaultdict

import numpy as np

from lab import boxscores, rapm, rotation
from lab.players import Tracker

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def walk(games: list[dict]) -> list[dict]:
    by_day = defaultdict(list)
    for g in games:
        by_day[g["date"][:10]].append(g)
    tr, seen, out = Tracker(), [], []
    impact: dict = {}
    for di, day in enumerate(sorted(by_day)):
        if len(seen) >= 50:
            impact = rapm.fit(seen, tr, now_index=di)
        for g in by_day[day]:
            row = {"id": g["id"], "date": g["date"], "season": g["season"], "stype": g["season_type"], "h": g["h"], "a": g["a"],
                   "margin": g["hs"] - g["as"], "total": g["hs"] + g["as"], "line": g.get("line")}
            if impact:
                outs = {}
                for t in (g["h"], g["a"]):
                    last = tr.played_last.get(t)
                    outs[t] = {} if last is None else {p: 1.0 for p in tr.roster(t) if p not in last}
                f = rotation.features(tr, impact, g["h"], g["a"], g["date"], outs[g["h"]], outs[g["a"]])
                if f:
                    row["f"] = {k: v for k, v in f.items() if not k.startswith("minutes")}
            out.append(row)
        for g in by_day[day]:
            tr.update(g)
            seen.append(g)
    return out


def fit(rows: list[dict]) -> dict:
    tr = [r for r in rows if r.get("f") and r["season"] == 2026 and r["stype"] == 2 and r["date"] >= "2025-11-20"]
    A = np.array([[1, r["f"]["strength_diff"], r["f"]["b2b_diff"]] for r in tr])
    y = np.array([r["margin"] for r in tr])
    cm, *_ = np.linalg.lstsq(A, y, rcond=None)
    B = np.array([[1, r["f"]["scoring"], r["f"]["pace"], r["f"]["b2b_n"]] for r in tr])
    z = np.array([r["total"] for r in tr])
    ct, *_ = np.linalg.lstsq(B, z, rcond=None)
    return {"fit_on": f"{len(tr)} games, 2025-26 regular season from Nov 20",
            "margin": {"intercept": float(cm[0]), "strength": float(cm[1]), "b2b": float(cm[2]), "sd": float(np.std(y - A @ cm))},
            "total": {"intercept": float(ct[0]), "scoring": float(ct[1]), "pace": float(ct[2]), "b2b": float(ct[3]),
                      "sd": float(np.std(z - B @ ct))}}


def main() -> None:
    games = [g for g in boxscores.load(ROOT) if g["players"] and g["season_type"] in (2, 3)]
    rows = walk(games)
    prm = fit(rows)
    with open(rotation.PARAMS_PATH, "w") as f:
        json.dump(prm, f, indent=1)
    for r in rows:
        if r.get("f"):
            r["fc"] = rotation.forecast(r["f"], prm)
    with open(os.path.join(ROOT, "data", "research", "rotation_backtest.json"), "w") as f:
        json.dump(rows, f, separators=(",", ":"))
    te = [r for r in rows if r.get("fc") and r["season"] == 2027]
    tl = [r for r in te if r["line"] and r["line"].get("home_spread") is not None and r["line"].get("total")]
    mae = lambda xs: sum(xs) / len(xs)
    print(json.dumps(prm, indent=1))
    print("2026-27 games:", len(te), "with a line:", len(tl))
    print("margin miss: model %.2f  line %.2f" % (mae([abs(r["fc"]["margin"] - r["margin"]) for r in tl]),
                                                 mae([abs(-r["line"]["home_spread"] - r["margin"]) for r in tl])))
    print("total miss:  model %.2f  line %.2f" % (mae([abs(r["fc"]["total"] - r["total"]) for r in tl]),
                                                 mae([abs(r["line"]["total"] - r["total"]) for r in tl])))


if __name__ == "__main__":
    main()
