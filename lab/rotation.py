"""Model A, "Rotation": a numbers-only NBA model built from players, not teams.

Team strength tonight = the expected rotation's minutes x each player's impact (lab/rapm.py),
with injured players' minutes removed using ESPN's injury report and handed to teammates. Because
it rates players, roster changes and injuries flow straight into the forecast, and last season's
games still count (at a lower weight) early in this season. The total comes from each team's
recent scoring for and against and its pace. It never sees a price or a sportsbook line.

The coefficients in rotation_params.json were fit on the 2025-26 season only and are frozen for
the evaluation window (research/backtest_rotation.py)."""
from __future__ import annotations

import json
import os

from . import rapm
from .players import Tracker, rest_days

PARAMS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rotation_params.json")


def params() -> dict:
    with open(PARAMS_PATH) as f:
        return json.load(f)


def features(tracker: Tracker, impact: dict, home: str, away: str, start: str, out_h: dict, out_a: dict) -> dict | None:
    ph, pa = tracker.pace_of(home), tracker.pace_of(away)
    if not ph or not pa or ph["w"] < 2 or pa["w"] < 2:
        return None
    sh = rapm.team_strength(tracker, impact, home, out_h)
    sa = rapm.team_strength(tracker, impact, away, out_a)
    rh, ra = rest_days(tracker.last_game.get(home), start), rest_days(tracker.last_game.get(away), start)
    b2b_h = 1 if rh is not None and rh < 1.6 else 0
    b2b_a = 1 if ra is not None and ra < 1.6 else 0
    return {"strength_diff": sh["strength"] - sa["strength"], "b2b_diff": b2b_h - b2b_a, "b2b_n": b2b_h + b2b_a,
            "scoring": (ph["pts"] + pa["opp"] + pa["pts"] + ph["opp"]) / 2, "pace": (ph["poss"] + pa["poss"]) / 2,
            "lost_h": sh["full_strength"] - sh["strength"], "lost_a": sa["full_strength"] - sa["strength"],
            "rest_h": rh, "rest_a": ra, "minutes_h": sh["minutes"], "minutes_a": sa["minutes"]}


def forecast(f: dict, prm: dict | None = None) -> dict:
    prm = prm or params()
    m, t = prm["margin"], prm["total"]
    margin = m["intercept"] + m["strength"] * f["strength_diff"] + m["b2b"] * f["b2b_diff"]
    total = t["intercept"] + t["scoring"] * f["scoring"] + t["pace"] * f["pace"] + t["b2b"] * f["b2b_n"]
    return {"margin": margin, "total": total, "sd_margin": m["sd"], "sd_total": t["sd"]}
