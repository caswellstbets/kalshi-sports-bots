# Kalshi sports paper-trading bots

Three separate bots (NBA, NFL, college football) that price pre-game Kalshi markets, paper-buy the few that
look mispriced, and grade themselves. **Paper only.** There is no order-placing code, no Kalshi login and no
API key anywhere in this repo. A "trade" is a line in a file.

Current results: [SCORECARD.md](SCORECARD.md)

## How a pick is made

The bot's own analysis drives every pick. The sportsbook line is a 10% input and a flag for the AI review, never a veto.

1. **Season strength.** A ridge regression on this season's scores gives each team an offense and a defense
   rating, adjusted for opponents and home field.
2. **Recent form.** The same ratings refit with a short memory (10 days NBA, 21 days football) make up 30 to 35%
   of the model.
3. **Situation.** Each bot adds its own terms: back-to-backs and rest (NBA), byes and short road weeks (NFL),
   byes and a blowout cap (college). See `bots/`.
4. **Back-tested scale.** The ratings were tuned by predicting the second half of this season from the first:
   how much to shrink them, how wide results really land around the forecast, and how much of a predicted total
   to believe. The NFL ratings showed no skill on totals, so the NFL bot does not trade them.
5. **AI review.** Each day's strongest opinions get a written review from Claude with team stats, last five
   results, injuries and the sportsbook line for reference. It can move the forecast by up to about 4 points or
   veto the game.
6. **Price check.** The bot buys when its probability beats the Kalshi ask by 6 to 16 points after fees. Above 16
   is treated as a model error, not an opportunity.

Each bot makes at most a few picks a day (4 NBA, 5 NFL, 8 college), best first, and at most one side and one
total per game.

## Paper trading rules

- $1,000 paper bankroll per bot, 1 unit = $10.
- **Stake size varies from 0.5 to 3 units.** It is one eighth of the Kelly stake, so it grows with the edge and
  shrinks as the price gets worse, then is scaled by the AI's confidence (0.7x low, 1x medium, 1.2x high).
  Flat staking would ignore how strong each opinion is; full Kelly assumes the probabilities are exact, which
  they are not, so the fraction and the cap keep one overconfident forecast from doing much damage.
- Fills at the ask, capped at the size offered, with Kalshi's taker fee. No long shots: 15 to 85 cents for
  winners, 35 to 65 for spreads and totals. Bid-ask gap 8 cents or less.
- Entry only before the scheduled start: within 12 hours (NBA) or 24 hours (football), never in the last 5 minutes.
- No adding and no re-entry.
- A pick can be **pulled** before the start if the market is bidding more than the bot now thinks it is worth, or
  if a fresh AI review vetoes the game. It is sold at the bid. Nothing is ever traded during a game.

## Files

| Path | What it is |
| --- | --- |
| `run_all.py` | Runs all three bots and rebuilds the scorecard |
| `bots/` | One file per bot: settings and sport-specific adjustments |
| `core/` | Shared code: Kalshi and ESPN readers, ratings, pricing, engine, grading, report |
| `data/<bot>/trades.jsonl` | Every paper entry, append-only |
| `data/<bot>/settlements.jsonl` | How each entry ended (won, lost, pulled), append-only |
| `data/<bot>/graded_predictions.jsonl` | Final pre-game probabilities for every tracked market, with the result |
| `data/<bot>/open_predictions.json` | Markets being tracked for games that have not finished |
| `SCORECARD.md`, `docs/index.html` | The scorecard |
| `RUNBOOK.md` | Step-by-step for running the bots |

## Run it

    pip install -r requirements.txt
    python run_all.py --dry-run     # look only
    python run_all.py               # save trades, grade finished games, rebuild the scorecard
    python tests/test_core.py
