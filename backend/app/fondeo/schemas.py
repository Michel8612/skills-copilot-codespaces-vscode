"""Request bodies for the funding API."""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class TraderCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)


class AccountOpen(BaseModel):
    trader_id: int
    plan_id: int


class AccountEvaluate(BaseModel):
    strategy: str = "breakout"
    strategy_params: Dict = Field(default_factory=dict)
    symbol: str = "AUTO"
    timeframe: str = "4h"
    bars: int = Field(1200, gt=10, le=20_000)
    leverage: float = Field(10.0, gt=0, le=500)


class PayoutCreate(BaseModel):
    gross_profit: float = Field(..., gt=0)


class PlanCreate(BaseModel):
    name: str
    market: str = "forex"
    account_size: float = 100_000.0
    price: float = 0.0
    profit_split_pct: float = 80.0
    profit_target_pct: float = 8.0
    max_daily_loss_pct: float = 5.0
    max_total_drawdown_pct: float = 10.0
    drawdown_mode: str = "static"
    min_trading_days: int = 4
    max_calendar_days: int = 30
    line: Optional[str] = "funding"
