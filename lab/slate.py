"""Tonight's NBA games with their Kalshi markets, shared by all three lab models in one run.
Read-only: Kalshi's public market data and ESPN's free feed."""
from __future__ import annotations

import re
from datetime import timedelta

from core import espn, kalshi, match
from core.engine import team_name
from core.util import get_json, now_utc, parse_iso

KBASE = kalshi.BASE


def _markets(series: str) -> list[dict]:
    """Open markets with the 24-hour-ago price kept as well (the core reader drops it)."""
    out, cursor = [], None
    for _ in range(20):
        p = {"series_ticker": series, "status": "open", "limit": 1000}
        if cursor:
            p["cursor"] = cursor
        d = get_json(f"{KBASE}/markets", p, min_gap=kalshi.GAP)
        for m in d.get("markets", []):
            pm = kalshi.parse_market(m)
            pm["open_time"] = m.get("open_time")
            pv = m.get("previous_yes_bid_dollars"), m.get("previous_yes_ask_dollars")
            pm["prev_bid"] = float(pv[0]) if pv[0] not in (None, "") and float(pv[0]) > 0 else None
            pm["prev_ask"] = float(pv[1]) if pv[1] not in (None, "") and 0 < float(pv[1]) < 1 else None
            out.append(pm)
        cursor = d.get("cursor")
        if not cursor or not d.get("markets"):
            break
    return out


def load(max_hours: float = 14.0, min_minutes: float = 5.0) -> list[dict]:
    """Every NBA game that starts between min_minutes and max_hours from now and has Kalshi markets."""
    now = now_utc()
    kg = kalshi.group_by_game(_markets("KXNBAGAME"), _markets("KXNBASPREAD"), _markets("KXNBATOTAL"))
    sched = espn.upcoming("nba", 1)
    lo, hi = now + timedelta(minutes=min_minutes), now + timedelta(hours=max_hours)
    sched = [g for g in sched if g["state"] == "pre" and lo < parse_iso(g["start"]) <= hi]
    matched, _ = match.match_games(kg, sched)
    out = []
    for key, mt in sorted(matched.items(), key=lambda kv: kv[1]["espn"]["start"]):
        g = mt["espn"]
        out.append({"key": key, "gid": g["id"], "g": g, "kg": kg[key], "home_code": mt["home_code"],
                    "away_code": mt["away_code"], "start": g["start"], "name": f"{full_name(g['away'])} at {full_name(g['home'])}",
                    "mins": (parse_iso(g["start"]) - now).total_seconds() / 60})
    return out


def home_ml(game: dict) -> dict | None:
    for m in game["kg"]["ml"]:
        if m["team_code"] == game["home_code"]:
            return m
    return None


def home_mid(game: dict) -> float | None:
    """Kalshi's home-win probability: the home market's midpoint, averaged with the mirror of the
    away market's midpoint when both books are two-sided."""
    ps = []
    for m in game["kg"]["ml"]:
        md = kalshi.mid(m)
        if md is not None:
            ps.append(md if m["team_code"] == game["home_code"] else 1 - md)
    return sum(ps) / len(ps) if ps else None


def main_total(game: dict) -> dict | None:
    """The total market priced closest to 50 cents."""
    best = None
    for m in game["kg"]["total"]:
        md = kalshi.mid(m)
        if md is not None and (best is None or abs(md - 0.5) < abs(kalshi.mid(best) - 0.5)):
            best = m
    return best


def main_spread(game: dict) -> dict | None:
    best = None
    for m in game["kg"]["spread"]:
        md = kalshi.mid(m)
        if md is not None and (best is None or abs(md - 0.5) < abs(kalshi.mid(best) - 0.5)):
            best = m
    return best


def describe(game: dict, m: dict, mtype: str, side: str) -> str:
    """Plain-English position with full team names, e.g. 'Boston Celtics -8.5' or 'Under 213.5'."""
    if mtype == "total":
        return f"{'Over' if side == 'yes' else 'Under'} {m['strike']}"
    home, away = full_name(game["g"]["home"]), full_name(game["g"]["away"])
    team, other = (home, away) if m["team_code"] == game["home_code"] else (away, home)
    if mtype == "ml":
        return f"{team if side == 'yes' else other} to win"
    return f"{team} -{m['strike']}" if side == "yes" else f"{other} +{m['strike']}"


def full_name(t: dict) -> str:
    return t.get("display") or team_name(t)


def athlete_id(item: dict) -> str | None:
    for ln in (item.get("athlete") or {}).get("links", []):
        mt = re.search(r"/id/(\d+)", ln.get("href", ""))
        if mt:
            return mt.group(1)
    return None


def injuries() -> dict[str, list[dict]]:
    """ESPN's injury report, team id -> [{pid, name, status, comment, date, p_out}]. p_out is how
    likely the player is to miss tonight, read from the status and the short note."""
    try:
        d = get_json(espn.SITE + espn.PATHS["nba"] + "/injuries", min_gap=espn.GAP)
    except RuntimeError:
        return {}
    out: dict[str, list[dict]] = {}
    for team in d.get("injuries", []):
        rows = []
        for i in team.get("injuries", []):
            st = (i.get("status") or "").lower()
            note = (i.get("shortComment") or "")
            rows.append({"pid": athlete_id(i), "name": (i.get("athlete") or {}).get("displayName"), "status": i.get("status"),
                         "comment": note[:220], "date": i.get("date"), "p_out": p_out(st, note)})
        out[str(team.get("id"))] = rows
    return out


def p_out(status: str, note: str) -> float:
    n = note.lower()
    if status in ("out", "suspension") or re.search(r"\b(ruled out|will not play|won't play|is out|will miss|out for|sidelined|not play)\b", n):
        if not re.search(r"\b(questionable|probable|game-time|expected to play|will play|cleared)\b", n):
            return 1.0
    if "doubtful" in n:
        return 0.8
    if "questionable" in n or "game-time" in n:
        return 0.45
    if re.search(r"\b(probable|expected to play|will play|cleared|available|upgraded)\b", n):
        return 0.1
    return 0.35 if status == "day-to-day" else 0.5
