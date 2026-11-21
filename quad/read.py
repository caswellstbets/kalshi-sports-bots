"""Claude's in-session read of one game, shared by the four new bots (no API key, no paid service).

    python3 -m quad.read <sport> <game_id> --margin -3.5 --total 51 --news -1.5 \
        --spot "lookahead:home" --spot "rivalry:away" --summary "two or three sentences"

--margin / --total  Claude's own expected HOME margin and total, written with the Kalshi price,
                    stats and injuries in view. Used by Full Scout and as one Consensus vote.
--news              HOME-margin points from injuries, suspensions, QB changes and other news the
                    stats cannot see (negative helps the away team). Used by Consensus,
                    Situational and Line Movement.
--spot TAG:SIDE     situational tags from the fixed list in SPOTS below; the point values are set
                    in code, not by the reader.
A read is saved once and cannot be replaced; the first one counts."""
from __future__ import annotations

import argparse
import os
import sys

from core.util import append_jsonl, iso, now_utc, read_json, read_jsonl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "data", "quad")
MODEL = "Claude (in session)"

# tag -> (home-margin points for the team it names, total points). Set before any result; GUESSES.
SPOTS = {
    "lookahead":       (-1.5, 0.0),  # the named team has a much bigger game next week
    "letdown":         (-1.0, 0.0),  # the named team is coming off an emotional or huge win
    "rivalry_dog":     (1.5, 0.0),   # the named team is the underdog in a rivalry game
    "bowl_push":       (1.5, 0.0),   # the named team needs this win for bowl eligibility or a title spot
    "nothing_to_play": (-1.5, 0.0),  # the named team is out of contention with little to play for
    "senior_night":    (0.5, 0.0),   # last home game for the named team
    "long_travel":     (-1.0, 0.0),  # the named team crosses two or more time zones or plays a 3rd road game in a row
    "coach_turmoil":   (-1.0, 0.0),  # coach just fired, interim, or public turmoil
    "weather_wind":    (0.0, -3.0),  # sustained wind 15+ mph or heavy rain/snow (side: either)
    "weather_cold":    (0.0, -1.5),  # well below freezing (side: either)
    "pace_clash":      (0.0, 2.0),   # both teams play fast, or a fast team meets a bad defense (side: either)
}


def reads() -> dict[str, dict]:
    out = {}
    for r in read_jsonl(os.path.join(DIR, "reads.jsonl")):
        out.setdefault(f"{r['sport']}:{r['game_id']}", r)
    return out


def spot_points(r: dict | None) -> tuple[float, float, list[str]]:
    if not r:
        return 0.0, 0.0, []
    m = t = 0.0
    names = []
    for s in r.get("spots", []):
        tag, side = s.split(":")
        pm, pt = SPOTS[tag]
        m += pm * (1 if side == "home" else -1 if side == "away" else 0)
        t += pt
        names.append(s)
    return m, t, names


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sport", choices=["cfb", "nfl", "nba"])
    ap.add_argument("game_id")
    ap.add_argument("--margin", type=float, required=True)
    ap.add_argument("--total", type=float, required=True)
    ap.add_argument("--news", type=float, default=0.0)
    ap.add_argument("--spot", action="append", default=[])
    ap.add_argument("--summary", required=True)
    a = ap.parse_args(argv)
    sheets = read_json(os.path.join(DIR, "sheets.json"), {})
    key = f"{a.sport}:{a.game_id}"
    if key not in sheets:
        print("no sheet waiting for that game; run `python3 run_quad.py` first"); return 1
    if key in reads():
        print("that game already has a read; it cannot be replaced"); return 1
    for s in a.spot:
        tag, _, side = s.partition(":")
        if tag not in SPOTS or side not in ("home", "away", "either"):
            print(f"bad spot {s!r}; tags: {', '.join(SPOTS)}; side home|away|either"); return 1
    if abs(a.news) > 10:
        print("news points over 10 need a second look"); return 1
    append_jsonl(os.path.join(DIR, "reads.jsonl"), [{
        "sport": a.sport, "game_id": a.game_id, "game": sheets[key]["game"], "ts": iso(now_utc()), "model": MODEL,
        "margin": a.margin, "total": a.total, "news": a.news, "spots": a.spot, "summary": a.summary,
        "sheet": sheets[key]}])
    print("saved", sheets[key]["game"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
