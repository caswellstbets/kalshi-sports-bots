"""Plain team and player numbers for the Scout's game sheet, from the box-score file."""
from __future__ import annotations

from collections import defaultdict

from .players import possessions


def season_games(games: list[dict], season: int) -> list[dict]:
    return [g for g in games if g["season"] == season and g["season_type"] == 2]


def team_summary(games: list[dict], team: str, names: dict) -> dict:
    mine = sorted((g for g in games if team in (g["h"], g["a"])), key=lambda g: g["date"])
    if not mine:
        return {}
    rec, home, away, pf, pa, poss, oposs = [0, 0], [0, 0], [0, 0], 0.0, 0.0, 0.0, 0.0
    lines = []
    for g in mine:
        is_h = g["h"] == team
        s, o = (g["hs"], g["as"]) if is_h else (g["as"], g["hs"])
        won = s > o
        rec[0 if won else 1] += 1
        (home if is_h else away)[0 if won else 1] += 1
        pf, pa = pf + s, pa + o
        mine_rows = [p for p in g["players"] if p["team"] == team]
        opp_rows = [p for p in g["players"] if p["team"] != team]
        poss += possessions(mine_rows)
        oposs += possessions(opp_rows)
        opp = g["aname"] if is_h else g["hname"]
        lines.append(f"{g['date'][:10]} {'W' if won else 'L'} {int(s)}-{int(o)} {'vs' if is_h else 'at'} {opp}")
    n = len(mine)
    p = (poss + oposs) / 2 or 1
    last10 = mine[-10:]
    l10 = [((g["hs"] - g["as"]) if g["h"] == team else (g["as"] - g["hs"])) for g in last10]
    return {"record": f"{rec[0]}-{rec[1]}", "home_record": f"{home[0]}-{home[1]}", "road_record": f"{away[0]}-{away[1]}",
            "points_for_per_game": round(pf / n, 1), "points_against_per_game": round(pa / n, 1),
            "offensive_rating_per_100": round(100 * pf / p, 1), "defensive_rating_per_100": round(100 * pa / p, 1),
            "pace_possessions_per_game": round(p / n, 1),
            "last_10": f"{sum(1 for x in l10 if x > 0)}-{sum(1 for x in l10 if x < 0)}, average margin {sum(l10) / len(l10):+.1f}",
            "recent_results": lines[-6:]}


def player_lines(games: list[dict], team: str) -> dict[str, dict]:
    """Per player this season with this team: games, minutes, points, starts."""
    acc = defaultdict(lambda: {"g": 0, "min": 0.0, "pts": 0.0, "starts": 0, "name": "", "last": ""})
    for g in games:
        for p in g["players"]:
            if p["team"] != team or p.get("min", 0) <= 0:
                continue
            a = acc[p["pid"]]
            a["g"] += 1
            a["min"] += p["min"]
            a["pts"] += p.get("pts", 0)
            a["starts"] += 1 if p.get("starter") else 0
            a["name"] = p.get("name") or a["name"]
            a["last"] = max(a["last"], g["date"][:10])
    return {pid: {"name": a["name"], "games": a["g"], "minutes_per_game": round(a["min"] / a["g"], 1),
                  "points_per_game": round(a["pts"] / a["g"], 1), "starts": a["starts"], "last_played": a["last"]}
            for pid, a in acc.items()}
