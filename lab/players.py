"""Player-level running stats for the Rotation model, built game by game from ESPN box scores.

Everything here is walk-forward: `features()` for a game only uses games already passed to
`update()`. Weights decay with NBA game-days (days with at least one game), so the summer
break costs nothing and last season carries into this one at a reduced weight."""
from __future__ import annotations

import math
from collections import defaultdict

HALF_LIFE_VALUE = 90.0    # game-days: how fast a player's production numbers forget
HALF_LIFE_ROLE = 6.0      # game-days: how fast expected minutes forget (roles change quickly)
PRIOR_MIN = 250.0         # minutes of league-replacement production every player starts with
REPL_GMSC48 = 10.0        # production per 48 minutes of a replacement-level player
PRIOR_MIN_PM = 900.0      # plus-minus is noisy: shrink it much harder
INJURY_DNP = "injury"


def game_score(p: dict) -> float:
    """Hollinger's Game Score: one number for a box-score line."""
    return (p["pts"] + 0.4 * p["fgm"] - 0.7 * p["fga"] - 0.4 * (p["fta"] - p["ftm"]) + 0.7 * p["oreb"]
            + 0.3 * p["dreb"] + p["stl"] + 0.7 * p["ast"] + 0.7 * p["blk"] - 0.4 * p["pf"] - p["tov"])


def possessions(rows: list[dict]) -> float:
    fga = sum(p.get("fga", 0) for p in rows)
    return fga - sum(p.get("oreb", 0) for p in rows) + sum(p.get("tov", 0) for p in rows) + 0.44 * sum(p.get("fta", 0) for p in rows)


class Tracker:
    def __init__(self):
        self.clock = 0            # game-days seen
        self.last_day = None
        # player -> decayed sums
        self.v = defaultdict(lambda: {"w_min": 0.0, "gmsc": 0.0, "pts": 0.0, "pm": 0.0, "t": 0})
        self.role = defaultdict(lambda: {"w": 0.0, "min": 0.0, "t": 0, "start": 0.0})
        self.team_of: dict[str, str] = {}
        self.name: dict[str, str] = {}
        self.last_game: dict[str, str] = {}      # team -> date of its last game
        self.played_last: dict[str, set] = {}    # team -> players who played its last game
        self.pace = defaultdict(lambda: {"w": 0.0, "poss": 0.0, "pts": 0.0, "opp": 0.0, "t": 0})

    # -- decay helpers
    def _decay(self, rec: dict, keys: tuple, hl: float) -> None:
        dt = self.clock - rec["t"]
        if dt > 0:
            f = 0.5 ** (dt / hl)
            for k in keys:
                rec[k] *= f
            rec["t"] = self.clock

    def tick(self, day: str) -> None:
        if day != self.last_day:
            self.clock += 1
            self.last_day = day

    def update(self, g: dict) -> None:
        """Add one finished game."""
        self.tick(g["date"][:10])
        margin = {g["h"]: g["hs"] - g["as"], g["a"]: g["as"] - g["hs"]}
        by_team = defaultdict(list)
        for p in g["players"]:
            by_team[p["team"]].append(p)
        for team, rows in by_team.items():
            opp = g["a"] if team == g["h"] else g["h"]
            played = set()
            for p in rows:
                pid = p["pid"]
                self.name[pid] = p.get("name") or pid
                self.team_of[pid] = team
                r = self.role[pid]
                self._decay(r, ("w", "min", "start"), HALF_LIFE_ROLE)
                if p.get("dnp"):
                    if "COACH" in (p["dnp"] or "").upper():
                        r["w"] += 1.0  # healthy scratch: a zero-minute game for his role
                    continue
                if p["min"] <= 0:
                    continue
                played.add(pid)
                r["w"] += 1.0
                r["min"] += p["min"]
                r["start"] += 1.0 if p.get("starter") else 0.0
                v = self.v[pid]
                self._decay(v, ("w_min", "gmsc", "pts", "pm"), HALF_LIFE_VALUE)
                v["w_min"] += p["min"]
                v["gmsc"] += game_score(p)
                v["pts"] += p["pts"]
                v["pm"] += p.get("pm", 0.0)
            self.played_last[team] = played
            self.last_game[team] = g["date"]
            pc = self.pace[team]
            self._decay(pc, ("w", "poss", "pts", "opp"), HALF_LIFE_VALUE / 2)
            pc["w"] += 1.0
            pc["poss"] += possessions(rows)
            pc["pts"] += g["hs"] if team == g["h"] else g["as"]
            pc["opp"] += g["as"] if team == g["h"] else g["hs"]

    # -- per-player numbers
    def gmsc48(self, pid: str) -> float:
        v = self.v.get(pid)
        if not v:
            return REPL_GMSC48
        return 48 * (v["gmsc"] + PRIOR_MIN * REPL_GMSC48 / 48) / (v["w_min"] + PRIOR_MIN)

    def pts48(self, pid: str) -> float:
        v = self.v.get(pid)
        if not v:
            return 15.0
        return 48 * (v["pts"] + PRIOR_MIN * 15.0 / 48) / (v["w_min"] + PRIOR_MIN)

    def pm48(self, pid: str) -> float:
        v = self.v.get(pid)
        if not v:
            return -2.0
        return 48 * (v["pm"] + PRIOR_MIN_PM * -2.0 / 48) / (v["w_min"] + PRIOR_MIN_PM)

    def exp_minutes(self, pid: str) -> float:
        r = self.role.get(pid)
        if not r or r["w"] <= 0:
            return 0.0
        f = 0.5 ** ((self.clock - r["t"]) / HALF_LIFE_ROLE)  # stale roles fade
        return (r["min"] / r["w"]) * min(1.0, 0.25 + f)

    def roster(self, team: str) -> list[str]:
        return [pid for pid, t in self.team_of.items() if t == team]

    def team_vector(self, team: str, out: set[str], doubt: dict[str, float] | None = None) -> dict:
        """Expected-minutes-weighted production for a team, with `out` players removed and their
        minutes handed to the rest in proportion to their own minutes (a full game is 240)."""
        doubt = doubt or {}
        mins = {}
        for pid in self.roster(team):
            m = self.exp_minutes(pid)
            if m <= 0.5 or pid in out:
                continue
            mins[pid] = m * (1 - doubt.get(pid, 0.0))
        full = {pid: self.exp_minutes(pid) for pid in self.roster(team) if self.exp_minutes(pid) > 0.5}
        tot = sum(mins.values())
        if tot <= 0:
            return {"gmsc": 0.0, "pts": 0.0, "pm": 0.0, "lost_gmsc": 0.0, "n": 0}
        scale = 240.0 / tot
        top = sorted(mins, key=lambda p: -mins[p])
        res = {"gmsc": 0.0, "pts": 0.0, "pm": 0.0, "n": len(mins)}
        for pid in top:
            # extra minutes go mostly to the existing rotation, but no one plays more than 42
            m = min(42.0, mins[pid] * scale)
            res["gmsc"] += m / 48 * self.gmsc48(pid)
            res["pts"] += m / 48 * self.pts48(pid)
            res["pm"] += m / 48 * self.pm48(pid) / 5
        # what the team would look like with everyone in
        tf = sum(full.values()) or 1.0
        full_g = sum(min(42.0, m * 240 / tf) / 48 * self.gmsc48(p) for p, m in full.items())
        res["lost_gmsc"] = full_g - res["gmsc"]
        return res

    def pace_of(self, team: str) -> dict | None:
        pc = self.pace.get(team)
        if not pc or pc["w"] < 1:
            return None
        return {"poss": pc["poss"] / pc["w"], "pts": pc["pts"] / pc["w"], "opp": pc["opp"] / pc["w"], "w": pc["w"]}


def rest_days(last_iso: str | None, start_iso: str) -> float | None:
    if not last_iso:
        return None
    from core.util import parse_iso
    return (parse_iso(start_iso) - parse_iso(last_iso)).total_seconds() / 86400
