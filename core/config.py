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
    book_weight: float = 0.70      # weight on the sportsbook (or Kalshi) anchor; the rest is the model
    max_model_gap_margin: float = 6.0   # model may disagree with the anchor by at most this much
    max_model_gap_total: float = 8.0
    ai_margin_cap: float = 2.0
    ai_total_cap: float = 3.0
    # --- paper trading ---
    window_hours: float = 24.0     # only trade this close to the start
    lockout_minutes: float = 5.0   # ... and never this close, or after
    bankroll: float = 1000.0
    unit_pct: float = 0.01
    kelly_fraction: float = 0.25
    max_units_trade: float = 2.0
    max_units_game: float = 5.0
    min_edge: dict = field(default_factory=lambda: {"ml": 0.04, "spread": 0.04, "total": 0.04})
    min_edge_no_book: float = 0.07
    max_edge: float = 0.15         # bigger than this is more likely bad data than a gift
    min_book_edge: float = 0.0     # the sportsbook on its own must rate the price fair or better after fees
    # only trade near the main line, where the forecast is most reliable; no long shots
    price_band: dict = field(default_factory=lambda: {"ml": (0.12, 0.88), "spread": (0.30, 0.70), "total": (0.30, 0.70)})
    # spreads and totals are only traded at (or right next to) the sportsbook's own number, so the
    # bot never has to guess how much an extra point is worth across football's key numbers
    max_strike_gap: dict = field(default_factory=lambda: {"spread": 0.0, "total": 1.0})
    notes_fresh_hours: float = 12.0  # how long an AI review of a game stays valid
    max_spread: float = 0.08
    min_ask_size: float = 10
    pull_margin: float = 0.01      # pull a pick when the market bids this much above the bot's fair value

    @property
    def unit(self) -> float:
        return self.bankroll * self.unit_pct
