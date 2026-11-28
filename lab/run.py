"""One pass of the three lab NBA models. Paper only: a "trade" is a line in a file.

    python3 run_lab.py            grade, forecast, trade, rebuild NBA_MODELS.md
    python3 run_lab.py --dry-run  look only

Each model decides once per game, at the first run between 3 hours and 10 minutes before the
start, and that decision (pick or pass, with its forecast) is final. A run prints
SCOUT READ NEEDED for games in that window without a Scout read; answer with
`python3 -m lab.scout read ...` and run again."""
from __future__ import annotations

import os
import traceback

from core import kalshi
from core.util import append_jsonl, iso, now_utc, r4, read_json, write_json

from . import boxscores, decide, ledger, slate
from .ledger import MODELS

WINDOW_MIN, WINDOW_MAX = 10.0, 180.0   # minutes before the start


def in_window(game: dict) -> bool:
    return WINDOW_MIN <= game["mins"] <= WINDOW_MAX


def label_for(game: dict, pick: dict) -> str:
    return slate.describe(game, pick["m"], pick["mtype"], pick["side"])


def decide_and_record(root, model, game, fc, w, now, why, types, out, dry, tier_cap=None, only=None):
    """Price the game with a model's forecast, take the best contract (or pass), and save both."""
    if only is not None:  # the Scout names its own contract; check it against its own numbers
        cands = [c for c in decide.contracts(game, fc, w, types)
                 if c["m"]["ticker"] == only["ticker"] and c["side"] == only["side"]]
        pick = None
        for c in cands:
            t = decide.tier_for(c["edge1"])
            if not t:
                break
            order = [x[0] for x in decide.TIERS]
            if tier_cap and order.index(tier_cap) > order.index(t[0]):
                t = next(x[0:3:2] for x in decide.TIERS if x[0] == tier_cap)
            sz = decide.size(c["p"], c["ask"], c["offered"], t[1])
            if sz and sz["edge"] >= decide.MIN_EDGE:
                pick = {**c, "sz": sz, "tier": t[0]}
    else:
        pick = decide.best(game, fc, w, types)
    pk = slate.home_mid(game)
    tot = slate.main_total(game)
    dec = {"model": model, "game_id": game["gid"], "game": game["name"], "start": game["start"], "ts": iso(now),
           "mins_to_start": round(game["mins"]), "version": ledger.VERSION,
           "p_home": r4(fc.get("p_home")), "margin": r4(fc.get("margin")), "total": r4(fc.get("total")),
           "kalshi_home": r4(pk), "kalshi_total_line": None if not tot else tot["strike"],
           "kalshi_total_over": None if not tot else r4(kalshi.mid(tot)), "pick": None, "why": why}
    if pick:
        t = ledger.new_trade(model, game, pick, label_for(game, pick), now, fc, why)
        dec["pick"] = {"ticker": t["ticker"], "side": t["side"], "label": t["label"], "tier": t["tier"], "edge": t["edge"]}
        out["trades"].setdefault(model, []).append(t)
        out["track"][t["ticker"]] = {"game_id": game["gid"], "game": game["name"], "start": game["start"],
                                     "mtype": t["mtype"], "label": slate.describe(game, pick["m"], pick["mtype"], "yes"),
                                     "p_kalshi": r4(kalshi.mid(pick["m"]))}
        print(f"  [{MODELS[model]['title']}] {t['tier'].upper()} {game['name']}: {t['label']} x{t['contracts']} at "
              f"{t['price']:.2f} | model {t['p_final'] * 100:.1f}% | edge {t['edge'] * 100:+.1f} | {t['units']:.2f}u")
    else:
        print(f"  [{MODELS[model]['title']}] pass {game['name']}")
    out["decisions"].append(dec)


def run(root: str, dry: bool = False) -> dict:
    now = now_utc()
    out = {"trades": {}, "decisions": [], "track": {}, "sheets": {}, "errors": []}
    try:
        added = boxscores.update(root) if not dry else 0
    except Exception:
        added = 0
        traceback.print_exc()
    log = {"ts": iso(now), "dry": dry, "boxscores_added": added}
    log.update(ledger.settle(root, now, dry))
    games = slate.load(max_hours=30)  # tomorrow's games too, so Injury News has a before picture
    done = ledger.decisions(root)
    # latest price for every contract already tracked, so the last run before the start is the close
    tracked = read_json(ledger.lab(root, "tracking.json"), {})
    for g in games:
        for mtype in ("ml", "spread", "total"):
            for m in g["kg"][mtype]:
                if m["ticker"] in tracked:
                    out["track"][m["ticker"]] = {"p_kalshi": r4(kalshi.mid(m))}
    window = [g for g in games if in_window(g)]
    log.update({"games": len(games), "in_window": len(window)})
    print(f"[lab] {len(games)} NBA games in the next 30h, {len(window)} inside the 3-hour decision window")

    # Models A and B share the player ratings and tonight's injury report
    need_a = [g for g in window if ("rotation", g["gid"]) not in done]
    try:
        from . import news, rotation_live
        tr, impact = rotation_live.build(root)
        inj = slate.injuries()
    except Exception:
        tr = None
        out["errors"].append("player ratings")
        traceback.print_exc()
    if tr is not None and need_a:
        try:  # Model A: Rotation
            for g, fc, why in rotation_live.forecasts(need_a, tr, impact, inj):
                decide_and_record(root, "rotation", g, fc, rotation_live.TRUST, now, why, rotation_live.TYPES, out, dry)
        except Exception:
            out["errors"].append("rotation")
            traceback.print_exc()
    if tr is not None:
        try:  # Model B: Injury News (looks at every game up to 12 hours out, acts only on fresh news)
            decided = {gid for (m, gid) in done if m == "news"}
            for g, fc, why in news.scan(root, games, tr, impact, inj, now, decided, dry):
                decide_and_record(root, "news", g, fc, 1.0, now, why, ("ml",), out, dry)
        except Exception:
            out["errors"].append("news")
            traceback.print_exc()
    # Model C: Scout (Claude in session)
    try:
        from . import scout, scout_sheet
        rd = scout.reads()
        need = [g for g in window if ("scout", g["gid"]) not in done and g["gid"] not in rd]
        if need:
            out["sheets"] = scout_sheet.build(root, need)
        for g in window:
            r = rd.get(g["gid"])
            if ("scout", g["gid"]) in done or not r:
                continue
            fc = {"p_home": r["p_home"], "margin": r["margin"], "total": r["total"],
                  "sd_margin": scout.SD_MARGIN, "sd_total": scout.SD_TOTAL}
            why = r["why"] + (f" What the price misses: {r['missing']}" if r.get("missing") else "")
            if r.get("pick"):
                decide_and_record(root, "scout", g, fc, 1.0, now, why, ("ml", "spread", "total"), out, dry,
                                  tier_cap=r["pick"]["confidence"], only=r["pick"])
            else:
                decide_and_record(root, "scout", g, fc, 1.0, now, why, (), out, dry)
    except Exception:
        out["errors"].append("scout")
        traceback.print_exc()

    for d in out["decisions"]:  # every forecast game's home-win contract is graded for accuracy
        g = next(x for x in games if x["gid"] == d["game_id"])
        hm = slate.home_ml(g)
        if hm:
            out["track"][hm["ticker"]] = {"game_id": g["gid"], "game": g["name"], "start": g["start"], "mtype": "ml",
                                          "label": f"{slate.full_name(g['g']['home'])} to win", "home_ml": True,
                                          "p_kalshi": r4(kalshi.mid(hm))}
    log.update({"decisions": len(out["decisions"]), "new_trades": sum(len(v) for v in out["trades"].values()),
                "scout_sheets": len(out["sheets"]), "errors": out["errors"]})
    if not dry:
        append_jsonl(ledger.lab(root, "decisions.jsonl"), out["decisions"])
        for model, ts in out["trades"].items():
            append_jsonl(os.path.join(ledger.mdir(root, model), "trades.jsonl"), ts)
        ledger.track(root, {k: v for k, v in out["track"].items() if v})
        os.makedirs(ledger.mdir(root, "scout"), exist_ok=True)
        write_json(os.path.join(ledger.mdir(root, "scout"), "sheets.json"), out["sheets"])
        append_jsonl(ledger.lab(root, "run_log.jsonl"), [log])
    print(f"[lab] decisions: {len(out['decisions'])}, new paper trades: {log['new_trades']}, settled: {log['settled']}, "
          f"Scout reads needed: {len(out['sheets'])}")
    return out

