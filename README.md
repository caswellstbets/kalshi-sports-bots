# Kalshi sports paper-trading bots

Three separate bots (NBA, NFL, college football) that price pre-game Kalshi markets, paper-buy the few that
look mispriced, and grade themselves. **Paper only.** There is no order-placing code, no Kalshi login and no
API key anywhere in this repo. A "trade" is a line in a file.

Current results: [SCORECARD.md](SCORECARD.md)

## How a pick is made (v2)

Every stage is saved separately so each can be graded on its own.

1. **Stats forecast.** A ridge regression on this season's scores gives each team an offense and a defense
   rating, adjusted for opponents, home field, recent form and rest. This is the numbers-only baseline. No price
   goes into it.
2. **Triage.** Each day the bot picks a limited number of games for a deep read: the ones where the stats and
   the market disagree most, plus a few chosen at random as a control group.
3. **Blind AI forecast.** Claude reads a game sheet (results with opponent strength, schedule strength,
   efficiency stats, injuries where a feed exists, rest) that contains no Kalshi price and no sportsbook line,
   and writes its own margin and total with tagged reasons. It is saved before any price is shown and cannot be
   replaced.
4. **Market check.** The prices are revealed. If the forecast is within 3 points of the market it stands
   automatically. Otherwise Claude must answer in writing what the other side of the price might know, and
   record `stands`, `shrink` or `drop`.
5. **Bet probability.** For each contract, the AI's probability is pulled toward the Kalshi price in log-odds:
   `logit(p_bet) = logit(p_market) + trust x (logit(p_ai) - logit(p_market))`. This is a blend with the price,
   stated plainly. It replaces the old fixed 90/10 weight.
6. **Code picks the bet.** Every eligible contract in the game is priced with exact fees. The single best one is
   bought if its edge is at least 3 points, sized at one eighth of Kelly with no minimum stake. Otherwise no bet.

Nothing is traded without both a blind forecast and a market check.

## Rules set in advance

These are fixed for the evaluation window that started 2026-11-14 and are not tuned on results inside it.
One change was made on day one: v2.0 ran for about an hour with trust 0.35/0.25 and made one pick before the
back-test was finished. The back-test result lowered trust to the values below (v2.1). Every pick records the
version and trust it was made under.
Numbers marked GUESS have no evidence behind them yet.

| Rule | Value | Basis |
| --- | --- | --- |
| Trust in the AI forecast, winner and spread | 0.25 | GUESS, cautious. The AI has no track record, and the back-test gives the stats alone no weight. |
| Trust, totals | 0.15 | GUESS. In the back-test the stats did worst on totals. |
| Trust when either team has under 6 rated games | x 0.7 | GUESS |
| Trust after a `shrink` market check | x 0.5 | GUESS |
| Trust ceiling | 0.70 | Never reached in this window |
| Minimum edge after the market check and fees | 3 points | GUESS |
| Stake | 1/8 Kelly, max 2 units, no floor | |
| Positions per game | 1 | Winner, spread and total on one game are correlated |
| Pull | net bid beats hold value by 4 cents, or forecast dropped | |
| Soft judgment alone may move a forecast | 3 points | |

**When trust changes.** Not weekly. After 60 graded AI-forecast games in a sport, trust for that sport is re-set
once to the value that would have scored best on those games, shrunk halfway back toward the starting value and
limited to a move of 0.15. The frozen starting values keep being scored alongside.

**When the AI loses authority.** After 60 graded AI-forecast games in a sport, if the blind AI forecast has a
larger average margin error than the stats forecast on the same games, AI forecasts for that sport are limited
to 3 points from the stats forecast until it recovers over the next 60. If the bet probability scores worse
than the Kalshi price on the same contracts (Brier), trust for that sport drops to 0.15.

## What is and is not proven

- `backtest.py` replays this season for the stats forecast only. See [BACKTEST.md](BACKTEST.md). Result: the
  stats forecast was less accurate than the sportsbook closing line in all three sports, and when it disagreed
  with the line its side won less than half the time in college football and the NFL. The numbers alone are
  not an edge. Any edge has to come from what the AI adds, and that is unproven.
- The AI forecast cannot be back-tested fairly, so it is tested forward. The scorecard grades the stats
  forecast, the blind AI forecast, the market and the bet probability on the same games.
- Picks made before v2 are labelled v1 and reported separately. They were made under earlier rules.
- Kalshi's taker fee is taken as 7% x price x (1 - price) per contract, rounded up per order. This has not been
  checked against each sports series' fee schedule.

## Paper trading rules

- $1,000 paper bankroll per bot, 1 unit = $10.
- Fills at the ask, capped at the size offered, with the taker fee. No long shots: 15 to 85 cents for
  winners, 35 to 65 for spreads and totals. Bid-ask gap 8 cents or less.
- Entry only before the scheduled start: within 12 hours (NBA) or 24 hours (football), never in the last 5 minutes.
- No adding and no re-entry. Daily caps: 4 NBA, 5 NFL, 8 college.
- Nothing is ever traded during a game.

## Files

| Path | What it is |
| --- | --- |
| `backtest.py`, `BACKTEST.md` | Walk-forward test of the stats forecast against results and closing lines |
| `run_all.py` | Runs all three bots and rebuilds the scorecard |
| `bots/` | One file per bot: settings and sport-specific adjustments |
| `core/` | Shared code: Kalshi and ESPN readers, ratings, pricing, engine, grading, report |
| `data/<bot>/trades.jsonl` | Every paper entry, append-only |
| `data/<bot>/settlements.jsonl` | How each entry ended (won, lost, pulled), append-only |
| `data/<bot>/forecasts.jsonl` | Every blind AI forecast and market check, append-only, with the sheet the AI saw |
| `data/<bot>/game_grades.jsonl` | Each stage's forecast for a finished game next to the real score |
| `data/<bot>/graded_predictions.jsonl` | Final pre-game probabilities for every tracked market, with the result |
| `data/<bot>/open_predictions.json` | Markets being tracked for games that have not finished |
| `SCORECARD.md`, `docs/index.html` | The scorecard |
| `RUNBOOK.md` | Step-by-step for running the bots |

## Run it

    pip install -r requirements.txt
    python run_all.py --dry-run     # look only
    python run_all.py               # save trades, grade finished games, rebuild the scorecard
    python tests/test_core.py
