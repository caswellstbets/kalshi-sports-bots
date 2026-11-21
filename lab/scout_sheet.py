"""The game sheet the Scout reads: Kalshi prices and how they moved, both teams' form and
numbers this season, rest, and the injury report with each player's usual role. No sportsbook
line and nothing from the other lab models."""
from __future__ import annotations

from zoneinfo import ZoneInfo

from core import kalshi
from core.util import parse_iso

from core.engine import side_price

from . import boxscores, decide, slate, teamstats
from .players import rest_days

CT = ZoneInfo("America/Chicago")


def _price(m: dict) -> dict:
    return {"yes_bid": m["yes_bid"], "yes_ask": m["yes_ask"], "no_ask": m["no_ask"],
            "yes_price_24h_ago": None if m.get("prev_bid") is None or m.get("prev_ask") is None
            else round((m["prev_bid"] + m["prev_ask"]) / 2, 3)}


def contracts(g: dict) -> list[dict]:
    """The contracts the Scout may pick from: both winners, and spreads and totals near the main line."""
    out = []
    for m in g["kg"]["ml"]:
        for side in ("yes", "no"):
            out.append({"ticker": m["ticker"], "side": side, "label": slate.describe(g, m, "ml", side),
                        "ask": m["yes_ask"] if side == "yes" else m["no_ask"]})
    for mtype in ("spread", "total"):
        ms = [m for m in g["kg"][mtype] if kalshi.mid(m) is not None and 0.3 <= kalshi.mid(m) <= 0.7]
        for m in ms:
            for side in ("yes", "no"):
                out.append({"ticker": m["ticker"], "side": side, "label": slate.describe(g, m, mtype, side),
                            "ask": m["yes_ask"] if side == "yes" else m["no_ask"]})
    ok = []
    for c in out:  # only contracts that pass the same market-quality rules as every other model
        m = next(x for t in ("ml", "spread", "total") for x in g["kg"][t] if x["ticker"] == c["ticker"])
        mtype = next(t for t in ("ml", "spread", "total") if m in g["kg"][t])
        ask, bid, size = side_price(m, c["side"])
        lo, hi = decide.PRICE_BAND[mtype]
        if lo <= ask <= hi and bid > 0 and ask - bid <= decide.MAX_SPREAD + 1e-9 and size >= decide.MIN_SIZE:
            ok.append(c)
    return ok


def build(root: str, games: list[dict]) -> dict:
    db = boxscores.load(root)
    season = max(g["season"] for g in db)
    cur = teamstats.season_games(db, season)
    last = {}
    for g in db:
        for t in (g["h"], g["a"]):
            last[t] = g["date"]
    inj = slate.injuries()
    sheets = {}
    for g in games:
        eg = g["g"]
        teams = {}
        for side in ("home", "away"):
            t = eg[side]
            tid = t["id"]
            pl = teamstats.player_lines(cur, tid)
            rot = [f"{p['name']}: {p['games']} games, {p['minutes_per_game']} min, {p['points_per_game']} pts, {p['starts']} starts, last played {p['last_played']}"
                   for p in sorted(pl.values(), key=lambda p: -p["minutes_per_game"] * p["games"])[:10]]
            injured = []
            for i in inj.get(tid, []):
                p = pl.get(i["pid"] or "") or {}
                injured.append({"player": i["name"], "status": i["status"], "note": i["comment"],
                                "this_season": {k: p.get(k) for k in ("games", "minutes_per_game", "points_per_game", "starts")} if p else "no games this season"})
            rd = rest_days(last.get(tid), g["start"])
            teams[side] = {"team": slate.full_name(t), **teamstats.team_summary(cur, tid, {}),
                           "days_since_last_game": None if rd is None else round(rd, 1),
                           "second_night_of_back_to_back": rd is not None and rd < 1.6,
                           "rotation_this_season": rot, "injury_report": injured}
        series = [f"{x['date'][:10]}: {x['aname']} {int(x['as'])} at {x['hname']} {int(x['hs'])}" for x in cur
                  if {x["h"], x["a"]} == {eg["home"]["id"], eg["away"]["id"]}]
        hm = slate.home_ml(g)
        am = next((m for m in g["kg"]["ml"] if m is not hm), None)
        sp, tt = slate.main_spread(g), slate.main_total(g)
        sheets[g["gid"]] = {
            "model": "Scout", "game_id": g["gid"], "game": f"{slate.full_name(eg['away'])} at {slate.full_name(eg['home'])}",
            "start_central": parse_iso(g["start"]).astimezone(CT).strftime("%a %b %-d %-I:%M %p CT"),
            "minutes_to_start": round(g["mins"]),
            "kalshi": {"home_win": _price(hm) if hm else None, "away_win": _price(am) if am else None,
                       "home_win_probability_midpoint": slate.home_mid(g),
                       "main_spread": None if not sp else {"contract": slate.describe(g, sp, "spread", "yes"), **_price(sp)},
                       "main_total": None if not tt else {"line": tt["strike"], "over": _price(tt)}},
            "home": teams["home"], "away": teams["away"], "season_series": series,
            "contracts": contracts(g),
            "task": ("Read everything, then give your own home-win probability, expected home margin and total. "
                     "Pick one contract only if you can name something specific the price is missing; otherwise pass. "
                     "Confidence: High needs an edge of 8+ points after the fee, Mid 5+, Low 3+.")}
    return sheets
