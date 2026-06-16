"""Tests for the new strategies and the parameter / walk-forward optimizer."""

from app.engine.backtest import run_backtest
from app.engine.data import default_provider
from app.engine.optimizer import grid_search, walk_forward_optimize
from app.engine.strategies import (
    STRATEGY_REGISTRY,
    build_strategy,
    strategy_param_grid,
)
from app.schemas import OptimizeRequest
from app.service import optimize


def test_new_strategies_registered():
    assert "rsi_reversion" in STRATEGY_REGISTRY
    assert "momentum" in STRATEGY_REGISTRY


def test_new_strategies_trade():
    bars = default_provider.get_bars("crypto", "BTC", "4h", 1500)
    for name in ("rsi_reversion", "momentum"):
        bt = run_backtest(bars, build_strategy(name), account_size=100_000, leverage=2)
        assert len(bt.equity_curve) == 1500
        assert bt.stats["num_trades"] >= 0


def test_param_grids_are_valid():
    for name, cls in STRATEGY_REGISTRY.items():
        grid = strategy_param_grid(name)
        assert isinstance(grid, list) and len(grid) >= 1
        # Every param set must build a usable strategy.
        for params in grid:
            build_strategy(name, params)
    # MA grid must only contain fast < slow.
    for p in strategy_param_grid("ma_crossover"):
        assert p["fast"] < p["slow"]


def test_grid_search_picks_best():
    bars = default_provider.get_bars("crypto", "BTC", "4h", 1500)
    gs = grid_search(bars, "breakout", metric="return", top=3)
    assert gs["best"] is not None
    assert gs["evaluated"] == len(strategy_param_grid("breakout"))
    # Sorted descending: first score >= last.
    assert gs["top"][0]["score"] >= gs["top"][-1]["score"]


def test_walk_forward_optimize_reports_efficiency():
    bars = default_provider.get_bars("crypto", "BTC", "4h", 2400)
    wfo = walk_forward_optimize(bars, "breakout", windows=4, metric="return")
    assert wfo["steps"] >= 2
    for w in wfo["windows"]:
        assert "in_sample_score" in w and "out_of_sample_score" in w
    assert "wfo_efficiency" in wfo
    assert 0 <= wfo["pct_oos_profitable"] <= 100


def test_optimize_service_end_to_end():
    out = optimize(OptimizeRequest(market="crypto", symbol="BTC", bars=2000, strategy="momentum", windows=4))
    assert out["grid_search"]["best"] is not None
    assert "walk_forward_optimization" in out
