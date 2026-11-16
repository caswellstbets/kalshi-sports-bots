"""NBA_MODELS.md and docs/nba_models.html: the four NBA models side by side.

Run on its own with:  python3 -m lab.report"""
from __future__ import annotations

import math
import os
import random

from core.report import CSS, md_to_html, money, pct, start_ct, when
from core.util import iso, now_utc, parse_iso, read_json, read_jsonl

from . import ledger
from .ledger import MODELS

UNIT = 10.0
ORDER = ["current", "rotation", "news", "scout"]
TITLES = {"current": "Current NBA bot (v2.3)", **{k: v["title"] for k, v in MODELS.items()}}
WHAT = {"current": "stats forecast, blind Claude forecast, then held close to the price",
        **{k: v["what"] for k, v in MODELS.items()}}


DISPLAY: dict[str, str] = {}  # the current bot's city names -> full team names


def full_team(loc: str) -> str:
    return DISPLAY.get(loc, loc)


def load_display(root: str) -> None:
    from . import boxscores
    shows = set()
    for g in boxscores.load(root)[-400:]:
        shows |= {g["hname"], g["aname"]}
    for d in shows:
        words = d.split(" ")
        for k in range(1, len(words)):
            loc = " ".join(words[:k])
            if sum(1 for x in shows if x.startswith(loc + " ")) == 1:
                DISPLAY.setdefault(loc, d)


def lab_start(root: str) -> str | None:
    runs = [r for r in read_jsonl(ledger.lab(root, "run_log.jsonl")) if not r.get("dry")]
    return min((r["ts"] for r in runs), default=None)


def load_trades(root: str, model: str, since: str | None) -> list[dict]:
    if model == "current":
        d = os.path.join(root, "data", "nba")
        ts = read_jsonl(os.path.join(d, "trades.jsonl"))
        st = {s["trade_id"]: s for s in read_jsonl(os.path.join(d, "settlements.jsonl"))}
        names = read_json(os.path.join(d, "names.json"), {})
        out = []
        for t in ts:
            s = st.get(t["id"])
            if not t.get("version") or (s and s["outcome"] == "withdrawn") or (since and t["start"] < since):
                continue
            t = dict(t, settle=s)
            t["game"] = " at ".join(full_team(x) for x in
                                    " ".join(names.get(w, w) for w in t["game"].replace(" @ ", " at ").split(" ")).split(" at "))
            t["label"] = " ".join(names.get(w, w) for w in t["label"].split(" "))
            for loc in sorted(DISPLAY, key=len, reverse=True):
                if t["label"].startswith(loc + " ") and not t["label"].startswith(DISPLAY[loc]):
                    t["label"] = DISPLAY[loc] + t["label"][len(loc):]
                    break
            t["confidence"] = {"Medium": "Mid"}.get(t.get("confidence") or "Low", t.get("confidence") or "Low")
            t["why"] = (t.get("forecast") or {}).get("summary") or ""
            out.append(t)
        return out
    st = ledger.settlements(root, model)
    return [dict(t, settle=st.get(t["id"])) for t in ledger.trades(root, model)]


def stats(trades: list[dict]) -> dict:
    done = [t for t in trades if t["settle"]]
    dec = [t for t in done if t["settle"]["outcome"] in ("won", "lost")]
    staked = sum(t["cost"] for t in done)
    pnl = sum(t["settle"]["pnl"] for t in done)
    clv = [t["settle"]["clv"] for t in done if t["settle"]["outcome"] != "pulled" and t["settle"].get("clv") is not None]
    return {"n": len(trades), "open": len(trades) - len(done), "won": sum(t["settle"]["outcome"] == "won" for t in done),
            "lost": sum(t["settle"]["outcome"] == "lost" for t in done), "pulled": sum(t["settle"]["outcome"] == "pulled" for t in done),
            "staked": staked, "pnl": pnl, "roi": pnl / staked if staked else None,
            "open_stake": sum(t["cost"] for t in trades if not t["settle"]),
            "exp_wins": sum(t["p_final"] for t in dec), "decided": len(dec),
            "clv": sum(clv) / len(clv) if clv else None, "clv_n": len(clv),
            "clv_beat": sum(c > 0 for c in clv) / len(clv) if clv else None}


def forecasts(root: str, since: str | None) -> dict[str, list[dict]]:
    """model -> [{game_id, p (home win), p_k_then, p_k_close, y}] for finished games."""
    graded = {g["game_id"]: g for g in read_jsonl(ledger.lab(root, "graded.jsonl")) if g.get("home_ml")}
    out = {m: [] for m in ORDER}
    for (model, gid), d in ledger.decisions(root).items():
        g = graded.get(gid)
        if g and d.get("p_home") is not None and d.get("kalshi_home") is not None:
            out[model].append({"game_id": gid, "p": d["p_home"], "p_then": d["kalshi_home"], "p_close": g.get("p_kalshi"),
                               "y": g["result"], "margin": d.get("margin"), "total": d.get("total")})
    # the current bot's blind forecast for the home team, from its own graded contracts
    cur = os.path.join(root, "data", "nba", "graded_predictions.jsonl")
    seen = set()
    for g in read_jsonl(cur):
        if g.get("mtype") != "ml" or g.get("p_ai") is None or (since and g["start"] < since) or g["game_id"] in seen:
            continue
        home = g["game"].replace(" @ ", " at ").split(" at ")[-1]
        names = read_json(os.path.join(root, "data", "nba", "names.json"), {})
        lab_ = " ".join(names.get(w, w) for w in g["label"].split(" "))
        if not (lab_.startswith(home) or g["label"].startswith(home)):
            continue
        seen.add(g["game_id"])
        out["current"].append({"game_id": g["game_id"], "p": g["p_ai"], "p_then": None, "p_close": g.get("p_kalshi"), "y": g["result"]})
    return out


def brier_pair(rows: list[dict], ref: str) -> dict | None:
    rows = [r for r in rows if r.get(ref) is not None]
    if not rows:
        return None
    diffs = [(r["p"] - r["y"]) ** 2 - (r[ref] - r["y"]) ** 2 for r in rows]
    rnd = random.Random(7)
    boots = sorted(sum(rnd.choice(diffs) for _ in diffs) / len(diffs) for _ in range(2000))

    def ll(p, y):
        p = min(max(p, 0.01), 0.99)
        return -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return {"n": len(rows), "model": sum((r["p"] - r["y"]) ** 2 for r in rows) / len(rows),
            "ref": sum((r[ref] - r["y"]) ** 2 for r in rows) / len(rows), "diff": sum(diffs) / len(diffs),
            "lo": boots[50], "hi": boots[1949],
            "ll_diff": sum(ll(r["p"], r["y"]) - ll(r[ref], r["y"]) for r in rows) / len(rows)}


def trade_table(trades: list[dict], model_label: str) -> list[str]:
    L = [f"| Confidence | Matchup | Start (CT) | Pick | Price | Size | {model_label} | Market says | Result | Profit | Closing edge |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    rank = {"High": 0, "Mid": 1, "Low": 2}
    for t in sorted(trades, key=lambda t: (t["start"][:10], -rank.get(t["confidence"], 3), t["start"]), reverse=True):
        s = t["settle"]
        closing = "" if not s or s.get("clv") is None or s["outcome"] == "pulled" else f"{s['clv'] * 100:+.0f}c"
        L.append(f"| **{t['confidence'].upper()}** | {t['game']} | {start_ct(t['start'])} | {t['label']} | {t['price'] * 100:.0f}c | "
                 f"{t['units']:.2f}u | {pct(t.get('p_final'), digits=0)} | {pct(t.get('p_kalshi'), digits=0)} | "
                 f"{s['outcome'] if s else 'open'} | {money(s['pnl']) if s else ''} | {closing} |")
    return L + [""]


def build(root: str = ".") -> str:
    since = lab_start(root)
    load_display(root)
    L = ["# NBA model comparison", "",
         f"Updated {when(iso(now_utc()))}. Paper trading only: no real orders, no real money. Every model trades the same "
         "Kalshi NBA markets with its own $1,000 paper bankroll (1 unit = $10), one position per game at most.", ""]
    if since:
        L += [f"Comparison window started {when(since)}. The current bot's row counts only games from then on, so all four "
              "cover the same nights.", ""]
    L += ["| Model | What drives it |", "| --- | --- |"] + [f"| **{TITLES[m]}** | {WHAT[m]} |" for m in ORDER] + [""]
    data = {m: load_trades(root, m, since) for m in ORDER}
    L += ["## Standings", "",
          "| Model | Picks | Won | Lost | Open | Staked | Profit | Units | Return | Closing-price edge | Beat the close |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for m in ORDER:
        s = stats(data[m])
        L.append(f"| **{TITLES[m]}** | {s['n']} | {s['won']} | {s['lost']} | {s['open']} | ${s['staked']:,.2f} | {money(s['pnl'])} | "
                 f"{s['pnl'] / UNIT:+.2f} | {pct(s['roi'], True)} | {'n/a' if s['clv'] is None else f'{s['clv'] * 100:+.1f}c'} | "
                 f"{pct(s['clv_beat'], digits=0)} |")
    L += ["", "Closing-price edge: the Kalshi price at the last hourly run before tip-off minus the price paid. Positive means "
          "the market moved toward the pick after it was made, the earliest sign of a real edge. Profit over one week is "
          "mostly luck.", ""]
    fc = forecasts(root, since)
    L += ["## Forecast accuracy on every game", "",
          "Each model's home-win probability on every game it looked at, picks and passes alike, against what happened. "
          "Brier score: lower is better, 0.25 is a coin flip. The difference column is the model minus Kalshi on the same "
          "games; below zero means the model beat the market. The range is a 95% bootstrap over games.", "",
          "| Model | Games | Model | Kalshi when the model decided | Difference | 95% range | Kalshi at the close | Difference vs close |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for m in ORDER:
        a, b = brier_pair(fc[m], "p_then"), brier_pair(fc[m], "p_close")
        if not a and not b:
            L.append(f"| {TITLES[m]} | 0 | | | | | | |")
            continue
        x = a or b
        L.append(f"| {TITLES[m]} | {x['n']} | {x['model']:.4f} | {'n/a' if not a else f'{a['ref']:.4f}'} | "
                 f"{'n/a' if not a else f'{a['diff']:+.4f}'} | {'' if not a else f'{a['lo']:+.4f} to {a['hi']:+.4f}'} | "
                 f"{'n/a' if not b else f'{b['ref']:.4f}'} | {'n/a' if not b else f'{b['diff']:+.4f}'} |")
    L += ["", "The current bot only writes a forecast for the games it picks for a deep read, so its row covers fewer games.", ""]
    for m in ORDER:
        tr = data[m]
        L += [f"## {TITLES[m]}", ""]
        s = stats(tr)
        if not tr:
            L += ["No picks yet.", ""]
            continue
        if s["decided"]:
            L.append(f"Expected to win {s['exp_wins']:.1f} of {s['decided']} decided picks; won {s['won']}.")
            L.append("")
        L += ["| Confidence | Picks | Won | Lost | Profit | Return |", "| --- | --- | --- | --- | --- | --- |"]
        for tier in ("High", "Mid", "Low"):
            x = stats([t for t in tr if t["confidence"] == tier])
            L.append(f"| **{tier.upper()}** | {x['n']} | {x['won']} | {x['lost']} | {money(x['pnl'])} | {pct(x['roi'], True)} |")
        L.append("")
        L += trade_table(tr, "Model says")
        L += ["Why each pick was made:", ""]
        for t in sorted(tr, key=lambda t: t["ts"], reverse=True)[:12]:
            L.append(f"- **{t['confidence'].upper()}: {t['game']}, {t['label']}.** {t.get('why') or ''}")
        L.append("")
    L += ["## How the week will be judged", "",
          "Set before the first pick. One week is about 50 games, enough to rule out a model that is badly wrong and not "
          "enough to prove one is right.", "",
          "1. **Forecast accuracy against Kalshi** on every game the model looked at (table above). A model that cannot get "
          "below Kalshi's own Brier score on the same games has no edge to bet, however its picks went.",
          "2. **Closing-price edge** on its picks. Positive on average means the market agreed with the pick after it was made.",
          "3. **Profit and return** on its picks, read with the record against the number it expected to win.",
          "4. **Calibration by confidence**: High picks should win more often than Mid, and Mid more than Low.", "",
          "A model is worth keeping past the week if it is ahead of Kalshi on point 1 or point 2 and not far behind on the "
          "other. A model behind on both is retired, whatever its profit.", ""]
    md = "\n".join(L) + "\n"
    with open(os.path.join(root, "NBA_MODELS.md"), "w") as f:
        f.write(md)
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    with open(os.path.join(root, "docs", "nba_models.html"), "w") as f:
        f.write("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>NBA Model Comparison</title><style>{CSS}</style></head><body>\n{md_to_html(md)}\n</body></html>\n")
    return md


if __name__ == "__main__":
    print(build(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
