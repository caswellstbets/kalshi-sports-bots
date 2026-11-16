"""Download past Kalshi NBA winner markets and their hourly pre-game price history.

    python -m research.fetch_kalshi

Writes data/research/kalshi_nba_games.json: one row per game with both team tickers,
the result, and hourly [end_ts, yes_bid, yes_ask, volume] candles for each team's
market from the market's open until it closed. Read-only public API, no login."""
from __future__ import annotations

import os
import sys
import time

import requests

from core.util import parse_iso, read_json, write_json

_s = requests.Session()
_last = [0.0]


def get_json(url: str, params: dict | None = None, min_gap: float = 0.6, tries: int = 30, **_):
    """Patient GET: Kalshi rate-limits the shared address this runs from, so wait it out."""
    for attempt in range(tries):
        # stay out of the way of the hourly bot runs (they start a few minutes past the hour)
        while 2 <= time.gmtime().tm_min < 22:
            time.sleep(20)
        wait = _last[0] + min_gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            r = _s.get(url, params=params, timeout=30)
        except requests.RequestException:
            time.sleep(5)
            continue
        _last[0] = time.monotonic()
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(min(60, 4 * (attempt + 1)))
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"{url} -> {r.status_code}")
        return r.json()
    raise RuntimeError(f"{url} failed after {tries} tries")

BASE = "https://api.elections.kalshi.com/trade-api/v2"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "research", "kalshi_nba_games.json")


def all_markets(path: str, extra: dict) -> list[dict]:
    out, cursor = [], None
    while True:
        p = {"series_ticker": "KXNBAGAME", "limit": 1000, **extra}
        if cursor:
            p["cursor"] = cursor
        d = get_json(f"{BASE}/{path}", p, min_gap=0.3)
        out += d.get("markets", [])
        cursor = d.get("cursor")
        if not cursor or not d.get("markets"):
            return out


def f(x):
    return None if x in (None, "") else float(x)


def candles(ticker: str, hist: bool, start: int, end: int) -> list[list]:
    path = f"historical/markets/{ticker}/candlesticks" if hist else f"series/KXNBAGAME/markets/{ticker}/candlesticks"
    rows = []
    s = start
    while s < end:  # the API caps the number of candles per call
        e = min(end, s + 4000 * 3600)
        d = get_json(f"{BASE}/{path}", {"start_ts": s, "end_ts": e, "period_interval": 60}, min_gap=0.55, tries=10)
        for c in d.get("candlesticks", []):
            rows.append([c["end_period_ts"], f((c.get("yes_bid") or {}).get("close")), f((c.get("yes_ask") or {}).get("close")),
                         f(c.get("volume") or c.get("volume_fp"))])
        s = e
    return rows


def main() -> int:
    have = read_json(OUT, {})
    lst = OUT.replace("games.json", "market_list.json")
    cached = read_json(lst, None)
    if cached is None or "--refresh" in sys.argv:
        cached = {"hist": all_markets("historical/markets", {}), "recent": all_markets("markets", {"status": "settled"})}
        write_json(lst, cached)
    ms = [(m, True) for m in cached["hist"]] + [(m, False) for m in cached["recent"]]
    print(len(ms), "markets")
    events: dict[str, list] = {}
    for m, hist in ms:
        if m.get("result") in ("yes", "no"):
            events.setdefault(m["event_ticker"], []).append((m, hist))
    todo = [e for e, v in events.items() if len(v) == 2 and e not in have]
    # this season first (the out-of-sample test), then last season in date order
    todo.sort(key=lambda e: (not any(not h for _, h in events[e]), events[e][0][0]["close_time"]))
    print(len(events), "events,", len(todo), "to fetch")
    for i, ev in enumerate(todo):
        row = {"event": ev, "markets": []}
        code = ev.split("-", 1)[1][7:]  # away code + home code
        pair = events[ev]
        home = [x for x in pair if code.endswith(x[0]["ticker"].rsplit("-", 1)[1])]
        for m, hist in pair:
            # the home team's market gets an hourly price history; the away market is its mirror
            want = bool(home) and m is home[0][0]
            o, c = int(parse_iso(m["open_time"]).timestamp()), int(parse_iso(m["close_time"]).timestamp())
            cs = None
            if want:
                try:
                    cs = candles(m["ticker"], hist, max(o, c - 3 * 86400), c + 3600)
                except RuntimeError as err:
                    print("skip", m["ticker"], err)
            row["markets"].append({"ticker": m["ticker"], "team": m["ticker"].rsplit("-", 1)[1], "name": m.get("yes_sub_title"),
                                   "result": m["result"], "open": m["open_time"], "close": m["close_time"],
                                   "expected_exp": m.get("expected_expiration_time"), "volume": f(m.get("volume_fp")),
                                   "title": m.get("title"), "candles": cs})
        have[ev] = row
        if i % 25 == 0:
            write_json(OUT, have)
            print(i, ev, flush=True)
    write_json(OUT, have)
    print("done", len(have))
    return 0


if __name__ == "__main__":
    sys.exit(main())
