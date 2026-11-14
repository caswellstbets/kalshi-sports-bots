# Runbook

One run does everything: grades finished games, records the latest pre-game prices, pulls picks that no longer
hold up, and places new paper trades. Run it as often as hourly; running it more often changes nothing except
how fresh the closing prices are.

## Steps

1. Get the latest ledger: `git pull --rebase` (or clone `caswellstbets/kalshi-sports-bots`).
2. `python run_all.py`
3. If the output ends with **REVIEWS NEEDED**, each listed game is close to a trade and has no AI review yet.
   Read its sheet (printed as one JSON line), then save a review:

       python -m core.notes <bot> <game_id> --margin <pts> --total <pts> --confidence low|medium|high \
           [--veto] --reason "two plain sentences"

   `--margin` is added to the expected HOME margin, `--total` to the expected combined score. Zero is the right
   answer most of the time. Veto when the sheet looks unreliable or the result hinges on an unknown
   (a star's game-time decision, a quarterback question). Reviews stay valid for 12 hours.
4. `python run_all.py` again so the reviewed games can trade.
5. Commit and push: `git add -A && git commit -m "Run <time>" && git push`.

## Notes

- If no games are inside the entry window and nothing needs grading, the run is a no-op and there is nothing to commit.
- Needs network access to `api.elections.kalshi.com` and `site.api.espn.com`.
- ESPN rejects user agents containing "bot"; the code uses the default `requests` one.
- If `ANTHROPIC_API_KEY` is set, reviews are fetched from the API automatically instead (optional, not required).
