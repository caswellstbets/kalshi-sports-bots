# Kalshi sports paper-trading scorecard

Updated Sat Nov 14 11:30 AM ET. Paper trading only: no real orders are placed and no real money is at risk. Each bot starts with a $1,000 paper bankroll and 1 unit is $10.

Test started Sat Nov 14 12:19 AM ET. Runs so far: 3.

| Bot | Trades | Open | Won | Lost | Pulled | Profit | Units | Return on stake | Closing-price edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NBA | 1 | 1 | 0 | 0 | 0 | +$0.00 | +0.00 | n/a | n/a |
| NFL | 0 | 0 | 0 | 0 | 0 | +$0.00 | +0.00 | n/a | n/a |
| College football | 9 | 9 | 0 | 0 | 0 | +$0.00 | +0.00 | n/a | n/a |
| **All three** | 10 | 10 | 0 | 0 | 0 | +$0.00 | +0.00 | n/a | n/a |

How to read this: profit over a handful of bets is mostly luck. Closing-price edge (did the price move toward the bot's side after it bought) and calibration (were its percentages right) are the fairer early tests.

## NBA

Too early to say. Not enough finished games yet.

| Paper trades | Open | Won | Lost | Pulled | Staked | Profit | Units | Return on stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a |

Average edge claimed at entry: +6.1 points after fees.

Calibration: no graded markets yet (32 being tracked).

| Placed | Game | Pick | Price | Size | Bot | Edge | Confidence | Result | Profit | Closing edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sat Nov 14 11:08 AM ET | DET @ MIA | Over 229.5 | 48c | 30 (1.49u) | 55.8% | +6.1 | Medium | open |  |  |

AI notes on the most recent picks:

- **DET @ MIA, Over 229.5:** Model and market agree on the margin; Miami back-to-back and Duren out roughly offset. No adjustment.

## NFL

Too early to say. Not enough finished games yet.

| Paper trades | Open | Won | Lost | Pulled | Staked | Profit | Units | Return on stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a |


Calibration: no graded markets yet (8 being tracked).

## College football

Too early to say. Not enough finished games yet.

| Paper trades | Open | Won | Lost | Pulled | Staked | Profit | Units | Return on stake |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9 | 9 | 0 | 0 | 0 | $0.00 | +$0.00 | +0.00 | n/a |

Average edge claimed at entry: +7.3 points after fees.

Calibration: no graded markets yet (665 being tracked).

| Placed | Game | Pick | Price | Size | Bot | Edge | Confidence | Result | Profit | Closing edge |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sat Nov 14 11:30 AM ET | SJSU @ AFA | SJSU +13.5 | 48c | 15 (0.75u) | 52.8% | +3.0 | Low | open |  |  |
| Sat Nov 14 12:31 AM ET | WAKE @ SMU | WAKE to win | 49c | 28 (1.42u) | 59.0% | +8.2 | Medium | open |  |  |
| Sat Nov 14 12:31 AM ET | WAKE @ SMU | WAKE -4.5 | 36c | 36 (1.35u) | 47.5% | +9.9 | Medium | open |  |  |
| Sat Nov 14 12:31 AM ET | TENN @ TA&M | TENN -3.5 | 39c | 36 (1.46u) | 50.8% | +10.1 | Medium | open |  |  |
| Sat Nov 14 12:31 AM ET | TENN @ TA&M | Under 40.5 | 38c | 25 (0.99u) | 46.6% | +7.0 | Low | open |  |  |
| Sat Nov 14 12:31 AM ET | TAR @ UWF | UWF to win | 15c | 41 (0.65u) | 22.2% | +6.3 | Low | open |  |  |
| Sat Nov 14 12:31 AM ET | TAR @ UWF | UWF +18.5 | 54c | 14 (0.78u) | 65.5% | +9.8 | Medium | open |  |  |
| Sat Nov 14 12:31 AM ET | ASU @ UCF | UCF -7.5 | 37c | 37 (1.43u) | 45.8% | +7.2 | Medium | open |  |  |
| Sat Nov 14 12:20 AM ET | EWU @ UTU | UTU to win | 35c | 50 (1.83u) | 41.3% | +4.7 | Low | open |  |  |

AI notes on the most recent picks:

- **WAKE @ SMU, WAKE to win:** Wake Forest's rating is inflated by lopsided wins over weak opponents, including a 77-0 game. SMU at home is the best team Wake has seen in a month. Forecast moved 3 points toward SMU.
- **WAKE @ SMU, WAKE -4.5:** Wake Forest's rating is inflated by lopsided wins over weak opponents, including a 77-0 game. SMU at home is the best team Wake has seen in a month. Forecast moved 3 points toward SMU.
- **TENN @ TA&M, TENN -3.5:** Tennessee is 7-2 with a win over Alabama and A&M has lost three of four, yet the book calls it even. That can mean a Tennessee absence the sheet does not show, so the forecast is moved 2 points toward A&M.
- **TENN @ TA&M, Under 40.5:** Tennessee is 7-2 with a win over Alabama and A&M has lost three of four, yet the book calls it even. That can mean a Tennessee absence the sheet does not show, so the forecast is moved 2 points toward A&M.
- **TAR @ UWF, UWF to win:** Tarleton State is 10-0 partly on a +12 turnover margin, which rarely lasts, and that supports the model's view that 17 points is too many. Their passing and rushing numbers are dominant though, so the forecast is moved 2.5 points back toward Tarleton.
- **TAR @ UWF, UWF +18.5:** Tarleton State is 10-0 partly on a +12 turnover margin, which rarely lasts, and that supports the model's view that 17 points is too many. Their passing and rushing numbers are dominant though, so the forecast is moved 2.5 points back toward Tarleton.
- **ASU @ UCF, UCF -7.5:** The model's higher total fits what these teams have actually done: their last five games each have averaged about 54 combined points against a line of 47.5. Nothing on the sheet explains the low number, so the forecast stands.
- **EWU @ UTU, UTU to win:** Two bad FCS teams rated nearly even by results, while the book makes the road team a 4.5-point favorite. No injury or weather information either way, so the forecast stands unadjusted and confidence is low.

