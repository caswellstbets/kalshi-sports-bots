# Kalshi sports paper-trading scorecard

Updated Sat Nov 14 2:08 PM ET. Paper trading only: no real orders are placed and no real money is at risk. Each bot starts with a $1,000 paper bankroll and 1 unit is $10.

Test started Sat Nov 14 12:19 AM ET. v2 rules started Sat Nov 14. Bot runs so far: 55 (each bot counts separately).

**v2 picks**

| Bot | Picks | Open | Won | Lost | Pulled | Open stake | Profit | Units | Return on settled stake | Closing-price edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NBA | 0 | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a |
| NFL | 0 | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a |
| College football | 7 | 7 | 0 | 0 | 0 | $22.93 | +$0.00 | +0.00 | n/a | n/a |
| **All three** | 7 | 7 | 0 | 0 | 0 | $22.93 | +$0.00 | +0.00 | n/a | n/a |

**v1 picks (earlier rules)**

| Bot | Picks | Open | Won | Lost | Pulled | Open stake | Profit | Units | Return on settled stake | Closing-price edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NBA | 1 | 1 | 0 | 0 | 0 | $14.93 | +$0.00 | +0.00 | n/a | n/a |
| NFL | 0 | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a |
| College football | 8 | 8 | 0 | 0 | 0 | $99.25 | +$0.00 | +0.00 | n/a | n/a |
| **All three** | 9 | 9 | 0 | 0 | 0 | $114.18 | +$0.00 | +0.00 | n/a | n/a |

**Confidence.** HIGH: the edge holds up even after the forecast is pulled most of the way to the market price; sized by Kelly, up to 2 units. MID: I have a specific written reason the price may be wrong and my own forecast beats the price by 10 or more points; half a unit. LOW: the same, with a 7 to 10 point gap; a quarter unit. A game with no specific reason against the market gets no pick. There is no daily limit on picks.

How to read this: profit over a handful of bets is mostly luck. The fairer tests are whether the AI forecast misses by less than the stats forecast and the market on the same games, and whether prices move toward the picks after they are made. The rules, and what would cause the AI to lose authority, are in the README.

## NBA

Too early to say: 0 settled picks and 0 graded games. The rules call for 60 graded AI-forecast games before any conclusion.

**v2 picks** (blind AI forecast, market check, code-chosen contract)

No picks yet.


Forecast accuracy by game: no finished games graded yet (5 games being tracked, 4 with an AI forecast).

**v1 picks** (earlier rules, kept for the record and not part of the v2 result). The first college picks on Nov 13 were placed minutes before two rule fixes, which is why some games hold two positions and one pick is under the old 6 point minimum.

| Picks | Open | Won | Lost | Pulled | Open stake | Settled stake | Profit | Units | Return on settled stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0 | 0 | 0 | $14.93 | $0.00 | +$0.00 | +0.00 | n/a |

| Confidence | Game | Pick | Price | Size | AI says | Market says | Result | Profit | Closing edge | Placed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **MID** | Detroit at Miami | Over 229.5 | 48c | 1.49u | 56% | 48% | open |  |  | Sat Nov 14 11:08 AM ET |

## NFL

Too early to say: 0 settled picks and 0 graded games. The rules call for 60 graded AI-forecast games before any conclusion.

**v2 picks** (blind AI forecast, market check, code-chosen contract)

No picks yet.


Forecast accuracy by game: no finished games graded yet (8 games being tracked, 8 with an AI forecast).

## College football

Too early to say: 0 settled picks and 0 graded games. The rules call for 60 graded AI-forecast games before any conclusion.

**v2 picks** (blind AI forecast, market check, code-chosen contract)

| Confidence | Picks | Open | Won | Lost | Open stake | Profit | Units | Return on settled stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **HIGH** | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a |
| **MID** | 3 | 3 | 0 | 0 | $14.29 | +$0.00 | +0.00 | n/a |
| **LOW** | 4 | 4 | 0 | 0 | $8.64 | +$0.00 | +0.00 | n/a |
| **ALL** | 7 | 7 | 0 | 0 | $22.93 | +$0.00 | +0.00 | n/a |

16 earlier picks were withdrawn before kickoff when the pick rules were tightened on Nov 14. They are in the ledger but not counted here.


| Confidence | Game | Pick | Price | Size | AI says | Market says | Result | Profit | Closing edge | Placed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **MID** | San José State at Air Force | Under 46.5 | 43c | 0.49u | 58% | 42% | open |  |  | Sat Nov 14 11:50 AM ET |
| **MID** | USC at Indiana | Under 50.5 | 46c | 0.48u | 60% | 46% | open |  |  | Sat Nov 14 11:50 AM ET |
| **MID** | Bucknell at William & Mary | Under 41.5 | 40c | 0.46u | 53% | 39% | open |  |  | Sat Nov 14 11:50 AM ET |
| **LOW** | Stanford at Virginia Tech | Stanford +16.5 | 50c | 0.21u | 61% | 50% | open |  |  | Sat Nov 14 11:50 AM ET |
| **LOW** | Abilene Christian at Austin Peay | Abilene Christian to win | 28c | 0.24u | 39% | 28% | open |  |  | Sat Nov 14 11:50 AM ET |
| **LOW** | Lindenwood at UT Martin | Lindenwood +2.5 | 61c | 0.19u | 72% | 60% | open |  |  | Sat Nov 14 11:50 AM ET |
| **LOW** | Minnesota at Penn State | Minnesota to win | 20c | 0.23u | 30% | 20% | open |  |  | Sat Nov 14 11:50 AM ET |

Why each pick was made:

- **MID: San José State at Air Force, Under 46.5.** My forecast: home team +8.5, total 43.0. Market: home team +15.4, total 48.7168. Air Force is better and at home at altitude, but it wins close. San Jose State's offense is weak on the ground and on third down, so points should be scarce. Why the price may be wrong: Market has Air Force by 14 to 15. Air Force's option offense shortens games and five of its six listed wins were by 10 or fewer. Against three common opponents (Nevada, Wyoming, NIU) Air Force was only about 6 points better than San Jose State before home field. Risk I cannot rule out: a San Jose State quarterback absence.
- **MID: USC at Indiana, Under 50.5.** My forecast: home team +7.0, total 46.0. Market: home team +11.2, total 51.7168. Indiana's defense allows 12 a game. Both teams off a bye. Why the price may be wrong: On the total: market has 51.5. Indiana's nine games averaged about 42 combined points and it allows 12 a game; only two of its games went over 52. USC's offense is good, but it scored 7 at Wisconsin, the closest defense to Indiana's it has faced.
- **MID: Bucknell at William & Mary, Under 41.5.** My forecast: home team +5.0, total 40.0. Market: home team +7.6, total 44.8494. Two of the worst teams in FCS. Low scoring. Why the price may be wrong: On the total: market has 45.5, but these offenses average 11.8 and 18.3 points, about 30 combined, and Bucknell has scored 14 or fewer in eight of ten. The market looks anchored to a generic FCS total.
- **LOW: Stanford at Virginia Tech, Stanford +16.5.** My forecast: home team +12.0, total 56.0. Market: home team +18.2, total 58.1506. Stanford has been routed every time it left home and now travels across the country. Virginia Tech is average but at home at night. Why the price may be wrong: Market has Virginia Tech by 16.5 to 18. I already charged Stanford for its road blowouts, but those came against teams rated 17 to 25 points above average. Virginia Tech is rated 6, lost at Cal (rated like Stanford) and by 23 at SMU. Stanford is also off a bye. The market may be pricing Stanford's worst games against a team that is not that class. Risk I cannot rule out: a Stanford quarterback or injury problem.
- **LOW: Abilene Christian at Austin Peay, Abilene Christian to win.** My forecast: home team +4.5, total 53.0. Market: home team +9.2, total 55.5848. Austin Peay at home and efficient, but less proven. Why the price may be wrong: Market has Austin Peay by 7.5 to 9. Common opponent West Florida: Abilene Christian won 35-7 at home, Austin Peay won 38-16 on the road. Austin Peay's schedule is rated about 9 points weaker. The market may be paying for the 8-2 record.
- **LOW: Lindenwood at UT Martin, Lindenwood +2.5.** My forecast: home team -6.5, total 46.0. Market: home team -2.2, total 50.3677. Lindenwood is the better team lately. Why the price may be wrong: Market has Lindenwood by only 1.5 to 2. Common opponents: Eastern Illinois (Lindenwood won 20-13 there, UT Martin lost 45-16 at home), Tennessee State (Lindenwood 27-0, UT Martin 42-28) and Gardner-Webb (Lindenwood won by 13 on the road, UT Martin by 11 at home). Lindenwood has won four straight. The market may be weighting its early losses.
- **LOW: Minnesota at Penn State, Minnesota to win.** My forecast: home team +8.5, total 45.5. Market: home team +13.3, total 42.2832. Minnesota's offense is one of the least efficient here (6.1 yards per pass, 31 percent on third down) and it lost by 28 at Purdue, a team Penn State beat by 14. Low-scoring game expected. Why the price may be wrong: Market has Penn State by 12.5 with a total of only 42.5, which is a lot of points in a low-scoring game for a 5-4 team whose best recent results are a 14 point home win over Purdue and a 3 point win at Washington, where Minnesota also won. Risk I cannot rule out: a Minnesota injury, and Minnesota's 28 point loss at Purdue.

Forecast accuracy by game: no finished games graded yet (115 games being tracked, 40 with an AI forecast).

**v1 picks** (earlier rules, kept for the record and not part of the v2 result). The first college picks on Nov 13 were placed minutes before two rule fixes, which is why some games hold two positions and one pick is under the old 6 point minimum.

| Picks | Open | Won | Lost | Pulled | Open stake | Settled stake | Profit | Units | Return on settled stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 8 | 0 | 0 | 0 | $99.25 | $0.00 | +$0.00 | +0.00 | n/a |

| Confidence | Game | Pick | Price | Size | AI says | Market says | Result | Profit | Closing edge | Placed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **MID** | Wake Forest at SMU | Wake Forest to win | 49c | 1.42u | 59% | 48% | open |  |  | Sat Nov 14 12:31 AM ET |
| **MID** | Wake Forest at SMU | Wake Forest -4.5 | 36c | 1.35u | 48% | 35% | open |  |  | Sat Nov 14 12:31 AM ET |
| **MID** | Tennessee at Texas A&M | Tennessee -3.5 | 39c | 1.46u | 51% | 38% | open |  |  | Sat Nov 14 12:31 AM ET |
| **MID** | Tarleton State at West Florida | West Florida +18.5 | 54c | 0.78u | 66% | 53% | open |  |  | Sat Nov 14 12:31 AM ET |
| **MID** | Arizona State at UCF | UCF -7.5 | 37c | 1.43u | 46% | 36% | open |  |  | Sat Nov 14 12:31 AM ET |
| **LOW** | Tennessee at Texas A&M | Under 40.5 | 38c | 0.99u | 47% | 38% | open |  |  | Sat Nov 14 12:31 AM ET |
| **LOW** | Tarleton State at West Florida | West Florida to win | 15c | 0.65u | 22% | 14% | open |  |  | Sat Nov 14 12:31 AM ET |
| **LOW** | Eastern Washington at Utah Tech | Utah Tech to win | 35c | 1.83u | 41% | 34% | open |  |  | Sat Nov 14 12:20 AM ET |

