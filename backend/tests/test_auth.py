"""Tests for client-panel authentication and history (in-memory DB)."""

import pytest
from sqlmodel import Session

from app.fondeo import auth, lines, service
from app.fondeo.db import init_db, make_engine
from app.fondeo.models import Plan


@pytest.fixture()
def session():
    engine = make_engine("sqlite://")
    init_db(engine)
    with Session(engine) as s:
        yield s


def test_password_hash_roundtrip():
    h = auth.hash_password("secret123")
    assert "$" in h
    assert auth.verify_password("secret123", h)
    assert not auth.verify_password("wrong", h)


def test_register_and_login(session):
    trader = auth.register_user(session, "Ada", "Ada@Example.com", "secret123")
    assert trader.email == "ada@example.com"  # normalized
    token = auth.login(session, "ada@example.com", "secret123")
    assert auth.trader_for_token(session, token).id == trader.id


def test_login_rejects_bad_credentials(session):
    auth.register_user(session, "Ada", "ada@x.com", "secret123")
    with pytest.raises(ValueError):
        auth.login(session, "ada@x.com", "nope")


def test_duplicate_email_and_short_password(session):
    auth.register_user(session, "Ada", "ada@x.com", "secret123")
    with pytest.raises(ValueError):
        auth.register_user(session, "Ada2", "ada@x.com", "secret123")
    with pytest.raises(ValueError):
        auth.register_user(session, "Bob", "bob@x.com", "123")


def test_logout_invalidates_token(session):
    auth.register_user(session, "Ada", "ada@x.com", "secret123")
    token = auth.login(session, "ada@x.com", "secret123")
    auth.logout(session, token)
    assert auth.trader_for_token(session, token) is None


def test_history_aggregates_activity(session):
    trader = auth.register_user(session, "Ada", "ada@x.com", "secret123")
    plan = service.create_plan(session, Plan(name="P", market="forex", account_size=10_000))
    service.open_account(session, trader.id, plan.id)
    lines.seed_default_tiers(session)
    tier = lines.list_tiers(session)[0]
    lines.buy_license(session, trader.id, tier.id)
    lines.create_pass_order(session, trader.id, plan.id)

    history = auth.trader_history(session, trader.id)
    assert len(history["accounts"]) == 1
    assert len(history["licenses"]) == 1
    assert len(history["pass_orders"]) == 1
