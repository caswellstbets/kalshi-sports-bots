"""ESPN's free public feed: schedules, final scores, the sportsbook line shown
on each game, and injury reports. Unofficial, so every field is read defensively."""
from __future__ import annotations

import re
from datetime import datetime, timedelta

from .util import ET, get_json, now_utc, parse_iso, read_json, write_json

SITE = "https://site.api.espn.com/apis/site/v2/sports/"
PATHS = {"nba": "basketball/nba", "nfl": "football/nfl", "cfb": "football/college-football"}
GAP = 0.25


def _american(s) -> int | None:
    if s is None:
        return None
    s = str(s).strip().upper()
    if s in ("EVEN", "EV"):
        return 100
    mt = re.match(r"^[+-]?\d+(\.\d+)?$", s)
    return int(float(s)) if mt else None


def _num(s) -> float | None:
    if s is None:
        return None
    mt = re.search(r"[+-]?\d+(\.\d+)?", str(s))
    return float(mt.group(0)) if mt else None


def _side(d: dict, *path):
    for p in path:
        d = d.get(p) if isinstance(d, dict) else None
    # prefer the current ("close") number, fall back to the opener
    if not isinstance(d, dict):
        return {}
    return d.get("close") or d.get("open") or {}


def parse_odds(comp: dict) -> dict | None:
    """Sportsbook line for a game: home spread with both prices, total with both
    prices, both moneylines. Missing pieces are None."""
    odds = comp.get("odds") or []
    if not odds:
        return None
    o = odds[0]
    hs, as_ = _side(o, "pointSpread", "home"), _side(o, "pointSpread", "away")
    ov, un = _side(o, "total", "over"), _side(o, "total", "under")
    out = {
        "book": (o.get("provider") or {}).get("name"),
        "home_spread": _num(hs.get("line")),
        "home_spread_odds": _american(hs.get("odds")),
        "away_spread_odds": _american(as_.get("odds")),
        "total": _num(ov.get("line")) if ov.get("line") else o.get("overUnder"),
        "over_odds": _american(ov.get("odds")),
        "under_odds": _american(un.get("odds")),
        "home_ml": _american(_side(o, "moneyline", "home").get("odds")),
        "away_ml": _american(_side(o, "moneyline", "away").get("odds")),
    }
    if out["home_spread"] is None and out["total"] is None and out["home_ml"] is None:
        return None
    return out


def _team(c: dict) -> dict:
    t = c.get("team") or {}
    recs = c.get("records") or []
    return {
        "id": str(t.get("id")),
        "abbr": t.get("abbreviation") or "",
        "location": t.get("location") or "",
        "name": t.get("name") or "",
        "display": t.get("displayName") or "",
        "short": t.get("shortDisplayName") or "",
        "score": _num(c.get("score")),
        "record": recs[0].get("summary") if recs else None,
    }


def parse_event(e: dict) -> dict | None:
    comps = e.get("competitions") or []
    if not comps:
        return None
    comp = comps[0]
    sides = {c.get("homeAway"): _team(c) for c in comp.get("competitors", [])}
    if "home" not in sides or "away" not in sides:
        return None
    st = (e.get("status") or {}).get("type") or {}
    return {
        "id": str(e["id"]),
        "start": e["date"],
        "state": st.get("state"),  # pre | in | post
        "completed": bool(st.get("completed")),
        "season_type": (e.get("season") or {}).get("type"),
        "neutral": bool(comp.get("neutralSite")),
        "home": sides["home"],
        "away": sides["away"],
        "odds": parse_odds(comp),
    }


def scoreboard(sport: str, **params) -> tuple[list[dict], dict]:
    d = get_json(SITE + PATHS[sport] + "/scoreboard", {"limit": 500, **params}, min_gap=GAP)
    games = [g for g in (parse_event(e) for e in d.get("events", [])) if g]
    return games, d


def upcoming(sport: str, days_ahead: int, groups: list[str] | None = None) -> list[dict]:
    """Games from yesterday (ET) through days_ahead, deduplicated."""
    today = now_utc().astimezone(ET).date()
    seen: dict[str, dict] = {}
    for off in range(-1, days_ahead + 1):
        day = (today + timedelta(days=off)).strftime("%Y%m%d")
        for grp in groups or [None]:
            p = {"dates": day}
            if grp:
                p["groups"] = grp
            try:
                games, _ = scoreboard(sport, **p)
            except RuntimeError:
                continue
            for g in games:
                seen[g["id"]] = g
    return list(seen.values())


def _compact(g: dict) -> dict:
    return {
        "id": g["id"], "date": g["start"], "neutral": g["neutral"],
        "h": g["home"]["id"], "a": g["away"]["id"],
        "hs": g["home"]["score"], "as": g["away"]["score"],
        "hn": g["home"]["abbr"] or g["home"]["location"], "an": g["away"]["abbr"] or g["away"]["location"],
    }


def season_results(sport: str, cache_path: str, *, season_start: str, groups: list[str] | None = None) -> list[dict]:
    """Every completed regular-season game so far. Days (NBA) or weeks (football)
    that are fully in the past are cached on disk so each run only fetches what is new."""
    cache = read_json(cache_path, {})
    now = now_utc()
    keys: list[tuple[str, dict]] = []
    if sport == "nba":
        day = datetime.strptime(season_start, "%Y-%m-%d").date()
        today = now.astimezone(ET).date()
        while day <= today:
            keys.append((day.strftime("%Y%m%d"), {"dates": day.strftime("%Y%m%d")}))
            day += timedelta(days=1)
    else:
        _, head = scoreboard(sport)
        wk = (head.get("week") or {}).get("number") or 1
        if (head.get("season") or {}).get("type") != 2:
            wk = 18 if sport == "nfl" else 16  # postseason: use the whole regular season
        for w in range(1, int(wk) + 1):
            for grp in groups or [None]:
                p = {"week": w, "seasontype": 2}
                if grp:
                    p["groups"] = grp
                keys.append((f"w{w}" + (f"g{grp}" if grp else ""), p))
    out: dict[str, dict] = {}
    for key, params in keys:
        ent = cache.get(key)
        if ent is None or not ent.get("final"):
            try:
                games, _ = scoreboard(sport, **params)
            except RuntimeError:
                continue
            games = [g for g in games if g["season_type"] == 2]
            done = [_compact(g) for g in games if g["completed"] and g["home"]["score"] is not None]
            latest = max((parse_iso(g["start"]) for g in games), default=None)
            final = all(g["completed"] for g in games) and (
                latest is not None and now - latest > timedelta(hours=36)
                or (not games and sport == "nba" and key < (now - timedelta(days=2)).strftime("%Y%m%d")))
            ent = {"final": bool(final), "games": done}
            cache[key] = ent
        for g in ent["games"]:
            out[g["id"]] = g
    write_json(cache_path, cache)
    return list(out.values())


def injuries(sport: str) -> dict[str, list[str]]:
    """Team id -> short injury lines. NBA and NFL only; college has no league report."""
    if sport == "cfb":
        return {}
    try:
        d = get_json(SITE + PATHS[sport] + "/injuries", min_gap=GAP)
    except RuntimeError:
        return {}
    out: dict[str, list[str]] = {}
    for team in d.get("injuries", []):
        lines = []
        for i in team.get("injuries", [])[:14]:
            ath = (i.get("athlete") or {})
            pos = ((ath.get("position") or {}).get("abbreviation")) or ""
            lines.append(f"{ath.get('displayName', '?')} ({pos}) {i.get('status', '')}: {(i.get('shortComment') or '')[:160]}")
        out[str(team.get("id"))] = lines
    return out
