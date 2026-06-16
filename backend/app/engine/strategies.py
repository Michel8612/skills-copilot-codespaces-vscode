"""Strategy framework + a couple of reference strategies.

A strategy receives the history of bars seen so far and returns a target
position: +1 (long), -1 (short) or 0 (flat). The backtester is responsible
for turning position changes into trades. Keeping strategies stateless and
position-based makes them easy to test and to swap out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Type

from .data import Bar


class Strategy:
    """Base class. Implement `target_position`."""

    name: str = "base"

    def target_position(self, bars: List[Bar]) -> int:
        """Return desired position (-1, 0, +1) given bars up to and including the last."""
        raise NotImplementedError

    @classmethod
    def describe(cls) -> Dict:
        return {"name": cls.name, "params": {}}


@dataclass
class MovingAverageCrossover(Strategy):
    """Go long when fast MA crosses above slow MA, short when below."""

    name: str = field(default="ma_crossover", init=False)
    fast: int = 10
    slow: int = 30
    allow_short: bool = True

    def target_position(self, bars: List[Bar]) -> int:
        if len(bars) < self.slow:
            return 0
        closes = [b.close for b in bars]
        fast_ma = sum(closes[-self.fast:]) / self.fast
        slow_ma = sum(closes[-self.slow:]) / self.slow
        if fast_ma > slow_ma:
            return 1
        if fast_ma < slow_ma:
            return -1 if self.allow_short else 0
        return 0

    @classmethod
    def describe(cls) -> Dict:
        return {"name": cls.name, "params": {"fast": 10, "slow": 30, "allow_short": True}}


@dataclass
class Breakout(Strategy):
    """Donchian-style breakout: long on N-bar high, short on N-bar low."""

    name: str = field(default="breakout", init=False)
    lookback: int = 20
    allow_short: bool = True

    def target_position(self, bars: List[Bar]) -> int:
        if len(bars) <= self.lookback:
            return 0
        window = bars[-(self.lookback + 1):-1]
        last = bars[-1]
        highest = max(b.high for b in window)
        lowest = min(b.low for b in window)
        if last.close >= highest:
            return 1
        if last.close <= lowest:
            return -1 if self.allow_short else 0
        return 0

    @classmethod
    def describe(cls) -> Dict:
        return {"name": cls.name, "params": {"lookback": 20, "allow_short": True}}


STRATEGY_REGISTRY: Dict[str, Type[Strategy]] = {
    MovingAverageCrossover.name: MovingAverageCrossover,
    Breakout.name: Breakout,
}


def build_strategy(name: str, params: Dict | None = None) -> Strategy:
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy '{name}'. Options: {list(STRATEGY_REGISTRY)}")
    params = params or {}
    return STRATEGY_REGISTRY[name](**params)


def list_strategies() -> List[Dict]:
    return [cls.describe() for cls in STRATEGY_REGISTRY.values()]
