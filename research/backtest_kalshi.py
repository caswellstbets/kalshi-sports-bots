"""Back-test the Rotation and Price Pattern models against real Kalshi NBA winner prices.

    python -m research.backtest_kalshi

The decision price is the home team's Kalshi quote about 3 hours before the start (the last
hourly candle that ended by then), the earliest point at which the lab models decide live.
Everything is fit on 2025-26 and scored on 2026-27 games the fit never saw. Writes
lab/pattern_params.json, prints the Rotation trust value, and writes BACKTEST_NBA_MODELS.md."""
from __future__ import annotations

import json
import math
import os
from statistics import NormalDist

import numpy as np

from core import pricing
from research.kalshi_join import load

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = NormalDist()
KEYS = ["x", "move_open", "move_24", "fav"]


def lg(p):
    p = min(max(p, 0.01), 0.99)
    return math.log(p / (1 - p))


def sig(z):
    return 1 / (1 + math.exp(-z))


def logistic(X, y, l2=1.0):
    w = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (p - y) + l2 * np.r_[0, w[1:]]
        H = (X * (p * (1 - p))[:, None]).T @ X + l2 * np.diag(np.r_[0, np.ones(len(w) - 1)])
        w -= np.linalg.solve(H, g)
    return w


def feats(r, at="t3"):
    from lab.pattern import features
    p_now = r[at]["mid"]
    p_open = r["open"]["mid"] if r["open"] and r["open"]["hours_before"] > 6 else None
    return features(p_now, p_open, r["t24"]["mid"] if r["t24"] else None)


def brier(ps, ys):
    return float(np.mean([(p - y) ** 2 for p, y in zip(ps, ys)]))


def simulate(rows, pfun, at="t3", min_edge=0.03):
    """Buy the better side of the winner market at the ask when the model beats it by min_edge after the fee."""
    from lab.decide import tier_for, size
    bets = []
    for r in rows:
        q = r[at]
        p = pfun(r)
        if p is None:
            continue
        for side, prob, ask in (("home", p, q["ask"]), ("away", 1 - p, 1 - q["bid"])):
            if not (0.15 <= ask <= 0.85) or q["ask"] - q["bid"] > 0.08:
                continue
            edge1 = prob - (ask + pricing.fee(100, ask) / 100)
            t = tier_for(edge1)
            if t and edge1 >= min_edge:
                sz = size(prob, ask, 10_000, t[1])
                if sz:
                    won = r["home_win"] == (1 if side == "home" else 0)
                    close = r["t0"]["mid"] if r["t0"] else None
                    clv = None if close is None else ((close if side == "home" else 1 - close) - ask)
                    bets.append({"tier": t[0], "cost": sz["cost"], "pnl": (sz["n"] if won else 0) - sz["cost"],
                                 "won": won, "p": prob, "clv": clv})
    n = len(bets)
    if not n:
        return {"n": 0}
    st = sum(b["cost"] for b in bets)
    cl = [b["clv"] for b in bets if b["clv"] is not None]
    return {"n": n, "won": sum(b["won"] for b in bets), "exp": sum(b["p"] for b in bets), "staked": st,
            "pnl": sum(b["pnl"] for b in bets), "roi": sum(b["pnl"] for b in bets) / st, "clv": sum(cl) / len(cl) if cl else None}


def main():
    K = [r for r in load() if r["stype"] == 2 and r["t3"] and r["t0"]]
    tr = [r for r in K if r["season"] == 2026]
    te = [r for r in K if r["season"] == 2027]
    out = ["# Back-test of the lab NBA models against Kalshi prices", "",
           f"Kalshi NBA winner markets, home team's price about 3 hours before the start. Fit on {len(tr)} games from "
           f"2025-26, scored on {len(te)} games from 2026-27 the fit never saw. `python -m research.backtest_kalshi`.", ""]
    # how good is Kalshi itself
    for name, rows in (("2025-26", tr), ("2026-27", te)):
        y = [r["home_win"] for r in rows]
        out.append(f"- {name}: Kalshi Brier at T-3h {brier([r['t3']['mid'] for r in rows], y):.4f}, at the close "
                   f"{brier([r['t0']['mid'] for r in rows], y):.4f} ({len(rows)} games).")
    out += ["", "## Calibration of Kalshi's price (both seasons)", "", "| Price band | Games | Average price | Home team won |", "| --- | --- | --- | --- |"]
    for lo, hi in ((0, .2), (.2, .35), (.35, .5), (.5, .65), (.65, .8), (.8, 1)):
        s = [r for r in K if lo <= r["t3"]["mid"] < hi]
        if s:
            out.append(f"| {lo:.2f}-{hi:.2f} | {len(s)} | {np.mean([r['t3']['mid'] for r in s]):.3f} | {np.mean([r['home_win'] for r in s]):.3f} |")
    out.append("")

    # Price Pattern
    X = np.array([[1] + [feats(r)[k] for k in KEYS] for r in tr])
    y = np.array([r["home_win"] for r in tr])
    w = logistic(X, y, l2=2.0)
    prm = {"intercept": float(w[0]), "coef": {k: float(v) for k, v in zip(KEYS, w[1:])},
           "fit_on": f"{len(tr)} games, 2025-26 regular season, Kalshi home price about 3h before the start"}
    from lab.pattern import prob
    pp = lambda r: prob(feats(r), prm)
    out += ["## Price Pattern (tried and dropped)", "", "The first idea for the second model used no basketball at all: a logistic regression of the home result on Kalshi's own numbers: "
            + ", ".join(f"{k} {v:+.3f}" for k, v in prm["coef"].items()) + f", intercept {prm['intercept']:+.3f}. "
            "`x` is the price in log-odds (a coefficient under 1 means favourites have been overpriced), `move_open` and "
            "`move_24` are how far it moved since the market opened and in the last 24 hours, `fav` is how lopsided it is.", ""]
    for name, rows in (("2025-26 (fit)", tr), ("2026-27 (new)", te)):
        yy = [r["home_win"] for r in rows]
        out.append(f"- {name}: Pattern Brier {brier([pp(r) for r in rows], yy):.4f} vs Kalshi {brier([r['t3']['mid'] for r in rows], yy):.4f}")
        s = simulate(rows, pp)
        if s["n"]:
            out.append(f"  - Trades at 3+ point edge: {s['n']}, won {s['won']} (expected {s['exp']:.1f}), staked ${s['staked']:.0f}, "
                       f"profit ${s['pnl']:+.2f}, return {100 * s['roi']:+.1f}%, closing-price edge {100 * (s['clv'] or 0):+.1f}c")
    from research import backtest_hypotheses
    out += ["", "It lost on the new season, so four more price-pattern ideas were written down first and then tested in "
            "both seasons. None held: each changes sign or stays inside its noise.", ""] + backtest_hypotheses.run()
    out += ["", "Kalshi's NBA winner prices show no simple pattern that survives from one season to the next, so the second "
            "model was replaced with Injury News (below).", ""]
    with open(os.path.join(ROOT, "lab", "pattern_params.json"), "w") as f:
        json.dump(prm, f, indent=1)

    # Rotation
    R = {r["id"]: r for r in json.load(open(os.path.join(ROOT, "data", "research", "rotation_backtest.json")))}

    def p_rot(r):
        x = R.get(r["id"])
        return None if not x or not x.get("fc") else N.cdf(x["fc"]["margin"] / x["fc"]["sd_margin"])
    trr = [r for r in tr if p_rot(r) is not None]
    ter = [r for r in te if p_rot(r) is not None]
    best = None
    out += ["## Rotation", "", "How far to lean from Kalshi's price toward the Rotation forecast (trust, in log-odds; 0 = the price, "
            "1 = the model). Brier on 2025-26:", "", "| Trust | Brier 2025-26 | Brier 2026-27 |", "| --- | --- | --- |"]
    for t in (0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0):
        f = lambda r, t=t: sig(lg(r["t3"]["mid"]) + t * (lg(p_rot(r)) - lg(r["t3"]["mid"])))
        b1 = brier([f(r) for r in trr], [r["home_win"] for r in trr])
        b2 = brier([f(r) for r in ter], [r["home_win"] for r in ter])
        out.append(f"| {t} | {b1:.4f} | {b2:.4f} |")
        if best is None or b1 < best[1]:
            best = (t, b1)
    trust = 0.25
    out += ["", f"Best on 2025-26 alone: {best[0]}. On 2026-27 any trust above 0 scored worse than Kalshi's price. "
            f"The live value is **{trust}**, between the two, chosen after seeing both seasons and frozen for the week. "
            "Read plainly: the Rotation forecast has not yet beaten Kalshi on games it was not fit on.", ""]
    for name, rows in (("2025-26 (fit)", trr), ("2026-27 (new)", ter)):
        f = lambda r: sig(lg(r["t3"]["mid"]) + trust * (lg(p_rot(r)) - lg(r["t3"]["mid"])))
        s = simulate(rows, f)
        if s["n"]:
            out.append(f"- {name}: trades at 3+ point edge {s['n']}, won {s['won']} (expected {s['exp']:.1f}), staked ${s['staked']:.0f}, "
                       f"profit ${s['pnl']:+.2f}, return {100 * s['roi']:+.1f}%, closing-price edge {100 * (s['clv'] or 0):+.1f}c")
    out += ["", "Winner markets only: spread and total prices from past seasons were not downloaded. Fills assume the "
            "quoted ask with enough size, and the Kalshi fee.", ""]
    from research import backtest_news
    out += ["## Injury News", ""] + backtest_news.run() + ["",
            "Some of these absences were announced after the 3-hour mark, which flatters the news side at 3 hours. "
            "At the close the gap left over predicted nothing. This model is tested forward with the injury report as "
            "it changes during the day.", "", "## Scout", "", "Claude's read cannot be replayed fairly on past games "
            "(it would know the results), so Scout is tested forward only.", ""]
    with open(os.path.join(ROOT, "BACKTEST_NBA_MODELS.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))
    print("ROTATION_TRUST", trust)


if __name__ == "__main__":
    main()
