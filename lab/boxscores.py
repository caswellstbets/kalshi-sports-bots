"""Every NBA game since the start of last season with player box scores, from ESPN's free feed.

Kept as an append-only file (data/nba_lab/boxscores.jsonl, one game per line) so each run only
fetches days it has not finished. Used by the Rotation model and by the Scout's game sheets."""
from __future__ import annotations

import json
import os
from datetime import date, timedelta

from core.util import ET, append_jsonl, get_json, now_utc, read_json, read_jsonl, write_json

SITE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/"
SEASONS = [(date(2025, 10, 21), date(2026, 6, 25)), (date(2026, 10, 20), None)]
COLS = ["MIN", "PTS", "FG", "3PT", "FT", "REB", "AST", "TO", "STL", "BLK", "OREB", "DREB", "PF", "+/-"]


def paths(root: str) -> tuple[str, str]:
    d = os.path.join(root, "data", "nba_lab")
    return os.path.join(d, "boxscores.jsonl"), os.path.join(d, "boxscore_days.json")


def _num(s) -> float:
    try:
        return float(str(s).replace("+", ""))
    except ValueError:
        return 0.0


def _ma(s) -> tuple[float, float]:
    try:
        a, b = str(s).split("-")
        return float(a), float(b)
    except ValueError:
        return 0.0, 0.0


def parse_players(box: dict) -> list[dict]:
    out = []
    for side in box.get("players", []):
        tid = str(side["team"]["id"])
        for st in side.get("statistics", [])[:1]:
            lab = st.get("labels") or COLS
            for a in st.get("athletes", []):
                ath = a.get("athlete") or {}
                row = {"pid": str(ath.get("id")), "name": ath.get("displayName"), "team": tid,
                       "pos": (ath.get("position") or {}).get("abbreviation"), "starter": bool(a.get("starter"))}
                if a.get("didNotPlay") or not a.get("stats"):
                    row.update({"min": 0.0, "dnp": a.get("reason") or "DNP"})
                else:
                    s = dict(zip(lab, a["stats"]))
                    fgm, fga = _ma(s.get("FG"))
                    tpm, tpa = _ma(s.get("3PT"))
                    ftm, fta = _ma(s.get("FT"))
                    row.update({"min": _num(s.get("MIN")), "pts": _num(s.get("PTS")), "fgm": fgm, "fga": fga, "tpm": tpm,
                                "tpa": tpa, "ftm": ftm, "fta": fta, "oreb": _num(s.get("OREB")), "dreb": _num(s.get("DREB")),
                                "ast": _num(s.get("AST")), "tov": _num(s.get("TO")), "stl": _num(s.get("STL")),
                                "blk": _num(s.get("BLK")), "pf": _num(s.get("PF")), "pm": _num(s.get("+/-"))})
                out.append(row)
    return out


def parse_game(e: dict, summary: dict) -> dict:
    comp = e["competitions"][0]
    sides = {c["homeAway"]: c for c in comp["competitors"]}
    line = None
    for pc in summary.get("pickcenter") or []:
        if pc.get("spread") is not None or pc.get("overUnder") is not None:
            line = {"book": (pc.get("provider") or {}).get("name"), "home_spread": pc.get("spread"), "total": pc.get("overUnder")}
            break
    return {"id": str(e["id"]), "date": e["date"], "season_type": (e.get("season") or {}).get("type"),
            "season": (e.get("season") or {}).get("year"), "neutral": bool(comp.get("neutralSite")),
            "h": str(sides["home"]["team"]["id"]), "a": str(sides["away"]["team"]["id"]),
            "hn": sides["home"]["team"].get("abbreviation"), "an": sides["away"]["team"].get("abbreviation"),
            "hname": sides["home"]["team"].get("displayName"), "aname": sides["away"]["team"].get("displayName"),
            "hs": _num(sides["home"].get("score")), "as": _num(sides["away"].get("score")),
            "line": line, "players": parse_players(summary.get("boxscore") or {})}


def load(root: str) -> list[dict]:
    games = {g["id"]: g for g in read_jsonl(paths(root)[0])}
    return sorted(games.values(), key=lambda g: g["date"])


def update(root: str, verbose: bool = False) -> int:
    """Fetch finished games for every day not yet marked complete. Returns games added."""
    gpath, dpath = paths(root)
    have = {g["id"] for g in read_jsonl(gpath)}
    done = set(read_json(dpath, []))
    today = now_utc().astimezone(ET).date()
    added = 0
    for start, end in SEASONS:
        day, end = start, min(end or today, today)
        while day <= end:
            key = day.strftime("%Y%m%d")
            day += timedelta(days=1)
            if key in done:
                continue
            try:
                sb = get_json(SITE + "scoreboard", {"dates": key, "limit": 100}, min_gap=0.2)
            except RuntimeError:
                continue
            complete, new = True, []
            for e in sb.get("events", []):
                st = (e.get("status") or {}).get("type") or {}
                if not st.get("completed"):
                    complete = False
                    continue
                if str(e["id"]) in have:
                    continue
                try:
                    new.append(parse_game(e, get_json(SITE + "summary", {"event": e["id"]}, min_gap=0.2)))
                except (RuntimeError, KeyError):
                    complete = False
            append_jsonl(gpath, new)
            have |= {g["id"] for g in new}
            added += len(new)
            if complete and key < (today - timedelta(days=1)).strftime("%Y%m%d"):
                done.add(key)
            if verbose and new:
                print(key, len(new), flush=True)
    write_json(dpath, sorted(done))
    return added
