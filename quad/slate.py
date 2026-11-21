"""Build the slate for the four new bots: every upcoming game with a Kalshi market, and every
signal the bots combine. Reuses the main bot's readers and stats model; changes nothing of it.

Signals, all in HOME-margin points (or total points) relative to Kalshi's own price:
  stats   stats forecast minus Kalshi-implied margin/total
  book    sportsbook-implied minus Kalshi-implied (kept small in every bot)
  move    Kalshi-implied margin now minus at the market's first two-sided quote
  rest    automatic schedule spots: bye weeks, short weeks, back-to-backs
  read    Claude's in-session read: own margin/total, news points, situational tags (quad/read.py)
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone

from bots import cfb, nba, nfl
from core import engine, espn, kalshi, match, pricing, ratings
from core.util import ET, get_json, iso, norm_inv, now_utc, parse_iso, r4

CONFIGS = {"cfb": cfb.CONFIG, "nfl": nfl.CONFIG, "nba": nba.CONFIG}
WINDOW_H = {"cfb": 14, "nfl": 14, "nba": 12}


def opening_mid(series: str, ticker: str, now) -> tuple[float | None, str | None]:
    """Mid price at the first hour with a real two-sided quote, from Kalshi's public candlesticks."""
    try:
        d = get_json(f"{kalshi.BASE}/series/{series}/markets/{ticker}/candlesticks",
                     {"start_ts": int(now.timestamp()) - 6 * 86400, "end_ts": int(now.timestamp()),
                      "period_interval": 60}, min_gap=kalshi.GAP, tries=2)
    except Exception:
        return None, None
    for c in d.get("candlesticks", []):
        try:
            b = float(c["yes_bid"]["close_dollars"]); a = float(c["yes_ask"]["close_dollars"])
        except (KeyError, TypeError, ValueError):
            continue
        if b > 0 and a < 1 and a - b <= 0.10:
            return (a + b) / 2, iso(datetime.fromtimestamp(c["end_period_ts"], tz=timezone.utc))
    return None, None


def rest_spots(sport: str, g: dict, last: dict) -> list[dict]:
    """Automatic schedule spots, signed in home-margin points."""
    out = []
    start = parse_iso(g["start"])
    for side, sign in (("home", 1), ("away", -1)):
        prev = last.get(g[side]["id"])
        if prev is None:
            continue
        days = (start - prev).total_seconds() / 86400
        name = engine.team_name(g[side])
        if sport == "nba" and days < 1.6:
            out.append({"tag": "back_to_back", "side": side, "pts": -sign * 1.5, "total": -1.0, "text": f"{name} played last night"})
        elif sport == "nba" and days >= 3.5:
            out.append({"tag": "rested", "side": side, "pts": sign * 0.5, "total": 0.0, "text": f"{name} has had {days:.0f} days off"})
        elif sport != "nba" and days >= 12.5:
            out.append({"tag": "bye", "side": side, "pts": sign * 1.0, "total": 0.0, "text": f"{name} is coming off a bye"})
        elif sport == "nfl" and days < 5.5:
            out.append({"tag": "short_week", "side": side, "pts": -sign * 1.0, "total": 0.0, "text": f"{name} is on a short week"})
    return out


def build(sport: str, root: str, now=None, with_movement: bool = True) -> list[dict]:
    cfg = CONFIGS[sport]
    now = now or now_utc()
    pre = cfg.kalshi_prefix
    kgames = kalshi.group_by_game(kalshi.list_markets(pre + "GAME"), kalshi.list_markets(pre + "SPREAD"),
                                  kalshi.list_markets(pre + "TOTAL"))
    win = WINDOW_H[sport]
    sched = espn.upcoming(sport, int(math.ceil(win / 24)) + 1, cfg.espn_groups)
    lo, hi = now + timedelta(minutes=cfg.lockout_minutes), now + timedelta(hours=win)
    sched = [g for g in sched if g["state"] == "pre" and lo < parse_iso(g["start"]) <= hi]
    matched, _ = match.match_games(kgames, sched)
    p = engine.paths(cfg, root)
    results = espn.season_results(sport, p["results_cache"], season_start=cfg.season_start,
                                  groups=cfg.espn_groups, save=False)
    rt = ratings.fit(results, hfa=cfg.hfa, ridge=cfg.ridge, half_life_days=cfg.half_life_days,
                     margin_cap=cfg.margin_cap, min_games=cfg.min_games, as_of=now)
    rt_form = ratings.fit(results, hfa=cfg.hfa, ridge=cfg.ridge, half_life_days=cfg.form_half_life_days,
                          margin_cap=cfg.margin_cap, min_games=cfg.min_games, as_of=now)
    inj = espn.injuries(sport) if matched else {}
    out = []
    for key, mt in sorted(matched.items(), key=lambda kv: kv[1]["espn"]["start"]):
        g, kg, home_code = mt["espn"], kgames[key], mt["home_code"]
        st = engine.stats_forecast(cfg, g, rt, rt_form)
        if st["margin"] is None:
            continue
        b = pricing.book_anchors(g["odds"], cfg.sd_margin, cfg.sd_total)
        book = {"margin": b["margin_spread"] if b["margin_spread"] is not None else b["margin_ml"], "total": b["total"]}
        km, kt = engine.kalshi_anchors(kg, home_code, cfg)
        if km is None:
            continue
        move, open_ts = None, None
        if with_movement:
            hm = next((m for m in kg["ml"] if m["team_code"] == home_code), None)
            if hm:
                om, open_ts = opening_mid(pre + "GAME", hm["ticker"], now)
                if om is not None:
                    move = km - cfg.sd_margin * norm_inv(min(max(om, 0.02), 0.98))
        rows = engine.price_markets(cfg, g, kg, home_code, st, book, None, None)
        if not engine.candidates(cfg, rows, "p_kalshi"):
            continue  # nothing buyable in this game
        out.append({
            "sport": sport, "game_id": g["id"], "game": engine.game_name(g), "start": g["start"],
            "home": engine.team_name(g["home"]), "away": engine.team_name(g["away"]),
            "neutral": g["neutral"], "g": g, "kg": kg, "home_code": home_code, "st": st,
            "kalshi": {"margin": km, "total": kt}, "book": book, "move": move, "open_ts": open_ts,
            "rest": rest_spots(sport, g, rt["last"]),
            "injuries": {"home": inj.get(g["home"]["id"], []), "away": inj.get(g["away"]["id"], [])} if sport != "cfb" else None,
            "records": {"home": g["home"].get("record"), "away": g["away"].get("record")},
            "ratings": {"home": r4(ratings.net(rt, g["home"]["id"])), "away": r4(ratings.net(rt, g["away"]["id"])),
                        "home_form": r4(ratings.net(rt_form, g["home"]["id"])), "away_form": r4(ratings.net(rt_form, g["away"]["id"]))},
        })
    return out


def sheet(c: dict) -> dict:
    """What Claude reads before writing a read. Prices are included on purpose (these bots are not blind)."""
    def f(x):
        return None if x is None else round(x, 1)
    return {"game_id": c["game_id"], "sport": c["sport"], "game": c["game"],
            "start_ct": parse_iso(c["start"]).astimezone(__import__("zoneinfo").ZoneInfo("America/Chicago")).strftime("%a %-I:%M %p"),
            "records": c["records"], "ratings": c["ratings"], "neutral": c["neutral"],
            "home_margin": {"kalshi": f(c["kalshi"]["margin"]), "stats": f(c["st"]["margin"]), "book": f(c["book"]["margin"])},
            "total": {"kalshi": f(c["kalshi"]["total"]), "stats": f(c["st"]["total"]), "book": f(c["book"]["total"])},
            "kalshi_move_since_open": f(c["move"]), "stats_notes": c["st"]["notes"],
            "rest_spots": [s["text"] for s in c["rest"]], "injuries": c["injuries"]}
