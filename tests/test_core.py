"""Run with:  python -m pytest tests  (or  python tests/test_core.py)"""
import os
import sys
import tempfile
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bots import nba
from core import engine, kalshi, pricing, ratings, report
from core.util import append_jsonl, iso, now_utc, read_jsonl, write_json


def test_fee_matches_kalshi_schedule():
    assert pricing.fee(100, 0.50) == 1.75          # 7% x 100 x .5 x .5
    assert pricing.fee(1, 0.50) == 0.02            # rounds up to the cent
    assert pricing.fee(10, 0.10) == 0.07


def test_devig_and_anchors():
    assert abs(pricing.devig(-110, -110) - 0.5) < 1e-9
    a = pricing.book_anchors({"home_spread": -3.5, "home_spread_odds": -110, "away_spread_odds": -110,
                              "total": 45.5, "over_odds": -110, "under_odds": -110,
                              "home_ml": -180, "away_ml": 150}, 13.3, 13.5)
    assert abs(a["margin_spread"] - 3.5) < 1e-6 and abs(a["total"] - 45.5) < 1e-6
    assert 0.6 < a["p_home_ml"] < 0.64 and a["margin_ml"] > 0


def test_p_yes_is_consistent():
    cfg = nba.CONFIG
    home = {"team_code": "AAA", "strike": 4.5}
    away = {"team_code": "BBB", "strike": 4.5}
    assert abs(engine.p_yes(home, "ml", "AAA", 0.0, None, cfg) - 0.5) < 1e-9
    assert abs(engine.p_yes(home, "spread", "AAA", 4.5, None, cfg) - 0.5) < 1e-9
    assert abs(engine.p_yes(away, "spread", "AAA", -4.5, None, cfg) - 0.5) < 1e-9
    # home and away winner markets are mirror images
    ph = engine.p_yes(home, "ml", "AAA", 3.0, None, cfg)
    pa = engine.p_yes(away, "ml", "AAA", 3.0, None, cfg)
    assert abs(ph + pa - 1) < 1e-9 and ph > 0.5


def test_ratings_rank_the_better_team_higher():
    games = []
    day = now_utc() - timedelta(days=30)
    for i in range(12):   # A beats B beats C, home and away
        d = iso(day + timedelta(days=i))
        games += [{"id": f"a{i}", "date": d, "h": "A", "a": "B", "hs": 110, "as": 100, "neutral": False},
                  {"id": f"b{i}", "date": d, "h": "B", "a": "C", "hs": 108, "as": 100, "neutral": False},
                  {"id": f"c{i}", "date": d, "h": "C", "a": "A", "hs": 95, "as": 109, "neutral": False}]
    r = ratings.fit(games, hfa=2.0, ridge=4.0, half_life_days=45)
    assert ratings.net(r, "A") > ratings.net(r, "B") > ratings.net(r, "C")
    margin, total = ratings.predict(r, "A", "C", hfa=2.0)
    assert margin > 8 and 190 < total < 225


def test_settlement_grades_trades_and_predictions(monkeypatch=None):
    cfg = nba.CONFIG
    with tempfile.TemporaryDirectory() as root:
        p = engine.paths(cfg, root)
        start = iso(now_utc() - timedelta(hours=5))
        trade = {"id": "t1", "bot": "nba", "ts": start, "game_id": "g1", "game": "AAA @ BBB", "start": start,
                 "ticker": "TK-1", "mtype": "ml", "side": "no", "label": "AAA to win", "price": 0.40,
                 "contracts": 10, "fee": 0.17, "cost": 4.17, "units": 0.42, "p_final": 0.47, "edge": 0.05,
                 "confidence": "Low", "ai": {}}
        append_jsonl(p["trades"], [trade])
        write_json(p["open_preds"], {"TK-1": {"game_id": "g1", "game": "AAA @ BBB", "start": start, "mtype": "ml",
                                              "label": "BBB to win", "p_kalshi": 0.55, "p_book": 0.56,
                                              "p_model": 0.5, "p_blend": 0.54, "p_final": 0.53}})
        real = kalshi.markets_by_ticker
        kalshi.markets_by_ticker = lambda tickers: {"TK-1": {"status": "finalized", "result": "no"}}
        try:
            out = engine.settle(cfg, p, now_utc(), dry=False)
        finally:
            kalshi.markets_by_ticker = real
        assert out == {"graded": 1, "settled": 1}
        s = read_jsonl(p["settlements"])[0]
        assert s["outcome"] == "won" and abs(s["pnl"] - (10 - 4.17)) < 1e-9
        assert abs(s["clv"] - (0.45 - 0.40)) < 1e-9          # NO side closed at 45c, bought at 40c
        assert read_jsonl(p["graded"])[0]["result"] == 0
        md = report.build(root)
        assert "+$5.83" in md and "| NBA | 1 | 0 | 1 | 0 |" in md


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
