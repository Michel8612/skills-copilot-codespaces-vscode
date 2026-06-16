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

    @classmethod
    def param_grid(cls) -> List[Dict]:
        """Candidate parameter sets for optimization (override per strategy)."""
        return [{}]


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

    @classmethod
    def param_grid(cls) -> List[Dict]:
        return [{"fast": f, "slow": s} for f in (5, 10, 20) for s in (30, 50, 100) if f < s]


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

    @classmethod
    def param_grid(cls) -> List[Dict]:
        return [{"lookback": n} for n in (10, 15, 20, 30, 50)]


def _rsi(closes: List[float], period: int) -> float:
    """Wilder-style RSI of the last `period` deltas. Returns 50 when flat/insufficient."""
    if len(closes) <= period:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(len(closes) - period, len(closes))]
    gains = sum(d for d in deltas if d > 0)
    losses = -sum(d for d in deltas if d < 0)
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    rs = (gains / period) / (losses / period)
    return 100 - 100 / (1 + rs)


@dataclass
class RSIReversion(Strategy):
    """Mean reversion: long when oversold, short when overbought."""

    name: str = field(default="rsi_reversion", init=False)
    period: int = 14
    oversold: int = 30
    allow_short: bool = True

    def target_position(self, bars: List[Bar]) -> int:
        if len(bars) <= self.period:
            return 0
        rsi = _rsi([b.close for b in bars], self.period)
        if rsi <= self.oversold:
            return 1
        if rsi >= 100 - self.oversold:
            return -1 if self.allow_short else 0
        return 0

    @classmethod
    def describe(cls) -> Dict:
        return {"name": cls.name, "params": {"period": 14, "oversold": 30, "allow_short": True}}

    @classmethod
    def param_grid(cls) -> List[Dict]:
        return [{"period": p, "oversold": o} for p in (7, 14, 21) for o in (25, 30, 35)]


@dataclass
class Momentum(Strategy):
    """Rate-of-change momentum: long if price rose over the lookback, short if fell."""

    name: str = field(default="momentum", init=False)
    lookback: int = 20
    allow_short: bool = True

    def target_position(self, bars: List[Bar]) -> int:
        if len(bars) <= self.lookback:
            return 0
        ref = bars[-(self.lookback + 1)].close
        if ref <= 0:
            return 0
        roc = bars[-1].close / ref - 1
        if roc > 0:
            return 1
        if roc < 0:
            return -1 if self.allow_short else 0
        return 0

    @classmethod
    def describe(cls) -> Dict:
        return {"name": cls.name, "params": {"lookback": 20, "allow_short": True}}

    @classmethod
    def param_grid(cls) -> List[Dict]:
        return [{"lookback": n} for n in (10, 20, 40)]


STRATEGY_REGISTRY: Dict[str, Type[Strategy]] = {
    MovingAverageCrossover.name: MovingAverageCrossover,
    Breakout.name: Breakout,
    RSIReversion.name: RSIReversion,
    Momentum.name: Momentum,
}


def build_strategy(name: str, params: Dict | None = None) -> Strategy:
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy '{name}'. Options: {list(STRATEGY_REGISTRY)}")
    params = params or {}
    return STRATEGY_REGISTRY[name](**params)


def strategy_param_grid(name: str) -> List[Dict]:
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy '{name}'. Options: {list(STRATEGY_REGISTRY)}")
    return STRATEGY_REGISTRY[name].param_grid()


def list_strategies() -> List[Dict]:
    return [cls.describe() for cls in STRATEGY_REGISTRY.values()]
