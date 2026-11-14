"""One run of one bot: grade what finished, price the upcoming slate, pull picks
that no longer hold up, place new paper trades, and save everything.

Nothing in here can place a real order. "Trade" always means a line written to
data/<bot>/trades.jsonl."""
from __future__ import annotations

import hashlib
import math
import os
import subprocess
import uuid
from datetime import timedelta

from . import espn, forecast as fstore, kalshi, match, pricing, ratings
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
        "forecasts": os.path.join(d, "forecasts.jsonl"),     # append-only: every AI forecast and market check
        "game_track": os.path.join(d, "game_track.json"),     # latest pre-game numbers per game, all stages
        "game_grades": os.path.join(d, "game_grades.jsonl"),  # append-only: each stage graded against the final score
        "reveal": os.path.join(d, "reveal_sheets.json"),
        "names": os.path.join(d, "names.json"),               # abbreviation -> full team name, for the scorecard      # games waiting for the market check
        "results_cache": os.path.join(d, "results_cache.json"),
        "run_log": os.path.join(d, "run_log.jsonl"),
        "sheets": os.path.join(d, "blind_sheets.json"),       # games waiting for a blind AI forecast (no prices inside)
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


def team_name(t: dict) -> str:
    """Full school or city name, never the abbreviation."""
    loc = t.get("location")
    if loc in ("New York", "Los Angeles", "LA"):  # two teams share the city
        return t.get("display") or loc
    return loc or t.get("display") or t.get("abbr") or "?"


def game_name(g: dict) -> str:
    return f"{team_name(g['away'])} at {team_name(g['home'])}"


def label(m: dict, mtype: str, side: str, home_code: str, g: dict) -> str:
    """Plain-English name of a position, e.g. 'DEN -10.5' or 'Under 233.5'."""
    if mtype == "total":
        return f"{'Over' if side == 'yes' else 'Under'} {m['strike']}"
    home, away = team_name(g["home"]), team_name(g["away"])
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



def stats_forecast(cfg: BotConfig, g: dict, rt: dict, rt_form: dict | None = None) -> dict:
    """The numbers-only forecast: expected home margin and total from the ratings. No prices involved."""
    notes: list[str] = []
    margin = total = None
    pred = ratings.predict(rt, g["home"]["id"], g["away"]["id"], hfa=cfg.hfa, neutral=g["neutral"])
    games = min(rt["games"].get(g["home"]["id"], 0), rt["games"].get(g["away"]["id"], 0))
    if pred and games >= cfg.min_rated_games:
        margin, total = pred
        form = ratings.predict(rt_form, g["home"]["id"], g["away"]["id"], hfa=cfg.hfa, neutral=g["neutral"]) if rt_form else None
        if form:  # season-long strength blended with how the teams have played lately
            margin = (1 - cfg.form_weight) * margin + cfg.form_weight * form[0]
            total = (1 - cfg.form_weight) * total + cfg.form_weight * form[1]
            notes.append(f"recent form alone says home by {form[0]:+.1f}, total {form[1]:.1f}")
        league_total = 2 * rt["mu"]
        total = league_total + cfg.total_scale * (total - league_total) + cfg.total_bias
        if cfg.situational:
            dm, dt, sit = cfg.situational({"game": g, "last": rt["last"]})
            margin += dm
            total += dt
            notes += sit
    return {"margin": margin, "total": total, "notes": notes, "min_games": games}


def logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def shrink_to_market(p_own: float, p_mkt: float, trust: float) -> float:
    """The probability the bot bets on: its own forecast pulled toward the market price in
    log-odds. trust=1 keeps the forecast as is, trust=0 gives the market price back."""
    z = logit(p_mkt) + trust * (logit(p_own) - logit(p_mkt))
    return 1 / (1 + math.exp(-z))


def effective_trust(cfg: BotConfig, mtype: str, min_games: int, check: str) -> float:
    t = cfg.trust[mtype]
    if min_games < cfg.thin_data_games:
        t *= cfg.thin_data_factor
    if check == "shrink":
        t *= cfg.shrink_factor
    return max(0.0, min(cfg.trust_ceiling, t))


def price_markets(cfg: BotConfig, g: dict, kg: dict, home_code: str, st: dict, book: dict,
                  ai: dict | None, check: str | None) -> list[dict]:
    """One row per Kalshi market with every stage's probability of YES kept separately."""
    rows = []
    for mtype in ("ml", "spread", "total"):
        for m in kg[mtype]:
            if m["status"] not in ("active", "open"):
                continue

            def p(mu):
                if mu is None:
                    return None
                return p_yes(m, mtype, home_code, *((mu, None) if mtype != "total" else (None, mu)), cfg)
            key = "total" if mtype == "total" else "margin"
            pk = kalshi.mid(m)
            p_ai = p(ai[key]) if ai else None
            p_trade = None
            if p_ai is not None and pk is not None and check in ("stands", "shrink"):
                p_trade = shrink_to_market(p_ai, pk, effective_trust(cfg, mtype, st["min_games"], check))
            odds, gap = g["odds"] or {}, None
            if mtype == "total" and odds.get("total") is not None:
                gap = abs(m["strike"] - odds["total"])
            elif mtype == "spread" and odds.get("home_spread") is not None:
                hs = odds["home_spread"]
                gap = abs(m["strike"] + hs) if m["team_code"] == home_code else abs(m["strike"] - hs)
            rows.append({"m": m, "mtype": mtype, "gap": gap, "p_kalshi": pk, "p_book": p(book[key]),
                         "p_stats": p(st[key]), "p_ai": p_ai, "p_trade": p_trade})
    return rows


def candidates(cfg: BotConfig, rows: list[dict], key: str = "p_trade") -> list[dict]:
    """Every buyable side that passes the market-quality rules, with its edge after fees."""
    out = []
    for r in rows:
        if r[key] is None or r["mtype"] not in cfg.trade_types:
            continue
        for side in ("yes", "no"):
            ask, bid, size = side_price(r["m"], side)
            lo, hi = cfg.price_band[r["mtype"]]
            if not (lo <= ask <= hi) or bid <= 0:
                continue
            if ask - bid > cfg.max_spread + 1e-9 or size < cfg.min_ask_size:
                continue
            p = r[key] if side == "yes" else 1 - r[key]
            out.append({**r, "side": side, "ask": ask, "bid": bid, "size": size, "p": p})
    return out


def size_trade(cfg: BotConfig, c: dict, spent_on_game: float = 0.0) -> dict | None:
    """Contracts, fee and edge for one candidate, using the exact fee for the exact order size.
    Stake is a fraction of Kelly on the market-checked probability. There is no minimum stake:
    a thin edge means a small bet or none."""
    cost1 = c["ask"] + pricing.fee(100, c["ask"]) / 100
    stake = cfg.bankroll * cfg.kelly_fraction * pricing.kelly(c["p"], cost1)
    stake = min(stake, cfg.max_units_trade * cfg.unit, cfg.max_units_game * cfg.unit - spent_on_game)
    n = int(min(stake / cost1, c["size"]))
    if n < 1:
        return None
    fee = pricing.fee(n, c["ask"])
    cost = n * c["ask"] + fee
    edge = c["p"] - cost / n
    if edge < cfg.min_edge_trade:
        return None
    p_ai = None if c.get("p_ai") is None else (c["p_ai"] if c["side"] == "yes" else 1 - c["p_ai"])
    return {"n": n, "fee": fee, "cost": cost, "edge": edge, "edge_ai": None if p_ai is None else p_ai - cost / n}


def size_sample(cfg: BotConfig, c: dict, units: float, min_edge: float) -> dict | None:
    """A fixed small stake on the side the AI's own (blind) forecast favours, when that forecast beats
    the ask by at least sample_min_edge after the exact fee. Edge on the market-checked probability is
    recorded too; it is usually near zero or negative, which is why this is a sample and not a bet."""
    if c.get("p_ai") is None:
        return None
    p_ai = c["p_ai"] if c["side"] == "yes" else 1 - c["p_ai"]
    cost1 = c["ask"] + pricing.fee(100, c["ask"]) / 100
    n = int(min(units * cfg.unit / cost1, c["size"]))
    if n < 1:
        return None
    fee = pricing.fee(n, c["ask"])
    cost = n * c["ask"] + fee
    edge_ai = p_ai - cost / n
    if edge_ai < min_edge:
        return None
    return {"n": n, "fee": fee, "cost": cost, "edge": c["p"] - cost / n, "edge_ai": edge_ai}


def read_pick(cfg: BotConfig, rows: list[dict]) -> tuple:
    """Best contract on the AI's own read, and its confidence tier, or (None, None)."""
    best = None
    for cand in candidates(cfg, rows):
        sz = size_sample(cfg, cand, cfg.read_units["Low"], cfg.read_min_edge["Low"])
        if sz and (best is None or sz["edge_ai"] > best[1]["edge_ai"]):
            best = (cand, sz)
    if not best:
        return None, None
    if best[1]["edge_ai"] >= cfg.read_min_edge["Mid"]:
        return (best[0], size_sample(cfg, best[0], cfg.read_units["Mid"], cfg.read_min_edge["Mid"]) or best[1]), "Mid"
    return best, "Low"


def confidence(edge: float) -> str:
    return "High" if edge >= 0.06 else "Medium" if edge >= 0.04 else "Low"


def should_pull(cfg: BotConfig, t: dict, bid: float, fair: float | None, check: str | None) -> str | None:
    """Hold-versus-sell: sell only when the sale, after its fee, beats the value of holding
    by a clear margin, or when the forecast behind the pick has been withdrawn."""
    if bid <= 0:
        return None
    if check == "drop":
        return "the forecast behind this pick was withdrawn"
    if fair is None:
        return None
    net_bid = bid - pricing.fee(t["contracts"], bid) / t["contracts"]
    if net_bid - fair > cfg.pull_margin:
        return f"market now pays {bid:.2f} for a position the bot values at {fair:.2f}"
    return None

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
        else:  # market voided: contract price returned. Whether Kalshi also returns the fee is
            # not verified, so the paper ledger assumes it does not.
            payout, outcome = t["cost"] - t.get("fee", 0.0), "void"
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



def commit_hash(root: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True, timeout=5).stdout.strip() or None
    except Exception:
        return None


def blind_sheet(cfg: BotConfig, g: dict, st: dict, rt: dict, inj: dict, rt_form: dict | None,
                results: list[dict], why: str) -> dict:
    """Everything the forecaster sees for the blind forecast. Deliberately contains no Kalshi
    price, no sportsbook line and nothing derived from either."""
    def team(t):
        tid = t["id"]
        mine_ = sorted((r for r in results if tid in (r["h"], r["a"]) and r["hs"] is not None), key=lambda r: r["date"])
        lines, opp_r, pf, pa, vs_good, blow = [], [], 0.0, 0.0, [0, 0], 0
        for r in mine_:
            home = r["h"] == tid
            s, o = (r["hs"], r["as"]) if home else (r["as"], r["hs"])
            orate = ratings.net(rt, r["a"] if home else r["h"])
            pf, pa = pf + s, pa + o
            if orate is not None:
                opp_r.append(orate)
                if orate > 0:
                    vs_good[0 if s > o else 1] += 1
                if s - o >= 28 and orate < -7:
                    blow += 1
            lines.append(f"{'W' if s > o else 'L'} {int(s)}-{int(o)} {'vs' if home else 'at'} {r['an'] if home else r['hn']}"
                         + ("" if orate is None else f" (opp {orate:+.0f})"))
        n = max(1, len(mine_))
        return {"name": t["display"], "record": t["record"],
                "season_rating_pts": r4(ratings.net(rt, tid)),
                "recent_form_rating_pts": r4(ratings.net(rt_form, tid)) if rt_form else None,
                "games_rated": rt["games"].get(tid, 0),
                "points_for_against_per_game": [round(pf / n, 1), round(pa / n, 1)],
                "avg_opponent_rating": round(sum(opp_r) / len(opp_r), 1) if opp_r else None,
                "record_vs_above_average_teams": f"{vs_good[0]}-{vs_good[1]}",
                "blowout_wins_over_weak_teams": blow,
                "results_oldest_first": lines[-8:],
                "stats": espn.team_stats(cfg.name, tid),
                "injuries": inj.get(tid, []) if cfg.name != "cfb" else "no injury feed for college"}
    return {"sport": cfg.title, "game_id": g["id"], "game": game_name(g),
            "start_utc": g["start"], "neutral_site": g["neutral"], "picked_for_review_because": why,
            "home": team(g["home"]), "away": team(g["away"]),
            "stats_forecast": {"home_margin": r4(st["margin"]), "total": r4(st["total"])},
            "situational_notes": st["notes"]}


def run(cfg: BotConfig, root: str = ".", *, dry: bool = False, use_ai: bool = True,
        window_hours: float | None = None, verbose: bool = True) -> dict:
    now = now_utc()
    p = paths(cfg, root)
    if not dry:
        os.makedirs(p["dir"], exist_ok=True)
    window = window_hours or cfg.window_hours
    log = {"ts": iso(now), "bot": cfg.name, "dry": dry, "version": cfg.strategy_version}

    def say(*a):
        if verbose:
            print(*a)

    # 1. grade finished contracts and trades
    log.update(settle(cfg, p, now, dry))

    # 2. markets, schedule, ratings
    pre = cfg.kalshi_prefix
    kgames = kalshi.group_by_game(kalshi.list_markets(pre + "GAME"), kalshi.list_markets(pre + "SPREAD"),
                                  kalshi.list_markets(pre + "TOTAL"))
    sched = espn.upcoming(cfg.name, int(math.ceil(window / 24)) + 1, cfg.espn_groups)
    lo, hi = now + timedelta(minutes=cfg.lockout_minutes), now + timedelta(hours=window)
    sched = [g for g in sched if g["state"] == "pre" and lo < parse_iso(g["start"]) <= hi]
    matched, _ = match.match_games(kgames, sched)
    results = espn.season_results(cfg.name, p["results_cache"], season_start=cfg.season_start,
                                  groups=cfg.espn_groups, save=not dry)
    rt = ratings.fit(results, hfa=cfg.hfa, ridge=cfg.ridge, half_life_days=cfg.half_life_days,
                     margin_cap=cfg.margin_cap, min_games=cfg.min_games, as_of=now)
    rt_form = ratings.fit(results, hfa=cfg.hfa, ridge=cfg.ridge, half_life_days=cfg.form_half_life_days,
                          margin_cap=cfg.margin_cap, min_games=cfg.min_games, as_of=now)
    log.update({"games_in_window": len(sched), "matched": len(matched), "results_used": rt["n"]})
    say(f"[{cfg.name}] {len(sched)} games start within {window:g}h, {len(matched)} have Kalshi markets, "
        f"ratings from {rt['n']} games")

    # 3. grade every stage's game forecast against final scores
    track = read_json(p["game_track"], {})
    final = {r["id"]: r for r in results if r.get("hs") is not None and r.get("as") is not None}
    grades = []
    for gid in list(track):
        if gid in final:
            r = final[gid]
            grades.append({**track.pop(gid), "game_id": gid, "graded_ts": iso(now),
                           "actual_margin": r["hs"] - r["as"], "actual_total": r["hs"] + r["as"]})
        elif now - parse_iso(track[gid]["start"]) > timedelta(days=7):
            del track[gid]
    log["games_graded"] = len(grades)

    settles = read_jsonl(p["settlements"])
    withdrawn = {s["trade_id"] for s in settles if s["outcome"] == "withdrawn"}
    trades = [t for t in read_jsonl(p["trades"]) if t["id"] not in withdrawn]  # a withdrawn pick never happened
    closed = {s["trade_id"] for s in settles}
    preds = read_json(p["open_preds"], {})
    names = read_json(p["names"], {})
    fc_all = fstore.latest(p["forecasts"])
    new_trades, new_settle, new_events = [], [], []
    stats = {"pulled": 0, "awaiting_forecast": 0, "awaiting_check": 0, "dropped": 0, "no_edge": 0}
    day = now.astimezone(ET).date()
    v2_today = [t for t in trades if t.get("version") and parse_iso(t["ts"]).astimezone(ET).date() == day]
    del v2_today  # no daily count limit: the bar for a pick is what keeps the number down

    # First pass: the numbers-only forecast and the market's view for every game.
    ctxs = []
    for key, mt in sorted(matched.items(), key=lambda kv: kv[1]["espn"]["start"]):
        g, kg, home_code = mt["espn"], kgames[key], mt["home_code"]
        st = stats_forecast(cfg, g, rt, rt_form)
        if st["margin"] is None:
            continue
        b = pricing.book_anchors(g["odds"], cfg.sd_margin, cfg.sd_total)
        book = {"margin": b["margin_spread"] if b["margin_spread"] is not None else b["margin_ml"], "total": b["total"]}
        k_margin, k_total = kalshi_anchors(kg, home_code, cfg)
        mkt = {"margin": k_margin, "total": k_total}
        gap = abs(st["margin"] - k_margin) if k_margin is not None else 0.0
        for t in (g["home"], g["away"]):
            if t.get("abbr"):
                names[t["abbr"]] = team_name(t)
        ctxs.append({"key": key, "g": g, "kg": kg, "home_code": home_code, "st": st, "book": book, "mkt": mkt, "gap": gap})

    # Which games get a deep read today: the biggest disagreements between the numbers and the
    # market, plus a few picked at random as a control group so the AI is also graded on games
    # nobody singled out. Games already forecast today count against the budget.
    have = {c["g"]["id"] for c in ctxs if c["g"]["id"] in fc_all}
    done_today = sum(1 for gid, f in fc_all.items()
                     if parse_iso(f["blind"]["ts"]).astimezone(ET).date() == day)
    budget = max(0, cfg.deep_reads_per_day + cfg.control_reads_per_day - done_today)
    lead = now + timedelta(minutes=cfg.forecast_lead_minutes)

    def tradeable(c):  # at least one contract passes the market-quality rules, whatever its price
        rows = price_markets(cfg, c["g"], c["kg"], c["home_code"], c["st"], c["book"], None, None)
        return bool(candidates(cfg, rows, "p_kalshi"))
    todo = [c for c in ctxs if c["g"]["id"] not in have and c["mkt"]["margin"] is not None
            and parse_iso(c["g"]["start"]) > lead
            and not any(t["game_id"] == c["g"]["id"] for t in trades) and tradeable(c)]
    by_gap = sorted(todo, key=lambda c: -c["gap"])
    n_ctrl = min(cfg.control_reads_per_day, budget)
    picks = {c["g"]["id"]: "the numbers and the market disagree" for c in by_gap[:max(0, budget - n_ctrl)]}
    rest = sorted((c for c in todo if c["g"]["id"] not in picks),
                  key=lambda c: hashlib.sha256((str(day) + c["g"]["id"]).encode()).hexdigest())
    for c in rest[:n_ctrl]:
        picks[c["g"]["id"]] = "random control game"
    if not use_ai:
        picks = {}
    inj = espn.injuries(cfg.name) if picks else {}
    sheets: dict[str, dict] = {}
    reveals: dict[str, dict] = {}

    # Games with the strongest checked AI opinion get first claim on the day's pick slots.
    def strength(c):
        f = fc_all.get(c["g"]["id"]) or {}
        b, ch = f.get("blind"), (f.get("check") or {}).get("outcome")
        if not b or ch not in ("stands", "shrink"):
            return 0.0
        rows = price_markets(cfg, c["g"], c["kg"], c["home_code"], c["st"], c["book"],
                             {"margin": b["margin"], "total": b["total"]}, ch)
        best = 0.0
        for cand in candidates(cfg, rows):
            sz = size_trade(cfg, cand)
            if sz:
                best = max(best, 1.0 + sz["edge"])
        if ch == "stands" and not f["check"].get("auto"):
            rp, _ = read_pick(cfg, rows)
            if rp:
                best = max(best, rp[1]["edge_ai"])
        return best
    ctxs.sort(key=lambda c: -strength(c))

    for c in ctxs:
        g, kg, home_code, st, book, mkt = c["g"], c["kg"], c["home_code"], c["st"], c["book"], c["mkt"]
        gid = g["id"]
        gname = game_name(g)
        mine = [t for t in trades if t["game_id"] == gid]
        held = [t for t in mine if t["id"] not in closed]
        f = fc_all.get(gid) or {}
        blind, chk = f.get("blind"), f.get("check")
        if gid in picks and not blind:
            sheets[gid] = blind_sheet(cfg, g, st, rt, inj, rt_form, results, picks[gid])
            stats["awaiting_forecast"] += 1
        ai = {"margin": blind["margin"], "total": blind["total"]} if blind else None
        # An automatic "stands" goes stale when the market moves a lot after the forecast: that is
        # usually news (an injury, a lineup change) the forecast never saw. A written check is needed.
        at_fc = (track.get(gid) or {}).get("market_at_forecast") or {}
        if (chk and chk.get("auto") and mkt["margin"] is not None and at_fc.get("margin") is not None
                and abs(mkt["margin"] - at_fc["margin"]) >= cfg.check_gap_margin):
            chk = None
        check = chk["outcome"] if chk else None

        # Market check. A small disagreement stands automatically; a big one waits for a written answer.
        if blind and not chk and mkt["margin"] is not None:
            dm = ai["margin"] - mkt["margin"]
            dt = None if mkt["total"] is None else ai["total"] - mkt["total"]
            if abs(dm) < cfg.check_gap_margin and (dt is None or abs(dt) < cfg.check_gap_total):
                chk = {"type": "check", "game_id": gid, "ts": iso(now), "outcome": "stands", "auto": True,
                       "why": "within a few points of the market on both margin and total"}
                new_events.append(chk)
                check = "stands"
            else:
                reveals[gid] = {"game": gname, "start_utc": g["start"],
                                "your_blind_forecast": {"home_margin": ai["margin"], "total": ai["total"]},
                                "stats_forecast": {"home_margin": r4(st["margin"]), "total": r4(st["total"])},
                                "kalshi_implied": {"home_margin": r4(mkt["margin"]), "total": r4(mkt["total"])},
                                "sportsbook": g["odds"],
                                "question": "What would someone on the other side of this price know that the forecast does not?"}
                stats["awaiting_check"] += 1

        rows = price_markets(cfg, g, kg, home_code, st, book, ai, check)
        by_ticker = {r["m"]["ticker"]: r for r in rows}

        # Pull rule for v2 picks. Picks made under v1 rules are left to settle untouched.
        for t in held:
            r = by_ticker.get(t["ticker"])
            if not r or not t.get("version"):
                continue
            _, bid, _ = side_price(r["m"], t["side"])
            fair = None if r["p_trade"] is None else (r["p_trade"] if t["side"] == "yes" else 1 - r["p_trade"])
            why = should_pull(cfg, t, bid, fair, check)
            if why:
                proceeds = t["contracts"] * bid - pricing.fee(t["contracts"], bid)
                new_settle.append({"trade_id": t["id"], "ts": iso(now), "outcome": "pulled",
                                   "payout": r4(proceeds), "pnl": r4(proceeds - t["cost"]),
                                   "exit_price": r4(bid), "close_price": None, "clv": None, "note": why})
                closed.add(t["id"])
                stats["pulled"] += 1
                say(f"  PULL  {gname}: {t['label']} sold at {bid:.2f} ({why})")
                notify(f"{cfg.title} paper pick pulled: {t['label']}", f"{gname}\n{why}")

        # New paper trade: at most one position per game, ever. The code prices every eligible
        # contract off the market-checked forecast and takes the single best one, or none.
        if check == "drop":
            stats["dropped"] += 1
        elif check in ("stands", "shrink") and not mine:
            # High: the edge survives the market check and is sized by Kelly.
            # Mid / Low: the market check ended in a written "stands" (a specific stated reason the
            #      price may be wrong) and the AI's own forecast beats the ask by a clear margin.
            #      Fixed small stakes. A "shrink" or an automatic "stands" never produces these.
            best, tier = None, "High"
            for cand in candidates(cfg, rows):
                sz = size_trade(cfg, cand)
                if sz and (best is None or sz["edge"] > best[1]["edge"]):
                    best = (cand, sz)
            if not best and check == "stands" and not chk.get("auto"):
                best, tier = read_pick(cfg, rows)
            if not best:
                stats["no_edge"] += 1
            else:
                cand, sz = best
                yes = cand["side"] == "yes"

                def sd(v):
                    return None if v is None else r4(v if yes else 1 - v)
                t = {
                    "id": uuid.uuid4().hex[:12], "bot": cfg.name, "ts": iso(now),
                    "version": cfg.strategy_version, "commit": commit_hash(root), "tier": tier,
                    "edge_ai": r4(sz.get("edge_ai")),
                    "rules": {"trust": effective_trust(cfg, cand["mtype"], st["min_games"], check),
                              "kelly_fraction": cfg.kelly_fraction, "min_edge": cfg.min_edge_trade,
                              "max_units": cfg.max_units_trade},
                    "game_id": gid, "game": gname, "start": g["start"], "ticker": cand["m"]["ticker"],
                    "mtype": cand["mtype"], "side": cand["side"],
                    "label": label(cand["m"], cand["mtype"], cand["side"], home_code, g),
                    "price": cand["ask"], "bid": cand["bid"], "ask_size": cand["size"],
                    "contracts": sz["n"], "fee": sz["fee"], "cost": r4(sz["cost"]),
                    "units": r4(sz["cost"] / cfg.unit),
                    "p_kalshi": sd(cand["p_kalshi"]), "p_book": sd(cand["p_book"]), "p_stats": sd(cand["p_stats"]),
                    "p_ai": sd(cand["p_ai"]), "p_final": r4(cand["p"]),
                    "edge": r4(sz["edge"]), "confidence": tier,
                    "book": g["odds"], "book_seen_ts": iso(now),
                    "forecast": {"margin": blind["margin"], "total": blind["total"],
                                 "stats_margin": r4(st["margin"]), "stats_total": r4(st["total"]),
                                 "market_margin": r4(mkt["margin"]), "market_total": r4(mkt["total"]),
                                 "summary": blind.get("summary"), "reasons": blind.get("reasons"),
                                 "check": check, "check_why": chk.get("why"), "selected": blind.get("selected")},
                }
                new_trades.append(t)
                mine.append(t)
                say(f"  {tier.upper():4} {gname}: {t['label']} x{sz['n']} at {cand['ask']:.2f} | bet on {cand['p'] * 100:.1f}% | "
                    f"AI {(t['p_ai'] or 0) * 100:.1f}% | stats {(t['p_stats'] or 0) * 100:.1f}% | market {(t['p_kalshi'] or 0) * 100:.1f}% | "
                    f"edge {sz['edge'] * 100:+.1f} | {t['units']:.2f}u")
                notify(f"{cfg.title} paper {tier.lower()}-confidence pick: {t['label']} at {cand['ask'] * 100:.0f}c",
                       f"{gname}\nKalshi {t['ticker']}\nSize {t['units']:.2f} units | Edge {sz['edge'] * 100:+.1f} pts\n"
                       "PAPER ONLY. No real order was placed.")

        # Remember the latest pre-game numbers: per game for the stage-by-stage comparison ...
        prev = track.get(gid) or {}
        snaps = prev.get("market_snapshots") or []
        mins = (parse_iso(g["start"]) - now).total_seconds() / 60
        snaps = (snaps + [{"ts": iso(now), "mins_to_start": round(mins), "margin": r4(mkt["margin"]), "total": r4(mkt["total"])}])[-30:]
        track[gid] = {
            "game": gname, "start": g["start"], "ts": iso(now), "min_games": st["min_games"],
            "stats": {"margin": r4(st["margin"]), "total": r4(st["total"])},
            "ai": None if not blind else {"margin": blind["margin"], "total": blind["total"], "ts": blind["ts"],
                                          "selected": blind.get("selected"), "prompt": blind.get("prompt_version")},
            "check": check,
            "market": {"margin": r4(mkt["margin"]), "total": r4(mkt["total"])},
            "market_at_forecast": prev.get("market_at_forecast") or (
                {"margin": r4(mkt["margin"]), "total": r4(mkt["total"])} if blind else None),
            "book": {"margin": r4(book["margin"]), "total": r4(book["total"])},
            "market_snapshots": snaps, "sd_margin": cfg.sd_margin,
            "traded": bool(mine), "version": cfg.strategy_version,
        }
        # ... and per contract for calibration and closing prices.
        held_tickers = {t["ticker"] for t in mine}
        for r in rows:
            tk = r["m"]["ticker"]
            pk = r["p_kalshi"]
            if not (r["mtype"] == "ml" or tk in preds or tk in held_tickers
                    or (r["gap"] is not None and r["gap"] <= 1.5)
                    or (r["gap"] is None and pk is not None and 0.4 <= pk <= 0.6)):
                continue
            if pk is None and tk in preds:
                pk = preds[tk].get("p_kalshi")  # keep the last real quote rather than erase it
            preds[tk] = {
                "game_id": gid, "game": gname, "start": g["start"], "mtype": r["mtype"],
                "label": label(r["m"], r["mtype"], "yes", home_code, g), "ts": iso(now),
                "p_kalshi": r4(pk), "p_book": r4(r["p_book"]), "p_stats": r4(r["p_stats"]),
                "p_ai": r4(r["p_ai"]), "p_trade": r4(r["p_trade"]), "version": cfg.strategy_version,
            }

    log.update(stats)
    log.update({"new_trades": len(new_trades), "tracked_markets": len(preds), "tracked_games": len(track)})
    if not dry:
        append_jsonl(p["trades"], new_trades)
        append_jsonl(p["settlements"], new_settle)
        append_jsonl(p["forecasts"], new_events)
        append_jsonl(p["game_grades"], grades)
        write_json(p["open_preds"], preds)
        write_json(p["game_track"], track)
        write_json(p["names"], names)
        write_json(p["sheets"], sheets)
        write_json(p["reveal"], reveals)
        append_jsonl(p["run_log"], [log])
    say(f"[{cfg.name}] new paper trades: {len(new_trades)}, pulled: {stats['pulled']}, settled: {log['settled']}, "
        f"games graded: {len(grades)}, awaiting forecast: {len(sheets)}, awaiting market check: {len(reveals)}")
    return {"log": log, "new_trades": new_trades, "sheets": sheets, "reveals": reveals}
