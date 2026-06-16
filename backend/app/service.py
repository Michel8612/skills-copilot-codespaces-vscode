"""Application service: ties data + strategy + backtest + challenge together."""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from .engine.backtest import run_backtest
from .engine.challenge import PRESETS, ChallengeConfig, evaluate_challenge
from .engine.data import get_data_provider
from .engine.strategies import build_strategy
from .schemas import RunRequest


def _resolve_challenge(req: RunRequest) -> ChallengeConfig:
    if req.preset:
        if req.preset not in PRESETS:
            raise ValueError(f"Unknown preset '{req.preset}'. Options: {list(PRESETS)}")
        return PRESETS[req.preset]
    if req.challenge:
        return ChallengeConfig(**req.challenge.model_dump())
    return ChallengeConfig()


def run_pipeline(req: RunRequest) -> Dict:
    """Run a full backtest and evaluate it against a challenge."""
    config = _resolve_challenge(req)

    provider = get_data_provider(req.source)
    bars = provider.get_bars(req.market, req.symbol, req.timeframe, req.bars)
    strategy = build_strategy(req.strategy, req.strategy_params)
    bt = run_backtest(bars, strategy, account_size=config.account_size, leverage=req.leverage)

    # Trading days with activity = distinct dates on which a trade was opened.
    active_days = {t.entry_time.date() for t in bt.trades}
    challenge = evaluate_challenge(bt.equity_curve, config, trading_days_with_activity=len(active_days))

    return {
        "request": req.model_dump(),
        "challenge_config": asdict(config),
        "backtest": bt.to_dict(),
        "challenge": challenge.to_dict(),
    }
