# Kalshi sports paper-trading bots

Three separate bots (NBA, NFL, college football) that price pre-game Kalshi markets, paper-buy the few that
look mispriced, and grade themselves. **Paper only.** There is no order-placing code, no Kalshi login and no
API key anywhere in this repo. A "trade" is a line in a file.

Current results: [SCORECARD.md](SCORECARD.md)

## How a pick is made

1. **Power ratings.** A ridge regression on this season's scores gives each team an offense and a defense
   rating, adjusted for opponents, home field and recency. Each bot adds its own situational terms
   (`bots/nba.py`, `bots/nfl.py`, `bots/cfb.py`).
2. **Sportsbook anchor.** The DraftKings line shown on ESPN is stripped of the book's cut. The bot's forecast is
   70% book and 30% model (75/25 for the NFL), and the model can pull the forecast at most 1.8 points.
3. **AI review.** Games that are within a point of the trading bar get a written review from Claude, which can
   nudge the forecast by a capped amount or veto the game. Reviews are saved with `python -m core.notes`.
4. **Price check.** The bot buys only if all of these hold:
   - its edge over the Kalshi ask is at least 4 points after fees, and no more than 15 (bigger means bad data);
   - the sportsbook on its own also rates the price fair or better;
   - for spreads and totals, the Kalshi strike is the sportsbook's own number (or right beside it);
   - the price is not a long shot, the bid-ask gap is 8 cents or less, and at least 10 contracts are offered.

Most games produce no trade. That is intended.

## Paper trading rules

- $1,000 paper bankroll per bot, 1 unit = $10. Quarter-Kelly sizing, 2 units max per trade, 5 per game.
- Fills at the ask, capped at the size offered, with Kalshi's taker fee.
- Entry only before the scheduled start: within 12 hours (NBA) or 24 hours (football), never in the last 5 minutes.
- One position per game per market type. No adding and no re-entry.
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
