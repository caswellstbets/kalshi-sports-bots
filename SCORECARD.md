# Kalshi sports paper-trading scorecard

Updated Sat Nov 14 11:45 AM ET. Paper trading only: no real orders are placed and no real money is at risk. Each bot starts with a $1,000 paper bankroll and 1 unit is $10.

Test started Sat Nov 14 12:19 AM ET. v2 rules started Sat Nov 14. Bot runs so far: 35 (each bot counts separately).

**v2 picks**

| Bot | Picks | Open | Won | Lost | Pulled | Open stake | Profit | Units | Return on settled stake | Closing-price edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NBA | 0 | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a |
| NFL | 0 | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a |
| College football | 16 | 16 | 0 | 0 | 0 | $78.25 | +$0.00 | +0.00 | n/a | n/a |
| **All three** | 16 | 16 | 0 | 0 | 0 | $78.25 | +$0.00 | +0.00 | n/a | n/a |

**v1 picks (earlier rules)**

| Bot | Picks | Open | Won | Lost | Pulled | Open stake | Profit | Units | Return on settled stake | Closing-price edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NBA | 1 | 1 | 0 | 0 | 0 | $14.93 | +$0.00 | +0.00 | n/a | n/a |
| NFL | 0 | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a | n/a |
| College football | 8 | 8 | 0 | 0 | 0 | $99.25 | +$0.00 | +0.00 | n/a | n/a |
| **All three** | 9 | 9 | 0 | 0 | 0 | $114.18 | +$0.00 | +0.00 | n/a | n/a |

How to read this: profit over a handful of bets is mostly luck. The fairer tests are whether the AI forecast misses by less than the stats forecast and the market on the same games, and whether prices move toward the picks after they are made. The rules, and what would cause the AI to lose authority, are in the README.

## NBA

Too early to say: 0 settled picks and 0 graded games. The rules call for 60 graded AI-forecast games before any conclusion.

**v2 picks** (blind AI forecast, market check, code-chosen contract)

*Bets* clear a 3 point edge after the market check and are sized by Kelly. *Samples* are 0.5 unit picks on games where the AI's own forecast beats the price by 5+ points but the market-checked edge is too thin to bet; they exist to grade the AI's read.


Forecast accuracy by game: no finished games graded yet (5 games being tracked, 0 with an AI forecast).

**v1 picks** (earlier rules, kept for the record and not part of the v2 result). The first college picks on Nov 13 were placed minutes before two rule fixes, which is why some games hold two positions and one pick is under the old 6 point minimum.

| Picks | Open | Won | Lost | Pulled | Open stake | Settled stake | Profit | Units | Return on settled stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0 | 0 | 0 | $14.93 | $0.00 | +$0.00 | +0.00 | n/a |

| Placed | Kind | Game | Pick | Price | Size | Bet on | AI | Market | Edge | Result | Profit | Closing edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sat Nov 14 11:08 AM ET | v1 | DET @ MIA | Over 229.5 | 48c | 30 (1.49u) | 55.8% | n/a | 47.5% | +6.1 | open |  |  |

## NFL

Too early to say: 0 settled picks and 0 graded games. The rules call for 60 graded AI-forecast games before any conclusion.

**v2 picks** (blind AI forecast, market check, code-chosen contract)

*Bets* clear a 3 point edge after the market check and are sized by Kelly. *Samples* are 0.5 unit picks on games where the AI's own forecast beats the price by 5+ points but the market-checked edge is too thin to bet; they exist to grade the AI's read.


Forecast accuracy by game: no finished games graded yet (1 games being tracked, 0 with an AI forecast).

## College football

Too early to say: 0 settled picks and 0 graded games. The rules call for 60 graded AI-forecast games before any conclusion.

**v2 picks** (blind AI forecast, market check, code-chosen contract)

*Bets* clear a 3 point edge after the market check and are sized by Kelly. *Samples* are 0.5 unit picks on games where the AI's own forecast beats the price by 5+ points but the market-checked edge is too thin to bet; they exist to grade the AI's read.

Bets:

| Picks | Open | Won | Lost | Pulled | Open stake | Settled stake | Profit | Units | Return on settled stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0 | 0 | 0 | $7.47 | $0.00 | +$0.00 | +0.00 | n/a |

Samples:

| Picks | Open | Won | Lost | Pulled | Open stake | Settled stake | Profit | Units | Return on settled stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 15 | 15 | 0 | 0 | 0 | $70.78 | $0.00 | +$0.00 | +0.00 | n/a |


| Placed | Kind | Game | Pick | Price | Size | Bet on | AI | Market | Edge | Result | Profit | Closing edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sat Nov 14 11:44 AM ET | sample | CIT @ VMI | VMI +20.5 | 58c | 8 (0.48u) | 58.6% | 66.0% | 57.5% | -1.2 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | NEB @ RUTG | RUTG +13.5 | 43c | 11 (0.49u) | 44.2% | 56.3% | 42.5% | -0.5 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | ALA @ VAN | Over 52.5 | 37c | 12 (0.46u) | 37.5% | 51.1% | 36.5% | -1.1 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | BUCK @ W&M | Under 41.5 | 40c | 11 (0.46u) | 41.1% | 53.4% | 39.0% | -0.6 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | NCAT @ HAMP | Under 42.5 | 40c | 11 (0.46u) | 41.2% | 51.1% | 39.5% | -0.5 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | DART @ COR | COR to win | 48c | 10 (0.50u) | 49.4% | 55.0% | 47.5% | -0.4 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | HARV @ PENN | PENN to win | 17c | 27 (0.49u) | 17.3% | 23.3% | 16.5% | -0.7 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | HCU @ NWST | Under 46.5 | 39c | 12 (0.49u) | 39.4% | 51.1% | 38.5% | -1.2 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | ACU @ APSU | ACU to win | 28c | 16 (0.47u) | 30.1% | 38.8% | 27.5% | +0.7 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | DRKE @ STMN | DRKE +14.5 | 45c | 10 (0.47u) | 46.8% | 53.8% | 44.5% | +0.0 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | SDST @ SIU | SIU +19.5 | 56c | 8 (0.46u) | 56.9% | 66.0% | 55.5% | -0.9 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | TXSO @ AAMU | Under 58.5 | 44c | 10 (0.46u) | 45.0% | 53.4% | 43.5% | -0.8 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | LIN @ UTM | LIN +2.5 | 61c | 7 (0.44u) | 63.4% | 71.5% | 60.5% | +0.7 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | PV @ UAPB | UAPB to win | 46c | 10 (0.48u) | 47.2% | 58.8% | 45.5% | -0.6 | open |  |  |
| Sat Nov 14 11:44 AM ET | sample | USC @ IU | Under 50.5 | 46c | 10 (0.48u) | 47.7% | 60.3% | 45.5% | -0.1 | open |  |  |
| Sat Nov 14 11:30 AM ET | bet | SJSU @ AFA | SJSU +13.5 | 48c | 15 (0.75u) | 52.8% | 62.4% | 47.5% | +3.0 | open |  |  |

Why each pick was made:

- **CIT @ VMI, VMI +20.5:** AI forecast home margin -14.0, market -18.9657, stats -10.6422. VMI is 0-10 and scores under 9 a game. The Citadel is bad but clearly better. Rivalry game at VMI keeps it from being a rout. Combined scoring of these two offenses points well under the stats total. Market check (shrink): Market has The Citadel by 17.5 to 19. My own common-opponent work pointed to about 20 and I trimmed it for the rivalry, which is soft. The total matches the market.
- **NEB @ RUTG, RUTG +13.5:** AI forecast home margin -11.0, market -16.7183, stats -12.6282. Nebraska is clearly better but its offense has stalled. Rutgers gives up 32 a game. Market check (shrink): Market has Nebraska by 16.5. Nebraska's recent scoring slump is public, so I have nothing the market lacks.
- **ALA @ VAN, Over 52.5:** AI forecast home margin -19.0, market -16.7183, stats -20.1644. Alabama has handled every team near Vanderbilt's level by multiple scores, including Kentucky, who beat Vanderbilt by 17. Vanderbilt's offense is inefficient on the ground. Market check (shrink): Market has Vanderbilt closer and the total 5.5 lower than mine. I have no information the market lacks; my total came mostly from the ratings.
- **BUCK @ W&M, Under 41.5:** AI forecast home margin 5.0, market 7.6113, stats 4.334. Two of the worst teams in FCS. Low scoring. Market check (stands): On the total: market has 45.5, but these offenses average 11.8 and 18.3 points, about 30 combined, and Bucknell has scored 14 or fewer in eight of ten. The market looks anchored to a generic FCS total.
- **NCAT @ HAMP, Under 42.5:** AI forecast home margin -12.5, market -13.582, stats -12.4591. Hampton is 1-9 and scores 15 a game. North Carolina A&T has won 4 of 6. Market check (stands): within a few points of the market on both margin and total
- **DART @ COR, COR to win:** AI forecast home margin 2.0, market -0.9908, stats 3.7283. Even Ivy game. Dartmouth's defense allows 21 a game. Market check (stands): within a few points of the market on both margin and total
- **HARV @ PENN, PENN to win:** AI forecast home margin -11.5, market -15.391, stats -12.2965. Harvard is 7-1 with the best defense in the league. Market check (shrink): Market has Harvard by 13.5 to 15. No specific reason the market is wrong.
- **HCU @ NWST, Under 46.5:** AI forecast home margin -12.0, market -18.1755, stats -14.565. Northwestern State is 0-10 and allows 48 a game, but Houston Christian's offense is weak. Market check (shrink): Market has Houston Christian by 16.5 to 18. The 88-0 distortion is visible to anyone, so I cannot claim the market missed it.
- **ACU @ APSU, ACU to win:** AI forecast home margin 4.5, market 9.2089, stats 5.9062. Austin Peay at home and efficient, but less proven. Market check (stands): Market has Austin Peay by 7.5 to 9. Common opponent West Florida: Abilene Christian won 35-7 at home, Austin Peay won 38-16 on the road. Austin Peay's schedule is rated about 9 points weaker. The market may be paying for the 8-2 record.
- **DRKE @ STMN, DRKE +14.5:** AI forecast home margin 13.0, market 15.391, stats 12.0164. Two teams with very weak schedules. St. Thomas is better. Market check (stands): within a few points of the market on both margin and total

Forecast accuracy by game: no finished games graded yet (115 games being tracked, 40 with an AI forecast).

**v1 picks** (earlier rules, kept for the record and not part of the v2 result). The first college picks on Nov 13 were placed minutes before two rule fixes, which is why some games hold two positions and one pick is under the old 6 point minimum.

| Picks | Open | Won | Lost | Pulled | Open stake | Settled stake | Profit | Units | Return on settled stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 8 | 0 | 0 | 0 | $99.25 | $0.00 | +$0.00 | +0.00 | n/a |

| Placed | Kind | Game | Pick | Price | Size | Bet on | AI | Market | Edge | Result | Profit | Closing edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sat Nov 14 12:31 AM ET | v1 | WAKE @ SMU | WAKE to win | 49c | 28 (1.42u) | 59.0% | n/a | 48.5% | +8.2 | open |  |  |
| Sat Nov 14 12:31 AM ET | v1 | WAKE @ SMU | WAKE -4.5 | 36c | 36 (1.35u) | 47.5% | n/a | 35.0% | +9.9 | open |  |  |
| Sat Nov 14 12:31 AM ET | v1 | TENN @ TA&M | TENN -3.5 | 39c | 36 (1.46u) | 50.8% | n/a | 38.5% | +10.1 | open |  |  |
| Sat Nov 14 12:31 AM ET | v1 | TENN @ TA&M | Under 40.5 | 38c | 25 (0.99u) | 46.6% | n/a | 37.5% | +7.0 | open |  |  |
| Sat Nov 14 12:31 AM ET | v1 | TAR @ UWF | UWF to win | 15c | 41 (0.65u) | 22.2% | n/a | 14.5% | +6.3 | open |  |  |
| Sat Nov 14 12:31 AM ET | v1 | TAR @ UWF | UWF +18.5 | 54c | 14 (0.78u) | 65.5% | n/a | 53.0% | +9.8 | open |  |  |
| Sat Nov 14 12:31 AM ET | v1 | ASU @ UCF | UCF -7.5 | 37c | 37 (1.43u) | 45.8% | n/a | 36.0% | +7.2 | open |  |  |
| Sat Nov 14 12:20 AM ET | v1 | EWU @ UTU | UTU to win | 35c | 50 (1.83u) | 41.3% | n/a | 34.0% | +4.7 | open |  |  |

