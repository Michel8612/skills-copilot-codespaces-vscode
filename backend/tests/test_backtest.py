"""Tests for the data provider and backtester."""

from app.engine.backtest import run_backtest
from app.engine.data import default_provider, supported_markets
from app.engine.strategies import build_strategy


def test_synthetic_data_is_deterministic():
    a = default_provider.get_bars("crypto", "BTCUSD", "1h", 200)
    b = default_provider.get_bars("crypto", "BTCUSD", "1h", 200)
    assert len(a) == 200
    assert [x.close for x in a] == [x.close for x in b]


def test_bars_are_internally_consistent():
    bars = default_provider.get_bars("forex", "EURUSD", "1d", 100)
    for bar in bars:
        assert bar.high >= bar.open
        assert bar.high >= bar.close
        assert bar.low <= bar.open
        assert bar.low <= bar.close


def test_backtest_runs_on_every_market():
    for market in supported_markets():
        bars = default_provider.get_bars(market, "TEST", "1h", 500)
        strat = build_strategy("ma_crossover", {"fast": 5, "slow": 20})
        res = run_backtest(bars, strat, account_size=100_000)
        assert len(res.equity_curve) == 500
        assert res.stats["num_trades"] >= 0
        # final_equity is the last point's equity (a leveraged run may blow up —
        # that's a valid outcome the challenge engine flags as a drawdown breach).
        assert res.final_equity == res.equity_curve[-1].equity


def test_breakout_strategy_produces_trades():
    bars = default_provider.get_bars("crypto", "BTCUSD", "4h", 800)
    strat = build_strategy("breakout", {"lookback": 10})
    res = run_backtest(bars, strat, account_size=50_000)
    assert res.stats["num_trades"] > 0
