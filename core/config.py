"""Settings shared by every bot. Each bot overrides the sport-specific ones."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class BotConfig:
    name: str                      # nba | nfl | cfb
    title: str
    kalshi_prefix: str             # KXNBA -> KXNBAGAME / KXNBASPREAD / KXNBATOTAL
    season_start: str              # first day of the regular season (used by the NBA day-by-day fetch)
    # --- model ---
    hfa: float                     # home-field advantage, points
    ridge: float                   # shrinkage, in league-average games
    half_life_days: float          # recency weighting
    sd_margin: float               # spread of final margin around the forecast
    sd_total: float                # spread of final total around the forecast
    margin_cap: float | None = None
    min_games: int = 3
    espn_groups: list[str] | None = None
    situational: Callable[[dict], tuple[float, float, list[str]]] | None = None
    # --- blending ---
    book_weight: float = 0.10      # the sportsbook line is a small input; the bot's own model is the rest
    form_weight: float = 0.35      # share of the model that comes from recent form rather than the full season
    form_half_life_days: float = 14.0
    total_scale: float = 1.0       # how much of the model's above/below-average total to believe (from back-testing)
    total_bias: float = 0.0
    trade_types: tuple = ("ml", "spread", "total")
    min_rated_games: int = 5       # both teams need this many games behind their rating
    flag_gap_margin: float = 7.0   # model vs sportsbook gap that gets called out for the AI review (no veto)
    ai_margin_cap: float = 3.5
    ai_total_cap: float = 4.5
    # --- paper trading ---
    window_hours: float = 24.0     # only trade this close to the start
    lockout_minutes: float = 5.0   # ... and never this close, or after
    bankroll: float = 1000.0
    unit_pct: float = 0.01
    kelly_fraction: float = 0.125  # an eighth of the Kelly stake: sized to the edge, discounted for model error
    min_units_trade: float = 0.5
    max_units_trade: float = 3.0
    confidence_stake: dict = field(default_factory=lambda: {"low": 0.7, "medium": 1.0, "high": 1.2})
    max_units_game: float = 5.0
    min_edge: dict = field(default_factory=lambda: {"ml": 0.06, "spread": 0.06, "total": 0.06})
    max_trades_per_day: int = 5    # only the strongest opinions of the day get a pick
    max_edge: float = 0.16         # bigger than this is more likely bad data than a real opinion
    # only trade near the main line, where the forecast is most reliable; no long shots
    price_band: dict = field(default_factory=lambda: {"ml": (0.15, 0.85), "spread": (0.35, 0.65), "total": (0.35, 0.65)})
    notes_fresh_hours: float = 12.0  # how long an AI review of a game stays valid
    max_spread: float = 0.08
    min_ask_size: float = 10
    pull_margin: float = 0.01      # pull a pick when the market bids this much above the bot's fair value

    @property
    def unit(self) -> float:
        return self.bankroll * self.unit_pct
