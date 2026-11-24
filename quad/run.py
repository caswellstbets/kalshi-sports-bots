"""One run of the four new bots: settle finished picks, build the slate, list games that still need
Claude's read, and place paper picks. Paper only: nothing here can place an order.

    python3 run_quad.py              normal run
    python3 run_quad.py --dry-run    look only
"""
from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import timedelta
from zoneinfo import ZoneInfo

from core import engine, kalshi, pricing
from core.util import norm_cdf, norm_inv, append_jsonl, iso, now_utc, parse_iso, r4, read_json, read_jsonl, write_json
from . import slate as slate_mod
from .bots import BOTS, RULES, signals
from .read import DIR, is_stale, reads

CT = ZoneInfo("America/Chicago")
BANKROLL, UNIT = 1000.0, 10.0
HIGH_EDGE, MID_EDGE, LOW_EDGE = 0.06, 0.03, 0.01
KELLY = 0.125
DAILY_TARGET = 2          # soft: fill to this many picks per bot per day with Low picks
FILL_HOURS = 4            # a Low fill-in is only taken for games starting within this many hours
READ_HOURS = {"cfb": 14, "nfl": 14, "nba": 12}


def bot_paths(bot):
    d = os.path.join(DIR, bot)
    return {"trades": os.path.join(d, "trades.jsonl"), "settle": os.path.join(d, "settlements.jsonl"), "dir": d}


def live_trades(bot):
    """Trades minus withdrawn ones (a withdrawn pick never happened)."""
    gone = {s["trade_id"] for s in read_jsonl(bot_paths(bot)["settle"]) if s["outcome"] == "withdrawn"}
    return [t for t in read_jsonl(bot_paths(bot)["trades"]) if t["id"] not in gone]


def settle(now, dry):
    quotes = read_json(os.path.join(DIR, "last_quotes.json"), {})
    n = 0
    for bot in BOTS:
        p = bot_paths(bot)
        done = {s["trade_id"] for s in read_jsonl(p["settle"])}
        due = [t for t in read_jsonl(p["trades"]) if t["id"] not in done and parse_iso(t["start"]) < now - timedelta(hours=2)]
        if not due:
            continue
        live = kalshi.markets_by_ticker([t["ticker"] for t in due])
        rows = []
        for t in due:
            mk = live.get(t["ticker"])
            if not mk:
                continue
            q = quotes.get(t["ticker"])
            close = None if q is None else (q if t["side"] == "yes" else 1 - q)
            if mk["result"] in ("yes", "no"):
                won = mk["result"] == t["side"]
                pay = float(t["contracts"]) if won else 0.0
                out = "won" if won else "lost"
            elif mk["status"] in ("finalized", "settled"):
                pay, out = t["cost"] - t["fee"], "void"
            else:
                continue
            rows.append({"trade_id": t["id"], "ts": iso(now), "outcome": out, "payout": r4(pay), "pnl": r4(pay - t["cost"]),
                         "close_price": r4(close), "clv": None if close is None else r4(close - t["price"])})
        n += len(rows)
        if not dry:
            append_jsonl(p["settle"], rows)
    return n


def best_pick(cfg, c, bot_out):
    rows = engine.price_markets(cfg, c["g"], c["kg"], c["home_code"], c["st"], c["book"], None, None)
    # Each contract keeps its own Kalshi price as the base, shifted by the bot's disagreement with
    # Kalshi (in points, turned into z-units). So a bot that agrees with Kalshi never "finds" an
    # edge from Kalshi's winner, spread and total markets disagreeing with each other.
    for r in rows:
        key = "total" if r["mtype"] == "total" else "margin"
        mu, base = bot_out[key], c["kalshi"][key]
        pk = r["p_kalshi"]
        if mu is None or base is None or pk is None:
            r["p_trade"] = None
            continue
        sd = cfg.sd_total if key == "total" else cfg.sd_margin
        sign = 1 if key == "total" or r["m"]["team_code"] == c["home_code"] else -1
        r["p_trade"] = norm_cdf(norm_inv(min(max(pk, 0.01), 0.99)) + sign * (mu - base) / sd)
    best = None
    for cand in engine.candidates(cfg, rows):
        cost1 = cand["ask"] + pricing.fee(100, cand["ask"]) / 100
        edge = cand["p"] - cost1
        if best is None or edge > best[1]:
            best = (cand, edge)
    return best


def size(cand, tier):
    cost1 = cand["ask"] + pricing.fee(100, cand["ask"]) / 100
    if tier == "High":
        units = min(2.0, max(1.0, BANKROLL * KELLY * pricing.kelly(cand["p"], cost1) / UNIT))
        why = f"High: edge of {(cand['p'] - cost1) * 100:.1f} pts, 1/8 Kelly gives {units:.2f}u (floor 1u, cap 2u)"
    elif tier == "Mid":
        units, why = 0.5, f"Mid: edge of {(cand['p'] - cost1) * 100:.1f} pts (3 to 6), fixed half unit"
    else:
        units, why = 0.25, f"Low: daily fill-in, edge of {(cand['p'] - cost1) * 100:.1f} pts (1 to 3), quarter unit"
    n = int(min(units * UNIT / cost1, cand["size"]))
    if n < 1:
        return None
    fee = pricing.fee(n, cand["ask"])
    return {"n": n, "fee": fee, "cost": n * cand["ask"] + fee, "why": why}


def run(root, dry=False, sports=("cfb", "nfl", "nba"), verbose=True):
    now = now_utc()
    os.makedirs(DIR, exist_ok=True)
    settled = settle(now, dry)
    rd = reads()
    sheets, new = {}, {b: [] for b in BOTS}
    quotes = read_json(os.path.join(DIR, "last_quotes.json"), {})
    day = now.astimezone(CT).date()
    trades = {b: live_trades(b) for b in BOTS}
    today = {b: sum(1 for t in trades[b] if parse_iso(t["ts"]).astimezone(CT).date() == day) for b in BOTS}
    held = {t["ticker"] for b in BOTS for t in trades[b]}
    for sport in sports:
        cfg = slate_mod.CONFIGS[sport]
        try:
            games = slate_mod.build(sport, root, now)
        except Exception as e:  # one sport's data problem must not stop the others
            print(f"[{sport}] slate failed: {e}")
            continue
        if verbose:
            print(f"[{sport}] {len(games)} tradeable games in window")
        fills = {b: [] for b in BOTS}
        for c in games:
            k = f"{sport}:{c['game_id']}"
            read = rd.get(k)
            if read and is_stale(read, c["kalshi"]["margin"]):
                read = None  # Kalshi moved a lot since the read: news it never saw. Needs a fresh read.
                sheets[k] = {**slate_mod.sheet(c), "stale_read": True}
            elif not read:
                sheets[k] = slate_mod.sheet(c)
            sg = signals(c, read)
            for row in engine.price_markets(cfg, c["g"], c["kg"], c["home_code"], c["st"], c["book"], None, None):
                if row["m"]["ticker"] in held and row["p_kalshi"] is not None:
                    quotes[row["m"]["ticker"]] = r4(row["p_kalshi"])
            for bot, rule in RULES.items():
                if any(t["game_id"] == c["game_id"] for t in trades[bot] + new[bot]):
                    continue
                out = rule(c, read, sg)
                if out["margin"] is None and out["total"] is None:
                    continue
                bp = best_pick(cfg, c, out)
                if not bp:
                    continue
                cand, edge = bp
                tier = "High" if edge >= HIGH_EDGE else "Mid" if edge >= MID_EDGE else None
                if tier == "High" and bot == "consensus" and out.get("agree_total" if cand["mtype"] == "total" else "agree", 0) < 4:
                    tier = "Mid"
                if tier == "High" and bot == "movement" and not out.get("agree"):
                    tier = "Mid"  # a fade never gets a big stake
                if tier is None:
                    if edge >= LOW_EDGE and parse_iso(c["start"]) <= now + timedelta(hours=FILL_HOURS):
                        fills[bot].append((edge, c, cand, out, sg, read))
                    continue
                place(bot, cfg, c, cand, edge, tier, out, sg, read, now, new)
        for bot in BOTS:  # soft daily target: top up with the best Low picks
            for edge, c, cand, out, sg, read in sorted(fills[bot], key=lambda x: -x[0]):
                if today[bot] + len(new[bot]) >= DAILY_TARGET:
                    break
                if not any(t["game_id"] == c["game_id"] for t in new[bot]):
                    place(bot, cfg, c, cand, edge, "Low", out, sg, read, now, new)
    if not dry:
        for bot in BOTS:
            os.makedirs(bot_paths(bot)["dir"], exist_ok=True)
            append_jsonl(bot_paths(bot)["trades"], new[bot])
        write_json(os.path.join(DIR, "sheets.json"), sheets)
        write_json(os.path.join(DIR, "last_quotes.json"), quotes)
        append_jsonl(os.path.join(DIR, "run_log.jsonl"), [{"ts": iso(now), "settled": settled, "sheets": len(sheets),
                                                            **{f"new_{b}": len(v) for b, v in new.items()}}])
    for bot, ts in new.items():
        for t in ts:
            print(f"  {BOTS[bot]:13} {t['tier'].upper():4} {t['game']} ({t['start_ct']}): {t['label']} at {t['price'] * 100:.0f}c, "
                  f"{t['units']:.2f}u, edge {t['edge'] * 100:+.1f}")
    print(f"settled {settled}; games waiting for a read: {len(sheets)}")
    return {"new": new, "sheets": sheets}


def place(bot, cfg, c, cand, edge, tier, out, sg, read, now, new):
    sz = size(cand, tier)
    if not sz:
        return
    yes = cand["side"] == "yes"

    def sd(v):
        return None if v is None else r4(v if yes else 1 - v)
    t = {"id": uuid.uuid4().hex[:12], "bot": bot, "bot_name": BOTS[bot], "sport": c["sport"], "ts": iso(now),
         "version": "quad-1", "commit": engine.commit_hash(os.path.dirname(os.path.dirname(DIR))),
         "tier": tier, "game_id": c["game_id"], "game": c["game"], "start": c["start"],
         "start_ct": parse_iso(c["start"]).astimezone(CT).strftime("%a %-I:%M %p"),
         "ticker": cand["m"]["ticker"], "mtype": cand["mtype"], "side": cand["side"],
         "label": engine.label(cand["m"], cand["mtype"], cand["side"], c["home_code"], c["g"]),
         "price": cand["ask"], "contracts": sz["n"], "fee": sz["fee"], "cost": r4(sz["cost"]),
         "units": r4(sz["cost"] / UNIT), "p_bot": r4(cand["p"]), "p_kalshi": sd(cand["p_kalshi"]),
         "p_stats": sd(cand["p_stats"]), "p_book": sd(cand["p_book"]), "edge": r4(edge), "size_why": sz["why"],
         "why": out["why"], "bot_margin": r4(out["margin"]), "bot_total": r4(out["total"]),
         "kalshi_margin": r4(c["kalshi"]["margin"]), "kalshi_total": r4(c["kalshi"]["total"]),
         "signals": {k: {kk: r4(vv) for kk, vv in v.items()} for k, v in sg.items()},
         "read_summary": read["summary"] if read else None}
    new[bot].append(t)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", choices=["cfb", "nfl", "nba"])
    a = ap.parse_args(argv)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run(root, dry=a.dry_run, sports=(a.only,) if a.only else ("cfb", "nfl", "nba"))
    from .report import build
    if not a.dry_run:
        build(root)
