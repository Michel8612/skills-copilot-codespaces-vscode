"""Pluggable signal oracle — the integration point for external information.

An *oracle* turns information into a directional bias in [-1, +1] for the
current bar. The honest principle: a price-only oracle adds **no edge** because
it carries no information the market hasn't already discounted. Real edge can
come from information the price has *not* yet reflected — sentiment, on-chain
flows, funding rates, order-flow, or a predictive model.

This module defines the contract and a deterministic mock so strategies and the
backtester can consume oracles today. A real source plugs in by subclassing
`Oracle` and registering it; no other code needs to change.
"""

from __future__ import annotations

from typing import Dict, List, Type

from .data import Bar


class Oracle:
    """Base class. Implement `bias`."""

    name: str = "base"

    def bias(self, bars: List[Bar]) -> float:
        """Directional conviction for the last bar in [-1, +1]. 0 = no opinion."""
        raise NotImplementedError


class NeutralOracle(Oracle):
    """No opinion ever — gating with it is a no-op (useful as a baseline)."""

    name = "neutral"

    def bias(self, bars: List[Bar]) -> float:
        return 0.0


class MockOracle(Oracle):
    """Deterministic stand-in derived from price, so the integration is
    testable end to end. This is NOT a real edge source (it only re-reads
    price); swap it for a real data/prediction feed."""

    name = "mock"

    def __init__(self, window: int = 50):
        self.window = window

    def bias(self, bars: List[Bar]) -> float:
        if len(bars) <= self.window:
            return 0.0
        closes = [b.close for b in bars]
        change = (closes[-1] - closes[-self.window]) / closes[-self.window]
        return max(-1.0, min(1.0, change * 10))


class ContrarianSentimentOracle(Oracle):
    """Contrarian retail-sentiment oracle (the Myfxbook "Community Outlook" idea).

    Given the % of retail traders that are LONG a symbol at each bar, it leans
    the *opposite* way: when the crowd is heavily long, retail is usually wrong,
    so the bias turns bearish (and vice-versa). This is real *information* the
    price does not directly contain — the kind of input that can actually carry
    an edge, unlike a price-only oracle.

    `sentiment` maps an ISO-8601 timestamp -> long_pct in [0, 100]. Bars whose
    timestamp has no sentiment datapoint produce a neutral (0) bias, so the
    oracle degrades gracefully when data is missing.
    """

    name = "contrarian_sentiment"

    def __init__(self, sentiment: Dict[str, float] | None = None, neutral_band: float = 10.0):
        self.sentiment = sentiment or {}
        self.neutral_band = neutral_band

    def bias(self, bars: List[Bar]) -> float:
        last = bars[-1]
        key = last.time.isoformat() if getattr(last, "time", None) is not None else None
        if key is None or key not in self.sentiment:
            return 0.0
        diff = self.sentiment[key] - 50.0  # >0 means crowd is net long
        if abs(diff) < self.neutral_band:
            return 0.0
        return max(-1.0, min(1.0, -diff / 50.0))  # contrarian: invert the crowd


def load_sentiment_json(path: str) -> Dict[str, float]:
    """Load a {iso_time: long_pct} sentiment map written by a forward-logger."""
    import json

    with open(path, "r", encoding="utf-8") as fh:
        return {str(k): float(v) for k, v in json.load(fh).items()}


ORACLE_REGISTRY: Dict[str, Type[Oracle]] = {
    NeutralOracle.name: NeutralOracle,
    MockOracle.name: MockOracle,
    ContrarianSentimentOracle.name: ContrarianSentimentOracle,
}


def build_oracle(name: str, params: Dict | None = None) -> Oracle:
    if name not in ORACLE_REGISTRY:
        raise ValueError(f"Unknown oracle '{name}'. Options: {list(ORACLE_REGISTRY)}")
    return ORACLE_REGISTRY[name](**(params or {}))
