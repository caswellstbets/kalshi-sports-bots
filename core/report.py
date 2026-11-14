"""Scorecard: reads the ledgers and writes SCORECARD.md plus docs/index.html.
Run on its own with:  python -m core.report"""
from __future__ import annotations

import html
import os
from zoneinfo import ZoneInfo

from .util import ET, iso, now_utc, parse_iso, read_json, read_jsonl

BOTS = [("nba", "NBA"), ("nfl", "NFL"), ("cfb", "College football")]
BANKROLL, UNIT = 1000.0, 10.0
SOURCES = [("p_kalshi", "Kalshi closing price"), ("p_book", "Sportsbook line"), ("p_stats", "Stats forecast alone"),
           ("p_ai", "Blind AI forecast"), ("p_trade", "Bet probability (AI after market check)")]


def version(t: dict) -> str:
    return t.get("version") or "v1"


def load(root: str, bot: str) -> dict:
    d = os.path.join(root, "data", bot)
    trades = read_jsonl(os.path.join(d, "trades.jsonl"))
    settles = {s["trade_id"]: s for s in read_jsonl(os.path.join(d, "settlements.jsonl"))}
    names = read_json(os.path.join(d, "names.json"), {})

    def full(s):  # older records used abbreviations; show full team names
        s = s.replace(" @ ", " at ")
        return " ".join(names.get(w, w) for w in s.split(" "))
    n_withdrawn = sum(1 for t in trades if (settles.get(t["id"]) or {}).get("outcome") == "withdrawn")
    trades = [t for t in trades if (settles.get(t["id"]) or {}).get("outcome") != "withdrawn"]
    for t in trades:
        t["settle"] = settles.get(t["id"])
        t["game"], t["label"] = full(t["game"]), full(t["label"])
        c = t.get("confidence") or "Low"
        t["confidence"] = {"Medium": "Mid"}.get(c, c)
    graded = read_jsonl(os.path.join(d, "graded_predictions.jsonl"))
    for g in graded:  # v1 rows used older names
        g.setdefault("p_stats", g.get("p_model"))
    return {"trades": trades, "graded": graded, "withdrawn": n_withdrawn,
            "open_preds": read_json(os.path.join(d, "open_predictions.json"), {}),
            "games": read_jsonl(os.path.join(d, "game_grades.jsonl")),
            "track": read_json(os.path.join(d, "game_track.json"), {}),
            "runs": read_jsonl(os.path.join(d, "run_log.jsonl"))}


def trade_stats(trades: list[dict]) -> dict:
    done = [t for t in trades if t["settle"]]
    decided = [t for t in done if t["settle"]["outcome"] in ("won", "lost")]
    pulled = [t for t in done if t["settle"]["outcome"] == "pulled"]
    staked = sum(t["cost"] for t in done)
    pnl = sum(t["settle"]["pnl"] for t in done)
    # closing-price edge only means something for picks held to the start
    clv = [t["settle"]["clv"] for t in done if t["settle"]["outcome"] != "pulled" and t["settle"].get("clv") is not None]
    return {
        "n": len(trades), "open": len(trades) - len(done), "settled": len(done),
        "won": sum(t["settle"]["outcome"] == "won" for t in done),
        "lost": sum(t["settle"]["outcome"] == "lost" for t in done),
        "pulled": len(pulled), "pulled_pnl": sum(t["settle"]["pnl"] for t in pulled),
        "staked": staked, "open_stake": sum(t["cost"] for t in trades if not t["settle"]),
        "pnl": pnl, "units": pnl / UNIT,
        "roi": pnl / staked if staked else None,
        "avg_edge": sum(t["edge"] for t in trades) / len(trades) if trades else None,
        "expected_wins": sum(t["p_final"] for t in decided), "decided": len(decided),
        "clv_n": len(clv), "clv_avg": sum(clv) / len(clv) if clv else None,
        "clv_beat": sum(c > 0 for c in clv) / len(clv) if clv else None,
    }


def brier(graded: list[dict], need: tuple = ("p_kalshi", "p_stats")) -> dict:
    """Brier score per source on exactly the same contracts (those where every source in `need`
    has a number), so the comparison is paired. Winner markets count once per game."""
    rows, seen = [], set()
    for g in graded:
        if g["mtype"] == "ml":
            if g["game_id"] in seen:
                continue
            seen.add(g["game_id"])
        rows.append(g)
    base = [g for g in rows if all(g.get(k) is not None for k in need)]
    out = {"n": len(base), "games": len({g["game_id"] for g in base})}
    for key, _ in SOURCES:
        sub = [g for g in base if g.get(key) is not None]
        out[key] = (sum((g[key] - g["result"]) ** 2 for g in sub) / len(sub), len(sub)) if sub else None
    return out


def game_scores(games: list[dict]) -> list[tuple]:
    """Average miss on the final margin and total, per forecast stage, by game. Each row compares
    the stages on exactly the same games."""
    def mae(rows, key, field, actual):
        v = [abs(g[key][field] - g[actual]) for g in rows if g.get(key) and g[key].get(field) is not None]
        return sum(v) / len(v) if v else None
    out = []
    groups = [("All tracked games", [g for g in games if g.get("market") and g["market"].get("margin") is not None]),
              ("Games with an AI forecast", [g for g in games if g.get("ai") and g.get("market") and g["market"].get("margin") is not None]),
              ("  of which random control games", [g for g in games if g.get("ai") and (g["ai"].get("selected") or "").startswith("random")])]
    for name, rows in groups:
        if rows:
            out.append((name, len(rows), [(mae(rows, k, "margin", "actual_margin"), mae(rows, k, "total", "actual_total"))
                                          for k in ("stats", "ai", "market")]))
    return out


def buckets(graded: list[dict], key: str = "p_stats") -> list[tuple]:
    edges = [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)]
    out = []
    for lo, hi in edges:
        sub = [g for g in graded if g.get(key) is not None and lo <= g[key] < hi]
        if sub:
            out.append((f"{int(lo * 100)}-{min(100, int(hi * 100))}%", len(sub),
                        sum(g[key] for g in sub) / len(sub), sum(g["result"] for g in sub) / len(sub)))
    return out


def pct(x, signed=False, digits=1):
    if x is None:
        return "n/a"
    return f"{x * 100:+.{digits}f}%" if signed else f"{x * 100:.{digits}f}%"


def money(x):
    return "n/a" if x is None else f"{'-' if x < 0 else '+'}${abs(x):,.2f}"


CT = ZoneInfo("America/Chicago")


def when(ts: str) -> str:
    return parse_iso(ts).astimezone(CT).strftime("%a %b %-d %-I:%M %p CT")


def start_ct(ts: str) -> str:
    return parse_iso(ts).astimezone(CT).strftime("%a %-I:%M %p")


def verdict(ts: dict, n_games: int) -> str:
    if ts["settled"] < 30 or n_games < 60:
        return (f"Too early to say: {ts['settled']} settled picks and {n_games} graded games. "
                "The rules call for 60 graded AI-forecast games before any conclusion.")
    return "Enough games to start reading the tables below. Profit alone is still mostly luck at this size."


def trade_table(trades: list[dict]) -> list[str]:
    L = ["| Confidence | Game | Start (CT) | Pick | Price | Size | AI says | Market says | Result | Profit | Closing edge |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    rank = {"High": 0, "Mid": 1, "Low": 2}
    for t in sorted(trades, key=lambda t: (t["start"][:10], -rank.get(t["confidence"], 3), t["start"]), reverse=True):
        s = t["settle"]
        closing = "" if not s or s.get("clv") is None or s["outcome"] == "pulled" else f"{s['clv'] * 100:+.0f}c"
        L.append(f"| **{t['confidence'].upper()}** | {t['game']} | {start_ct(t['start'])} | {t['label']} | {t['price'] * 100:.0f}c | "
                 f"{t['units']:.2f}u | {pct(t.get('p_ai') or t.get('p_final'), digits=0)} | {pct(t.get('p_kalshi'), digits=0)} | "
                 f"{s['outcome'] if s else 'open'} | {money(s['pnl']) if s else ''} | {closing} |")
    return L + [""]


def stats_line(ts: dict) -> list[str]:
    return ["| Picks | Open | Won | Lost | Pulled | Open stake | Settled stake | Profit | Units | Return on settled stake |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            f"| {ts['n']} | {ts['open']} | {ts['won']} | {ts['lost']} | {ts['pulled']} | ${ts['open_stake']:,.2f} | "
            f"${ts['staked']:,.2f} | {money(ts['pnl'])} | {ts['units']:+.2f} | {pct(ts['roi'], True)} |", ""]


def bot_md(bot: str, title: str, d: dict) -> str:
    v2 = [t for t in d["trades"] if version(t) != "v1"]
    v1 = [t for t in d["trades"] if version(t) == "v1"]
    ts = trade_stats(v2)
    ai_games = [g for g in d["games"] if g.get("ai")]
    L = [f"## {title}", "", verdict(ts, len(ai_games)), "", "**v2 picks** (blind AI forecast, market check, code-chosen contract)", ""]
    if v2:
        L += ["| Confidence | Picks | Open | Won | Lost | Open stake | Profit | Units | Return on settled stake |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for tier in ("High", "Mid", "Low", "All"):
            s = trade_stats([t for t in v2 if tier == "All" or t["confidence"] == tier])
            L.append(f"| **{tier.upper()}** | {s['n']} | {s['open']} | {s['won']} | {s['lost']} | ${s['open_stake']:,.2f} | "
                     f"{money(s['pnl'])} | {s['units']:+.2f} | {pct(s['roi'], True)} |")
        L.append("")
    else:
        L += ["No picks yet.", ""]
    if d["withdrawn"]:
        L += [f"{d['withdrawn']} earlier picks were withdrawn before kickoff when the pick rules were tightened on Nov 14. "
              "They are in the ledger but not counted here.", ""]
    if ts["decided"]:
        L.append(f"Of {ts['decided']} decided picks the bot expected to win {ts['expected_wins']:.1f} and won {ts['won']}.")
    if ts["clv_n"]:
        L.append(f"Closing-price edge on picks held to the start: {ts['clv_avg'] * 100:+.1f} cents per contract on average "
                 f"across {ts['clv_n']} picks, and {pct(ts['clv_beat'], digits=0)} beat the last recorded price. "
                 "The last price is from the final hourly run before the start, not the exact close.")
    if ts["pulled"]:
        L.append(f"Pulled picks: {ts['pulled']}, exit profit {money(ts['pulled_pnl'])} (not counted as closing-price edge).")
    L.append("")
    if v2:
        L += trade_table(v2)
        L += ["Why each pick was made:", ""]
        for t in sorted(v2, key=lambda t: t["ts"], reverse=True)[:10]:
            f = t.get("forecast") or {}
            def n1(x):
                return "n/a" if x is None else f"{x:+.1f}"
            L.append(f"- **{t['confidence'].upper()}: {t['game']}, {t['label']}.** My forecast: home team {n1(f.get('margin'))}, "
                     f"total {f.get('total')}. Market: home team {n1(f.get('market_margin'))}, total {f.get('market_total')}. "
                     f"{f.get('summary') or ''} Why the price may be wrong: {f.get('check_why') or ''}")
        L.append("")
    gs = game_scores(d["games"])
    if gs:
        L += ["**Forecast accuracy by game** (average miss in points, lower is better; each row uses the same games "
              "for every column)", "",
              "| Games | Count | Margin: stats | Margin: AI | Margin: market | Total: stats | Total: AI | Total: market |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]

        def f1(x):
            return "n/a" if x is None else f"{x:.1f}"
        for name, n, cols in gs:
            L.append(f"| {name} | {n} | {f1(cols[0][0])} | {f1(cols[1][0])} | {f1(cols[2][0])} | "
                     f"{f1(cols[0][1])} | {f1(cols[1][1])} | {f1(cols[2][1])} |")
        L += ["", "Games get an AI forecast because the stats and the market disagreed, so that group is not a "
              "random sample. The control row is.", ""]
    else:
        L += [f"Forecast accuracy by game: no finished games graded yet ({len(d['track'])} games being tracked, "
              f"{sum(1 for g in d['track'].values() if g.get('ai'))} with an AI forecast).", ""]
    for label_, need in (("all tracked contracts", ("p_kalshi", "p_stats")),
                         ("contracts in games with an AI forecast", ("p_kalshi", "p_stats", "p_ai"))):
        br = brier(d["graded"], need)
        if br["n"]:
            L += [f"**Probability accuracy on {label_}**: {br['n']} contracts from {br['games']} games (Brier score, lower is "
                  "better, 0.25 is a coin flip). Several contracts come from the same game, so treat the game count as the sample size.",
                  "", "| Forecast | Brier score | Contracts |", "| --- | --- | --- |"]
            for key, name in SOURCES:
                if br.get(key):
                    L.append(f"| {name} | {br[key][0]:.4f} | {br[key][1]} |")
            L.append("")
    if v1:
        t1 = trade_stats(v1)
        L += ["**v1 picks** (earlier rules, kept for the record and not part of the v2 result). The first college "
              "picks on Nov 13 were placed minutes before two rule fixes, which is why some games hold two "
              "positions and one pick is under the old 6 point minimum.", ""]
        L += stats_line(t1)
        L += trade_table(v1)
    return "\n".join(L)


def md_to_html(md: str) -> str:
    """Just enough Markdown for this report: headings, tables, bullets, bold, paragraphs."""
    import re
    out, table = [], False

    def inline(s):
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(s))
    for line in md.split("\n"):
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("- ") for c in cells):
                continue
            if not table:
                out.append("<div class='tw'><table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells) + "</tr>")
                table = True
            else:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
            continue
        if table:
            out.append("</table></div>")
            table = False
        if line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("- "):
            out.append(f"<p class='li'>{inline(line[2:])}</p>")
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
    if table:
        out.append("</table></div>")
    return "\n".join(out)


CSS = """:root{--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#e3e3e3;--alt:#f7f7f7}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eaeaea;--mut:#a0a0a0;--line:#333;--alt:#1d1d1d}}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:1.5em}h2{margin-top:2em;border-bottom:1px solid var(--line);padding-bottom:4px}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.88em;margin:.6em 0}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);white-space:nowrap}th{color:var(--mut);font-weight:600}
tr:nth-child(even) td{background:var(--alt)}.li{margin:.3em 0 .3em 1em}"""


def build(root: str = ".") -> str:
    data = {b: load(root, b) for b, _ in BOTS}
    runs = [r for d in data.values() for r in d["runs"] if not r.get("dry")]
    first = min((r["ts"] for r in runs), default=None)
    L = ["# Kalshi sports paper-trading scorecard", "",
         f"Updated {when(iso(now_utc()))}. Paper trading only: no real orders are placed and no real money is at risk. "
         "Each bot starts with a $1,000 paper bankroll and 1 unit is $10.", ""]
    if first:
        L += [f"Test started {when(first)}. v2 rules started Sat Nov 14. Bot runs so far: {len(runs)} "
              "(each bot counts separately).", ""]
    for ver, name in (("v2", "v2 picks"), ("v1", "v1 picks (earlier rules)")):
        L += [f"**{name}**", "",
              "| Bot | Picks | Open | Won | Lost | Pulled | Open stake | Profit | Units | Return on settled stake | Closing-price edge |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        allv = []
        for b, title in BOTS + [(None, "**All three**")]:
            tr = allv if b is None else [t for t in data[b]["trades"] if (version(t) == "v1") == (ver == "v1")]
            if b is not None:
                allv += tr
            s = trade_stats(tr)
            L.append(f"| {title} | {s['n']} | {s['open']} | {s['won']} | {s['lost']} | {s['pulled']} | ${s['open_stake']:,.2f} | "
                     f"{money(s['pnl'])} | {s['units']:+.2f} | {pct(s['roi'], True)} | "
                     f"{'n/a' if s['clv_avg'] is None else f'{s['clv_avg'] * 100:+.1f}c'} |")
        L.append("")
    L += ["**Confidence.** HIGH: the edge holds up even after the forecast is pulled most of the way to the market price; "
          "sized by Kelly, up to 2 units. MID: I have a specific written reason the price may be wrong and my own forecast "
          "beats the price by 10 or more points; half a unit. LOW: the same, with a 7 to 10 point gap; a quarter unit. "
          "A game with no specific reason against the market gets no pick. There is no daily limit on picks.", ""]
    L += ["How to read this: profit over a handful of bets is mostly luck. The fairer tests are whether the AI forecast "
          "misses by less than the stats forecast and the market on the same games, and whether prices move toward the "
          "picks after they are made. The rules, and what would cause the AI to lose authority, are in the README.", ""]
    for b, title in BOTS:
        L.append(bot_md(b, title, data[b]))
    md = "\n".join(L) + "\n"
    with open(os.path.join(root, "SCORECARD.md"), "w") as f:
        f.write(md)
    os.makedirs(os.path.join(root, "docs"), exist_ok=True)
    with open(os.path.join(root, "docs", "index.html"), "w") as f:
        f.write("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>Sports Bot Scorecard</title><style>{CSS}</style></head><body>\n{md_to_html(md)}\n</body></html>\n")
    return md


if __name__ == "__main__":
    print(build(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
