# Kalshi sports paper-trading scorecard

Updated Mon Nov 16 6:12 PM CT. Paper trading only: no real orders are placed and no real money is at risk. Each bot starts with a $1,000 paper bankroll and 1 unit is $10.

Test started Fri Nov 13 11:19 PM CT. v2 rules started Sat Nov 14. Bot runs so far: 192 (each bot counts separately).

**v2 picks**

| Bot | Picks | Open | Won | Lost | Pulled | Open stake | Profit | Units | Return on settled stake | Closing-price edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NBA | 1 | 0 | 0 | 0 | 1 | $0.00 | -$0.78 | -0.08 | -11.2% | n/a |
| NFL | 0 | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a |
| College football | 7 | 0 | 4 | 3 | 0 | $0.00 | +$10.07 | +1.01 | +43.9% | -1.2c |
| **All three** | 8 | 0 | 4 | 3 | 1 | $0.00 | +$9.29 | +0.93 | +31.1% | -1.2c |

**v1 picks (earlier rules)**

| Bot | Picks | Open | Won | Lost | Pulled | Open stake | Profit | Units | Return on settled stake | Closing-price edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NBA | 1 | 0 | 1 | 0 | 0 | $0.00 | +$15.07 | +1.51 | +100.9% | -1.5c |
| NFL | 0 | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a |
| College football | 8 | 0 | 5 | 3 | 0 | $0.00 | +$39.75 | +3.98 | +40.1% | -0.7c |
| **All three** | 9 | 0 | 6 | 3 | 0 | $0.00 | +$54.82 | +5.48 | +48.0% | -0.8c |

**Confidence.** HIGH: the edge holds up even after the forecast is pulled most of the way to the market price; sized by Kelly, up to 2 units. MID: I have a specific written reason the price may be wrong and my own forecast beats the price by 10 or more points; half a unit. LOW: the same, with a 7 to 10 point gap; a quarter unit. A game with no specific reason against the market gets no pick. There is no daily limit on picks.

How to read this: profit over a handful of bets is mostly luck. The fairer tests are whether the AI forecast misses by less than the stats forecast and the market on the same games, and whether prices move toward the picks after they are made. The rules, and what would cause the AI to lose authority, are in the README.

## NBA

Too early to say: 1 settled picks and 11 graded games. The rules call for 60 graded AI-forecast games before any conclusion.

**v2 picks** (blind AI forecast, market check, code-chosen contract)

| Confidence | Picks | Open | Won | Lost | Open stake | Profit | Units | Return on settled stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **HIGH** | 1 | 0 | 0 | 0 | $0.00 | -$0.78 | -0.08 | -11.2% |
| **MID** | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a |
| **LOW** | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a |
| **ALL** | 1 | 0 | 0 | 0 | $0.00 | -$0.78 | -0.08 | -11.2% |

Pulled picks: 1, exit profit -$0.78 (not counted as closing-price edge).

| Confidence | Game | Start (CT) | Pick | Price | Size | AI says | Market says | Result | Profit | Closing edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **HIGH** | Dallas at Cleveland | Sat 6:30 PM | Cleveland +4.5 | 37c | 0.70u | 60% | 36% | pulled | -$0.78 |  |

Why each pick was made:

- **HIGH: Dallas at Cleveland, Cleveland +4.5.** My forecast: home team -1.0, total 229.0. Market: home team -10.0, total 226.8155. Even matchup. Cleveland is on a back-to-back and Mobley sat last night; Dallas is without Lively and lost by 39 on Thursday. Why the price may be wrong: within a few points of the market on both margin and total

**Forecast accuracy by game** (average miss in points, lower is better; each row uses the same games for every column)

| Games | Count | Margin: stats | Margin: AI | Margin: market | Total: stats | Total: AI | Total: market |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All tracked games | 14 | 11.0 | 10.1 | 11.8 | 14.0 | 12.0 | 16.5 |
| Games with an AI forecast | 11 | 10.1 | 10.1 | 11.0 | 11.2 | 12.0 | 13.4 |
|   of which random control games | 1 | 3.0 | 5.0 | 4.1 | 22.2 | 25.0 | 28.2 |

Games get an AI forecast because the stats and the market disagreed, so that group is not a random sample. The control row is.

**Probability accuracy on all tracked contracts**: 107 contracts from 14 games (Brier score, lower is better, 0.25 is a coin flip). Several contracts come from the same game, so treat the game count as the sample size.

| Forecast | Brier score | Contracts |
| --- | --- | --- |
| Kalshi closing price | 0.2469 | 107 |
| Sportsbook line | 0.2452 | 107 |
| Stats forecast alone | 0.2132 | 107 |
| Blind AI forecast | 0.2196 | 85 |
| Bet probability (AI after market check) | 0.2306 | 61 |

**Probability accuracy on contracts in games with an AI forecast**: 85 contracts from 11 games (Brier score, lower is better, 0.25 is a coin flip). Several contracts come from the same game, so treat the game count as the sample size.

| Forecast | Brier score | Contracts |
| --- | --- | --- |
| Kalshi closing price | 0.2502 | 85 |
| Sportsbook line | 0.2474 | 85 |
| Stats forecast alone | 0.2157 | 85 |
| Blind AI forecast | 0.2196 | 85 |
| Bet probability (AI after market check) | 0.2306 | 61 |

**v1 picks** (earlier rules, kept for the record and not part of the v2 result). The first college picks on Nov 13 were placed minutes before two rule fixes, which is why some games hold two positions and one pick is under the old 6 point minimum.

| Picks | Open | Won | Lost | Pulled | Open stake | Settled stake | Profit | Units | Return on settled stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 1 | 0 | 0 | $0.00 | $14.93 | +$15.07 | +1.51 | +100.9% |

| Confidence | Game | Start (CT) | Pick | Price | Size | AI says | Market says | Result | Profit | Closing edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **MID** | Detroit at Miami | Sat 7:00 PM | Over 229.5 | 48c | 1.49u | 56% | 48% | won | +$15.07 | -2c |

## NFL

Too early to say: 0 settled picks and 12 graded games. The rules call for 60 graded AI-forecast games before any conclusion.

**v2 picks** (blind AI forecast, market check, code-chosen contract)

No picks yet.


**Forecast accuracy by game** (average miss in points, lower is better; each row uses the same games for every column)

| Games | Count | Margin: stats | Margin: AI | Margin: market | Total: stats | Total: AI | Total: market |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All tracked games | 12 | 11.8 | 11.9 | 10.3 | 10.3 | 10.0 | 9.1 |
| Games with an AI forecast | 12 | 11.8 | 11.9 | 10.3 | 10.3 | 10.0 | 9.1 |
|   of which random control games | 2 | 13.4 | 12.2 | 9.8 | 10.0 | 6.5 | 6.7 |

Games get an AI forecast because the stats and the market disagreed, so that group is not a random sample. The control row is.

**Probability accuracy on all tracked contracts**: 85 contracts from 12 games (Brier score, lower is better, 0.25 is a coin flip). Several contracts come from the same game, so treat the game count as the sample size.

| Forecast | Brier score | Contracts |
| --- | --- | --- |
| Kalshi closing price | 0.2319 | 85 |
| Sportsbook line | 0.2332 | 85 |
| Stats forecast alone | 0.2560 | 85 |
| Blind AI forecast | 0.2586 | 85 |
| Bet probability (AI after market check) | 0.2363 | 74 |

**Probability accuracy on contracts in games with an AI forecast**: 85 contracts from 12 games (Brier score, lower is better, 0.25 is a coin flip). Several contracts come from the same game, so treat the game count as the sample size.

| Forecast | Brier score | Contracts |
| --- | --- | --- |
| Kalshi closing price | 0.2319 | 85 |
| Sportsbook line | 0.2332 | 85 |
| Stats forecast alone | 0.2560 | 85 |
| Blind AI forecast | 0.2586 | 85 |
| Bet probability (AI after market check) | 0.2363 | 74 |

## College football

Too early to say: 7 settled picks and 40 graded games. The rules call for 60 graded AI-forecast games before any conclusion.

**v2 picks** (blind AI forecast, market check, code-chosen contract)

| Confidence | Picks | Open | Won | Lost | Open stake | Profit | Units | Return on settled stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **HIGH** | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a |
| **MID** | 3 | 0 | 2 | 1 | $0.00 | +$6.71 | +0.67 | +47.0% |
| **LOW** | 4 | 0 | 2 | 2 | $0.00 | +$3.36 | +0.34 | +38.9% |
| **ALL** | 7 | 0 | 4 | 3 | $0.00 | +$10.07 | +1.01 | +43.9% |

16 earlier picks were withdrawn before kickoff when the pick rules were tightened on Nov 14. They are in the ledger but not counted here.

Of 7 decided picks the bot expected to win 3.0 and won 4.
Closing-price edge on picks held to the start: -1.2 cents per contract on average across 7 picks, and 14% beat the last recorded price. The last price is from the final hourly run before the start, not the exact close.

| Confidence | Game | Start (CT) | Pick | Price | Size | AI says | Market says | Result | Profit | Closing edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **MID** | San José State at Air Force | Sat 6:00 PM | Under 46.5 | 43c | 0.49u | 58% | 42% | won | +$6.08 | -4c |
| **LOW** | Stanford at Virginia Tech | Sat 6:30 PM | Stanford +16.5 | 50c | 0.21u | 61% | 50% | won | +$1.93 | -4c |
| **LOW** | Minnesota at Penn State | Sat 6:00 PM | Minnesota to win | 20c | 0.23u | 30% | 20% | lost | -$2.33 | -0c |
| **MID** | USC at Indiana | Sat 2:30 PM | Under 50.5 | 46c | 0.48u | 60% | 46% | won | +$5.22 | -0c |
| **MID** | Bucknell at William & Mary | Sat 12:00 PM | Under 41.5 | 40c | 0.46u | 53% | 39% | lost | -$4.59 | -0c |
| **LOW** | Lindenwood at UT Martin | Sat 2:00 PM | Lindenwood +2.5 | 61c | 0.19u | 72% | 60% | lost | -$1.88 | -0c |
| **LOW** | Abilene Christian at Austin Peay | Sat 1:00 PM | Abilene Christian to win | 28c | 0.24u | 39% | 28% | won | +$5.64 | +0c |

Why each pick was made:

- **MID: San José State at Air Force, Under 46.5.** My forecast: home team +8.5, total 43.0. Market: home team +15.4, total 48.7168. Air Force is better and at home at altitude, but it wins close. San Jose State's offense is weak on the ground and on third down, so points should be scarce. Why the price may be wrong: Market has Air Force by 14 to 15. Air Force's option offense shortens games and five of its six listed wins were by 10 or fewer. Against three common opponents (Nevada, Wyoming, NIU) Air Force was only about 6 points better than San Jose State before home field. Risk I cannot rule out: a San Jose State quarterback absence.
- **MID: USC at Indiana, Under 50.5.** My forecast: home team +7.0, total 46.0. Market: home team +11.2, total 51.7168. Indiana's defense allows 12 a game. Both teams off a bye. Why the price may be wrong: On the total: market has 51.5. Indiana's nine games averaged about 42 combined points and it allows 12 a game; only two of its games went over 52. USC's offense is good, but it scored 7 at Wisconsin, the closest defense to Indiana's it has faced.
- **MID: Bucknell at William & Mary, Under 41.5.** My forecast: home team +5.0, total 40.0. Market: home team +7.6, total 44.8494. Two of the worst teams in FCS. Low scoring. Why the price may be wrong: On the total: market has 45.5, but these offenses average 11.8 and 18.3 points, about 30 combined, and Bucknell has scored 14 or fewer in eight of ten. The market looks anchored to a generic FCS total.
- **LOW: Stanford at Virginia Tech, Stanford +16.5.** My forecast: home team +12.0, total 56.0. Market: home team +18.2, total 58.1506. Stanford has been routed every time it left home and now travels across the country. Virginia Tech is average but at home at night. Why the price may be wrong: Market has Virginia Tech by 16.5 to 18. I already charged Stanford for its road blowouts, but those came against teams rated 17 to 25 points above average. Virginia Tech is rated 6, lost at Cal (rated like Stanford) and by 23 at SMU. Stanford is also off a bye. The market may be pricing Stanford's worst games against a team that is not that class. Risk I cannot rule out: a Stanford quarterback or injury problem.
- **LOW: Abilene Christian at Austin Peay, Abilene Christian to win.** My forecast: home team +4.5, total 53.0. Market: home team +9.2, total 55.5848. Austin Peay at home and efficient, but less proven. Why the price may be wrong: Market has Austin Peay by 7.5 to 9. Common opponent West Florida: Abilene Christian won 35-7 at home, Austin Peay won 38-16 on the road. Austin Peay's schedule is rated about 9 points weaker. The market may be paying for the 8-2 record.
- **LOW: Lindenwood at UT Martin, Lindenwood +2.5.** My forecast: home team -6.5, total 46.0. Market: home team -2.2, total 50.3677. Lindenwood is the better team lately. Why the price may be wrong: Market has Lindenwood by only 1.5 to 2. Common opponents: Eastern Illinois (Lindenwood won 20-13 there, UT Martin lost 45-16 at home), Tennessee State (Lindenwood 27-0, UT Martin 42-28) and Gardner-Webb (Lindenwood won by 13 on the road, UT Martin by 11 at home). Lindenwood has won four straight. The market may be weighting its early losses.
- **LOW: Minnesota at Penn State, Minnesota to win.** My forecast: home team +8.5, total 45.5. Market: home team +13.3, total 42.2832. Minnesota's offense is one of the least efficient here (6.1 yards per pass, 31 percent on third down) and it lost by 28 at Purdue, a team Penn State beat by 14. Low-scoring game expected. Why the price may be wrong: Market has Penn State by 12.5 with a total of only 42.5, which is a lot of points in a low-scoring game for a 5-4 team whose best recent results are a 14 point home win over Purdue and a 3 point win at Washington, where Minnesota also won. Risk I cannot rule out: a Minnesota injury, and Minnesota's 28 point loss at Purdue.

**Forecast accuracy by game** (average miss in points, lower is better; each row uses the same games for every column)

| Games | Count | Margin: stats | Margin: AI | Margin: market | Total: stats | Total: AI | Total: market |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All tracked games | 115 | 12.3 | 14.4 | 12.3 | 12.5 | 13.0 | 12.6 |
| Games with an AI forecast | 40 | 14.1 | 14.4 | 13.0 | 13.6 | 13.0 | 13.7 |
|   of which random control games | 9 | 16.2 | 16.6 | 15.3 | 12.9 | 12.7 | 12.9 |

Games get an AI forecast because the stats and the market disagreed, so that group is not a random sample. The control row is.

**Probability accuracy on all tracked contracts**: 581 contracts from 116 games (Brier score, lower is better, 0.25 is a coin flip). Several contracts come from the same game, so treat the game count as the sample size.

| Forecast | Brier score | Contracts |
| --- | --- | --- |
| Kalshi closing price | 0.2417 | 581 |
| Sportsbook line | 0.2418 | 581 |
| Stats forecast alone | 0.2411 | 581 |
| Blind AI forecast | 0.2348 | 211 |
| Bet probability (AI after market check) | 0.2274 | 193 |

**Probability accuracy on contracts in games with an AI forecast**: 211 contracts from 40 games (Brier score, lower is better, 0.25 is a coin flip). Several contracts come from the same game, so treat the game count as the sample size.

| Forecast | Brier score | Contracts |
| --- | --- | --- |
| Kalshi closing price | 0.2262 | 211 |
| Sportsbook line | 0.2288 | 211 |
| Stats forecast alone | 0.2377 | 211 |
| Blind AI forecast | 0.2348 | 211 |
| Bet probability (AI after market check) | 0.2274 | 193 |

**v1 picks** (earlier rules, kept for the record and not part of the v2 result). The first college picks on Nov 13 were placed minutes before two rule fixes, which is why some games hold two positions and one pick is under the old 6 point minimum.

| Picks | Open | Won | Lost | Pulled | Open stake | Settled stake | Profit | Units | Return on settled stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 0 | 5 | 3 | 0 | $0.00 | $99.25 | +$39.75 | +3.98 | +40.1% |

| Confidence | Game | Start (CT) | Pick | Price | Size | AI says | Market says | Result | Profit | Closing edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **MID** | Arizona State at UCF | Sat 4:30 PM | UCF -7.5 | 37c | 1.43u | 46% | 36% | lost | -$14.30 | -1c |
| **MID** | Tennessee at Texas A&M | Sat 2:00 PM | Tennessee -3.5 | 39c | 1.46u | 51% | 38% | won | +$21.36 | -0c |
| **MID** | Tarleton State at West Florida | Sat 2:00 PM | West Florida +18.5 | 54c | 0.78u | 66% | 53% | won | +$6.19 | -0c |
| **MID** | Wake Forest at SMU | Sat 11:00 AM | Wake Forest to win | 49c | 1.42u | 59% | 48% | won | +$13.79 | -4c |
| **MID** | Wake Forest at SMU | Sat 11:00 AM | Wake Forest -4.5 | 36c | 1.35u | 48% | 35% | won | +$22.45 | -4c |
| **LOW** | Eastern Washington at Utah Tech | Sat 3:00 PM | Utah Tech to win | 35c | 1.83u | 41% | 34% | lost | -$18.30 | +4c |
| **LOW** | Tennessee at Texas A&M | Sat 2:00 PM | Under 40.5 | 38c | 0.99u | 47% | 38% | won | +$15.08 | +2c |
| **LOW** | Tarleton State at West Florida | Sat 2:00 PM | West Florida to win | 15c | 0.65u | 22% | 14% | lost | -$6.52 | -2c |

