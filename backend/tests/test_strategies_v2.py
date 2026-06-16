"""Tests for trend-filtered strategies and the consistency rule."""

from datetime import datetime, timedelta

from app.engine.backtest import EquityPoint, run_backtest
from app.engine.challenge import ChallengeConfig, evaluate_challenge
from app.engine.data import default_provider
from app.engine.strategies import STRATEGY_REGISTRY, build_strategy, strategy_param_grid


def test_trend_strategies_registered_and_trade():
    for name in ("trend_breakout", "trend_rsi"):
        assert name in STRATEGY_REGISTRY
        bars = default_provider.get_bars("crypto", "BTC", "4h", 1500)
        bt = run_backtest(bars, build_strategy(name), account_size=100_000, leverage=2)
        assert len(bt.equity_curve) == 1500
        # Valid param grids.
        for params in strategy_param_grid(name):
            build_strategy(name, params)


def _curve(daily_equities, start=datetime(2023, 1, 1)):
    """One point per day with given end-of-day equity (high=low=close)."""
    return [
        EquityPoint(time=start + timedelta(days=i), equity=v, equity_high=v, equity_low=v)
        for i, v in enumerate(daily_equities)
    ]


def test_consistency_rule_withholds_pass_when_one_day_dominates():
    cfg = ChallengeConfig(
        account_size=100_000, profit_target_pct=5, min_trading_days=3,
        max_daily_loss_pct=90, max_total_drawdown_pct=90, max_calendar_days=0,
        max_single_day_profit_pct=40,
    )
    # Total profit 6000; one day contributes 5500 (>40%) -> consistency breach.
    curve = _curve([100_000, 100_300, 105_800, 106_000])
    res = evaluate_challenge(curve, cfg, trading_days_with_activity=4)
    assert res.status == "in_progress"
    assert "consistencia" in (res.breach_detail or "").lower()


def test_consistency_rule_passes_when_balanced():
    cfg = ChallengeConfig(
        account_size=100_000, profit_target_pct=5, min_trading_days=3,
        max_daily_loss_pct=90, max_total_drawdown_pct=90, max_calendar_days=0,
        max_single_day_profit_pct=60,
    )
    # Profit spread across days; best day well under 60% of total.
    curve = _curve([100_000, 102_000, 104_000, 106_000])
    res = evaluate_challenge(curve, cfg, trading_days_with_activity=4)
    assert res.status == "passed"


def test_consistency_disabled_by_default():
    cfg = ChallengeConfig(
        account_size=100_000, profit_target_pct=5, min_trading_days=1,
        max_daily_loss_pct=90, max_total_drawdown_pct=90, max_calendar_days=0,
    )
    curve = _curve([100_000, 106_000])  # one big day, but rule disabled (0)
    res = evaluate_challenge(curve, cfg, trading_days_with_activity=2)
    assert res.status == "passed"
