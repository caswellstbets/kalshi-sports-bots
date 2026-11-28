"""Offline checks for the lab NBA models: pick rules, sizing, and the Scout's guard rails."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lab import decide, pattern, rapm  # noqa: E402
from lab.players import Tracker  # noqa: E402


def market(ticker, team, yes_bid, yes_ask, strike=None, size=500):
    return {"ticker": ticker, "team_code": team, "strike": strike, "status": "active", "yes_bid": yes_bid, "yes_ask": yes_ask,
            "no_bid": round(1 - yes_ask, 2), "no_ask": round(1 - yes_bid, 2), "yes_ask_size": size, "no_ask_size": size}


def game():
    return {"home_code": "BOS", "kg": {"ml": [market("G-BOS", "BOS", 0.60, 0.62), market("G-ORL", "ORL", 0.38, 0.40)],
                                      "spread": [market("S-BOS4", "BOS", 0.48, 0.51, 4.5)],
                                      "total": [market("T-220", None, 0.49, 0.52, 220.5)]}}


def test_no_pick_when_model_agrees_with_price():
    assert decide.best(game(), {"p_home": 0.61}, 1.0, ("ml",)) is None


def test_pick_and_tier_follow_the_edge():
    p = decide.best(game(), {"p_home": 0.72}, 1.0, ("ml",))
    assert p and p["m"]["ticker"] == "G-BOS" and p["side"] == "yes"
    assert p["tier"] == "High" and p["sz"]["edge"] >= 0.08
    assert p["sz"]["cost"] <= 2.0 * decide.UNIT + 1e-9
    low = decide.best(game(), {"p_home": 0.675}, 1.0, ("ml",))
    assert low and low["tier"] == "Low" and low["sz"]["cost"] <= 0.5 * decide.UNIT + 1e-9


def test_trust_pulls_toward_market():
    full = decide.best(game(), {"p_home": 0.72}, 1.0, ("ml",))
    part = decide.best(game(), {"p_home": 0.72}, 0.3, ("ml",))
    assert part is None or part["sz"]["edge"] < full["sz"]["edge"]


def test_spread_and_total_probabilities():
    fc = {"margin": 4.5, "sd_margin": 14.6, "total": 220.5, "sd_total": 19.0}
    g = game()
    assert abs(decide.p_yes(g["kg"]["spread"][0], "spread", "BOS", fc) - 0.5) < 1e-9
    assert abs(decide.p_yes(g["kg"]["total"][0], "total", "BOS", fc) - 0.5) < 1e-9
    away = market("S-ORL4", "ORL", 0.3, 0.32, 4.5)
    assert decide.p_yes(away, "spread", "BOS", fc) < 0.5


def test_pattern_prob_is_identity_with_neutral_params():
    prm = {"intercept": 0.0, "coef": {"x": 1.0, "move_open": 0.0, "move_24": 0.0, "fav": 0.0}}
    f = pattern.features(0.7, 0.6, None)
    assert abs(pattern.prob(f, prm) - 0.7) < 0.01


def test_injured_star_lowers_team_strength():
    tr = Tracker()
    for i in range(10):
        players = []
        for team, base in (("1", 0), ("2", 100)):
            for j in range(8):
                pid = str(base + j)
                players.append({"pid": pid, "team": team, "name": pid, "min": 40.0 if j == 0 else 28.6, "starter": j < 5,
                                "pts": 30 if (j == 0 and team == "1") else 10, "fgm": 4, "fga": 9, "tpm": 1, "tpa": 3, "ftm": 1,
                                "fta": 2, "oreb": 1, "dreb": 3, "ast": 2, "tov": 1, "stl": 1, "blk": 0, "pf": 2, "pm": 0})
        tr.update({"date": f"2026-11-{i + 1:02d}T00:00Z", "h": "1", "a": "2", "hs": 110, "as": 100, "players": players})
    impact = {"0": 6.0}
    full = rapm.team_strength(tr, impact, "1", {})
    hurt = rapm.team_strength(tr, impact, "1", {"0": 1.0})
    assert hurt["strength"] < full["strength"]
    assert abs(sum(hurt["minutes"].values()) - 240) < 1


if __name__ == "__main__":
    n = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            n += 1
    print(f"{n} lab tests passed")
