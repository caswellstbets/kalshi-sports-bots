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


def test_shrink_to_market_sits_between_forecast_and_price():
    assert abs(engine.shrink_to_market(0.62, 0.48, 0.0) - 0.48) < 1e-9
    assert abs(engine.shrink_to_market(0.62, 0.48, 1.0) - 0.62) < 1e-9
    mid = engine.shrink_to_market(0.62, 0.48, 0.35)
    assert 0.48 < mid < 0.62 and mid < 0.55          # closer to the price than to the forecast
    assert abs(engine.shrink_to_market(0.5, 0.5, 0.35) - 0.5) < 1e-9


def test_trust_is_cut_for_thin_data_and_shrink():
    cfg = nba.CONFIG
    full = engine.effective_trust(cfg, "ml", 20, "stands")
    assert full == cfg.trust["ml"]
    assert engine.effective_trust(cfg, "ml", 3, "stands") < full
    assert abs(engine.effective_trust(cfg, "ml", 20, "shrink") - full * cfg.shrink_factor) < 1e-9


def test_no_bet_below_minimum_edge_and_no_stake_floor():
    cfg = nba.CONFIG
    base = {"ask": 0.50, "bid": 0.48, "size": 500}
    assert engine.size_trade(cfg, {**base, "p": 0.52}) is None          # 2 points before fees: no bet
    small = engine.size_trade(cfg, {**base, "p": 0.55})
    assert small and small["edge"] >= cfg.min_edge_trade
    assert small["cost"] < 0.5 * cfg.unit * 4                           # sized by Kelly, not lifted to a floor
    big = engine.size_trade(cfg, {**base, "p": 0.90})
    assert big["cost"] <= cfg.max_units_trade * cfg.unit + 1e-9         # capped
    assert abs(small["edge"] - (0.55 - small["cost"] / small["n"])) < 1e-9  # edge uses the exact fee for the order


def test_candidates_need_a_checked_forecast_and_a_clean_market():
    cfg = nba.CONFIG
    m = {"yes_ask": 0.50, "yes_bid": 0.47, "yes_ask_size": 100, "no_ask": 0.53, "no_bid": 0.50, "no_ask_size": 100}
    row = {"m": m, "mtype": "spread", "p_trade": None, "p_kalshi": 0.485}
    assert engine.candidates(cfg, [row]) == []                           # no forecast, no pick
    assert len(engine.candidates(cfg, [{**row, "p_trade": 0.56}])) == 2
    wide = {**m, "yes_bid": 0.30, "no_ask": 0.70, "no_bid": 0.50}
    assert [c["side"] for c in engine.candidates(cfg, [{"m": wide, "mtype": "spread", "p_trade": 0.56}])] == []


def test_pull_needs_a_clear_margin_or_a_dropped_forecast():
    cfg = nba.CONFIG
    t = {"contracts": 20}
    assert engine.should_pull(cfg, t, 0.52, 0.51, "stands") is None      # a cent or two is noise
    assert engine.should_pull(cfg, t, 0.60, 0.50, "stands")
    assert engine.should_pull(cfg, t, 0.40, 0.50, "drop")
    assert engine.should_pull(cfg, t, 0.0, 0.50, "drop") is None         # nothing to sell into


def test_blind_forecast_rules():
    from core import forecast
    cfg = nba.CONFIG
    sheet = {"stats_forecast": {"home_margin": 4.0, "total": 220.0}}
    soft = [{"type": "soft_judgment", "points": 6, "text": "hunch"}]
    stat = [{"type": "stat_read", "points": 6, "text": "numbers"}]
    assert forecast.validate_blind(cfg, sheet, 4.2, 220, []) is None
    assert forecast.validate_blind(cfg, sheet, 6.0, 220, [])             # a departure needs a reason
    assert forecast.validate_blind(cfg, sheet, 10.0, 220, soft)          # soft judgment alone is capped
    assert forecast.validate_blind(cfg, sheet, 10.0, 220, stat) is None


def test_first_blind_forecast_is_kept_and_checks_stay_separate():
    from core import forecast
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "forecasts.jsonl")
        append_jsonl(path, [{"type": "check", "game_id": "g1", "outcome": "stands"},   # a check with no forecast is ignored
                            {"type": "blind", "game_id": "g1", "margin": 3.0, "ts": "a"},
                            {"type": "blind", "game_id": "g1", "margin": 9.0, "ts": "b"},
                            {"type": "check", "game_id": "g1", "outcome": "shrink"},
                            {"type": "check", "game_id": "g1", "outcome": "drop"}])
        got = forecast.latest(path)["g1"]
        assert got["blind"]["margin"] == 3.0 and got["check"]["outcome"] == "drop"


def test_scorecard_counts_open_stake_and_keeps_versions_apart():
    trades = [{"id": "a", "cost": 10.0, "edge": 0.05, "p_final": 0.55, "settle": None, "version": "v2.0"},
              {"id": "b", "cost": 7.0, "edge": 0.07, "p_final": 0.6, "settle": None}]
    s = report.trade_stats(trades)
    assert s["open_stake"] == 17.0 and s["staked"] == 0
    assert report.version(trades[0]) == "v2.0" and report.version(trades[1]) == "v1"
    pulled = [{"id": "c", "cost": 10.0, "edge": 0.05, "p_final": 0.55, "version": "v2.0",
               "settle": {"outcome": "pulled", "pnl": 1.0, "clv": 0.2}}]
    assert report.trade_stats(pulled)["clv_n"] == 0                      # an exit is not a closing price


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
