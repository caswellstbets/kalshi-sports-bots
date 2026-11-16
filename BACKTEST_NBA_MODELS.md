# Back-test of the lab NBA models against Kalshi prices

Kalshi NBA winner markets, home team's price about 3 hours before the start. Fit on 416 games from 2025-26, scored on 197 games from 2026-27 the fit never saw. `python -m research.backtest_kalshi`.

- 2025-26: Kalshi Brier at T-3h 0.2143, at the close 0.2144 (416 games).
- 2026-27: Kalshi Brier at T-3h 0.1830, at the close 0.1813 (197 games).

## Calibration of Kalshi's price (both seasons)

| Price band | Games | Average price | Home team won |
| --- | --- | --- | --- |
| 0.00-0.20 | 38 | 0.152 | 0.105 |
| 0.20-0.35 | 94 | 0.274 | 0.309 |
| 0.35-0.50 | 125 | 0.419 | 0.424 |
| 0.50-0.65 | 133 | 0.574 | 0.549 |
| 0.65-0.80 | 136 | 0.726 | 0.699 |
| 0.80-1.00 | 87 | 0.856 | 0.851 |

## Price Pattern (tried and dropped)

The first idea for the second model used no basketball at all: a logistic regression of the home result on Kalshi's own numbers: x +0.756, move_open +0.071, move_24 +0.330, fav -0.019, intercept -0.011. `x` is the price in log-odds (a coefficient under 1 means favourites have been overpriced), `move_open` and `move_24` are how far it moved since the market opened and in the last 24 hours, `fav` is how lopsided it is.

- 2025-26 (fit): Pattern Brier 0.2123 vs Kalshi 0.2143
  - Trades at 3+ point edge: 69, won 22 (expected 19.9), staked $373, profit $+114.35, return +30.7%, closing-price edge +0.1c
- 2026-27 (new): Pattern Brier 0.1897 vs Kalshi 0.1830
  - Trades at 3+ point edge: 42, won 7 (expected 13.2), staked $251, profit $-117.97, return -47.0%, closing-price edge -0.2c

It lost on the new season, so four more price-pattern ideas were written down first and then tested in both seasons. None held: each changes sign or stays inside its noise.

| Idea | 2025-26 | 2026-27 |
| --- | --- | --- |
| a team's last 5 games beyond its season average (market overreacts to streaks) | +0.16 (standard error 0.14, 401 games) | -0.20 (standard error 0.31, 103 games) |
| the margin of each team's last game (market overreacts to one result) | -0.05 (standard error 0.10, 401 games) | +0.16 (standard error 0.20, 103 games) |
| Lakers, Warriors, Knicks or Celtics (popular teams overpriced) | +0.11 (standard error 0.22, 401 games) | +0.76 (standard error 0.46, 103 games) |
| price move over the last 24 hours (momentum or reversal) | +0.16 (standard error 0.49, 401 games) | -0.31 (standard error 0.70, 103 games) |

Kalshi's NBA winner prices show no simple pattern that survives from one season to the next, so the second model was replaced with Injury News (below).

## Rotation

How far to lean from Kalshi's price toward the Rotation forecast (trust, in log-odds; 0 = the price, 1 = the model). Brier on 2025-26:

| Trust | Brier 2025-26 | Brier 2026-27 |
| --- | --- | --- |
| 0 | 0.2143 | 0.1830 |
| 0.1 | 0.2136 | 0.1834 |
| 0.2 | 0.2131 | 0.1840 |
| 0.3 | 0.2127 | 0.1847 |
| 0.4 | 0.2125 | 0.1856 |
| 0.5 | 0.2125 | 0.1866 |
| 0.7 | 0.2132 | 0.1891 |
| 1.0 | 0.2161 | 0.1937 |

Best on 2025-26 alone: 0.4. On 2026-27 any trust above 0 scored worse than Kalshi's price. The live value is **0.25**, between the two, chosen after seeing both seasons and frozen for the week. Read plainly: the Rotation forecast has not yet beaten Kalshi on games it was not fit on.

- 2025-26 (fit): trades at 3+ point edge 20, won 10 (expected 6.9), staked $100, profit $+67.75, return +67.6%, closing-price edge +0.3c
- 2026-27 (new): trades at 3+ point edge 2, won 2 (expected 1.1), staked $25, profit $+25.35, return +102.8%, closing-price edge -5.0c

Winner markets only: spread and total prices from past seasons were not downloaded. Fills assume the quoted ask with enough size, and the Kalshi fee.

## Injury News

131 games where a rotation player sat unexpectedly and the ratings value it at 1+ points.
- 3 hours before the start: Kalshi had moved 61% of what the ratings say the absence was worth. Where the gap left was over 4 points (57 games), the side the news favoured beat the price by +2.4 points on average (noise at this sample size is about 7 points).
- at the close: Kalshi had moved 79% of what the ratings say the absence was worth. Where the gap left was over 4 points (55 games), the side the news favoured beat the price by -0.1 points on average (noise at this sample size is about 7 points).

Some of these absences were announced after the 3-hour mark, which flatters the news side at 3 hours. At the close the gap left over predicted nothing. This model is tested forward with the injury report as it changes during the day.

## Scout

Claude's read cannot be replayed fairly on past games (it would know the results), so Scout is tested forward only.

