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
    max_single_day_profit_pct: float = Field(0.0, ge=0)


class RunRequest(BaseModel):
    market: str = "forex"
    symbol: str = "EURUSD"
    timeframe: str = "1h"
    bars: int = Field(1000, gt=10, le=20_000)
    source: str = "synthetic"  # "synthetic" | "binance" (real crypto data)
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


class ValidateRequest(BaseModel):
    market: str = "crypto"
    symbol: str = "BTCUSDT"
    timeframe: str = "4h"
    bars: int = Field(2000, gt=100, le=20_000)
    source: str = "synthetic"
    strategy: str = "breakout"
    strategy_params: Dict = Field(default_factory=dict)
    leverage: float = Field(3.0, gt=0, le=500)
    account_size: float = Field(100_000.0, gt=0)
    folds: int = Field(4, ge=2, le=12)
    mc_runs: int = Field(2000, ge=100, le=20_000)
    dd_breach_pct: float = Field(10.0, gt=0)


class OptimizeRequest(BaseModel):
    market: str = "crypto"
    symbol: str = "BTCUSDT"
    timeframe: str = "4h"
    bars: int = Field(2000, gt=100, le=20_000)
    source: str = "synthetic"
    strategy: str = "breakout"
    leverage: float = Field(3.0, gt=0, le=500)
    account_size: float = Field(100_000.0, gt=0)
    metric: str = "sharpe"  # "sharpe" | "sortino" | "return"
    windows: int = Field(5, ge=2, le=12)


class PresetInfo(BaseModel):
    key: str
    config: ChallengeConfigSchema


class AgencyRequest(BaseModel):
    question: str = Field(..., min_length=3)
    max_agents: int = Field(4, ge=1, le=6)
    # Optionally run a backtest first and feed its results as context to the agents.
    run: Optional[RunRequest] = None
