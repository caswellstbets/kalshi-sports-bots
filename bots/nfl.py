"""NFL bot. One game a week per team, so ratings lean harder on the sportsbook
line, and the calendar matters: byes help, short road weeks hurt."""
from core.config import BotConfig
from core.util import parse_iso


def situational(ctx: dict) -> tuple[float, float, list[str]]:
    g, last = ctx["game"], ctx["last"]
    start = parse_iso(g["start"])
    margin, notes = 0.0, []
    for side, sign in (("home", 1), ("away", -1)):
        prev = last.get(g[side]["id"])
        if prev is None:
            continue
        days = (start - prev).total_seconds() / 86400
        if days >= 12.5:                       # coming off a bye
            margin += sign * 0.8
            notes.append(f"{g[side]['abbr']} off a bye")
        elif days <= 5.2 and side == "away":   # Thursday game on the road
            margin -= sign * 0.6
            notes.append(f"{g[side]['abbr']} on a short week, on the road")
    return margin, 0.0, notes


CONFIG = BotConfig(
    name="nfl", title="NFL", kalshi_prefix="KXNFL", season_start="2026-09-09",
    hfa=1.6, ridge=8.0, half_life_days=70, sd_margin=13.3, sd_total=13.5,
    window_hours=24, situational=situational, book_weight=0.75,
    ai_margin_cap=2.0, ai_total_cap=3.0,
)

if __name__ == "__main__":
    from core.cli import main
    main(CONFIG)
