"""Tests for the edge-validation harness."""

from app.engine.backtest import run_backtest
from app.engine.data import default_provider
from app.engine.strategies import build_strategy
from app.engine.validation import (
    compute_metrics,
    edge_verdict,
    monte_carlo,
    walk_forward,
)
from app.schemas import ValidateRequest
from app.service import validate_edge


def _backtest(market="crypto", bars=1500, strat="breakout"):
    data = default_provider.get_bars(market, "TEST", "4h", bars)
    strategy = build_strategy(strat, {"lookback": 15})
    return run_backtest(data, strategy, account_size=100_000, leverage=3), strategy, data


def test_metrics_have_expected_keys():
    bt, _, _ = _backtest()
    m = compute_metrics(bt, "4h")
    for k in ["sharpe", "sortino", "profit_factor", "expectancy", "win_rate_pct", "num_trades"]:
        assert k in m
    assert m["num_trades"] >= 0


def test_walk_forward_reports_folds():
    bt, strat, data = _backtest()
    wf = walk_forward(data, strat, 100_000, 3, folds=4)
    assert wf["folds"] >= 2
    assert len(wf["fold_returns_pct"]) == wf["folds"]
    assert 0 <= wf["pct_folds_profitable"] <= 100


def test_monte_carlo_distribution_is_ordered():
    bt, _, _ = _backtest(bars=2000)
    mc = monte_carlo(bt, 100_000, runs=500)
    if mc["runs"]:  # enough trades
        assert mc["return_p05_pct"] <= mc["return_median_pct"] <= mc["return_p95_pct"]
        assert 0 <= mc["prob_profit_pct"] <= 100
        assert 0 <= mc["prob_dd_breach_pct"] <= 100


def test_monte_carlo_handles_too_few_trades():
    data = default_provider.get_bars("forex", "X", "1d", 60)
    bt = run_backtest(data, build_strategy("ma_crossover", {"fast": 20, "slow": 50}), leverage=1)
    mc = monte_carlo(bt, 100_000, runs=100)
    assert mc["runs"] == 0  # falls back gracefully


def test_edge_verdict_labels():
    good = edge_verdict(
        {"expectancy": 50, "profit_factor": 1.5, "sharpe": 1.0},
        {"pct_folds_profitable": 75},
        {"runs": 1000, "prob_profit_pct": 70},
    )
    assert good["label"] == "edge_prometedor"
    bad = edge_verdict(
        {"expectancy": -10, "profit_factor": 0.8, "sharpe": -0.2},
        {"pct_folds_profitable": 20},
        {"runs": 1000, "prob_profit_pct": 30},
    )
    assert bad["label"] == "sin_evidencia"


def test_validate_edge_end_to_end():
    out = validate_edge(ValidateRequest(market="crypto", symbol="TEST", bars=1500, mc_runs=500))
    assert "verdict" in out and out["verdict"]["label"] in {"edge_prometedor", "edge_debil", "sin_evidencia"}
    assert "metrics" in out and "walk_forward" in out and "monte_carlo" in out
