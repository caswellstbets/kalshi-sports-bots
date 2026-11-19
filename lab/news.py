"""Model B, "Injury News": bets only when the injury report changes and Kalshi has not caught up.

Each run saves every upcoming game's injury picture (each rotation player's chance of sitting)
and the Kalshi home price. When a later run finds that a player who plays 15+ minutes has changed
status (say Questionable to Out), it values the change with the Rotation model's player ratings,
moves the price from before the news by that amount, and compares the result with tonight's price.
If the market has moved less than the news is worth, the gap is the edge. No news, no bet.

Thesis, from the back-test (BACKTEST_NBA_MODELS.md): when a rotation player sat unexpectedly last
season, Kalshi's price 3 hours before tip-off had moved about 60% of what the player ratings say the
absence was worth, and about 80% by the close. Whether the rest is the market being slow or the
ratings being too generous is what this model tests. Winner markets only, one decision per game."""
from __future__ import annotations

import os
from statistics import NormalDist

from core.util import iso, read_json, write_json

from . import rotation, slate

N = NormalDist()
MIN_MINUTES = 15.0      # players this involved count as news
MIN_CHANGE = 0.35       # change in the chance he sits that counts as news
MIN_MARGIN = 1.0        # points the news must be worth before the model looks at the price
MAX_HOURS = 12.0        # news is acted on from 12 hours to 10 minutes before the start


def snap_path(root: str) -> str:
    return os.path.join(root, "data", "nba_news", "snapshots.json")


def outs_for(tr, inj: dict, team: str) -> dict[str, float]:
    return {i["pid"]: i["p_out"] for i in inj.get(team, []) if i["pid"] and i["p_out"] > 0}


def scan(root: str, games: list[dict], tr, impact: dict, inj: dict, now, decided: set, dry: bool = False):
    """Yields (game, forecast, why) for games with fresh news worth a look; saves new snapshots."""
    snaps = read_json(snap_path(root), {})
    prm = rotation.params()
    sd = prm["margin"]["sd"]
    keep = {}
    for g in games:
        h, a = g["g"]["home"]["id"], g["g"]["away"]["id"]
        p_now = slate.home_mid(g)
        cur = {"ts": iso(now), "p_home": p_now, "outs": {h: outs_for(tr, inj, h), a: outs_for(tr, inj, a)}}
        prev = snaps.get(g["gid"])
        keep[g["gid"]] = cur
        if not prev or p_now is None or prev.get("p_home") is None or g["gid"] in decided:
            continue
        if not (10 <= g["mins"] <= MAX_HOURS * 60):
            keep[g["gid"]] = cur
            continue
        changes = []
        for t in (h, a):
            old, new = prev["outs"].get(t, {}), cur["outs"][t]
            for pid in set(old) | set(new):
                d = new.get(pid, 0.0) - old.get(pid, 0.0)
                if abs(d) >= MIN_CHANGE and tr.exp_minutes(pid) >= MIN_MINUTES:
                    changes.append((t, pid, old.get(pid, 0.0), new.get(pid, 0.0)))
        if not changes:
            continue
        f_old = rotation.features(tr, impact, h, a, g["start"], prev["outs"].get(h, {}), prev["outs"].get(a, {}))
        f_new = rotation.features(tr, impact, h, a, g["start"], cur["outs"][h], cur["outs"][a])
        if not f_old or not f_new:
            continue
        dm = prm["margin"]["strength"] * (f_new["strength_diff"] - f_old["strength_diff"])
        if abs(dm) < MIN_MARGIN:
            continue
        p_prev = min(max(prev["p_home"], 0.02), 0.98)
        expected = N.cdf(N.inv_cdf(p_prev) + dm / sd)
        if (expected - p_now) * dm <= 0:
            continue  # the price already moved as far as the news is worth (or further): not this model's bet
        names = {pid: tr.name.get(pid, pid) for _, pid, _, _ in changes}
        home, away = slate.full_name(g["g"]["home"]), slate.full_name(g["g"]["away"])
        news = "; ".join(f"{names[pid]} ({home if t == h else away}) {o:.0%} to {n:.0%} likely to sit" for t, pid, o, n in changes)
        why = (f"News since {prev['ts'][11:16]} UTC: {news}. Worth {dm:+.1f} points to {home} by the player ratings, so a "
               f"{p_prev:.0%} price should now be about {expected:.0%}; Kalshi is at {p_now:.0%}.")
        yield g, {"p_home": expected, "news": news, "dm": dm, "p_before": p_prev}, why
    if not dry:
        write_json(snap_path(root), keep)
