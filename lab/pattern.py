"""Model B, "Price Pattern": no basketball at all. It only asks how Kalshi's own NBA winner prices
have been wrong in the past, and bets when tonight's price fits a pattern that has lost money for
the side the crowd took.

Inputs, all from Kalshi: the home team's price now, its first two-sided price after the market
opened, and its price 24 hours before the start. A logistic regression fit on last season's
settled games turns those into a home-win probability (pattern_params.json, fit by
research/backtest_pattern.py, frozen for the week). It trades winner markets only."""
from __future__ import annotations

import json
import math
import os

from core.util import get_json, parse_iso

from . import slate

PARAMS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pattern_params.json")
KBASE = "https://api.elections.kalshi.com/trade-api/v2"


def logit(p: float) -> float:
    p = min(max(p, 0.01), 0.99)
    return math.log(p / (1 - p))


def params() -> dict:
    with open(PARAMS_PATH) as f:
        return json.load(f)


def features(p_now: float, p_open: float | None, p_24: float | None) -> dict:
    x = logit(p_now)
    return {"x": x, "move_open": 0.0 if p_open is None else x - logit(p_open),
            "move_24": 0.0 if p_24 is None else x - logit(p_24), "fav": abs(x)}


def prob(f: dict, prm: dict) -> float:
    z = prm["intercept"] + sum(prm["coef"][k] * f[k] for k in prm["coef"])
    return 1 / (1 + math.exp(-z))


def history(tickers: list[str], start_ts: int, end_ts: int) -> dict[str, list]:
    """Hourly [end_ts, bid, ask] for several open markets in one call each 10 tickers."""
    out = {}
    for i in range(0, len(tickers), 10):
        d = get_json(f"{KBASE}/markets/candlesticks", {"market_tickers": ",".join(tickers[i:i + 10]),
                                                       "start_ts": start_ts, "end_ts": end_ts, "period_interval": 60}, min_gap=0.4)
        for x in d.get("markets", []):
            rows = []
            for c in x.get("candlesticks", []):
                b, a = (c.get("yes_bid") or {}).get("close_dollars"), (c.get("yes_ask") or {}).get("close_dollars")
                if b not in (None, "") and a not in (None, ""):
                    rows.append([c["end_period_ts"], float(b), float(a)])
            out[x["market_ticker"]] = rows
    return out


def first_two_sided(rows: list) -> float | None:
    for ts, b, a in rows:
        if 0 < b < a < 1:
            return (b + a) / 2
    return None


def at(rows: list, ts: float) -> float | None:
    best = None
    for t, b, a in rows:
        if t <= ts and 0 < b < a < 1:
            best = (b + a) / 2
    return best


def forecasts(todo: list[dict]):
    prm = params()
    now_ts = max(parse_iso(g["start"]).timestamp() for g in todo)
    homes = {g["gid"]: slate.home_ml(g) for g in todo}
    tick = [m["ticker"] for m in homes.values() if m]
    opens = [parse_iso(m["open_time"]).timestamp() for m in homes.values() if m and m.get("open_time")]
    hist = history(tick, int(min(opens or [now_ts - 4 * 86400])), int(now_ts)) if tick else {}
    for g in todo:
        m, p_now = homes[g["gid"]], slate.home_mid(g)
        if not m or p_now is None:
            continue
        rows = hist.get(m["ticker"], [])
        start = parse_iso(g["start"]).timestamp()
        f = features(p_now, first_two_sided(rows), at(rows, start - 24 * 3600))
        p = prob(f, prm)
        home, away = slate.full_name(g["g"]["home"]), slate.full_name(g["g"]["away"])
        po = first_two_sided(rows)
        why = (f"Kalshi has {home} at {p_now:.0%}" + ("" if po is None else f" (opened at {po:.0%})")
               + f". Last season, games priced and moving like this went {home} {p:.0%}.")
        yield g, {"p_home": p}, why
