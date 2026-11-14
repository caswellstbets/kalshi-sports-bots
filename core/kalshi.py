"""Read-only Kalshi market data. There is deliberately no order endpoint, no
login and no API key anywhere in this project: the bots can only look."""
from __future__ import annotations

import re

from .util import get_json

BASE = "https://api.elections.kalshi.com/trade-api/v2"
GAP = 0.4  # seconds between calls; the public API rate-limits bursts


def _price(m: dict, key: str) -> float | None:
    v = m.get(key + "_dollars")
    if v not in (None, ""):
        return float(v)
    v = m.get(key)
    return None if v in (None, "") else float(v) / 100.0


def _size(m: dict, key: str) -> float:
    v = m.get(key + "_fp")
    if v in (None, ""):
        v = m.get(key)
    return float(v) if v not in (None, "") else 0.0


def parse_market(m: dict) -> dict:
    yes_bid, yes_ask = _price(m, "yes_bid"), _price(m, "yes_ask")
    no_bid, no_ask = _price(m, "no_bid"), _price(m, "no_ask")
    return {
        "ticker": m["ticker"],
        "event_ticker": m["event_ticker"],
        "title": m.get("title") or "",
        "team_name": m.get("yes_sub_title") or "",
        "strike": m.get("floor_strike"),
        "status": m.get("status"),
        "result": m.get("result") or "",
        "yes_bid": yes_bid or 0.0,
        "yes_ask": yes_ask or 0.0,
        "no_bid": no_bid or 0.0,
        "no_ask": no_ask or 0.0,
        # contracts offered at the ask; a NO ask is the mirror of the YES bid
        "yes_ask_size": _size(m, "yes_ask_size"),
        "no_ask_size": _size(m, "yes_bid_size"),
        "volume": _size(m, "volume"),
    }


def list_markets(series_ticker: str, status: str = "open") -> list[dict]:
    out, cursor = [], None
    for _ in range(20):
        params = {"series_ticker": series_ticker, "status": status, "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        d = get_json(f"{BASE}/markets", params, min_gap=GAP)
        out += [parse_market(m) for m in d.get("markets", [])]
        cursor = d.get("cursor")
        if not cursor or not d.get("markets"):
            break
    return out


def markets_by_ticker(tickers: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    tickers = sorted(set(tickers))
    for i in range(0, len(tickers), 40):
        d = get_json(f"{BASE}/markets", {"tickers": ",".join(tickers[i:i + 40]), "limit": 1000}, min_gap=GAP)
        for m in d.get("markets", []):
            out[m["ticker"]] = parse_market(m)
    return out


def mid(m: dict) -> float | None:
    """Midpoint of the YES bid/ask, or None when the book is one-sided or empty."""
    if m["yes_bid"] > 0 and 0 < m["yes_ask"] < 1:
        return (m["yes_bid"] + m["yes_ask"]) / 2
    return None


_MONTHS = {m: i + 1 for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}


def game_key(event_ticker: str) -> str:
    """KXNBASPREAD-26NOV14DENNOP -> 26NOV14DENNOP (shared by a game's winner,
    spread and total events)."""
    return event_ticker.split("-", 1)[1]


def key_date(key: str) -> tuple[int, int, int] | None:
    mt = re.match(r"(\d{2})([A-Z]{3})(\d{2})", key)
    if not mt or mt.group(2) not in _MONTHS:
        return None
    return 2000 + int(mt.group(1)), _MONTHS[mt.group(2)], int(mt.group(3))


def group_by_game(game_mkts: list[dict], spread_mkts: list[dict], total_mkts: list[dict]) -> dict[str, dict]:
    """Bundle every market for one game under its shared key."""
    games: dict[str, dict] = {}
    for m in game_mkts:
        g = games.setdefault(game_key(m["event_ticker"]), {"ml": [], "spread": [], "total": []})
        m["team_code"] = m["ticker"].rsplit("-", 1)[1]
        g["ml"].append(m)
    for m in spread_mkts:
        g = games.get(game_key(m["event_ticker"]))
        mt = re.match(r"^(.*?)(\d+)$", m["ticker"].rsplit("-", 1)[1])
        if g is None or mt is None or m["strike"] is None:
            continue
        m["team_code"] = mt.group(1)
        g["spread"].append(m)
    for m in total_mkts:
        g = games.get(game_key(m["event_ticker"]))
        if g is None or m["strike"] is None:
            continue
        g["total"].append(m)
    # a usable game has exactly two winner markets, one per team
    return {k: g for k, g in games.items() if len(g["ml"]) == 2}
