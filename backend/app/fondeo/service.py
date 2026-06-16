"""Business logic for the funding domain.

Every evaluation runs through the SAME deterministic challenge engine used for
backtests — so the verdict is reproducible and auditable for every trader.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from sqlmodel import Session, select

from ..engine.backtest import run_backtest
from ..engine.challenge import ChallengeConfig, evaluate_challenge
from ..engine.data import default_provider
from ..engine.strategies import build_strategy
from .models import Account, AccountStatus, BusinessLine, Payout, Plan, Trader

# Honest, transparent default plans — published and identical for everyone.
DEFAULT_PLANS = [
    Plan(name="Forex 100K · 2 Fases", line=BusinessLine.funding, market="forex",
         account_size=100_000, price=499, profit_split_pct=80,
         profit_target_pct=8, max_daily_loss_pct=5, max_total_drawdown_pct=10,
         drawdown_mode="static", min_trading_days=4, max_calendar_days=30),
    Plan(name="Futuros 50K · 1 Fase", line=BusinessLine.funding, market="futures",
         account_size=50_000, price=299, profit_split_pct=85,
         profit_target_pct=6, max_daily_loss_pct=4, max_total_drawdown_pct=6,
         drawdown_mode="trailing", min_trading_days=1, max_calendar_days=0),
    Plan(name="Crypto 25K · 1 Fase", line=BusinessLine.funding, market="crypto",
         account_size=25_000, price=199, profit_split_pct=80,
         profit_target_pct=10, max_daily_loss_pct=5, max_total_drawdown_pct=8,
         drawdown_mode="trailing", min_trading_days=3, max_calendar_days=0),
]


def seed_default_plans(session: Session) -> int:
    """Insert the default published plans if the table is empty. Returns count added."""
    existing = session.exec(select(Plan)).first()
    if existing is not None:
        return 0
    for plan in DEFAULT_PLANS:
        session.add(Plan(**plan.model_dump(exclude={"id"})))
    session.commit()
    return len(DEFAULT_PLANS)


def list_plans(session: Session, only_published: bool = True) -> List[Plan]:
    stmt = select(Plan)
    if only_published:
        stmt = stmt.where(Plan.published == True)  # noqa: E712
    return list(session.exec(stmt))


def create_plan(session: Session, plan: Plan) -> Plan:
    plan.id = None
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def register_trader(session: Session, name: str, email: str) -> Trader:
    trader = Trader(name=name, email=email)
    session.add(trader)
    session.commit()
    session.refresh(trader)
    return trader


def open_account(session: Session, trader_id: int, plan_id: int) -> Account:
    plan = session.get(Plan, plan_id)
    trader = session.get(Trader, trader_id)
    if plan is None or trader is None:
        raise ValueError("Plan o trader inexistente")
    account = Account(
        trader_id=trader_id,
        plan_id=plan_id,
        line=plan.line,
        status=AccountStatus.evaluation,
        starting_balance=plan.account_size,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def _plan_to_config(plan: Plan) -> ChallengeConfig:
    return ChallengeConfig(
        name=plan.name,
        account_size=plan.account_size,
        profit_target_pct=plan.profit_target_pct,
        max_daily_loss_pct=plan.max_daily_loss_pct,
        max_total_drawdown_pct=plan.max_total_drawdown_pct,
        drawdown_mode=plan.drawdown_mode,
        min_trading_days=plan.min_trading_days,
        max_calendar_days=plan.max_calendar_days,
    )


def evaluate_account(
    session: Session,
    account_id: int,
    strategy: str = "breakout",
    strategy_params: Optional[Dict] = None,
    symbol: str = "AUTO",
    timeframe: str = "4h",
    bars: int = 1200,
    leverage: float = 10.0,
) -> Dict:
    """Run the bot on the account's plan and apply the (frozen) challenge rules."""
    account = session.get(Account, account_id)
    if account is None:
        raise ValueError("Cuenta inexistente")
    plan = session.get(Plan, account.plan_id)
    config = _plan_to_config(plan)

    bars_data = default_provider.get_bars(plan.market, symbol, timeframe, bars)
    strat = build_strategy(strategy, strategy_params or {})
    bt = run_backtest(bars_data, strat, account_size=plan.account_size, leverage=leverage)
    active_days = {t.entry_time.date() for t in bt.trades}
    verdict = evaluate_challenge(bt.equity_curve, config, trading_days_with_activity=len(active_days))

    # Map the engine verdict onto the account.
    status_map = {
        "passed": AccountStatus.passed,
        "failed": AccountStatus.failed,
        "in_progress": AccountStatus.evaluation,
    }
    account.status = status_map[verdict.status]
    account.final_equity = bt.final_equity
    account.return_pct = bt.stats["total_return_pct"]
    account.max_drawdown_pct = bt.stats["max_drawdown_pct"]
    account.breached_rule = verdict.breached_rule
    account.breach_detail = verdict.breach_detail
    account.evaluated_at = datetime.utcnow()
    session.add(account)
    session.commit()
    session.refresh(account)

    return {
        "account": account.model_dump(),
        "verdict": verdict.to_dict(),
        "backtest_stats": bt.stats,
    }


def fund_account(session: Session, account_id: int) -> Account:
    """Promote a passed evaluation account to a funded account."""
    account = session.get(Account, account_id)
    if account is None:
        raise ValueError("Cuenta inexistente")
    if account.status != AccountStatus.passed:
        raise ValueError("Solo se pueden financiar cuentas que han pasado la evaluación")
    account.status = AccountStatus.funded
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def record_payout(session: Session, account_id: int, gross_profit: float) -> Payout:
    """Split a funded account's profit transparently per the plan's profit_split."""
    account = session.get(Account, account_id)
    if account is None or account.status != AccountStatus.funded:
        raise ValueError("La cuenta debe estar financiada para repartir beneficios")
    if gross_profit <= 0:
        raise ValueError("El beneficio a repartir debe ser positivo")
    plan = session.get(Plan, account.plan_id)
    trader_share = round(gross_profit * plan.profit_split_pct / 100, 2)
    payout = Payout(
        account_id=account_id,
        gross_profit=round(gross_profit, 2),
        trader_share=trader_share,
        company_share=round(gross_profit - trader_share, 2),
    )
    session.add(payout)
    session.commit()
    session.refresh(payout)
    return payout


def list_accounts(session: Session) -> List[Account]:
    return list(session.exec(select(Account)))
