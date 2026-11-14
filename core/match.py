"""Pair each Kalshi game with its ESPN game, and work out which Kalshi team
code is the home side."""
from __future__ import annotations

import re
from datetime import date

from .kalshi import key_date
from .util import ET, parse_iso


def norm(s: str) -> str:
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"\bst\b\.?", "state", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _team_score(code: str, name: str, t: dict) -> int:
    """How well a Kalshi (code, name) fits an ESPN team: 0 none ... 3 certain."""
    n = norm(name)
    cands = {norm(t["location"]), norm(t["short"]), norm(t["display"]),
             norm(f"{t['location']} {t['name']}")}
    cands.discard("")
    abbr = (t["abbr"] or "").upper()
    score = 0
    if n and n in cands:
        score = 3
    elif code and code.upper() == abbr:
        score = 2
    elif n and any(n == c[:len(n)] and len(n) >= 5 for c in cands):
        score = 1  # e.g. "Los Angeles L" vs "Los Angeles Lakers"
    if score == 3 and code and abbr and code.upper() == abbr:
        score = 4
    return score


def match_games(kalshi_games: dict[str, dict], espn_games: list[dict]) -> tuple[dict[str, dict], list[str]]:
    """Returns ({key: {"espn": game, "home_code": ..., "away_code": ...}}, unmatched keys)."""
    by_day: dict[date, list[dict]] = {}
    for g in espn_games:
        by_day.setdefault(parse_iso(g["start"]).astimezone(ET).date(), []).append(g)
    out, missing = {}, []
    for key, kg in kalshi_games.items():
        ymd = key_date(key)
        if not ymd:
            continue
        (c1, n1), (c2, n2) = [(m["team_code"], m["team_name"]) for m in kg["ml"]]
        best, best_score, tie = None, 0, False
        for g in by_day.get(date(*ymd), []):
            for hc, hn, ac, an in ((c1, n1, c2, n2), (c2, n2, c1, n1)):
                sh, sa = _team_score(hc, hn, g["home"]), _team_score(ac, an, g["away"])
                if sh == 0 or sa == 0:
                    continue
                s = sh + sa
                if s > best_score:
                    best, best_score, tie = {"espn": g, "home_code": hc, "away_code": ac}, s, False
                elif s == best_score:
                    tie = True
        if best and not tie and best_score >= 3:
            out[key] = best
        else:
            missing.append(key)
    return out, missing
