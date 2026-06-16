"""Tests for the prop-firm challenge rules engine."""

from datetime import datetime, timedelta

from app.engine.backtest import EquityPoint
from app.engine.challenge import ChallengeConfig, evaluate_challenge


def make_curve(values, start=datetime(2023, 1, 1), step=timedelta(days=1)):
    """Build an equity curve where each value is the bar close (high=low=close)."""
    return [
        EquityPoint(time=start + step * i, equity=v, equity_high=v, equity_low=v)
        for i, v in enumerate(values)
    ]


def test_passes_when_target_hit_with_enough_days():
    cfg = ChallengeConfig(account_size=100_000, profit_target_pct=8, min_trading_days=3,
                          max_daily_loss_pct=50, max_total_drawdown_pct=50, max_calendar_days=0)
    curve = make_curve([100_000, 102_000, 104_000, 106_000, 109_000])
    res = evaluate_challenge(curve, cfg, trading_days_with_activity=5)
    assert res.status == "passed"
    assert res.pass_time is not None


def test_in_progress_when_target_hit_but_too_few_days():
    cfg = ChallengeConfig(account_size=100_000, profit_target_pct=8, min_trading_days=10,
                          max_daily_loss_pct=50, max_total_drawdown_pct=50, max_calendar_days=0)
    curve = make_curve([100_000, 109_000])
    res = evaluate_challenge(curve, cfg, trading_days_with_activity=2)
    assert res.status == "in_progress"


def test_fails_on_total_drawdown_static():
    cfg = ChallengeConfig(account_size=100_000, profit_target_pct=8, drawdown_mode="static",
                          max_total_drawdown_pct=10, max_daily_loss_pct=50, max_calendar_days=0)
    # Drops below the 90,000 static floor.
    curve = make_curve([100_000, 95_000, 89_000])
    res = evaluate_challenge(curve, cfg)
    assert res.status == "failed"
    assert res.breached_rule == "max_total_drawdown"


def test_fails_on_trailing_drawdown():
    cfg = ChallengeConfig(account_size=100_000, profit_target_pct=20, drawdown_mode="trailing",
                          max_total_drawdown_pct=10, max_daily_loss_pct=50, max_calendar_days=0)
    # Peak 110k -> trailing floor 99k. Drop to 98k breaches.
    curve = make_curve([100_000, 110_000, 98_000])
    res = evaluate_challenge(curve, cfg)
    assert res.status == "failed"
    assert res.breached_rule == "max_total_drawdown"


def test_fails_on_daily_loss():
    cfg = ChallengeConfig(account_size=100_000, profit_target_pct=8, max_daily_loss_pct=5,
                          max_total_drawdown_pct=50, max_calendar_days=0)
    # Within a single day, equity drops 6k from the day's start.
    start = datetime(2023, 1, 2, 0, 0)
    curve = [
        EquityPoint(time=start, equity=100_000, equity_high=100_000, equity_low=100_000),
        EquityPoint(time=start + timedelta(hours=1), equity=94_000, equity_high=100_000, equity_low=94_000),
    ]
    res = evaluate_challenge(curve, cfg)
    assert res.status == "failed"
    assert res.breached_rule == "max_daily_loss"


def test_fails_on_calendar_limit():
    cfg = ChallengeConfig(account_size=100_000, profit_target_pct=8, max_calendar_days=5,
                          max_daily_loss_pct=50, max_total_drawdown_pct=50)
    curve = make_curve([100_000] * 8)  # 8 days > 5 day limit
    res = evaluate_challenge(curve, cfg)
    assert res.status == "failed"
    assert res.breached_rule == "max_calendar_days"


def test_drawdown_breach_takes_priority_over_late_profit():
    cfg = ChallengeConfig(account_size=100_000, profit_target_pct=8, drawdown_mode="static",
                          max_total_drawdown_pct=10, max_daily_loss_pct=50, max_calendar_days=0)
    # Breaches drawdown before ever reaching profit.
    curve = make_curve([100_000, 88_000, 120_000])
    res = evaluate_challenge(curve, cfg, trading_days_with_activity=3)
    assert res.status == "failed"
