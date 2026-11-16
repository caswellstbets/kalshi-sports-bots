# NBA lab: three more models, one week, compared

Three new NBA models paper-trade Kalshi alongside the current NBA bot for one week, each with its own
ledger and $1,000 paper bankroll, then get compared in [NBA_MODELS.md](NBA_MODELS.md). Paper only:
there is still no order code, login or API key anywhere. The current bots and their rules are untouched;
the lab runs from `run_lab.py`, writes only under `data/nba_lab/` and `data/nba_<model>/`, and runs at a
different minute of the hour.

## The four models

They differ in where the information comes from, not in settings.

| Model | Signal | Sees the price? | AI? |
| --- | --- | --- | --- |
| **Current NBA bot (v2.3)** | team ratings from scores, then a blind Claude forecast held close to the price | after the forecast | yes |
| **Rotation** | players: who is playing tonight and how much each one moves the score | only to pick a contract | no |
| **Injury News** | changes in the injury report during the day, valued with Rotation's player ratings | yes: bets only where the price has not caught up | no |
| **Scout** | Claude's full read with everything in view, prices included | yes | yes, all of it |

**Rotation** (`lab/rotation.py`, `lab/rapm.py`, `lab/players.py`). Rates every player rather than every
team: a regularized adjusted plus-minus fit on every game since October 2025, with each player pulled
toward a box-score prior. Tonight's strength is the expected rotation's minutes times those ratings,
with injured players' minutes removed using ESPN's injury report. Because it rates players, last season
still counts early in this one and injuries flow straight into the number. On this season's games it
missed the final margin by 11.6 points on average, against 12.0 for the current bot's stats model and
11.1 for the closing sportsbook line. It bets winners and spreads only (its total ignores who plays).
Its forecast is pulled toward the Kalshi price by a trust value set from the Kalshi back-test.

**Injury News** (`lab/news.py`). Event-driven. Every run saves each upcoming game's injury picture and
Kalshi price. When a later run finds that a player who plays 15+ minutes has changed status (Questionable
to Out, say), it values the change with Rotation's player ratings, moves the earlier price by that much,
and bets if Kalshi has moved less than the news is worth. No news, no bet. Winner markets only. In the
back-test, when a rotation player sat unexpectedly, Kalshi's price 3 hours out had moved about 60% of
what the ratings say the absence was worth, and about 80% by the close.

A first idea for this slot, **Price Pattern** (`lab/pattern.py`: bet on how Kalshi's own prices had
been miscalibrated), was built, back-tested and dropped before the week started: fit on last season it
lost 47% on this season's games, and four more price-pattern ideas tested in both seasons all flipped
sign. The code and numbers are kept for the record.

**Scout** (`lab/scout.py`, `lab/scout_sheet.py`). Claude reads a game sheet with the Kalshi prices and
how they moved, both teams' record, form, efficiency and pace, rest, the injury report with each
player's usual role, and the season series. No sportsbook line and nothing from the other models. It
writes its own home-win probability, margin and total, and either names one contract and a confidence
or passes. It must name what the price is missing. The code checks the pick against the Scout's own
numbers and lowers or refuses a tier the edge does not support.

## Rules shared by all three (set before the first pick)

- Rotation and Scout decide once per game, at the first run between 3 hours and 10 minutes before the
  start; the forecast is saved for every game, pick or pass, so accuracy is graded on all of them.
  Injury News decides once per game, at the first run that finds news worth 1+ points (up to 12 hours out).
- Edge = the model's bet probability minus the price paid per contract including Kalshi's fee
  (7% x price x (1 - price), rounded up; the NBA series fee multiplier is 1, checked Nov 16).
- **High**: edge 8+ points, stake 1/8 Kelly up to 2 units. **Mid**: 5 to 8 points, up to 1 unit.
  **Low**: 3 to 5 points, up to 0.5 units. Under 3 points: no pick. Kelly already grows with the edge,
  so a clearer edge gets a bigger stake; the caps stop one forecast from carrying the week.
- One position per game per model, held to the result (no pulls). No daily limit.
- Same market-quality rules as the current bots: winners priced 15 to 85 cents, spreads 35 to 65,
  bid-ask gap 8 cents or less, at least 10 contracts offered.
- Nothing here is tuned during the week. Model settings are in `lab/rotation_params.json` (fit on last season
  only), `lab/rotation_live.py` (Rotation trust 0.25) and the constants at the top of `lab/news.py`.

## How the week is judged

See the end of [NBA_MODELS.md](NBA_MODELS.md). In short: forecast accuracy against Kalshi on every game
(Brier score, paired, with a bootstrap range), closing-price edge on picks, then profit, then whether
High picks beat Mid and Low. A model behind Kalshi on both accuracy and closing-price edge is retired
whatever its profit.

## Back-test

[BACKTEST_NBA_MODELS.md](BACKTEST_NBA_MODELS.md), from `python -m research.backtest_rotation` and
`python -m research.backtest_kalshi`. Scout cannot be back-tested fairly and is tested forward only.

## Running it

    python3 run_lab.py          # grade, forecast, trade, rebuild NBA_MODELS.md
    python3 -m lab.scout read <game_id> --p-home 0.58 --margin 3.5 --total 229.5 \
        --pick "<TICKER>:yes" --confidence Mid --why "..." --missing "..."   # or --pick none
    python3 run_lab.py          # again, so Scout reads can trade
    python3 tests/test_lab.py
