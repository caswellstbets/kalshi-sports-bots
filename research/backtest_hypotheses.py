"""Pre-stated price-pattern ideas for Kalshi NBA winner prices, each fit on 2025-26 and again on
2026-27 with the Kalshi price as the starting point. An idea that holds would show the same sign
in both seasons and clear about twice its standard error."""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from lab import boxscores
from research.kalshi_join import load

POP = {"LAL", "GSW", "NYK", "BOS"}
IDEAS = {"form": "a team's last 5 games beyond its season average (market overreacts to streaks)",
         "last": "the margin of each team's last game (market overreacts to one result)",
         "popular": "Lakers, Warriors, Knicks or Celtics (popular teams overpriced)",
         "move": "price move over the last 24 hours (momentum or reversal)"}


def lg(p):
    p = min(max(p, 0.01), 0.99)
    return math.log(p / (1 - p))


def run() -> list[str]:
    games = [g for g in boxscores.load(".") if g["season_type"] == 2]
    hist, form = defaultdict(list), {}
    for g in games:
        for t, m in ((g["h"], g["hs"] - g["as"]), (g["a"], g["as"] - g["hs"])):
            h = [x for x in hist[t] if x[0] == g["season"]]
            if len(h) >= 6:
                form[(g["id"], t)] = (np.mean([x[1] for x in h[-5:]]) - np.mean([x[1] for x in h]), h[-1][1])
            hist[t].append((g["season"], m))
    K = [r for r in load() if r["stype"] == 2 and r["t3"] and r["t0"]]

    def feats(r):
        fh, fa = form.get((r["id"], r["h"])), form.get((r["id"], r["a"]))
        if not fh or not fa:
            return None
        p3 = r["t3"]["mid"]
        p24 = r["t24"]["mid"] if r["t24"] else p3
        return {"off": lg(p3), "form": (fh[0] - fa[0]) / 10, "last": (fh[1] - fa[1]) / 20,
                "popular": (r["hn"] in POP) - (r["an"] in POP), "move": lg(p3) - lg(p24)}
    out = ["| Idea | 2025-26 | 2026-27 |", "| --- | --- | --- |"]
    for key, text in IDEAS.items():
        cells = []
        for season in (2026, 2027):
            rows = [(feats(r), r["home_win"]) for r in K if r["season"] == season and feats(r)]
            off = np.array([f["off"] for f, _ in rows])
            x = np.array([f[key] for f, _ in rows])
            y = np.array([v for _, v in rows])
            w = np.zeros(2)
            X = np.c_[np.ones(len(x)), x]
            for _ in range(30):
                p = 1 / (1 + np.exp(-(off + X @ w)))
                H = (X * (p * (1 - p))[:, None]).T @ X + np.diag([1e-6, 1.0])
                w -= np.linalg.solve(H, X.T @ (p - y) + np.r_[0, w[1]])
            se = math.sqrt(np.linalg.inv(H)[1, 1])
            cells.append(f"{w[1]:+.2f} (standard error {se:.2f}, {len(rows)} games)")
        out.append(f"| {text} | {cells[0]} | {cells[1]} |")
    return out


if __name__ == "__main__":
    print("\n".join(run()))
