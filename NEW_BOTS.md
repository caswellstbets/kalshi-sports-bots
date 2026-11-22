# Four new bots (started Sat Nov 21, 2026)

Four paper-trading bots that run beside the main bot and the NBA lab, so all of them can be compared.
They cover college football, the NFL and the NBA. **Paper only**: like the rest of the repo, there is no
order code, no Kalshi login and no API key. They only enter before a game starts, never during one.

Results: [NEW_BOTS_SCORECARD.md](NEW_BOTS_SCORECARD.md). Code: `quad/`. Ledger: `data/quad/<bot>/`.

## Why these four

What this week showed:

- Kalshi's own price was the most accurate number we had. It beat the stats model, the sportsbook-based
  blend and every mechanical NBA model out of sample (BACKTEST.md, NBA_MODELS.md on the lab branch).
- The main bot's blind forecast and market check blocked nearly everything (8 picks in 8 days). Each
  existing bot also leans on one idea.
- Scout, where Claude reads the whole game with the price in view, was the only model that looked useful (3-1).

So every new bot **starts from Kalshi's price and moves away from it only by what its signals add.**
A bot that sees nothing returns Kalshi's own number and finds no edge. Each bot combines several inputs.
The sportsbook line is weighted at 5% or less in every bot: it never drives a pick and never blocks one.

## The signals

All are measured in points of home margin (or total points) against Kalshi's price. See `quad/slate.py`.

| Signal | Where it comes from |
| --- | --- |
| stats | The main bot's ratings model (opponent-adjusted, recent form, home field) minus the Kalshi-implied margin |
| book | The sportsbook-implied margin from ESPN minus the Kalshi-implied margin |
| move | How far the Kalshi-implied margin has moved since the market's first real two-sided quote (Kalshi's public price history) |
| rest | Spots found automatically: bye weeks, NFL short weeks, NBA back-to-backs and long rests |
| news | Points Claude assigns for injury, QB or suspension news it thinks **Kalshi's price hasn't absorbed yet** (news already priced in counts zero). Comes from ESPN's injury report for NFL and NBA. Claude also records whether known news explains the price move since opening. |
| spots | Situational tags Claude picks from a fixed list. **The code sets the point values, not Claude.** The tags are look-ahead, letdown, rivalry underdog, bowl or playoff push, nothing to play for, senior night, long travel, coach turmoil, wind, cold and pace clash. |
| read | Claude's own expected margin and total, written in session with the price, stats and injuries in view |

Claude writes one read per game with `python3 -m quad.read`. It can't be replaced once saved.

## The four bots (`quad/bots.py`)

1. **Consensus.** Each of the six margin signals votes for a side when its disagreement with Kalshi is big
   enough. A pick needs at least 3 votes for the same side and no more than 1 against. Its number is Kalshi's
   margin plus a weighted blend: read 35%, stats 20%, news 15%, spots 15%, movement 10%, book 5%. Totals
   work the same way: read 45%, stats 30%, weather/pace spots 20%, book 5%, with 2 agreeing votes and none against.
2. **Full Scout.** Claude's read, pulled toward Kalshi's price: it keeps 60% of Claude's difference on
   margins and 45% on totals. This widens the NBA lab's Scout to all three sports.
3. **Situational.** Kalshi plus the situational and rest spots, plus half the news points. It only bets when
   the spots add up to at least 1 point and the stats or the news point the same way. Totals need at least
   1.5 points of weather or pace spots, with the stats agreeing.
4. **Line Movement.** It looks at moves of 1.5 points or more since the market opened. If the stats, Claude's read, or known news (injuries, rest) back the
   move, it bets on half the move again (the market is still catching up). If a move
   of 3 or more points has nothing behind it, it fades about a third of it, but only after Claude has checked the news for that game. A fade is never rated High. Winner
   and spread markets only.

## From a number to a pick (`quad/run.py`)

- Each contract is priced from **its own Kalshi price**, shifted by the bot's disagreement with Kalshi
  (points divided by the sport's typical miss). This keeps a bot from "finding" an edge that is really Kalshi's
  winner, spread and total markets disagreeing slightly with each other.
- The bot takes the single best contract per game, after Kalshi's taker fee (7% x price x (1 - price)).
  Each bot holds at most one position per game.
- The same quality rules apply as the main bot: winners priced 15c to 85c, spreads and totals 35c to 65c,
  a bid-ask gap of 8c or less, and at least 10 contracts on offer.

## Confidence and bet size

Every pick shows Low, Mid or High, and the label sets the stake. The reason is written on the pick.

| Confidence | When | Stake | Why this size |
| --- | --- | --- | --- |
| **High** | Edge of 6+ points after fees. Consensus also needs 4+ agreeing signals. A Line Movement fade can't be High. | 1/8 Kelly, at least 1u, at most 2u | Only big, well-supported edges get real money. An eighth of Kelly allows for the edge estimate being too high. |
| **Mid** | Edge of 3 to 6 points | 0.5u | The edge clears the fee comfortably but isn't proven, so the stake is flat and small. |
| **Low** | A daily fill-in: the best remaining edge of 1 to 3 points, for a game starting within 4 hours | 0.25u | It's there so each bot makes about 2 picks a day and builds a graded record. At this size a bad week costs little. |

There's no daily cap. The 2-a-day target is soft: if nothing clears 1 point, there's no pick.
Picks are held until the game is settled. The new bots never sell early.

## What would prove or kill them

Every value above was set before the first pick and is a **GUESS**. None of it is tuned on results.
Grading will compare:

- **Closing-price edge:** whether Kalshi's price moved toward each pick before kickoff. This is the fastest honest signal.
- Profit and return on stake, by bot and by confidence label.
- Low picks are reported separately, since they're expected to be about break-even.

The plan is to review on Mon Nov 30 after about a week. A bot whose picks show a negative average
closing-price edge over 25+ picks gets retired or reworked, and only with Livy's OK.

## Run it

    python3 run_quad.py            # settle, build the slate, list games needing a read, place picks
    # for each game it lists, write a read:
    python3 -m quad.read cfb <game_id> --margin <home margin> --total <points> --news <pts> \
        --spot "bowl_push:home" --summary "two or three sentences"
    python3 run_quad.py            # again, to place picks from the new reads

`data/quad/sheets.json` holds the sheet for every game still waiting for a read.

## Change log

- **Sat Nov 21, first hour.** Three Line Movement NBA fades were placed before Claude's reads existed, so
  injury-driven moves looked unexplained. They were withdrawn before tip-off (a withdrawn pick never counts).
  New rule: a fade needs a read, and a read records whether news explains the move.
