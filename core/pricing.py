"""Turning lines and predictions into probabilities, fees and stake sizes."""
from __future__ import annotations

import math

from .util import norm_cdf, norm_inv


def implied(american: int) -> float:
    return 100 / (american + 100) if american > 0 else -american / (-american + 100)


def devig(a: int | None, b: int | None) -> float | None:
    """Fair probability of side A given both American prices (removes the book's cut)."""
    if a is None or b is None:
        return None
    pa, pb = implied(a), implied(b)
    return pa / (pa + pb) if pa + pb > 0 else None


def book_anchors(odds: dict | None, sd_margin: float, sd_total: float) -> dict:
    """Sportsbook line -> implied expected home margin (from the spread and, separately,
    from the moneyline) and implied expected total."""
    out = {"margin_spread": None, "margin_ml": None, "total": None, "p_home_ml": None}
    if not odds:
        return out
    if odds.get("home_spread") is not None:
        p = devig(odds.get("home_spread_odds"), odds.get("away_spread_odds")) or 0.5
        # home covers when margin + spread > 0
        out["margin_spread"] = sd_margin * norm_inv(p) - odds["home_spread"]
    p_ml = devig(odds.get("home_ml"), odds.get("away_ml"))
    if p_ml is not None:
        out["p_home_ml"] = p_ml
        out["margin_ml"] = sd_margin * norm_inv(p_ml)
    if odds.get("total") is not None:
        p = devig(odds.get("over_odds"), odds.get("under_odds")) or 0.5
        out["total"] = odds["total"] + sd_total * norm_inv(p)
    return out


def p_margin_over(mu: float, line: float, sd: float) -> float:
    """P(margin > line)."""
    return norm_cdf((mu - line) / sd)


def fee(contracts: int, price: float) -> float:
    """Kalshi taker fee: 7% of price x (1 - price) per contract, rounded up to the cent."""
    return math.ceil(0.07 * contracts * price * (1 - price) * 100 - 1e-9) / 100


def fee_per_contract(price: float) -> float:
    """Fee for a typical clip, per contract (rounding matters less on larger orders)."""
    return fee(20, price) / 20


def kelly(p: float, cost: float) -> float:
    """Full-Kelly fraction of bankroll for a binary contract bought at `cost`."""
    if cost <= 0 or cost >= 1:
        return 0.0
    return max(0.0, (p - cost) / (1 - cost))
