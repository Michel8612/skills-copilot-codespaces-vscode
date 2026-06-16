"""Tests for the oracle integration point and the oracle-gated strategy."""

from app.engine.backtest import run_backtest
from app.engine.data import Bar, default_provider
from app.engine.oracle import MockOracle, NeutralOracle, build_oracle
from app.engine.strategies import STRATEGY_REGISTRY, build_strategy, strategy_param_grid


def test_oracle_registry_and_bias_range():
    neutral = build_oracle("neutral")
    assert isinstance(neutral, NeutralOracle)
    bars = default_provider.get_bars("crypto", "BTC", "4h", 300)
    mock = MockOracle(window=50)
    b = mock.bias(bars)
    assert -1.0 <= b <= 1.0
    assert neutral.bias(bars) == 0.0


def test_mock_oracle_sign_follows_trend():
    up = [Bar(time=None, open=p, high=p, low=p, close=p, volume=1) for p in range(1, 120)]
    down = [Bar(time=None, open=p, high=p, low=p, close=p, volume=1) for p in range(120, 1, -1)]
    assert MockOracle(window=50).bias(up) > 0
    assert MockOracle(window=50).bias(down) < 0


def test_oracle_gated_strategy_registered_and_runs():
    assert "oracle_trend_rsi" in STRATEGY_REGISTRY
    bars = default_provider.get_bars("crypto", "BTC", "4h", 1200)
    strat = build_strategy("oracle_trend_rsi")
    bt = run_backtest(bars, strat, account_size=100_000, leverage=2)
    assert len(bt.equity_curve) == 1200
    for params in strategy_param_grid("oracle_trend_rsi"):
        build_strategy("oracle_trend_rsi", params)


def test_neutral_oracle_gates_out_all_trades():
    bars = default_provider.get_bars("crypto", "BTC", "4h", 1200)
    strat = build_strategy("oracle_trend_rsi", {"oracle": "neutral"})
    # Neutral oracle never confirms, so no position is ever taken.
    assert all(strat.target_position(bars[: i + 1]) == 0 for i in range(0, len(bars), 50))
