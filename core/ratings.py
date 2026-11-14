"""Power ratings: an offense and a defense number for every team, fit by ridge
regression on this season's scores with opponent, home field and recency handled
in one solve."""
from __future__ import annotations

from collections import Counter

import numpy as np

from .util import now_utc, parse_iso

POOL = "POOL"  # stand-in for teams with too few games to rate (lower-division opponents)


def fit(results: list[dict], *, hfa: float, ridge: float, half_life_days: float,
        margin_cap: float | None = None, min_games: int = 3, as_of=None) -> dict:
    """Returns {"mu": league points per team-game, "off": {...}, "def": {...},
    "games": {...}, "last": {team: last game time}, "n": games used}.

    Model:  home_pts = mu + off[home] - def[away] + hfa/2
            away_pts = mu + off[away] - def[home] - hfa/2
    (positive def = allows fewer points). ridge is the number of league-average
    games each rating is shrunk toward zero with."""
    as_of = as_of or now_utc()
    games = [g for g in results if g.get("hs") is not None and g.get("as") is not None
             and parse_iso(g["date"]) < as_of]
    counts = Counter()
    for g in games:
        counts[g["h"]] += 1
        counts[g["a"]] += 1

    def key(t):
        return t if counts[t] >= min_games else POOL

    teams = sorted({key(g["h"]) for g in games} | {key(g["a"]) for g in games})
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    if not games or n < 2:
        return {"mu": 0.0, "off": {}, "def": {}, "games": {}, "last": {}, "n": 0, "names": {}}

    rows, ys, ws = [], [], []
    last: dict[str, object] = {}
    names: dict[str, str] = {}
    for g in games:
        when = parse_iso(g["date"])
        w = 0.5 ** ((as_of - when).total_seconds() / 86400 / half_life_days)
        hs, as_ = float(g["hs"]), float(g["as"])
        if margin_cap is not None and abs(hs - as_) > margin_cap:
            # blowouts say little beyond "much better": count half of the excess
            excess = (abs(hs - as_) - margin_cap) / 2
            if hs > as_:
                hs, as_ = hs - excess / 2, as_ + excess / 2
            else:
                hs, as_ = hs + excess / 2, as_ - excess / 2
        h, a = key(g["h"]), key(g["a"])
        bump = 0.0 if g.get("neutral") else hfa / 2
        for off_t, def_t, pts in ((h, a, hs - bump), (a, h, as_ + bump)):
            r = np.zeros(2 * n)
            r[idx[off_t]] = 1.0
            r[n + idx[def_t]] = -1.0
            rows.append(r)
            ys.append(pts)
            ws.append(w)
        for t in (g["h"], g["a"]):
            if t not in last or when > last[t]:
                last[t] = when
        names[g["h"]], names[g["a"]] = g.get("hn", ""), g.get("an", "")

    X, y, w = np.array(rows), np.array(ys), np.array(ws)
    mu = float(np.average(y, weights=w))
    sw = np.sqrt(w)[:, None]
    A = np.vstack([X * sw, np.sqrt(ridge) * np.eye(2 * n)])
    b = np.concatenate([(y - mu) * sw[:, 0], np.zeros(2 * n)])
    coef, *_ = np.linalg.lstsq(A, b, rcond=None)
    return {
        "mu": mu,
        "off": {t: float(coef[idx[t]]) for t in teams},
        "def": {t: float(coef[n + idx[t]]) for t in teams},
        "games": dict(counts),
        "last": last,
        "n": len(games),
        "names": names,
    }


def predict(r: dict, home: str, away: str, *, hfa: float, neutral: bool = False) -> tuple[float, float] | None:
    """(expected home margin, expected total), or None if nothing is known."""
    if not r["off"]:
        return None

    def k(t):
        return t if t in r["off"] else POOL

    h, a = k(home), k(away)
    if h not in r["off"] or a not in r["off"]:
        return None
    hp = r["mu"] + r["off"][h] - r["def"][a]
    ap = r["mu"] + r["off"][a] - r["def"][h]
    return hp - ap + (0.0 if neutral else hfa), hp + ap


def net(r: dict, team: str) -> float | None:
    t = team if team in r["off"] else POOL
    return None if t not in r["off"] else r["off"][t] + r["def"][t]
