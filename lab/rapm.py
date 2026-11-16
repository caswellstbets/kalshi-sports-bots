"""Player impact for the Rotation model: a regularized adjusted plus-minus fit on game results.

Each finished game says: home margin - home court = sum over home players of (minutes/48 x impact)
minus the same for the away players. Solving that for every player at once, with each player's
impact pulled toward a box-score prior (Game Score per 48 minutes), separates a player from the
teammates he shares the floor with. Older games count less (half-life in NBA game-days)."""
from __future__ import annotations

import numpy as np

LAMBDA = 30.0       # strength of the pull toward the box-score prior, in game-equivalents
HALF_LIFE = 120.0   # game-days
BOX_WEIGHT = 0.3    # points of impact per point of Game Score per 48 above 15
HOME_EDGE = 2.5     # home court, points, removed before fitting
REPLACEMENT_SHARE = 0.0   # share of an absent player's minutes given to end-of-bench players (0 scored best in the back-test)
REPLACEMENT_IMPACT = -2.0 # impact per 48 of an end-of-bench player


def day_index(games: list[dict]) -> dict[str, int]:
    days = sorted({g["date"][:10] for g in games})
    return {d: i for i, d in enumerate(days)}


def prior(tracker, pid: str) -> float:
    return BOX_WEIGHT * (tracker.gmsc48(pid) - 15.0)


def fit(games: list[dict], tracker, now_index: int | None = None) -> dict[str, float]:
    """games: finished games (all before the forecast). tracker: a players.Tracker already updated
    with the same games (for the box-score prior). Returns player id -> impact in points per 48."""
    if len(games) < 50:
        return {}
    di = day_index(games)
    now_index = max(di.values()) + 1 if now_index is None else now_index
    pidx: dict[str, int] = {}
    rows = []
    for g in games:
        r = []
        for p in g["players"]:
            if p.get("min", 0) > 0:
                if p["pid"] not in pidx:
                    pidx[p["pid"]] = len(pidx)
                r.append((pidx[p["pid"]], (1 if p["team"] == g["h"] else -1) * p["min"] / 48))
        rows.append((di[g["date"][:10]], r, g["hs"] - g["as"] - (0 if g.get("neutral") else HOME_EDGE)))
    P, n = len(pidx), len(rows)
    A = np.zeros((n, P))
    y = np.zeros(n)
    w = np.zeros(n)
    for k, (d, r, yy) in enumerate(rows):
        for i, s in r:
            A[k, i] += s
        y[k] = yy
        w[k] = 0.5 ** ((now_index - d) / HALF_LIFE)
    pr = np.zeros(P)
    for pid, i in pidx.items():
        pr[i] = prior(tracker, pid)
    sw = np.sqrt(w)
    Aw = A * sw[:, None]
    yw = (y - A @ pr) * sw
    beta = pr + np.linalg.solve(Aw.T @ Aw + LAMBDA * np.eye(P), Aw.T @ yw)
    return {pid: float(beta[i]) for pid, i in pidx.items()}


def team_strength(tracker, impact: dict[str, float], team: str, p_out: dict[str, float]) -> dict:
    """Sum of minutes/48 x impact over the expected rotation. p_out: player id -> chance he sits.
    Missing minutes go to the rest of the rotation in proportion to their usual minutes (240 total,
    nobody above 42)."""
    mins = {}
    for pid in tracker.roster(team):
        m = tracker.exp_minutes(pid)
        if m > 0.5:
            mins[pid] = m
    full = dict(mins)
    exp = {pid: m * (1 - p_out.get(pid, 0.0)) for pid, m in mins.items()}

    def total(ms):
        tot = sum(ms.values())
        if tot <= 0:
            return 0.0, {}
        alloc = {pid: min(42.0, m * 240.0 / tot) for pid, m in ms.items()}
        return sum(a / 48 * impact.get(pid, prior(tracker, pid)) for pid, a in alloc.items()), alloc
    s_full, _ = total(full)
    # minutes the injured players would have played: some go to the rotation, some to the end of the bench
    missing = sum(full.values()) - sum(exp.values())
    tot_full = sum(full.values()) or 1.0
    repl_min = REPLACEMENT_SHARE * missing * 240.0 / tot_full
    if repl_min > 0 and sum(exp.values()) > 0:
        scale = (240.0 - repl_min) / 240.0
        s_rot, alloc = total(exp)
        s_exp = s_rot * scale + repl_min / 48 * REPLACEMENT_IMPACT
        alloc = {pid: a * scale for pid, a in alloc.items()}
    else:
        s_exp, alloc = total(exp)
    return {"strength": s_exp, "full_strength": s_full, "minutes": alloc}
