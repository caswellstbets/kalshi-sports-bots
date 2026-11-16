"""Fast path for this season's settled Kalshi NBA winner markets: the batch candlestick endpoint
takes many tickers per call (it does not serve the historical archive, which fetch_kalshi.py reads
one market at a time). Writes into the same data/research/kalshi_nba_games.json."""
from __future__ import annotations

import sys
from collections import defaultdict

from core.util import parse_iso, read_json, write_json
from research.fetch_kalshi import BASE, OUT, get_json


def f(x):
    return None if x in (None, "") else float(x)


def main() -> int:
    have = read_json(OUT, {})
    lst = read_json(OUT.replace("games.json", "market_list.json"), {})
    events = defaultdict(list)
    for m in lst.get("recent", []):
        if m.get("result") in ("yes", "no"):
            events[m["event_ticker"]].append(m)
    todo = [e for e, v in events.items() if len(v) == 2 and e not in have]
    by_day = defaultdict(list)
    for e in todo:
        by_day[events[e][0]["close_time"][:10]].append(e)
    days = sorted(by_day)
    # the endpoint allows 10,000 candles per call (markets x hours requested): three days per call,
    # home team's market only (the away market is its mirror)
    for i in range(0, len(days), 3):
        evs = [e for d in days[i:i + 3] for e in by_day[d]]
        homes = {}
        for e in evs:
            code = e.split("-", 1)[1][7:]
            h = [m for m in events[e] if code.endswith(m["ticker"].rsplit("-", 1)[1])]
            if h:
                homes[e] = h[0]
        if not homes:
            continue
        end = max(int(parse_iso(m["close_time"]).timestamp()) for m in homes.values()) + 3600
        start = min(int(parse_iso(m["close_time"]).timestamp()) for m in homes.values()) - 3 * 86400
        per = max(1, int(10000 // ((end - start) / 3600 + 2)))
        hm = list(homes.values())
        got = {}
        for j in range(0, len(hm), per):
            chunk = hm[j:j + per]
            d = get_json(f"{BASE}/markets/candlesticks", {"market_tickers": ",".join(m["ticker"] for m in chunk),
                                                         "start_ts": start, "end_ts": end, "period_interval": 60}, min_gap=8)
            for x in d.get("markets", []):
                got[x["market_ticker"]] = [[c["end_period_ts"], f((c.get("yes_bid") or {}).get("close_dollars")),
                                            f((c.get("yes_ask") or {}).get("close_dollars")), f(c.get("volume_fp"))]
                                           for c in x.get("candlesticks", [])]
        for e in evs:
            have[e] = {"event": e, "markets": [{"ticker": m["ticker"], "team": m["ticker"].rsplit("-", 1)[1],
                                                "name": m.get("yes_sub_title"), "result": m["result"], "open": m["open_time"],
                                                "close": m["close_time"], "expected_exp": m.get("expected_expiration_time"),
                                                "volume": f(m.get("volume_fp")), "title": m.get("title"),
                                                "candles": got.get(m["ticker"])} for m in events[e]]}
        write_json(OUT, have)
        print(days[i], len(evs), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
