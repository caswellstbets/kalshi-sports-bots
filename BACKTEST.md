# Back-test of the stats forecast

Generated 2026-11-14T16:34:41Z by `python backtest.py`. Walk-forward: each game is forecast from ratings fit only on games that started before that day, then compared with the final score and with the sportsbook closing line (ESPN, DraftKings).

**Read this first.**

- This tests the numbers-only forecast. It says nothing about the AI forecast, which is tested forward.
- It is not a Kalshi trading back-test. No historical Kalshi prices are used.
- The model settings were tuned on this same season, so the stats model looks a little better here than it would on new data.
- The closing line is the yardstick. A real bet is placed hours earlier at a different price.
- 52.4% is the break-even rate against a standard sportsbook spread. The ± is the 95% range for a coin flip at that sample size.

## NBA

105 games with both a stats forecast and a closing line (105 forecast in all).

| Measure | Stats forecast | Closing line |
| --- | --- | --- |
| Average miss on the margin, points | 11.98 | 11.32 |
| Average miss on the total, points | 14.29 | 13.75 |
| Winner probability, Brier score (lower is better) | 0.1987 | 0.1797 |

When the stats forecast disagreed with the closing line, how often was its side right?

| Disagreement of at least | Against the spread | Over/under |
| --- | --- | --- |
| 0 points | 54-51 (51.4%, coin-flip range ±10) | 53-52 (50.5%, coin-flip range ±10) |
| 3 points | 29-29 (50.0%, coin-flip range ±13) | 21-22 (48.8%, coin-flip range ±15) |
| 6 points | 14-9 (60.9%, coin-flip range ±20) | 4-11 (26.7%, coin-flip range ±25) |

Best single weight on the stats forecast when mixed with the closing line: **0.03** for the margin and **-0.28** for the total (0 means the line alone is best, 1 means the stats alone). This is fit on the same games it is reported on, so it is an upper estimate.

## NFL

56 games with both a stats forecast and a closing line (56 forecast in all).

| Measure | Stats forecast | Closing line |
| --- | --- | --- |
| Average miss on the margin, points | 9.64 | 9.01 |
| Average miss on the total, points | 11.07 | 10.61 |
| Winner probability, Brier score (lower is better) | 0.2249 | 0.2028 |

When the stats forecast disagreed with the closing line, how often was its side right?

| Disagreement of at least | Against the spread | Over/under |
| --- | --- | --- |
| 0 points | 24-32 (42.9%, coin-flip range ±13) | 31-25 (55.4%, coin-flip range ±13) |
| 3 points | 6-12 (33.3%, coin-flip range ±23) | 13-12 (52.0%, coin-flip range ±20) |
| 6 points | n/a | 0-4 (0.0%, coin-flip range ±49) |

Best single weight on the stats forecast when mixed with the closing line: **-0.61** for the margin and **-0.55** for the total (0 means the line alone is best, 1 means the stats alone). This is fit on the same games it is reported on, so it is an upper estimate.

## College football

282 games with both a stats forecast and a closing line (282 forecast in all).

| Measure | Stats forecast | Closing line |
| --- | --- | --- |
| Average miss on the margin, points | 12.92 | 11.74 |
| Average miss on the total, points | 13.82 | 12.93 |
| Winner probability, Brier score (lower is better) | 0.2210 | 0.2005 |

When the stats forecast disagreed with the closing line, how often was its side right?

| Disagreement of at least | Against the spread | Over/under |
| --- | --- | --- |
| 0 points | 127-151 (45.7%, coin-flip range ±6) | 112-170 (39.7%, coin-flip range ±6) |
| 3 points | 52-75 (40.9%, coin-flip range ±9) | 47-67 (41.2%, coin-flip range ±9) |
| 6 points | 19-20 (48.7%, coin-flip range ±16) | 16-25 (39.0%, coin-flip range ±15) |

Best single weight on the stats forecast when mixed with the closing line: **-0.19** for the margin and **-0.60** for the total (0 means the line alone is best, 1 means the stats alone). This is fit on the same games it is reported on, so it is an upper estimate.

