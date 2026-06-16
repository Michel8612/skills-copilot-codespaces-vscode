"""Database models for the funding domain (SQLModel / SQLite).

Design principle — honesty by construction:
  * Plans carry their rules openly (`published=True` makes them publicly visible).
  * An account freezes the plan's rules at creation (rule_snapshot) so they can
    never be changed mid-evaluation.
  * Evaluation is delegated to the same deterministic challenge engine used in
    backtests, so every trader gets the same auditable verdict.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class BusinessLine(str, Enum):
    funding = "funding"            # our own prop firm
    bot_sale = "bot_sale"          # selling the bot as a product
    pass_service = "pass_service"  # passing challenges for clients


class AccountStatus(str, Enum):
    evaluation = "evaluation"  # in progress / not yet passed
    passed = "passed"          # met the target within the rules
    failed = "failed"          # breached a rule
    funded = "funded"          # passed and promoted to a funded account


class Plan(SQLModel, table=True):
    """A funding plan: account size, price, profit split and transparent rules."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    line: BusinessLine = BusinessLine.funding
    market: str = "forex"
    account_size: float = 100_000.0
    price: float = 0.0
    profit_split_pct: float = 80.0  # share of profit the trader keeps (honest, public)
    published: bool = True

    # Transparent challenge rules (mirror ChallengeConfig).
    profit_target_pct: float = 8.0
    max_daily_loss_pct: float = 5.0
    max_total_drawdown_pct: float = 10.0
    drawdown_mode: str = "static"
    min_trading_days: int = 4
    max_calendar_days: int = 30


class Trader(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(index=True)
    hashed_password: Optional[str] = None  # set when the trader registers with a password
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuthToken(SQLModel, table=True):
    """An opaque session token mapping to a trader (created on login)."""

    token: str = Field(primary_key=True)
    trader_id: int = Field(foreign_key="trader.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Account(SQLModel, table=True):
    """A trader's evaluation/funded account against a plan."""

    id: Optional[int] = Field(default=None, primary_key=True)
    trader_id: int = Field(foreign_key="trader.id", index=True)
    plan_id: int = Field(foreign_key="plan.id", index=True)
    line: BusinessLine = BusinessLine.funding
    status: AccountStatus = AccountStatus.evaluation
    starting_balance: float = 0.0

    # Filled after an evaluation run.
    final_equity: Optional[float] = None
    return_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    breached_rule: Optional[str] = None
    breach_detail: Optional[str] = None
    evaluated_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Payout(SQLModel, table=True):
    """A profit distribution on a funded account (transparent split)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="account.id", index=True)
    gross_profit: float
    trader_share: float
    company_share: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Línea de negocio: VENTA DEL BOT -------------------------------------------


class LicenseStatus(str, Enum):
    active = "active"
    cancelled = "cancelled"
    expired = "expired"


class BillingPeriod(str, Enum):
    monthly = "monthly"
    yearly = "yearly"
    one_time = "one_time"


class LicenseTier(SQLModel, table=True):
    """A product tier for the bot-sale line (its own rules: límites de uso)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float = 0.0
    period: BillingPeriod = BillingPeriod.monthly
    max_accounts: int = 1            # cuántas cuentas puede operar a la vez
    markets: str = "forex,futures,crypto"  # mercados permitidos (csv)
    published: bool = True


class License(SQLModel, table=True):
    """A customer's active subscription to a LicenseTier."""

    id: Optional[int] = Field(default=None, primary_key=True)
    trader_id: int = Field(foreign_key="trader.id", index=True)
    tier_id: int = Field(foreign_key="licensetier.id", index=True)
    status: LicenseStatus = LicenseStatus.active
    started_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


# --- Línea de negocio: SERVICIO DE PASE ----------------------------------------


class PassStatus(str, Enum):
    queued = "queued"
    passed = "passed"
    failed = "failed"
    refunded = "refunded"


class PassOrder(SQLModel, table=True):
    """An order to pass a challenge (a funding Plan) on behalf of a client.

    Honest by design: a transparent price, a capped number of attempts, and an
    explicit refund path — never a promise of approval.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    trader_id: int = Field(foreign_key="trader.id", index=True)
    plan_id: int = Field(foreign_key="plan.id", index=True)
    price: float = 0.0
    status: PassStatus = PassStatus.queued
    attempts: int = 0
    max_attempts: int = 3        # reintentos honestos incluidos en el precio
    last_detail: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
