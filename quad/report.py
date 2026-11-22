"""Scorecard for the four new bots: NEW_BOTS_SCORECARD.md."""
from __future__ import annotations

import os
from zoneinfo import ZoneInfo

from core.util import now_utc, parse_iso, read_jsonl
from .bots import BOTS
from .read import DIR

CT = ZoneInfo("America/Chicago")
SPORT = {"cfb": "College football", "nfl": "NFL", "nba": "NBA"}


def money(x):
    return f"{'+' if x >= 0 else '-'}${abs(x):.2f}"


def build(root):
    lines = ["# New bots scorecard", "",
             f"Updated {now_utc().astimezone(CT).strftime('%a %b %-d %-I:%M %p')} CT. Paper trading only. "
             "Each bot has a $1,000 paper bankroll; 1 unit = $10. How each bot works: [NEW_BOTS.md](NEW_BOTS.md).", "",
             "| Bot | Picks | Open | Won | Lost | Profit | Units | Return on settled stake | Avg closing-price edge |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    detail = []
    for bot, name in BOTS.items():
        st = {s["trade_id"]: s for s in read_jsonl(os.path.join(DIR, bot, "settlements.jsonl"))}
        tr = [t for t in read_jsonl(os.path.join(DIR, bot, "trades.jsonl")) if st.get(t["id"], {}).get("outcome") != "withdrawn"]
        won = sum(1 for t in tr if st.get(t["id"], {}).get("outcome") == "won")
        lost = sum(1 for t in tr if st.get(t["id"], {}).get("outcome") == "lost")
        pnl = sum(st[t["id"]]["pnl"] for t in tr if t["id"] in st)
        staked = sum(t["cost"] for t in tr if t["id"] in st)
        clv = [st[t["id"]]["clv"] for t in tr if t["id"] in st and st[t["id"]].get("clv") is not None]
        lines.append(f"| {name} | {len(tr)} | {len(tr) - len(st)} | {won} | {lost} | {money(pnl)} | {pnl / 10:+.2f} | "
                     f"{'n/a' if not staked else f'{pnl / staked * 100:+.1f}%'} | "
                     f"{'n/a' if not clv else f'{sum(clv) / len(clv) * 100:+.1f}c'} |")
        detail += ["", f"## {name}", ""]
        if not tr:
            detail.append("No picks yet.")
            continue
        detail += ["| Confidence | Game | Start (CT) | Sport | Pick | Price | Size | Edge | Result | Profit |",
                   "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for t in sorted(tr, key=lambda t: t["start"], reverse=True):
            s = st.get(t["id"])
            detail.append(f"| **{t['tier'].upper()}** | {t['game']} | {t['start_ct']} | {SPORT[t['sport']]} | {t['label']} | "
                          f"{t['price'] * 100:.0f}c | {t['units']:.2f}u | {t['edge'] * 100:+.1f} | "
                          f"{s['outcome'] if s else 'open'} | {money(s['pnl']) if s else ''} |")
        detail += ["", "Why each pick was made:", ""]
        for t in sorted(tr, key=lambda t: t["start"], reverse=True)[:30]:
            detail.append(f"- **{t['tier'].upper()}: {t['game']}, {t['label']}.** {' '.join(t['why'])}. {t['size_why']}.")
    lines += ["", "Profit over a few dozen picks is mostly luck. The fairer early test is the closing-price edge: "
              "whether Kalshi's price moved toward each pick before the game started."] + detail
    with open(os.path.join(root, "NEW_BOTS_SCORECARD.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
