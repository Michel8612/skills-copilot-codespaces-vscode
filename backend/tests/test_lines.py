"""Tests for the bot-sale and pass-service business lines (in-memory DB)."""

import pytest
from sqlmodel import Session

from app.fondeo import lines, service
from app.fondeo.db import init_db, make_engine
from app.fondeo.models import LicenseStatus, PassStatus, Plan


@pytest.fixture()
def session():
    engine = make_engine("sqlite://")
    init_db(engine)
    with Session(engine) as s:
        yield s


# --- bot-sale ---------------------------------------------------------------


def test_seed_tiers_and_buy_license(session):
    assert lines.seed_default_tiers(session) == 3
    assert lines.seed_default_tiers(session) == 0  # idempotent
    tiers = lines.list_tiers(session)
    trader = service.register_trader(session, "Ada", "ada@x.com")

    monthly = next(t for t in tiers if t.period.value == "monthly")
    lic = lines.buy_license(session, trader.id, monthly.id)
    assert lic.status == LicenseStatus.active
    assert lic.expires_at is not None  # monthly => has expiry

    lifetime = next(t for t in tiers if t.period.value == "one_time")
    lic2 = lines.buy_license(session, trader.id, lifetime.id)
    assert lic2.expires_at is None  # one-time => no expiry

    cancelled = lines.cancel_license(session, lic.id)
    assert cancelled.status == LicenseStatus.cancelled


# --- pass-service -----------------------------------------------------------


def _easy_plan(session):
    return service.create_plan(session, Plan(
        name="Pase Easy", market="forex", account_size=10_000, price=150,
        profit_target_pct=0.0, max_daily_loss_pct=99, max_total_drawdown_pct=99,
        drawdown_mode="static", min_trading_days=0, max_calendar_days=0,
    ))


def test_pass_order_succeeds(session):
    plan = _easy_plan(session)
    trader = service.register_trader(session, "Ada", "ada@x.com")
    order = lines.create_pass_order(session, trader.id, plan.id)
    assert order.price == 150
    res = lines.run_pass_attempt(session, order.id, leverage=1)
    assert res["order"]["status"] == "passed"
    assert res["order"]["attempts"] == 1
    # A passed order can't be retried or refunded.
    with pytest.raises(ValueError):
        lines.refund_pass_order(session, order.id)


def test_pass_order_exhausts_attempts_then_refunds(session):
    # Impossible plan => every attempt fails.
    plan = service.create_plan(session, Plan(
        name="Imposible", market="forex", account_size=10_000, price=150,
        profit_target_pct=99, max_daily_loss_pct=1, max_total_drawdown_pct=1,
        drawdown_mode="static", min_trading_days=99, max_calendar_days=1,
    ))
    trader = service.register_trader(session, "Bob", "bob@x.com")
    order = lines.create_pass_order(session, trader.id, plan.id)
    for _ in range(order.max_attempts):
        lines.run_pass_attempt(session, order.id, leverage=1)
    refreshed = lines.list_pass_orders(session)[0]
    assert refreshed.status == PassStatus.failed
    assert refreshed.attempts == refreshed.max_attempts
    # No attempts left => honest refund path is available.
    refunded = lines.refund_pass_order(session, order.id)
    assert refunded.status == PassStatus.refunded


def test_pass_order_rejects_unknown(session):
    with pytest.raises(ValueError):
        lines.create_pass_order(session, 999, 999)
