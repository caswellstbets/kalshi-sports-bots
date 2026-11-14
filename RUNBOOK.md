# Runbook

One run grades finished games, records the latest pre-game prices, applies the pull rule, and places new paper
trades for games that already have a forecast and a market check. Hourly runs are light. The AI work happens
when a run asks for it.

## Steps

1. Get the latest ledger: `git pull --rebase` (or clone `caswellstbets/kalshi-sports-bots`).
2. `python run_all.py`
3. For each **BLIND FORECAST NEEDED** line, read the game sheet printed under it. The sheet has no Kalshi price
   and no sportsbook line in it on purpose. Do not look prices up. The sheet's stats forecast is a starting
   point, not an authority: in the back-test it was less accurate than the closing line and its disagreements
   with the line were worth nothing. Look for what the formula cannot see. Write your own forecast:

       python -m core.forecast blind <bot> <game_id> --margin <home margin> --total <points> \
           --reason "hard|<pts>|<text>" --reason "stat|<pts>|<text>" --reason "soft|<pts>|<text>" \
           --summary "two or three plain sentences" --unknowns "what you could not see"

   `--margin` is the expected HOME margin (negative if the away team should win). Each reason is tagged
   hard (a verifiable fact), stat (a read of the numbers) or soft (judgment), with roughly how many points it
   moved the margin away from the stats forecast. Soft judgment alone may move it at most 3 points; more than
   that needs hard or stat-based reasons that cover the difference. A blind forecast cannot be replaced.
4. `python run_all.py` again. For each **MARKET CHECK NEEDED** line you now see the prices. Answer the question
   "what would someone on the other side of this price know that the forecast does not?" and record one of:

       python -m core.forecast check <bot> <game_id> --outcome stands|shrink|drop --why "..."

   - `stands`: you have a specific, stated reason the market may be wrong.
   - `shrink`: no specific reason either way. Trust is halved.
   - `drop`: the gap is large and unexplained. No bet.
5. `python run_all.py` once more so checked games can trade.
6. Commit and push: `git add -A && git commit -m "Run <time>" && git push`.

## Notes

- A game with no blind forecast or no market check is never traded. There is no automatic fallback.
- Each bot asks for a limited number of forecasts per day (college 13, NFL 9, NBA 7): the games where the
  numbers and the market disagree most, plus a few chosen at random as a control group.
- Contract choice, stake size and pulls are done by code from the saved forecast. They are not judgment calls.
- If no games are inside the entry window and nothing needs grading, there is nothing to commit.
- Needs network access to `api.elections.kalshi.com` and `site.api.espn.com`.
- ESPN rejects user agents containing "bot"; the code uses the default `requests` one.
