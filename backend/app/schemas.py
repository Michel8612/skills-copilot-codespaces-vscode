"""Pydantic request/response models for the API."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ChallengeConfigSchema(BaseModel):
    name: str = "Custom Challenge"
    account_size: float = Field(100_000.0, gt=0)
    profit_target_pct: float = Field(8.0, ge=0)
    max_daily_loss_pct: float = Field(5.0, gt=0)
    max_total_drawdown_pct: float = Field(10.0, gt=0)
    drawdown_mode: str = "trailing"
    min_trading_days: int = Field(4, ge=0)
    max_calendar_days: int = Field(30, ge=0)


class RunRequest(BaseModel):
    market: str = "forex"
    symbol: str = "EURUSD"
    timeframe: str = "1h"
    bars: int = Field(1000, gt=10, le=20_000)
    strategy: str = "ma_crossover"
    strategy_params: Dict = Field(default_factory=dict)
    leverage: float = Field(10.0, gt=0, le=500)
    # Either reference a preset by key, or pass a full config. Preset wins if set.
    preset: Optional[str] = None
    challenge: Optional[ChallengeConfigSchema] = None


class RunResponse(BaseModel):
    request: RunRequest
    backtest: Dict
    challenge: Dict


class PresetInfo(BaseModel):
    key: str
    config: ChallengeConfigSchema
