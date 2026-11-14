"""One run of one bot: grade what finished, price the upcoming slate, pull picks
that no longer hold up, place new paper trades, and save everything.

Nothing in here can place a real order. "Trade" always means a line written to
data/<bot>/trades.jsonl."""
from __future__ import annotations

import math
import os
import uuid
from datetime import timedelta

from . import ai, espn, kalshi, match, pricing, ratings
from .config import BotConfig
from .util import (ET, append_jsonl, iso, norm_inv, now_utc, parse_iso, r4, read_json,
                   read_jsonl, write_json)


def paths(cfg: BotConfig, root: str) -> dict:
    d = os.path.join(root, "data", cfg.name)
    return {
        "dir": d,
        "trades": os.path.join(d, "trades.jsonl"),            # append-only: every paper entry
        "settlements": os.path.join(d, "settlements.jsonl"),  # append-only: how each entry ended
        "open_preds": os.path.join(d, "open_predictions.json"),
        "graded": os.path.join(d, "graded_predictions.jsonl"),
        "ai_cache": os.path.join(d, "ai_cache.json"),
        "results_cache": os.path.join(d, "results_cache.json"),
        "run_log": os.path.join(d, "run_log.jsonl"),
        "sheets": os.path.join(d, "review_sheets.json"),      # games waiting for an AI review
    }


# ---------------------------------------------------------------- pricing one game

def side_price(m: dict, side: str) -> tuple[float, float, float]:
    """(ask, bid, contracts offered at the ask) for buying `side` of market m."""
    if side == "yes":
        return m["yes_ask"], m["yes_bid"], m["yes_ask_size"]
    return m["no_ask"], m["no_bid"], m["no_ask_size"]


def p_yes(m: dict, mtype: str, home_code: str, mu_margin: float | None, mu_total: float | None,
          cfg: BotConfig) -> float | None:
    """Probability the market resolves YES given an expected home margin / total."""
    if mtype == "total":
        return None if mu_total is None else pricing.p_margin_over(mu_total, m["strike"], cfg.sd_total)
    if mu_margin is None:
        return None
    is_home = m["team_code"] == home_code
    line = 0.0 if mtype == "ml" else float(m["strike"])
    if is_home:
        return pricing.p_margin_over(mu_margin, line, cfg.sd_margin)
    return 1 - pricing.p_margin_over(mu_margin, -line, cfg.sd_margin)


def label(m: dict, mtype: str, side: str, home_code: str, g: dict) -> str:
    """Plain-English name of a position, e.g. 'DEN -10.5' or 'Under 233.5'."""
    if mtype == "total":
        return f"{'Over' if side == 'yes' else 'Under'} {m['strike']}"
    home, away = g["home"]["abbr"], g["away"]["abbr"]
    team, other = (home, away) if m["team_code"] == home_code else (away, home)
    if mtype == "ml":
        return f"{team if side == 'yes' else other} to win"
    return f"{team} -{m['strike']}" if side == "yes" else f"{other} +{m['strike']}"


def kalshi_anchors(kg: dict, home_code: str, cfg: BotConfig) -> tuple[float | None, float | None]:
    """Expected margin and total implied by Kalshi's own prices (used when there is no sportsbook line)."""
    ps = []
    for m in kg["ml"]:
        md = kalshi.mid(m)
        if md is not None:
            ps.append(md if m["team_code"] == home_code else 1 - md)
    margin = cfg.sd_margin * norm_inv(sum(ps) / len(ps)) if ps else None
    best = None
    for m in kg["total"]:
        md = kalshi.mid(m)
        if md is not None and (best is None or abs(md - 0.5) < abs(best[0] - 0.5)):
            best = (md, m["strike"])
    total = best[1] + cfg.sd_total * norm_inv(best[0]) if best else None
    return margin, total


def blend(anchor: float | None, model: float | None, w_anchor: float) -> float | None:
    if anchor is None:
        return model
    if model is None:
        return anchor
    return w_anchor * anchor + (1 - w_anchor) * model


def forecast(cfg: BotConfig, g: dict, kg: dict, home_code: str, rt: dict, rt_form: dict | None = None) -> dict:
    """All the expected margins/totals for one game, before the AI step."""
    notes: list[str] = []
    model_margin = model_total = None
    pred = ratings.predict(rt, g["home"]["id"], g["away"]["id"], hfa=cfg.hfa, neutral=g["neutral"])
    enough = min(rt["games"].get(g["home"]["id"], 0), rt["games"].get(g["away"]["id"], 0)) >= cfg.min_rated_games
    if pred and enough:
        model_margin, model_total = pred
        form = ratings.predict(rt_form, g["home"]["id"], g["away"]["id"], hfa=cfg.hfa, neutral=g["neutral"]) if rt_form else None
        if form:  # season-long strength blended with how the teams have played lately
            model_margin = (1 - cfg.form_weight) * model_margin + cfg.form_weight * form[0]
            model_total = (1 - cfg.form_weight) * model_total + cfg.form_weight * form[1]
            notes.append(f"recent form alone says home by {form[0]:+.1f}, total {form[1]:.1f}")
        league_total = 2 * rt["mu"]
        model_total = league_total + cfg.total_scale * (model_total - league_total) + cfg.total_bias
        if cfg.situational:
            dm, dt, notes = cfg.situational({"game": g, "last": rt["last"]})
            model_margin += dm
            model_total += dt
    book = pricing.book_anchors(g["odds"], cfg.sd_margin, cfg.sd_total)
    k_margin, k_total = kalshi_anchors(kg, home_code, cfg)
    anchors = {
        "ml": book["margin_ml"] if book["margin_ml"] is not None else book["margin_spread"],
        "spread": book["margin_spread"] if book["margin_spread"] is not None else book["margin_ml"],
        "total": book["total"],
    }
    has_book = {k: v is not None for k, v in anchors.items()}
    if anchors["ml"] is None:
        anchors["ml"] = anchors["spread"] = k_margin
    if anchors["total"] is None:
        anchors["total"] = k_total
    return {
        "model": {"ml": model_margin, "spread": model_margin, "total": model_total},
        "book": {k: (anchors[k] if has_book[k] else None) for k in anchors},
        "has_book": has_book,
        "blend": {
            "ml": blend(anchors["ml"], model_margin, cfg.book_weight),
            "spread": blend(anchors["spread"], model_margin, cfg.book_weight),
            "total": blend(anchors["total"], model_total, cfg.book_weight),
        },
        "notes": notes,
    }


def price_markets(cfg: BotConfig, g: dict, kg: dict, home_code: str, fc: dict, adj: dict) -> list[dict]:
    """One row per Kalshi market with every probability the scorecard compares."""
    rows = []
    for mtype in ("ml", "spread", "total"):
        shift = adj["total_adj"] if mtype == "total" else adj["margin_adj"]
        for m in kg[mtype]:
            if m["status"] not in ("active", "open"):
                continue
            mu_b = fc["blend"][mtype]
            a = (mu_b, None) if mtype != "total" else (None, mu_b)
            pb = p_yes(m, mtype, home_code, *a, cfg)
            if pb is None:
                continue
            f = (mu_b + shift, None) if mtype != "total" else (None, mu_b + shift)
            mo, bo = fc["model"][mtype], fc["book"][mtype]
            odds, gap = g["odds"] or {}, None
            if mtype == "total" and odds.get("total") is not None:
                gap = abs(m["strike"] - odds["total"])
            elif mtype == "spread" and odds.get("home_spread") is not None:
                hs = odds["home_spread"]
                gap = abs(m["strike"] + hs) if m["team_code"] == home_code else abs(m["strike"] - hs)
            rows.append({
                "m": m, "mtype": mtype, "has_book": fc["has_book"][mtype], "gap": gap,
                "p_kalshi": kalshi.mid(m),
                "p_book": None if bo is None else p_yes(m, mtype, home_code, *((bo, None) if mtype != "total" else (None, bo)), cfg),
                "p_model": None if mo is None else p_yes(m, mtype, home_code, *((mo, None) if mtype != "total" else (None, mo)), cfg),
                "p_blend": pb,
                "p_final": p_yes(m, mtype, home_code, *f, cfg),
            })
    return rows


def candidates(cfg: BotConfig, rows: list[dict], key: str = "p_final") -> list[dict]:
    """Every buyable side that passes the market-quality rules, with its edge after fees."""
    out = []
    for r in rows:
        for side in ("yes", "no"):
            ask, bid, size = side_price(r["m"], side)
            lo, hi = cfg.price_band[r["mtype"]]
            if not (lo <= ask <= hi) or bid <= 0:
                continue
            if ask - bid > cfg.max_spread + 1e-9 or size < cfg.min_ask_size:
                continue
            if r["mtype"] not in cfg.trade_types or r["p_model"] is None:
                continue  # no opinion of the bot's own, no pick
            p = r[key] if side == "yes" else 1 - r[key]
            cost = ask + pricing.fee_per_contract(ask)
            out.append({**r, "side": side, "ask": ask, "bid": bid, "size": size, "p": p,
                        "edge": p - cost, "cost": cost,
                        "threshold": cfg.min_edge[r["mtype"]]})
    return out


def confidence(edge: float, ai_conf: str | None) -> str:
    level = 2 if edge >= 0.08 else 1 if edge >= 0.06 else 0
    if ai_conf == "low":
        level = max(0, level - 1)
    return ["Low", "Medium", "High"][level]


# ---------------------------------------------------------------- grading

def settle(cfg: BotConfig, p: dict, now, dry: bool) -> dict:
    """Close out finished games: grade every tracked prediction and every open paper trade."""
    preds = read_json(p["open_preds"], {})
    trades = read_jsonl(p["trades"])
    done = {s["trade_id"] for s in read_jsonl(p["settlements"])}
    open_trades = [t for t in trades if t["id"] not in done]
    cutoff = now - timedelta(hours=2)
    due = [t for t, pr in preds.items() if parse_iso(pr["start"]) < cutoff]
    due += [t["ticker"] for t in open_trades if parse_iso(t["start"]) < cutoff]
    if not due:
        return {"graded": 0, "settled": 0}
    live = kalshi.markets_by_ticker(due)
    new_settle, new_graded = [], []
    for t in open_trades:
        mk = live.get(t["ticker"])
        if not mk or parse_iso(t["start"]) >= cutoff:
            continue
        final = mk["status"] in ("finalized", "settled")
        if mk["result"] not in ("yes", "no") and not final:
            continue
        close_yes = (preds.get(t["ticker"]) or {}).get("p_kalshi")
        close_side = None if close_yes is None else (close_yes if t["side"] == "yes" else 1 - close_yes)
        if mk["result"] in ("yes", "no"):
            won = mk["result"] == t["side"]
            payout = float(t["contracts"]) if won else 0.0
            outcome = "won" if won else "lost"
        else:  # market voided: stake returned
            payout, outcome = t["cost"], "void"
        new_settle.append({
            "trade_id": t["id"], "ts": iso(now), "outcome": outcome, "payout": r4(payout),
            "pnl": r4(payout - t["cost"]), "close_price": r4(close_side),
            "clv": None if close_side is None else r4(close_side - t["price"]),
        })
    for tk in list(preds):
        pr = preds[tk]
        if parse_iso(pr["start"]) >= cutoff:
            continue
        mk = live.get(tk)
        if mk and mk["result"] in ("yes", "no"):
            new_graded.append({**pr, "ticker": tk, "result": 1 if mk["result"] == "yes" else 0})
            del preds[tk]
        elif (mk and mk["status"] in ("finalized", "settled")) or now - parse_iso(pr["start"]) > timedelta(days=7):
            del preds[tk]  # voided or never resolved: nothing to grade
    if not dry:
        append_jsonl(p["settlements"], new_settle)
        append_jsonl(p["graded"], new_graded)
        write_json(p["open_preds"], preds)
    return {"graded": len(new_graded), "settled": len(new_settle)}


# ---------------------------------------------------------------- the run

def notify(title: str, body: str) -> None:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return
    try:
        import requests
        requests.post(f"https://ntfy.sh/{topic}", data=body.encode(), timeout=10,
                      headers={"Title": title, "Tags": "test_tube"})
    except Exception:
        pass  # an alert failing must never break a run


def game_sheet(cfg: BotConfig, g: dict, fc: dict, rows: list[dict], cands: list[dict], rt: dict,
               inj: dict, home_code: str, rt_form: dict | None = None, results: list[dict] | None = None) -> dict:
    def last5(tid):
        out = []
        for r in sorted((r for r in results or [] if tid in (r["h"], r["a"])), key=lambda r: r["date"])[-5:]:
            mine_, theirs = (r["hs"], r["as"]) if r["h"] == tid else (r["as"], r["hs"])
            opp = r["an"] if r["h"] == tid else r["hn"]
            out.append(f"{'W' if mine_ > theirs else 'L'} {int(mine_)}-{int(theirs)} {'vs' if r['h'] == tid else 'at'} {opp}")
        return out

    def team(t):
        return {"name": t["display"], "record": t["record"],
                "season_rating_pts": r4(ratings.net(rt, t["id"])),
                "recent_form_rating_pts": r4(ratings.net(rt_form, t["id"])) if rt_form else None,
                "games_rated": rt["games"].get(t["id"], 0), "last_5": last5(t["id"]),
                "stats": espn.team_stats(cfg.name, t["id"]),
                "injuries": inj.get(t["id"], [])}
    best, seen = [], set()
    for c in sorted(cands, key=lambda c: -c["edge"]):
        lb = label(c["m"], c["mtype"], c["side"], home_code, g)
        if lb not in seen and len(best) < 4:
            seen.add(lb)
            best.append(c)
    flags = []
    mo, bo = fc["model"]["spread"], fc["book"]["spread"]
    if mo is not None and bo is not None and abs(mo - bo) >= cfg.flag_gap_margin:
        flags.append(f"Model and sportsbook disagree by {abs(mo - bo):.1f} points on the margin. "
                     "Look for what the book may know (injury, suspension, quarterback change) before trusting the model.")
    return {
        "sport": cfg.title, "start_utc": g["start"], "neutral_site": g["neutral"],
        "game_id": g["id"], "home": team(g["home"]), "away": team(g["away"]),
        "sportsbook_line_for_reference": g["odds"],
        "expected_home_margin": {"bot_model": r4(mo), "sportsbook": r4(bo), "forecast_used": r4(fc["blend"]["spread"])},
        "expected_total": {"bot_model": r4(fc["model"]["total"]), "sportsbook": r4(fc["book"]["total"]),
                           "forecast_used": r4(fc["blend"]["total"])},
        "situational_notes": fc["notes"], "flags": flags,
        "kalshi_sides_the_bot_is_considering": [
            {"position": label(c["m"], c["mtype"], c["side"], home_code, g), "ask": c["ask"],
             "bot_probability": r4(c["p"]), "edge_after_fees": r4(c["edge"])} for c in best],
        "adjustment_caps": {"margin": cfg.ai_margin_cap, "total": cfg.ai_total_cap},
    }


def run(cfg: BotConfig, root: str = ".", *, dry: bool = False, use_ai: bool = True,
        window_hours: float | None = None, verbose: bool = True) -> dict:
    now = now_utc()
    p = paths(cfg, root)
    os.makedirs(p["dir"], exist_ok=True)
    window = window_hours or cfg.window_hours
    log = {"ts": iso(now), "bot": cfg.name, "dry": dry}

    def say(*a):
        if verbose:
            print(*a)

    # 1. grade finished games
    log.update(settle(cfg, p, now, dry))

    # 2. markets, schedule, ratings
    pre = cfg.kalshi_prefix
    kgames = kalshi.group_by_game(kalshi.list_markets(pre + "GAME"), kalshi.list_markets(pre + "SPREAD"),
                                  kalshi.list_markets(pre + "TOTAL"))
    sched = espn.upcoming(cfg.name, int(math.ceil(window / 24)) + 1, cfg.espn_groups)
    lo, hi = now + timedelta(minutes=cfg.lockout_minutes), now + timedelta(hours=window)
    sched = [g for g in sched if g["state"] == "pre" and lo < parse_iso(g["start"]) <= hi]
    matched, _ = match.match_games(kgames, sched)
    results = espn.season_results(cfg.name, p["results_cache"], season_start=cfg.season_start, groups=cfg.espn_groups)
    rt = ratings.fit(results, hfa=cfg.hfa, ridge=cfg.ridge, half_life_days=cfg.half_life_days,
                     margin_cap=cfg.margin_cap, min_games=cfg.min_games, as_of=now)
    rt_form = ratings.fit(results, hfa=cfg.hfa, ridge=cfg.ridge, half_life_days=cfg.form_half_life_days,
                          margin_cap=cfg.margin_cap, min_games=cfg.min_games, as_of=now)
    inj = espn.injuries(cfg.name) if use_ai else {}
    log.update({"games_in_window": len(sched), "matched": len(matched), "results_used": rt["n"]})
    say(f"[{cfg.name}] {len(sched)} games start within {window:g}h, {len(matched)} have Kalshi markets, "
        f"ratings from {rt['n']} games")

    trades = read_jsonl(p["trades"])
    closed = {s["trade_id"] for s in read_jsonl(p["settlements"])}
    preds = read_json(p["open_preds"], {})
    ai_cache = read_json(p["ai_cache"], {})
    new_trades, new_settle = [], []
    stats = {"ai_calls": 0, "vetoed": 0, "too_good": 0, "pulled": 0, "awaiting_review": 0}
    sheets: dict[str, dict] = {}

    # First pass: price every game with the numbers alone and rank them. Only the day's
    # strongest opinions go forward to an AI review and a possible pick.
    zero = {**ai.NEUTRAL, "status": "not_needed"}
    day = now.astimezone(ET).date()
    today_n = sum(1 for t in trades if parse_iso(t["ts"]).astimezone(ET).date() == day)
    slots = max(0, cfg.max_trades_per_day - today_n)
    ctxs = []
    for key, mt in sorted(matched.items(), key=lambda kv: kv[1]["espn"]["start"]):
        g, kg, home_code = mt["espn"], kgames[key], mt["home_code"]
        fc = forecast(cfg, g, kg, home_code, rt, rt_form)
        if fc["blend"]["ml"] is None and fc["blend"]["total"] is None:
            continue
        rows0 = price_markets(cfg, g, kg, home_code, fc, zero)
        cands0 = candidates(cfg, rows0, "p_blend")
        fresh = [c for c in cands0 if not any(t["game_id"] == g["id"] and t["mtype"] == c["mtype"] for t in trades)]
        best0 = max((c["edge"] - c["threshold"] for c in fresh if c["edge"] <= cfg.max_edge), default=-1)
        ctxs.append((best0, key, mt, fc, rows0, cands0))
    ranked = sorted((c for c in ctxs if c[0] >= -0.01), key=lambda c: -c[0])
    shortlist = {c[1] for c in ranked[:slots + 2]} if slots else set()

    for best0, key, mt, fc, rows0, cands0 in ctxs:
        g, kg, home_code = mt["espn"], kgames[key], mt["home_code"]
        gname = f"{g['away']['abbr']} @ {g['home']['abbr']}"
        mine = [t for t in trades if t["game_id"] == g["id"]]
        held = [t for t in mine if t["id"] not in closed]

        # 3. AI step, only for games that are near a trade or already hold a pick.
        #    A review is a note in ai_cache.json: written by Claude during the run
        #    (python -m core.notes), or fetched from the API when a key is configured.
        adj, waiting = zero, False
        near = key in shortlist
        if use_ai and (near or held):
            cached = ai_cache.get(g["id"])
            if cached and now - parse_iso(cached["ts"]) < timedelta(hours=cfg.notes_fresh_hours):
                adj = cached
            else:
                sheet = game_sheet(cfg, g, fc, rows0, cands0, rt, inj, home_code, rt_form, results)
                if ai.available():
                    adj = ai.analyze(sheet, cfg.ai_margin_cap, cfg.ai_total_cap)
                    if adj["status"] == "ok":
                        stats["ai_calls"] += 1
                        ai_cache[g["id"]] = {**adj, "ts": iso(now)}
                else:
                    # no review yet: hold new trades for this game until one is written
                    sheets[g["id"]] = {"game": gname, **sheet}
                    waiting = near
                    adj = cached or zero  # a stale note still protects a held pick
        elif near or held:
            adj = {**ai.NEUTRAL, "status": "skipped", "reason": "AI turned off for this run"}
        rows = price_markets(cfg, g, kg, home_code, fc, adj)
        by_ticker = {r["m"]["ticker"]: r for r in rows}

        # 4. pull picks the bot no longer believes in (allowed once, before the start only)
        for t in held:
            r = by_ticker.get(t["ticker"])
            if not r:
                continue
            _, bid, _ = side_price(r["m"], t["side"])
            fair = r["p_final"] if t["side"] == "yes" else 1 - r["p_final"]
            exit_fee = pricing.fee(t["contracts"], bid) if bid > 0 else 0.0
            net_bid = bid - exit_fee / t["contracts"]
            why = None
            if bid > 0 and adj.get("veto"):
                why = "AI flagged the game: " + adj.get("reason", "")[:200]
            elif bid > 0 and net_bid - fair > cfg.pull_margin:
                why = f"market now pays {bid:.2f} for a position the bot values at {fair:.2f}"
            if why:
                proceeds = t["contracts"] * bid - exit_fee
                new_settle.append({"trade_id": t["id"], "ts": iso(now), "outcome": "pulled",
                                   "payout": r4(proceeds), "pnl": r4(proceeds - t["cost"]),
                                   "close_price": r4(bid), "clv": r4(bid - t["price"]), "note": why})
                closed.add(t["id"])
                stats["pulled"] += 1
                say(f"  PULL  {gname}: {t['label']} sold at {bid:.2f} ({why})")
                notify(f"{cfg.title} paper pick pulled: {t['label']}", f"{gname}\n{why}")

        # 5. new paper trades: at most one per game per market type, never a re-entry
        if adj.get("veto"):
            stats["vetoed"] += 1
        elif waiting:
            stats["awaiting_review"] += 1
        elif key in shortlist and slots - len(new_trades) > 0:
            cands = candidates(cfg, rows)
            spent = sum(t["cost"] for t in mine if t["id"] not in closed)
            for mtype in ("ml", "total"):
                # winner and spread are the same opinion, so a game gets one of them, not both
                group = ("ml", "spread") if mtype != "total" else ("total",)
                if any(t["mtype"] in group for t in mine) or slots - len(new_trades) <= 0:
                    continue
                pool = [c for c in cands if c["mtype"] in group]
                stats["too_good"] += sum(c["edge"] > cfg.max_edge for c in pool)
                pool = [c for c in pool if c["edge"] <= cfg.max_edge]  # larger is more likely error than insight
                if not pool:
                    continue
                c = max(pool, key=lambda c: c["edge"])
                if c["edge"] < c["threshold"]:
                    continue
                # Stake grows with the edge (fractional Kelly) and with the AI's confidence,
                # inside a floor and a cap so one overconfident forecast cannot dominate.
                stake = cfg.bankroll * cfg.kelly_fraction * pricing.kelly(c["p"], c["cost"])
                stake *= cfg.confidence_stake.get(adj.get("confidence") or "medium", 1.0)
                stake = max(stake, cfg.min_units_trade * cfg.unit)
                stake = min(stake, cfg.max_units_trade * cfg.unit, cfg.max_units_game * cfg.unit - spent)
                n = int(min(stake / c["cost"], c["size"]))
                if n < 1:
                    continue
                fee = pricing.fee(n, c["ask"])
                cost = n * c["ask"] + fee
                yes = c["side"] == "yes"

                def sd(v):
                    return None if v is None else r4(v if yes else 1 - v)
                t = {
                    "id": uuid.uuid4().hex[:12], "bot": cfg.name, "ts": iso(now),
                    "game_id": g["id"], "game": gname, "start": g["start"], "ticker": c["m"]["ticker"],
                    "mtype": c["mtype"], "side": c["side"], "label": label(c["m"], c["mtype"], c["side"], home_code, g),
                    "price": c["ask"], "contracts": n, "fee": fee, "cost": r4(cost),
                    "units": r4(cost / cfg.unit),
                    "p_kalshi": sd(c["p_kalshi"]), "p_book": sd(c["p_book"]), "p_model": sd(c["p_model"]),
                    "p_blend": sd(c["p_blend"]), "p_final": r4(c["p"]),
                    "edge": r4(c["edge"]), "confidence": confidence(c["edge"], adj.get("confidence")),
                    "has_book": c["has_book"], "book": g["odds"],
                    "ai": {k: adj.get(k) for k in ("status", "margin_adj", "total_adj", "confidence", "reason")},
                    "notes": fc["notes"],
                }
                new_trades.append(t)
                mine.append(t)
                spent += cost
                say(f"  TRADE {gname}: {t['label']} x{n} at {c['ask']:.2f} | bot {c['p'] * 100:.1f}% | "
                    f"book {(t['p_book'] or 0) * 100:.1f}% | model {(t['p_model'] or 0) * 100:.1f}% | edge {c['edge'] * 100:+.1f} | {t['units']:.2f}u | {t['confidence']} | AI {adj['status']}")
                notify(f"{cfg.title} paper pick: {t['label']} at {c['ask'] * 100:.0f}c",
                       f"{gname}\nKalshi {t['ticker']}\nSize {t['units']:.2f} units | Edge {c['edge'] * 100:+.1f} pts | "
                       f"Confidence {t['confidence']}\nPAPER ONLY. No real order was placed.")

        # 6. remember the latest pre-game numbers for calibration and closing prices
        held_tickers = {t["ticker"] for t in mine}
        for r in rows:
            tk = r["m"]["ticker"]
            pk = r["p_kalshi"]
            # winner markets, plus the spread/total strikes at or beside the sportsbook's number
            if not (r["mtype"] == "ml" or tk in preds or tk in held_tickers
                    or (r["gap"] is not None and r["gap"] <= 1.5)
                    or (r["gap"] is None and pk is not None and 0.4 <= pk <= 0.6)):
                continue
            if pk is None and tk in preds:
                pk = preds[tk].get("p_kalshi")  # keep the last real quote rather than erase it
            preds[tk] = {
                "game_id": g["id"], "game": gname, "start": g["start"], "mtype": r["mtype"],
                "label": label(r["m"], r["mtype"], "yes", home_code, g), "ts": iso(now),
                "p_kalshi": r4(pk), "p_book": r4(r["p_book"]), "p_model": r4(r["p_model"]),
                "p_blend": r4(r["p_blend"]), "p_final": r4(r["p_final"]),
                "ai": adj["status"],
            }

    log.update(stats)
    log.update({"new_trades": len(new_trades), "tracked_markets": len(preds)})
    if not dry:
        append_jsonl(p["trades"], new_trades)
        append_jsonl(p["settlements"], new_settle)
        write_json(p["open_preds"], preds)
        write_json(p["ai_cache"], {k: v for k, v in ai_cache.items()
                                   if now - parse_iso(v["ts"]) < timedelta(days=3)})
        append_jsonl(p["run_log"], [log])
    write_json(p["sheets"], sheets)
    say(f"[{cfg.name}] new paper trades: {len(new_trades)}, pulled: {stats['pulled']}, "
        f"settled: {log['settled']}, graded predictions: {log['graded']}, AI calls: {stats['ai_calls']}")
    if sheets:
        say(f"[{cfg.name}] {len(sheets)} game(s) need an AI review before trading: {p['sheets']}")
    return {"log": log, "new_trades": new_trades, "sheets": sheets}
