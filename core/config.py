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
    # --- stats model ---
    form_weight: float = 0.35      # share of the model that comes from recent form rather than the full season
    form_half_life_days: float = 14.0
    total_scale: float = 1.0       # how much of the model's above/below-average total to believe (from back-testing)
    total_bias: float = 0.0
    trade_types: tuple = ("ml", "spread", "total")
    min_rated_games: int = 5       # both teams need this many games behind their rating
    # --- AI forecast and market check (v2) ---
    strategy_version: str = "v2.0"
    deep_reads_per_day: int = 8    # games per day that get a full AI forecast: biggest stats-vs-market gaps
    forecast_lead_minutes: float = 40.0  # no deep read for a game starting sooner than this
    control_reads_per_day: int = 2 # plus this many chosen at random, so the AI is graded on unselected games too
    # Trust: how far the bet probability moves from the market price toward the AI forecast (log-odds).
    # GUESS, deliberately cautious. The AI has no track record yet, and the stats back-test cannot
    # stand in for one. Frozen for the evaluation window; see README "Rules set in advance".
    trust: dict = field(default_factory=lambda: {"ml": 0.35, "spread": 0.35, "total": 0.25})
    trust_ceiling: float = 0.70
    thin_data_games: int = 6       # either team with fewer rated games than this ...
    thin_data_factor: float = 0.7  # ... multiplies trust by this (GUESS)
    shrink_factor: float = 0.5     # a market check that ends in "shrink" halves trust (GUESS)
    check_gap_margin: float = 3.0  # AI vs market gap that needs a written market check
    check_gap_total: float = 4.0
    soft_reason_cap: float = 3.0   # most a forecast may differ from the stats on soft judgment alone
    hard_reason_gap: float = 7.0   # beyond this, at least one hard fact or stat-based reason is required
    # --- paper trading ---
    window_hours: float = 24.0     # only trade this close to the start
    lockout_minutes: float = 5.0   # ... and never this close, or after
    bankroll: float = 1000.0
    unit_pct: float = 0.01
    kelly_fraction: float = 0.125  # an eighth of Kelly on the market-checked probability; no minimum stake
    max_units_trade: float = 2.0
    max_units_game: float = 2.0    # one position per game, so this equals the per-trade cap
    min_edge_trade: float = 0.03   # edge after the market check and exact fees, below which there is no bet (GUESS)
    max_trades_per_day: int = 5
    # only trade near the main line, where the forecast is most reliable; no long shots
    price_band: dict = field(default_factory=lambda: {"ml": (0.15, 0.85), "spread": (0.35, 0.65), "total": (0.35, 0.65)})
    max_spread: float = 0.08
    min_ask_size: float = 10
    pull_margin: float = 0.04      # sell only when the net bid beats the value of holding by this much

    @property
    def unit(self) -> float:
        return self.bankroll * self.unit_pct
