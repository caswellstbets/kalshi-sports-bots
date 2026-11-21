"""Live forecasts for Model A, Rotation (see lab/rotation.py for the model itself)."""
from __future__ import annotations

from core.util import norm_cdf

from . import boxscores, rapm, rotation, slate
from .players import Tracker

# How far the bet probability moves from Kalshi's price toward the Rotation forecast, in log-odds.
# Set from the Kalshi back-test on 2025-26 (research/backtest_kalshi.py) and frozen for the week.
TRUST = 0.25
# Winner and spread only: the Rotation total is a plain pace-and-scoring number that ignores who
# plays, so it is graded but never bet.
TYPES = ("ml", "spread")


def build(root: str):
    games = [g for g in boxscores.load(root) if g["players"] and g["season_type"] in (2, 3)]
    tr = Tracker()
    for g in games:
        tr.update(g)
    return tr, rapm.fit(games, tr)


def forecasts(todo: list[dict], tr, impact: dict, inj: dict):
    prm = rotation.params()
    for g in todo:
        h, a = g["g"]["home"]["id"], g["g"]["away"]["id"]
        outs, notes = {}, []
        for t in (h, a):
            outs[t] = {}
            for i in inj.get(t, []):
                if i["pid"] and i["p_out"] > 0:
                    outs[t][i["pid"]] = i["p_out"]
                    m = tr.exp_minutes(i["pid"])
                    if m >= 12:
                        notes.append(f"{i['name']} ({i['status']}, {i['p_out']:.0%} likely out, usually {m:.0f} min)")
        f = rotation.features(tr, impact, h, a, g["start"], outs[h], outs[a])
        if not f:
            continue
        fc = rotation.forecast(f, prm)
        fc["p_home"] = norm_cdf(fc["margin"] / fc["sd_margin"])
        home, away = slate.full_name(g["g"]["home"]), slate.full_name(g["g"]["away"])
        lead = home if fc["margin"] >= 0 else away
        why = (f"{lead} by {abs(fc['margin']):.1f}, total {fc['total']:.1f}. Player strength {home} {f['strength_diff']:+.1f} "
               f"after injuries (lost to injury: {home} {f['lost_h']:.1f}, {away} {f['lost_a']:.1f}).")
        if f["b2b_diff"]:
            why += f" {home if f['b2b_diff'] > 0 else away} on the second night of a back-to-back."
        if notes:
            why += " Out or doubtful: " + "; ".join(notes[:4]) + "."
        yield g, fc, why
