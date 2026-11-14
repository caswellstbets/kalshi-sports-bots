"""Scorecard: reads the ledgers and writes SCORECARD.md plus docs/index.html.
Run on its own with:  python -m core.report"""
from __future__ import annotations

import html
import os

from .util import ET, iso, now_utc, parse_iso, read_json, read_jsonl

BOTS = [("nba", "NBA"), ("nfl", "NFL"), ("cfb", "College football")]
BANKROLL, UNIT = 1000.0, 10.0
SOURCES = [("p_kalshi", "Kalshi closing price"), ("p_book", "Sportsbook line"), ("p_model", "Power ratings alone"),
           ("p_blend", "Bot before AI"), ("p_final", "Bot with AI")]


def load(root: str, bot: str) -> dict:
    d = os.path.join(root, "data", bot)
    trades = read_jsonl(os.path.join(d, "trades.jsonl"))
    settles = {s["trade_id"]: s for s in read_jsonl(os.path.join(d, "settlements.jsonl"))}
    for t in trades:
        t["settle"] = settles.get(t["id"])
    return {"trades": trades, "graded": read_jsonl(os.path.join(d, "graded_predictions.jsonl")),
            "open_preds": read_json(os.path.join(d, "open_predictions.json"), {}),
            "runs": read_jsonl(os.path.join(d, "run_log.jsonl"))}


def trade_stats(trades: list[dict]) -> dict:
    done = [t for t in trades if t["settle"]]
    decided = [t for t in done if t["settle"]["outcome"] in ("won", "lost")]
    staked = sum(t["cost"] for t in done)
    pnl = sum(t["settle"]["pnl"] for t in done)
    clv = [t["settle"]["clv"] for t in done if t["settle"].get("clv") is not None]
    return {
        "n": len(trades), "open": len(trades) - len(done), "settled": len(done),
        "won": sum(t["settle"]["outcome"] == "won" for t in done),
        "lost": sum(t["settle"]["outcome"] == "lost" for t in done),
        "pulled": sum(t["settle"]["outcome"] == "pulled" for t in done),
        "staked": staked, "pnl": pnl, "units": pnl / UNIT,
        "roi": pnl / staked if staked else None,
        "avg_edge": sum(t["edge"] for t in trades) / len(trades) if trades else None,
        "expected_wins": sum(t["p_final"] for t in decided), "decided": len(decided),
        "clv_n": len(clv), "clv_avg": sum(clv) / len(clv) if clv else None,
        "clv_beat": sum(c > 0 for c in clv) / len(clv) if clv else None,
    }


def brier(graded: list[dict]) -> dict:
    """Brier score per source on the markets where every source has a number, so they are comparable.
    Winner markets only count once per game (the two sides are mirror images)."""
    rows, seen = [], set()
    for g in graded:
        if g["mtype"] == "ml":
            if g["game_id"] in seen:
                continue
            seen.add(g["game_id"])
        rows.append(g)
    need = ["p_kalshi", "p_blend", "p_final"]
    base = [g for g in rows if all(g.get(k) is not None for k in need)]
    out = {"n": len(base), "games": len({g["game_id"] for g in base})}
    for key, _ in SOURCES:
        sub = [g for g in base if g.get(key) is not None]
        out[key] = (sum((g[key] - g["result"]) ** 2 for g in sub) / len(sub), len(sub)) if sub else None
    return out


def buckets(graded: list[dict], key: str = "p_final") -> list[tuple]:
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


def when(ts: str) -> str:
    return parse_iso(ts).astimezone(ET).strftime("%a %b %-d %-I:%M %p ET")


def verdict(ts: dict, br: dict) -> str:
    if ts["settled"] < 10 and br["n"] < 60:
        return "Too early to say. Not enough finished games yet."
    bits = []
    if ts["clv_n"] >= 8:
        bits.append("prices moved toward its picks on average" if ts["clv_avg"] > 0.003 else
                    "prices moved against its picks on average" if ts["clv_avg"] < -0.003 else
                    "prices did not move for or against its picks")
    if br.get("p_final") and br.get("p_kalshi") and br["n"] >= 60:
        d = br["p_final"][0] - br["p_kalshi"][0]
        bits.append("its probabilities scored better than Kalshi's closing prices" if d < -0.002 else
                    "its probabilities scored worse than Kalshi's closing prices" if d > 0.002 else
                    "its probabilities scored about the same as Kalshi's closing prices")
    return ("So far, " + " and ".join(bits) + ".") if bits else "Too early to say."


def bot_md(bot: str, title: str, d: dict) -> str:
    ts, br = trade_stats(d["trades"]), brier(d["graded"])
    L = [f"## {title}", "", verdict(ts, br), ""]
    L += ["| Paper trades | Open | Won | Lost | Pulled | Staked | Profit | Units | Return on stake |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
          f"| {ts['n']} | {ts['open']} | {ts['won']} | {ts['lost']} | {ts['pulled']} | ${ts['staked']:,.2f} | "
          f"{money(ts['pnl'])} | {ts['units']:+.2f} | {pct(ts['roi'], True)} |", ""]
    if ts["decided"]:
        L.append(f"Of {ts['decided']} decided trades the bot expected to win {ts['expected_wins']:.1f} and won {ts['won']}.")
    if ts["clv_n"]:
        L.append(f"Closing-price edge: {ts['clv_avg'] * 100:+.1f} cents per contract on average across {ts['clv_n']} trades, "
                 f"and {pct(ts['clv_beat'], digits=0)} of them beat the closing price.")
    if ts["avg_edge"] is not None:
        L.append(f"Average edge claimed at entry: {ts['avg_edge'] * 100:+.1f} points after fees.")
    L.append("")
    if br["n"]:
        L += [f"**Calibration** on {br['n']} graded markets from {br['games']} games (Brier score, lower is better; "
              "0.25 is a coin flip):", "", "| Forecast | Brier score | Markets |", "| --- | --- | --- |"]
        for key, name in SOURCES:
            if br.get(key):
                L.append(f"| {name} | {br[key][0]:.4f} | {br[key][1]} |")
        L += ["", "| When the bot said | Markets | Average forecast | Actually happened |", "| --- | --- | --- | --- |"]
        for name, n, avg, hit in buckets(d["graded"]):
            L.append(f"| {name} | {n} | {pct(avg)} | {pct(hit)} |")
        L.append("")
    else:
        L += [f"Calibration: no graded markets yet ({len(d['open_preds'])} being tracked).", ""]
    if d["trades"]:
        L += ["| Placed | Game | Pick | Price | Size | Bot | Edge | Confidence | Result | Profit | Closing edge |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for t in sorted(d["trades"], key=lambda t: t["ts"], reverse=True):
            s = t["settle"]
            L.append(f"| {when(t['ts'])} | {t['game']} | {t['label']} | {t['price'] * 100:.0f}c | "
                     f"{t['contracts']} ({t['units']:.2f}u) | {pct(t['p_final'])} | {t['edge'] * 100:+.1f} | {t['confidence']} | "
                     f"{s['outcome'] if s else 'open'} | {money(s['pnl']) if s else ''} | "
                     f"{'' if not s or s.get('clv') is None else f'{s['clv'] * 100:+.0f}c'} |")
        L.append("")
        why = [t for t in d["trades"] if (t.get("ai") or {}).get("reason")]
        if why:
            L.append("AI notes on the most recent picks:")
            L.append("")
            for t in sorted(why, key=lambda t: t["ts"], reverse=True)[:8]:
                L.append(f"- **{t['game']}, {t['label']}:** {t['ai']['reason']}")
            L.append("")
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
    all_trades = [t for d in data.values() for t in d["trades"]]
    ts = trade_stats(all_trades)
    runs = [r for d in data.values() for r in d["runs"]]
    first = min((r["ts"] for r in runs), default=None)
    L = ["# Kalshi sports paper-trading scorecard", "",
         f"Updated {when(iso(now_utc()))}. Paper trading only: no real orders are placed and no real money is at risk. "
         "Each bot starts with a $1,000 paper bankroll and 1 unit is $10.", ""]
    if first:
        L += [f"Test started {when(first)}. Runs so far: {len({r['ts'][:13] for r in runs})}.", ""]
    L += ["| Bot | Trades | Open | Won | Lost | Pulled | Profit | Units | Return on stake | Closing-price edge |",
          "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for b, title in BOTS:
        s = trade_stats(data[b]["trades"])
        L.append(f"| {title} | {s['n']} | {s['open']} | {s['won']} | {s['lost']} | {s['pulled']} | {money(s['pnl'])} | "
                 f"{s['units']:+.2f} | {pct(s['roi'], True)} | "
                 f"{'n/a' if s['clv_avg'] is None else f'{s['clv_avg'] * 100:+.1f}c'} |")
    L.append(f"| **All three** | {ts['n']} | {ts['open']} | {ts['won']} | {ts['lost']} | {ts['pulled']} | {money(ts['pnl'])} | "
             f"{ts['units']:+.2f} | {pct(ts['roi'], True)} | "
             f"{'n/a' if ts['clv_avg'] is None else f'{ts['clv_avg'] * 100:+.1f}c'} |")
    L += ["", "How to read this: profit over a handful of bets is mostly luck. Closing-price edge (did the price move "
          "toward the bot's side after it bought) and calibration (were its percentages right) are the fairer early tests.", ""]
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
