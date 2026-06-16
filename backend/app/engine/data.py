"""Market data providers.

For the MVP we generate deterministic synthetic OHLCV data so the whole
system runs offline, without API keys. Each market (forex / futures / crypto)
has slightly different volatility and price characteristics. Real providers
(MetaTrader, Rithmic, Binance, ...) can later implement the same `MarketDataProvider`
interface without touching the rest of the engine.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
        # Stable seed across processes — Python's built-in hash() is salted per
        # run, which would make backtests non-reproducible. hashlib is stable.
        digest = hashlib.md5(f"{market}|{symbol}|{timeframe}|{bars}".encode()).digest()
        seed = int.from_bytes(digest[:4], "big")
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


# ---------------------------------------------------------------------------
# Real market data (crypto) via Binance public REST — no API key required.
# Works wherever outbound HTTPS to the host is allowed. Falls back with a clear
# error when the environment's network policy blocks it.
# ---------------------------------------------------------------------------

BINANCE_BASE = os.getenv("BINANCE_BASE_URL", "https://data-api.binance.vision")
_BINANCE_INTERVAL = {"1h": "1h", "4h": "4h", "1d": "1d"}


def _normalize_symbol(symbol: str) -> str:
    s = symbol.upper().replace("/", "").replace("-", "")
    if s in ("AUTO", ""):
        return "BTCUSDT"
    if s.endswith("USD") and not s.endswith("USDT"):
        s += "T"  # BTCUSD -> BTCUSDT
    return s


def _http_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "fondeo-bot/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except Exception as e:  # network blocked, host down, rate limited, etc.
        raise ValueError(
            f"No se pudieron obtener datos reales ({type(e).__name__}). "
            "Revisa la política de red del entorno o usa source='synthetic'."
        )


def parse_klines(rows: list) -> List[Bar]:
    """Map Binance kline rows to Bar objects (pure, testable without network)."""
    bars: List[Bar] = []
    for row in rows:
        bars.append(
            Bar(
                time=datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc).replace(tzinfo=None),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
        )
    return bars


class BinanceDataProvider(MarketDataProvider):
    """Fetches real OHLCV candles from Binance's public data endpoint."""

    def __init__(self, base: str = BINANCE_BASE):
        self.base = base

    def get_bars(self, market: str, symbol: str, timeframe: str, bars: int) -> List[Bar]:
        if market != "crypto":
            raise ValueError("La fuente 'binance' solo soporta el mercado crypto")
        interval = _BINANCE_INTERVAL.get(timeframe)
        if interval is None:
            raise ValueError(f"Timeframe '{timeframe}' no soportado por Binance. Opciones: {list(_BINANCE_INTERVAL)}")
        sym = _normalize_symbol(symbol)

        collected: list = []
        end_time = None
        remaining = bars
        while remaining > 0:
            limit = min(1000, remaining)
            url = f"{self.base}/api/v3/klines?symbol={sym}&interval={interval}&limit={limit}"
            if end_time is not None:
                url += f"&endTime={end_time}"
            rows = _http_json(url)
            if not rows:
                break
            collected = rows + collected
            remaining -= len(rows)
            end_time = rows[0][0] - 1  # just before the earliest candle fetched
            if len(rows) < limit:
                break
        if not collected:
            raise ValueError(f"Binance no devolvió datos para {sym} {interval}")
        return parse_klines(collected[-bars:])


def supported_sources() -> List[str]:
    return ["synthetic", "binance"]


def get_data_provider(source: str = "synthetic") -> MarketDataProvider:
    if source == "binance":
        return BinanceDataProvider()
    if source == "synthetic":
        return default_provider
    raise ValueError(f"Fuente de datos desconocida '{source}'. Opciones: {supported_sources()}")
