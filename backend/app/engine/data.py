"""Market data providers.

For the MVP we generate deterministic synthetic OHLCV data so the whole
system runs offline, without API keys. Each market (forex / futures / crypto)
has slightly different volatility and price characteristics. Real providers
(MetaTrader, Rithmic, Binance, ...) can later implement the same `MarketDataProvider`
interface without touching the rest of the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

import numpy as np


@dataclass
class Bar:
    """A single OHLCV candle."""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


# Per-market characteristics used by the synthetic generator.
MARKET_PROFILES = {
    "forex": {"start_price": 1.10, "annual_vol": 0.08, "drift": 0.0},
    "futures": {"start_price": 18000.0, "annual_vol": 0.18, "drift": 0.05},
    "crypto": {"start_price": 42000.0, "annual_vol": 0.65, "drift": 0.10},
}

# Approximate number of bars per year for a few timeframes (used to scale vol).
_BARS_PER_YEAR = {
    "1h": 24 * 365,
    "4h": 6 * 365,
    "1d": 365,
}

_TIMEFRAME_DELTA = {
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
}


def supported_markets() -> List[str]:
    return list(MARKET_PROFILES.keys())


def supported_timeframes() -> List[str]:
    return list(_TIMEFRAME_DELTA.keys())


class MarketDataProvider:
    """Interface every data source must implement."""

    def get_bars(self, market: str, symbol: str, timeframe: str, bars: int) -> List[Bar]:
        raise NotImplementedError


class SyntheticDataProvider(MarketDataProvider):
    """Deterministic geometric-brownian-motion OHLCV generator.

    Deterministic per (market, symbol, timeframe, bars) seed so that backtests
    are reproducible — essential when you need to *verify* a strategy works.
    """

    def __init__(self, start_time: datetime | None = None):
        self.start_time = start_time or datetime(2023, 1, 1)

    def get_bars(self, market: str, symbol: str, timeframe: str, bars: int) -> List[Bar]:
        if market not in MARKET_PROFILES:
            raise ValueError(f"Unknown market '{market}'. Options: {supported_markets()}")
        if timeframe not in _TIMEFRAME_DELTA:
            raise ValueError(f"Unknown timeframe '{timeframe}'. Options: {supported_timeframes()}")
        if bars <= 0:
            raise ValueError("bars must be positive")

        profile = MARKET_PROFILES[market]
        seed = abs(hash((market, symbol, timeframe, bars))) % (2**32)
        rng = np.random.default_rng(seed)

        bars_per_year = _BARS_PER_YEAR[timeframe]
        dt = 1.0 / bars_per_year
        vol = profile["annual_vol"]
        drift = profile["drift"]

        # GBM log-returns.
        shocks = rng.normal(
            loc=(drift - 0.5 * vol**2) * dt,
            scale=vol * np.sqrt(dt),
            size=bars,
        )
        closes = profile["start_price"] * np.exp(np.cumsum(shocks))

        delta = _TIMEFRAME_DELTA[timeframe]
        result: List[Bar] = []
        prev_close = profile["start_price"]
        for i in range(bars):
            close = float(closes[i])
            open_ = prev_close
            # Intrabar range proportional to the bar's move.
            spread = abs(close - open_) + open_ * vol * np.sqrt(dt) * 0.5
            high = max(open_, close) + abs(rng.normal(0, spread * 0.5))
            low = min(open_, close) - abs(rng.normal(0, spread * 0.5))
            volume = float(abs(rng.normal(1000, 250)))
            result.append(
                Bar(
                    time=self.start_time + delta * i,
                    open=round(open_, 6),
                    high=round(high, 6),
                    low=round(low, 6),
                    close=round(close, 6),
                    volume=round(volume, 2),
                )
            )
            prev_close = close
        return result


# Default provider instance used across the app.
default_provider = SyntheticDataProvider()
