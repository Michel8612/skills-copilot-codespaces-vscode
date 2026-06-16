"""Tests for the funding domain — uses an isolated in-memory database."""

import pytest
from sqlmodel import Session

from app.fondeo import service
from app.fondeo.db import init_db, make_engine
from app.fondeo.models import AccountStatus, BusinessLine


@pytest.fixture()
def session():
    engine = make_engine("sqlite://")  # shared in-memory DB
    init_db(engine)
    with Session(engine) as s:
        yield s


def test_seed_creates_published_plans(session):
    added = service.seed_default_plans(session)
    assert added == 3
    plans = service.list_plans(session)
    assert len(plans) == 3
    assert all(p.published for p in plans)
    # Seeding again is idempotent.
    assert service.seed_default_plans(session) == 0


def test_full_funding_flow_pass_and_payout(session):
    # A permissive plan so the bot's run passes deterministically.
    from app.fondeo.models import Plan

    # Forex + leverage 1 keeps moves tiny; profit_target 0% is met at the first
    # bar and the loose risk limits are never breached → a deterministic pass.
    plan = service.create_plan(session, Plan(
        name="Test Easy", market="forex", account_size=10_000, price=0,
        profit_split_pct=80, profit_target_pct=0.0, max_daily_loss_pct=99,
        max_total_drawdown_pct=99, drawdown_mode="static", min_trading_days=0,
        max_calendar_days=0,
    ))
    trader = service.register_trader(session, "Ada", "ada@example.com")
    account = service.open_account(session, trader.id, plan.id)
    assert account.status == AccountStatus.evaluation
    assert account.line == BusinessLine.funding

    result = service.evaluate_account(session, account.id, bars=600, leverage=1)
    # profit_target 0% means any run reaches the target → passes.
    assert result["verdict"]["status"] == "passed"
    assert result["account"]["status"] == "passed"

    funded = service.fund_account(session, account.id)
    assert funded.status == AccountStatus.funded

    payout = service.record_payout(session, account.id, gross_profit=1000)
    assert payout.trader_share == 800.0   # 80% split, honest and public
    assert payout.company_share == 200.0


def test_cannot_fund_unpassed_account(session):
    from app.fondeo.models import Plan

    plan = service.create_plan(session, Plan(
        name="Hard", market="forex", account_size=100_000, price=0,
        profit_target_pct=99, max_daily_loss_pct=1, max_total_drawdown_pct=1,
        drawdown_mode="static", min_trading_days=99, max_calendar_days=1,
    ))
    trader = service.register_trader(session, "Bob", "bob@example.com")
    account = service.open_account(session, trader.id, plan.id)
    service.evaluate_account(session, account.id, bars=600)
    with pytest.raises(ValueError):
        service.fund_account(session, account.id)


def test_open_account_rejects_unknown_ids(session):
    with pytest.raises(ValueError):
        service.open_account(session, 999, 999)
