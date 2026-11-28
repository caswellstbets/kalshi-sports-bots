"""Files for the lab models. Each model has its own ledger (data/nba_<model>/trades.jsonl and
settlements.jsonl, same layout as the current bots); data/nba_lab/ holds what they share."""
from __future__ import annotations

import os
import uuid
from datetime import timedelta

from core import kalshi, pricing
from core.util import append_jsonl, iso, parse_iso, r4, read_json, read_jsonl, write_json

MODELS = {
    "rotation": {"title": "Rotation", "what": "player availability and player impact, numbers only"},
    "news": {"title": "Injury News", "what": "fresh injury-report changes the Kalshi price has not caught up with"},
    "scout": {"title": "Scout", "what": "Claude's full read of the game, prices in view"},
}
VERSION = "lab-1"


def mdir(root: str, model: str) -> str:
    return os.path.join(root, "data", f"nba_{model}")


def lab(root: str, name: str) -> str:
    return os.path.join(root, "data", "nba_lab", name)


def decisions(root: str) -> dict[tuple, dict]:
    """(model, game_id) -> the one decision-time forecast that counts."""
    out = {}
    for r in read_jsonl(lab(root, "decisions.jsonl")):
        out.setdefault((r["model"], r["game_id"]), r)
    return out


def trades(root: str, model: str) -> list[dict]:
    return read_jsonl(os.path.join(mdir(root, model), "trades.jsonl"))


def settlements(root: str, model: str) -> dict[str, dict]:
    return {s["trade_id"]: s for s in read_jsonl(os.path.join(mdir(root, model), "settlements.jsonl"))}


def new_trade(model: str, game: dict, pick: dict, label_: str, now, fc: dict, why: str) -> dict:
    sz, yes = pick["sz"], pick["side"] == "yes"
    return {"id": uuid.uuid4().hex[:12], "bot": f"nba_{model}", "model": model, "ts": iso(now), "version": VERSION,
            "game_id": game["gid"], "game": game["name"], "start": game["start"], "ticker": pick["m"]["ticker"],
            "mtype": pick["mtype"], "side": pick["side"], "label": label_, "price": pick["ask"], "bid": pick["bid"],
            "ask_size": pick["offered"], "contracts": sz["n"], "fee": sz["fee"], "cost": r4(sz["cost"]),
            "units": r4(sz["cost"] / 10.0), "p_kalshi": r4(pick["p_kalshi"]), "p_model": r4(pick["p_model"]),
            "p_final": r4(pick["p"]), "edge": r4(sz["edge"]), "confidence": pick["tier"], "tier": pick["tier"],
            "forecast": {k: (r4(v) if isinstance(v, float) else v) for k, v in fc.items() if k in ("p_home", "margin", "total")},
            "why": why, "strike": pick["m"].get("strike"), "yes_team": pick["m"].get("team_code")}


def track(root: str, tickers: dict[str, dict]) -> None:
    """Remember the latest pre-game Kalshi midpoint for every contract a model forecast or bought."""
    path = lab(root, "tracking.json")
    cur = read_json(path, {})
    for tk, row in tickers.items():
        old = cur.get(tk, {})
        if row.get("p_kalshi") is None:
            row["p_kalshi"] = old.get("p_kalshi")
        cur[tk] = {**old, **row}
    write_json(path, cur)


def settle(root: str, now, dry: bool = False) -> dict:
    """Grade every tracked contract whose game ended, and close every lab model's open trades."""
    path = lab(root, "tracking.json")
    cur = read_json(path, {})
    open_trades = {}
    for model in MODELS:
        st = settlements(root, model)
        open_trades[model] = [t for t in trades(root, model) if t["id"] not in st]
    cutoff = now - timedelta(hours=2, minutes=30)
    due = {tk for tk, r in cur.items() if parse_iso(r["start"]) < cutoff}
    due |= {t["ticker"] for ts in open_trades.values() for t in ts if parse_iso(t["start"]) < cutoff}
    if not due:
        return {"graded": 0, "settled": 0}
    live = kalshi.markets_by_ticker(sorted(due))
    graded, n_settled = [], 0
    for model, ts in open_trades.items():
        rows = []
        for t in ts:
            mk = live.get(t["ticker"])
            if not mk or parse_iso(t["start"]) >= cutoff:
                continue
            close_yes = (cur.get(t["ticker"]) or {}).get("p_kalshi")
            close = None if close_yes is None else (close_yes if t["side"] == "yes" else 1 - close_yes)
            if mk["result"] in ("yes", "no"):
                won = mk["result"] == t["side"]
                payout, outcome = (float(t["contracts"]) if won else 0.0), ("won" if won else "lost")
            elif mk["status"] in ("finalized", "settled"):
                payout, outcome = t["cost"] - t.get("fee", 0.0), "void"
            else:
                continue
            rows.append({"trade_id": t["id"], "ts": iso(now), "outcome": outcome, "payout": r4(payout),
                         "pnl": r4(payout - t["cost"]), "close_price": r4(close),
                         "clv": None if close is None else r4(close - t["price"])})
        n_settled += len(rows)
        if not dry:
            append_jsonl(os.path.join(mdir(root, model), "settlements.jsonl"), rows)
    for tk in list(cur):
        r = cur[tk]
        if parse_iso(r["start"]) >= cutoff:
            continue
        mk = live.get(tk)
        if mk and mk["result"] in ("yes", "no"):
            graded.append({**r, "ticker": tk, "result": 1 if mk["result"] == "yes" else 0, "graded_ts": iso(now)})
            del cur[tk]
        elif (mk and mk["status"] in ("finalized", "settled")) or now - parse_iso(r["start"]) > timedelta(days=5):
            del cur[tk]
    if not dry:
        append_jsonl(lab(root, "graded.jsonl"), graded)
        write_json(path, cur)
    return {"graded": len(graded), "settled": n_settled}


def fee_note() -> str:
    return "Kalshi taker fee 7% x price x (1 - price), rounded up per order (NBA series fee multiplier 1, checked Nov 16)."


__all__ = ["MODELS", "VERSION", "decisions", "trades", "settlements", "new_trade", "track", "settle", "pricing"]
