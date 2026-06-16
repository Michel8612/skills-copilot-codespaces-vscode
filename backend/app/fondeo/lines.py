"""Business logic for the bot-sale and pass-service lines.

Both reuse the same auditable engine and database as the funding line, with
their own complementary rules (licence limits / honest pass guarantees).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlmodel import Session, select

from ..engine.backtest import run_backtest
from ..engine.challenge import evaluate_challenge
from ..engine.data import default_provider
from ..engine.strategies import build_strategy
from .models import (
    BillingPeriod,
    License,
    LicenseStatus,
    LicenseTier,
    PassOrder,
    PassStatus,
    Plan,
    Trader,
)
from .service import _plan_to_config

# ---------------------------------------------------------------------------
# Bot-sale line: licence tiers and subscriptions
# ---------------------------------------------------------------------------

DEFAULT_TIERS = [
    LicenseTier(name="Starter", price=49, period=BillingPeriod.monthly, max_accounts=1, markets="forex"),
    LicenseTier(name="Pro", price=99, period=BillingPeriod.monthly, max_accounts=3, markets="forex,futures,crypto"),
    LicenseTier(name="Lifetime", price=1499, period=BillingPeriod.one_time, max_accounts=10, markets="forex,futures,crypto"),
]

_PERIOD_DAYS = {BillingPeriod.monthly: 30, BillingPeriod.yearly: 365}


def seed_default_tiers(session: Session) -> int:
    if session.exec(select(LicenseTier)).first() is not None:
        return 0
    for tier in DEFAULT_TIERS:
        session.add(LicenseTier(**tier.model_dump(exclude={"id"})))
    session.commit()
    return len(DEFAULT_TIERS)


def list_tiers(session: Session) -> List[LicenseTier]:
    return list(session.exec(select(LicenseTier).where(LicenseTier.published == True)))  # noqa: E712


def buy_license(session: Session, trader_id: int, tier_id: int) -> License:
    tier = session.get(LicenseTier, tier_id)
    if tier is None:
        raise ValueError("Tier inexistente")
    expires_at = None
    if tier.period in _PERIOD_DAYS:
        expires_at = datetime.utcnow() + timedelta(days=_PERIOD_DAYS[tier.period])
    lic = License(trader_id=trader_id, tier_id=tier_id, expires_at=expires_at)
    session.add(lic)
    session.commit()
    session.refresh(lic)
    return lic


def cancel_license(session: Session, license_id: int) -> License:
    lic = session.get(License, license_id)
    if lic is None:
        raise ValueError("Licencia inexistente")
    lic.status = LicenseStatus.cancelled
    session.add(lic)
    session.commit()
    session.refresh(lic)
    return lic


def list_licenses(session: Session) -> List[License]:
    return list(session.exec(select(License)))


# ---------------------------------------------------------------------------
# Pass-service line: orders to pass a challenge on a client's behalf
# ---------------------------------------------------------------------------


def create_pass_order(
    session: Session, trader_id: int, plan_id: int, price: Optional[float] = None
) -> PassOrder:
    plan = session.get(Plan, plan_id)
    if plan is None or session.get(Trader, trader_id) is None:
        raise ValueError("Plan o trader inexistente")
    order = PassOrder(
        trader_id=trader_id,
        plan_id=plan_id,
        price=plan.price if price is None else price,
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def run_pass_attempt(
    session: Session,
    order_id: int,
    strategy: str = "breakout",
    strategy_params: Optional[Dict] = None,
    symbol: str = "AUTO",
    timeframe: str = "4h",
    bars: int = 1200,
    leverage: float = 3.0,
) -> Dict:
    """Run one honest attempt of the bot against the order's plan."""
    order = session.get(PassOrder, order_id)
    if order is None:
        raise ValueError("Orden inexistente")
    if order.status == PassStatus.passed:
        raise ValueError("La orden ya está aprobada")
    if order.attempts >= order.max_attempts:
        raise ValueError("Se agotaron los intentos incluidos; elegible a reembolso")

    plan = session.get(Plan, order.plan_id)
    config = _plan_to_config(plan)
    bars_data = default_provider.get_bars(plan.market, symbol, timeframe, bars)
    strat = build_strategy(strategy, strategy_params or {})
    bt = run_backtest(bars_data, strat, account_size=plan.account_size, leverage=leverage)
    active_days = {t.entry_time.date() for t in bt.trades}
    verdict = evaluate_challenge(bt.equity_curve, config, trading_days_with_activity=len(active_days))

    order.attempts += 1
    if verdict.status == "passed":
        order.status = PassStatus.passed
        order.last_detail = "Challenge superado."
    else:
        order.status = PassStatus.failed if order.attempts >= order.max_attempts else PassStatus.queued
        order.last_detail = verdict.breach_detail or "Objetivo no alcanzado en este intento."
    session.add(order)
    session.commit()
    session.refresh(order)
    return {"order": order.model_dump(), "verdict": verdict.to_dict()}


def refund_pass_order(session: Session, order_id: int) -> PassOrder:
    """Honest refund path: only when attempts are exhausted without passing."""
    order = session.get(PassOrder, order_id)
    if order is None:
        raise ValueError("Orden inexistente")
    if order.status == PassStatus.passed:
        raise ValueError("Una orden aprobada no es reembolsable")
    if order.attempts < order.max_attempts:
        raise ValueError("Aún quedan intentos incluidos antes de reembolsar")
    order.status = PassStatus.refunded
    order.last_detail = "Reembolsado tras agotar los intentos sin superar el challenge."
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


def list_pass_orders(session: Session) -> List[PassOrder]:
    return list(session.exec(select(PassOrder)))
