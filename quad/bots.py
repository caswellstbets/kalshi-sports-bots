"""The four new bots. Each turns the same slate of signals into its own expected home margin and
total, by its own rule. All numbers are relative to Kalshi's price: a bot that sees nothing returns
Kalshi's own numbers and so finds no edge. The sportsbook line is weighted at 5% or less in every bot.

Every value here was set before any of these bots made a pick and is a GUESS until graded."""
from __future__ import annotations

from .read import spot_points

BOTS = {
    "consensus": "Consensus",
    "scout": "Full Scout",
    "situational": "Situational",
    "movement": "Line Movement",
}

# Consensus: weight of each signal's disagreement with the Kalshi price, and the size a disagreement
# needs to count as a vote. Weights sum to 1 for margins.
CONS_W = {"read": 0.35, "stats": 0.20, "news": 0.15, "spots": 0.15, "move": 0.10, "book": 0.05}
CONS_W_TOTAL = {"read": 0.45, "stats": 0.30, "spots": 0.20, "book": 0.05}
VOTE_MIN = {"read": 1.0, "stats": 1.5, "news": 0.5, "spots": 0.5, "move": 1.0, "book": 1.0}
CONS_MIN_VOTES, CONS_MAX_AGAINST = 3, 1
CONS_MIN_VOTES_TOTAL = 2

SCOUT_TRUST = {"margin": 0.6, "total": 0.45}  # how far toward Claude's read from the Kalshi price

SIT_NEWS_W = 0.5

MOVE_MIN = 1.5        # points the Kalshi-implied margin must have moved since its first quote
MOVE_FOLLOW = 0.5     # follow a move that a stats, news or read signal backs: half of it again
MOVE_FADE = -0.35     # fade a big move (3+ points) nothing explains
MOVE_FADE_MIN = 3.0


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def signals(c: dict, read: dict | None) -> dict:
    km, kt = c["kalshi"]["margin"], c["kalshi"]["total"]
    sm, stt = spot_points(read)[:2]
    rest_m = sum(s["pts"] for s in c["rest"])
    rest_t = sum(s["total"] for s in c["rest"])
    d = {
        "stats": c["st"]["margin"] - km,
        "book": None if c["book"]["margin"] is None else c["book"]["margin"] - km,
        "move": c["move"],
        "spots": sm + rest_m,
        "news": read["news"] if read else None,
        "read": None if not read else read["margin"] - km,
    }
    dt = {
        "stats": None if kt is None else c["st"]["total"] - kt,
        "book": None if kt is None or c["book"]["total"] is None else c["book"]["total"] - kt,
        "spots": stt + rest_t,
        "read": None if not read or kt is None else read["total"] - kt,
    }
    return {"margin": d, "total": dt}


def consensus(c, read, sg):
    d = sg["margin"]
    votes = {k: _sign(v) for k, v in d.items() if v is not None and abs(v) >= VOTE_MIN[k]}
    side = _sign(sum(votes.values()))
    pro = [k for k, v in votes.items() if v == side and side]
    con = [k for k, v in votes.items() if v == -side and side]
    out = {"margin": None, "total": None, "why": [], "agree": len(pro)}
    if side and len(pro) >= CONS_MIN_VOTES and len(con) <= CONS_MAX_AGAINST:
        delta = sum(CONS_W[k] * (d[k] or 0) for k in CONS_W)
        if _sign(delta) == side:
            out["margin"] = c["kalshi"]["margin"] + delta
            out["why"].append(f"{len(pro)} signals agree ({', '.join(pro)})" + (f", {len(con)} against ({', '.join(con)})" if con else ""))
    t = sg["total"]
    if c["kalshi"]["total"] is not None:
        tv = {k: _sign(v) for k, v in t.items() if v is not None and abs(v) >= (1.5 if k != "spots" else 0.5)}
        ts = _sign(sum(tv.values()))
        tpro = [k for k, v in tv.items() if v == ts and ts]
        tcon = [k for k, v in tv.items() if v == -ts and ts]
        if ts and len(tpro) >= CONS_MIN_VOTES_TOTAL and not tcon:
            delta = sum(CONS_W_TOTAL[k] * (t[k] or 0) for k in CONS_W_TOTAL)
            if _sign(delta) == ts:
                out["total"] = c["kalshi"]["total"] + delta
                out["why"].append(f"total: {len(tpro)} signals agree ({', '.join(tpro)})")
                out["agree_total"] = len(tpro)
    return out


def scout(c, read, sg):
    if not read:
        return {"margin": None, "total": None, "why": []}
    km, kt = c["kalshi"]["margin"], c["kalshi"]["total"]
    return {"margin": km + SCOUT_TRUST["margin"] * (read["margin"] - km),
            "total": None if kt is None else kt + SCOUT_TRUST["total"] * (read["total"] - kt),
            "why": [read["summary"]]}


def situational(c, read, sg):
    d = sg["margin"]
    spots = d["spots"] or 0.0
    news = d["news"] or 0.0
    out = {"margin": None, "total": None, "why": []}
    names = [s["text"] for s in c["rest"]] + spot_points(read)[2]
    if abs(spots) >= 1.0 and (_sign(d["stats"]) == _sign(spots) and abs(d["stats"]) >= 1.0 or _sign(news) == _sign(spots)):
        out["margin"] = c["kalshi"]["margin"] + spots + SIT_NEWS_W * news + 0.05 * (d["book"] or 0)
        out["why"].append("spots: " + "; ".join(names))
    ts = sg["total"]["spots"] or 0.0
    if abs(ts) >= 1.5 and c["kalshi"]["total"] is not None and (_sign(sg["total"]["stats"] or 0) == _sign(ts)):
        out["total"] = c["kalshi"]["total"] + ts
        out["why"].append("total spots: " + "; ".join(names))
    return out


def movement(c, read, sg):
    d = sg["margin"]
    mv = d["move"]
    out = {"margin": None, "total": None, "why": []}
    if mv is None or abs(mv) < MOVE_MIN:
        return out
    backers = [k for k in ("stats", "news", "read") if d[k] is not None and abs(d[k]) >= VOTE_MIN[k] and _sign(d[k]) == _sign(mv)]
    if read and read.get("explains_move") == "yes":
        backers.append("known news")
    if backers:
        out["margin"] = c["kalshi"]["margin"] + MOVE_FOLLOW * mv + 0.05 * (d["book"] or 0)
        out["why"].append(f"Kalshi moved {mv:+.1f} pts toward the home side since opening, backed by {', '.join(backers)}")
        out["agree"] = len(backers)
    elif read and read.get('sheet', {}).get('kalshi_move_since_open') is not None and abs(mv) >= MOVE_FADE_MIN:
        # only fade once Claude has seen the move and checked the news for it
        out["margin"] = c["kalshi"]["margin"] + MOVE_FADE * mv
        out["why"].append(f"Kalshi moved {mv:+.1f} pts since opening with no stats, news or read behind it; fading part of it")
        out["agree"] = 0
    return out


RULES = {"consensus": consensus, "scout": scout, "situational": situational, "movement": movement}
