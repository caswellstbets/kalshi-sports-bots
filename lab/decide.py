"""Shared pick rules for the three lab models, so they differ only in how they forecast.

Every model hands over a forecast (home-win probability, and where it has them, an expected
margin and total with their spread). The code prices every Kalshi contract in the game, applies
the same market-quality rules as the current bots, and takes the single best contract or none.

Confidence and size (the same for all three models):
  Edge = the model's bet probability minus the price paid per contract including Kalshi's fee.
  High  edge of 8 points or more   stake 1/8 Kelly, at most 2 units
  Mid   edge of 5 to 8 points      stake 1/8 Kelly, at most 1 unit
  Low   edge of 3 to 5 points      stake 1/8 Kelly, at most 0.5 units
  Under 3 points: no pick.
Kelly grows with the edge and with how cheap the contract is, so a bigger, cleaner edge gets a
bigger stake; the tier caps stop one confident forecast from carrying the week."""
from __future__ import annotations

import math

from core import pricing
from core.engine import side_price
from core.kalshi import mid
from core.util import norm_cdf

TIERS = [("High", 0.08, 2.0), ("Mid", 0.05, 1.0), ("Low", 0.03, 0.5)]
MIN_EDGE = TIERS[-1][1]
KELLY = 0.125
BANKROLL, UNIT = 1000.0, 10.0
PRICE_BAND = {"ml": (0.15, 0.85), "spread": (0.35, 0.65), "total": (0.35, 0.65)}
MAX_SPREAD = 0.08
MIN_SIZE = 10


def logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def toward(p_own: float, p_mkt: float, w: float) -> float:
    """Pull a probability toward the market in log-odds: w=1 keeps it, w=0 returns the market."""
    return 1 / (1 + math.exp(-(logit(p_mkt) + w * (logit(p_own) - logit(p_mkt)))))


def p_yes(m: dict, mtype: str, home_code: str, fc: dict) -> float | None:
    """Model probability that market m resolves YES."""
    if mtype == "ml":
        if fc.get("p_home") is None:
            return None
        return fc["p_home"] if m["team_code"] == home_code else 1 - fc["p_home"]
    if mtype == "total":
        if fc.get("total") is None:
            return None
        return 1 - norm_cdf((float(m["strike"]) - fc["total"]) / fc["sd_total"])
    if fc.get("margin") is None:
        return None
    line = float(m["strike"])
    if m["team_code"] == home_code:
        return 1 - norm_cdf((line - fc["margin"]) / fc["sd_margin"])
    return 1 - norm_cdf((line + fc["margin"]) / fc["sd_margin"])


def tier_for(edge: float) -> tuple[str, float] | None:
    for name, lo, cap in TIERS:
        if edge >= lo - 1e-9:
            return name, cap
    return None


def size(p: float, ask: float, offered: float, cap_units: float) -> dict | None:
    cost1 = ask + pricing.fee(100, ask) / 100
    stake = min(BANKROLL * KELLY * pricing.kelly(p, cost1), cap_units * UNIT)
    n = int(min(stake / cost1, offered))
    if n < 1:
        return None
    fee = pricing.fee(n, ask)
    cost = n * ask + fee
    return {"n": n, "fee": fee, "cost": cost, "edge": p - cost / n}


def contracts(game: dict, fc: dict, w: float, types=("ml", "spread", "total")) -> list[dict]:
    """Every buyable side with the model's bet probability and its edge after the fee."""
    out = []
    for mtype in types:
        for m in game["kg"][mtype]:
            if m["status"] not in ("active", "open"):
                continue
            py = p_yes(m, mtype, game["home_code"], fc)
            pk = mid(m)
            if py is None or pk is None:
                continue
            pb = toward(py, pk, w)
            for side in ("yes", "no"):
                ask, bid, offered = side_price(m, side)
                lo, hi = PRICE_BAND[mtype]
                if not (lo <= ask <= hi) or bid <= 0 or ask - bid > MAX_SPREAD + 1e-9 or offered < MIN_SIZE:
                    continue
                p = pb if side == "yes" else 1 - pb
                cost1 = ask + pricing.fee(100, ask) / 100
                out.append({"m": m, "mtype": mtype, "side": side, "ask": ask, "bid": bid, "offered": offered,
                            "p": p, "p_model": py if side == "yes" else 1 - py,
                            "p_kalshi": pk if side == "yes" else 1 - pk, "edge1": p - cost1})
    return out


def best(game: dict, fc: dict, w: float, types=("ml", "spread", "total")) -> dict | None:
    """The single best contract and its size, or None when nothing clears the minimum edge."""
    pick = None
    for c in contracts(game, fc, w, types):
        t = tier_for(c["edge1"])
        if not t:
            continue
        sz = size(c["p"], c["ask"], c["offered"], t[1])
        if not sz or sz["edge"] < MIN_EDGE:
            continue
        t = tier_for(sz["edge"])
        sz = size(c["p"], c["ask"], c["offered"], t[1]) or sz
        if pick is None or sz["edge"] > pick["sz"]["edge"]:
            pick = {**c, "sz": sz, "tier": t[0]}
    return pick
