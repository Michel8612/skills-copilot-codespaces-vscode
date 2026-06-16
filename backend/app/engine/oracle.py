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


ORACLE_REGISTRY: Dict[str, Type[Oracle]] = {
    NeutralOracle.name: NeutralOracle,
    MockOracle.name: MockOracle,
}


def build_oracle(name: str, params: Dict | None = None) -> Oracle:
    if name not in ORACLE_REGISTRY:
        raise ValueError(f"Unknown oracle '{name}'. Options: {list(ORACLE_REGISTRY)}")
    return ORACLE_REGISTRY[name](**(params or {}))
