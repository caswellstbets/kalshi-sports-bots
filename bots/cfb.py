"""College football bot. 260+ teams of wildly different strength, so opponent
adjustment does the heavy lifting: blowouts are capped, FBS and FCS results are
rated together, and anyone with fewer than three games is pooled as a generic
lower-division opponent. Outcomes are wider than the NFL, so the bot is less sure."""
from core.config import BotConfig
from core.util import parse_iso


def situational(ctx: dict) -> tuple[float, float, list[str]]:
    g, last = ctx["game"], ctx["last"]
    start = parse_iso(g["start"])
    margin, notes = 0.0, []
    for side, sign in (("home", 1), ("away", -1)):
        prev = last.get(g[side]["id"])
        if prev is not None and (start - prev).total_seconds() / 86400 >= 12.5:
            margin += sign * 0.6
            notes.append(f"{g[side]['abbr']} off a bye")
    return margin, 0.0, notes


CONFIG = BotConfig(
    name="cfb", title="College football", kalshi_prefix="KXNCAAF", season_start="2026-08-22",
    hfa=2.6, ridge=1.0, half_life_days=70, sd_margin=15.8, sd_total=17.3, total_scale=0.63, total_bias=-1.3,
    margin_cap=28.0, min_games=3, espn_groups=["80", "81"],
    window_hours=24, situational=situational,
    form_half_life_days=21, form_weight=0.30, max_trades_per_day=8, ai_margin_cap=3.5, ai_total_cap=4.5,
)

if __name__ == "__main__":
    from core.cli import main
    main(CONFIG)
