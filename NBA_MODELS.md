# NBA model comparison

Updated Mon Nov 16 4:43 PM CT. Paper trading only: no real orders, no real money. Every model trades the same Kalshi NBA markets with its own $1,000 paper bankroll (1 unit = $10), one position per game at most.

| Model | What drives it |
| --- | --- |
| **Current NBA bot (v2.3)** | stats forecast, blind Claude forecast, then held close to the price |
| **Rotation** | player availability and player impact, numbers only |
| **Price Pattern** | how Kalshi's own NBA prices have been wrong before |
| **Scout** | Claude's full read of the game, prices in view |

## Standings

| Model | Picks | Won | Lost | Open | Staked | Profit | Units | Return | Closing-price edge | Beat the close |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Current NBA bot (v2.3)** | 1 | 0 | 0 | 0 | $6.96 | -$0.78 | -0.08 | -11.2% | n/a | n/a |
| **Rotation** | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a | n/a |
| **Price Pattern** | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a | n/a |
| **Scout** | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a | n/a |

Closing-price edge: the Kalshi price at the last hourly run before tip-off minus the price paid. Positive means the market moved toward the pick after it was made, the earliest sign of a real edge. Profit over one week is mostly luck.

## Forecast accuracy on every game

Each model's home-win probability on every game it looked at, picks and passes alike, against what happened. Brier score: lower is better, 0.25 is a coin flip. The difference column is the model minus Kalshi on the same games; below zero means the model beat the market. The range is a 95% bootstrap over games.

| Model | Games | Model | Kalshi when the model decided | Difference | 95% range | Kalshi at the close | Difference vs close |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current NBA bot (v2.3) | 11 | 0.1743 | n/a | n/a |  | 0.1987 | -0.0244 |
| Rotation | 0 | | | | | | |
| Price Pattern | 0 | | | | | | |
| Scout | 0 | | | | | | |

The current bot only writes a forecast for the games it picks for a deep read, so its row covers fewer games.

## Current NBA bot (v2.3)

| Confidence | Picks | Won | Lost | Profit | Return |
| --- | --- | --- | --- | --- | --- |
| **HIGH** | 1 | 0 | 0 | -$0.78 | -11.2% |
| **MID** | 0 | 0 | 0 | +$0.00 | n/a |
| **LOW** | 0 | 0 | 0 | +$0.00 | n/a |

| Confidence | Matchup | Start (CT) | Pick | Price | Size | Model says | Market says | Result | Profit | Closing edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **HIGH** | Dallas Mavericks at Cleveland Cavaliers | Sat 6:30 PM | Cleveland Cavaliers +4.5 | 37c | 0.70u | 42% | 36% | pulled | -$0.78 |  |

Why each pick was made:

- **HIGH: Dallas Mavericks at Cleveland Cavaliers, Cleveland Cavaliers +4.5.** Even matchup. Cleveland is on a back-to-back and Mobley sat last night; Dallas is without Lively and lost by 39 on Thursday.

## Rotation

No picks yet.

## Price Pattern

No picks yet.

## Scout

No picks yet.

## How the week will be judged

Set before the first pick. One week is about 50 games, enough to rule out a model that is badly wrong and not enough to prove one is right.

1. **Forecast accuracy against Kalshi** on every game the model looked at (table above). A model that cannot get below Kalshi's own Brier score on the same games has no edge to bet, however its picks went.
2. **Closing-price edge** on its picks. Positive on average means the market agreed with the pick after it was made.
3. **Profit and return** on its picks, read with the record against the number it expected to win.
4. **Calibration by confidence**: High picks should win more often than Mid, and Mid more than Low.

A model is worth keeping past the week if it is ahead of Kalshi on point 1 or point 2 and not far behind on the other. A model behind on both is retired, whatever its profit.

