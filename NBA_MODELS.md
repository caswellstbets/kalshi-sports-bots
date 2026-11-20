# NBA model comparison

Updated Thu Nov 19 7:39 PM CT. Paper trading only: no real orders, no real money. Every model trades the same Kalshi NBA markets with its own $1,000 paper bankroll (1 unit = $10), one position per game at most.

Comparison window started Mon Nov 16 4:51 PM CT. The current bot's row counts only games from then on, so all four cover the same nights.

| Model | What drives it |
| --- | --- |
| **Current NBA bot (v2.3)** | stats forecast, blind Claude forecast, then held close to the price |
| **Rotation** | player availability and player impact, numbers only |
| **Injury News** | fresh injury-report changes the Kalshi price has not caught up with |
| **Scout** | Claude's full read of the game, prices in view |

## Standings

| Model | Picks | Won | Lost | Open | Staked | Profit | Units | Return | Closing-price edge | Beat the close |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Current NBA bot (v2.3)** | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a | n/a |
| **Rotation** | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a | n/a |
| **Injury News** | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a | n/a |
| **Scout** | 4 | 2 | 1 | 1 | $18.87 | +$3.88 | +0.39 | +27.5% | +0.2c | 33% |

Closing-price edge: the Kalshi price at the last hourly run before tip-off minus the price paid. Positive means the market moved toward the pick after it was made, the earliest sign of a real edge. Profit over one week is mostly luck.

## Forecast accuracy on every game

Each model's home-win probability on every game it looked at, picks and passes alike, against what happened. Brier score: lower is better, 0.25 is a coin flip. The difference column is the model minus Kalshi on the same games; below zero means the model beat the market. The range is a 95% bootstrap over games.

| Model | Games | Model | Kalshi when the model decided | Difference | 95% range | Kalshi at the close | Difference vs close |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current NBA bot (v2.3) | 19 | 0.3099 | n/a | n/a |  | 0.2991 | +0.0108 |
| Rotation | 25 | 0.2628 | 0.2874 | -0.0246 | -0.0497 to -0.0016 | 0.2906 | -0.0278 |
| Injury News | 1 | 0.4021 | 0.4096 | -0.0075 | -0.0075 to -0.0075 | 0.3782 | +0.0239 |
| Scout | 25 | 0.2803 | 0.2874 | -0.0070 | -0.0229 to +0.0085 | 0.2906 | -0.0102 |

The current bot only writes a forecast for the games it picks for a deep read, so its row covers fewer games.

## Current NBA bot (v2.3)

No picks yet.

## Rotation

No picks yet.

## Injury News

No picks yet.

## Scout

Expected to win 1.5 of 3 decided picks; won 2.

| Confidence | Picks | Won | Lost | Profit | Return |
| --- | --- | --- | --- | --- | --- |
| **HIGH** | 0 | 0 | 0 | +$0.00 | n/a |
| **MID** | 0 | 0 | 0 | +$0.00 | n/a |
| **LOW** | 4 | 2 | 1 | +$3.88 | +27.5% |

| Confidence | Matchup | Start (CT) | Pick | Price | Size | Model says | Market says | Result | Profit | Closing edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **LOW** | LA Clippers at San Antonio Spurs | Thu 7:00 PM | LA Clippers +15.5 | 51c | 0.47u | 57% | 50% | open |  |  |
| **LOW** | Washington Wizards at Toronto Raptors | Wed 6:30 PM | Washington Wizards +4.5 | 49c | 0.46u | 57% | 48% | won | +$4.43 | +2c |
| **LOW** | Portland Trail Blazers at Minnesota Timberwolves | Mon 7:00 PM | Minnesota Timberwolves -2.5 | 49c | 0.46u | 55% | 48% | won | +$4.43 | -0c |
| **LOW** | Philadelphia 76ers at Brooklyn Nets | Mon 6:30 PM | Brooklyn Nets to win | 34c | 0.50u | 40% | 34% | lost | -$4.98 | -2c |

Why each pick was made:

- **LOW: LA Clippers at San Antonio Spurs, LA Clippers +15.5.** San Antonio (net +11.2) are far better than the Clippers (net -5.7, 0-5 on the road), and on raw season numbers would be about 17-point favourites. Pulling the 15-game ratings partly toward average and taking off about 2.5 for Dylan Harper's absence leaves San Antonio by about 13, two to three points short of the 15.5 spread. What the price misses: Dylan Harper (31.7 minutes, 18.4 points, a starter in all 15 games) was ruled out for two to three weeks after Wednesday's game, yet San Antonio's price rose from 86c to 87.5c over the day, even after a home loss to Detroit.
- **LOW: Washington Wizards at Toronto Raptors, Washington Wizards +4.5.** Last-ten form says Toronto by about 5 at home at full strength; take off about 2 for the back-to-back, about 3 for Scottie Barnes (out) and about 1 for RJ Barrett's hamstring, leaving Toronto by about 2. The 4.5-point spread and 64c price still look closer to a Toronto with Barnes. What the price misses: Toronto are on the second night of a back-to-back (known yesterday) and Scottie Barnes has since been ruled out with RJ Barrett questionable, yet the price only fell from 68c to 64c, about half of what Barnes alone is worth.
- **LOW: Philadelphia 76ers at Brooklyn Nets, Brooklyn Nets to win.** Philadelphia are 11-3 but only +2.2 points per game, so the record flatters them; tonight they are on the second night of a back-to-back without LeBron James and with Embiid questionable on a sore foot. Brooklyn at home should be closer to 40% than 34%. What the price misses: The price looks anchored on Philadelphia's 11-3 record rather than their +2.2 point differential, and Embiid sitting the second night of a back-to-back is a real chance.
- **LOW: Portland Trail Blazers at Minnesota Timberwolves, Minnesota Timberwolves -2.5.** Minnesota have built a +11.5 point differential and the best defense here while Edwards played only 4 of 13 games. At home against Portland, who are without Morant and Sharpe, they should be about 4 to 5 point favourites, not 2.5. What the price misses: Edwards' surgery last week reads as fresh bad news, but Minnesota's numbers were made almost entirely without him, so the price discounts them twice.

## How the week will be judged

Set before the first pick. One week is about 50 games, enough to rule out a model that is badly wrong and not enough to prove one is right.

1. **Forecast accuracy against Kalshi** on every game the model looked at (table above). A model that cannot get below Kalshi's own Brier score on the same games has no edge to bet, however its picks went.
2. **Closing-price edge** on its picks. Positive on average means the market agreed with the pick after it was made.
3. **Profit and return** on its picks, read with the record against the number it expected to win.
4. **Calibration by confidence**: High picks should win more often than Mid, and Mid more than Low.

A model is worth keeping past the week if it is ahead of Kalshi on point 1 or point 2 and not far behind on the other. A model behind on both is retired, whatever its profit.

