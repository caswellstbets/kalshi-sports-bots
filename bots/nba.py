"""NBA bot. Daily slates, high scoring, and rest matters more than in any other
sport: a team on the second night of a back-to-back gives up about a point and a half."""
from core.config import BotConfig
from core.util import parse_iso


def situational(ctx: dict) -> tuple[float, float, list[str]]:
    g, last = ctx["game"], ctx["last"]
    start = parse_iso(g["start"])
    margin, total, notes = 0.0, 0.0, []
    for side, sign in (("home", 1), ("away", -1)):
        prev = last.get(g[side]["id"])
        if prev is None:
            continue
        days = (start - prev).total_seconds() / 86400
        if days < 1.6:      # played last night
            margin -= sign * 1.6
            total -= 1.0
            notes.append(f"{g[side]['abbr']} on a back-to-back")
        elif days >= 3.5:   # two or more full days off
            margin += sign * 0.4
            notes.append(f"{g[side]['abbr']} rested ({days:.0f} days)")
    return margin, total, notes


CONFIG = BotConfig(
    name="nba", title="NBA", kalshi_prefix="KXNBA", season_start="2026-10-20",
    hfa=2.2, ridge=8.0, half_life_days=45, sd_margin=12.3, sd_total=18.0,
    window_hours=12, situational=situational,
    ai_margin_cap=2.0, ai_total_cap=3.0,
    max_strike_gap={"spread": 1.0, "total": 2.0},  # no key numbers in basketball
)

if __name__ == "__main__":
    from core.cli import main
    main(CONFIG)
