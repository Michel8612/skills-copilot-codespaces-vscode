"""Event-driven backtester.

Signals are computed from bars strictly *before* the current bar and executed
at the current bar's open, which avoids look-ahead bias. Each bar is then
marked to market using its high/low/close so the challenge engine can see the
worst-case intrabar equity (important for drawdown rules).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

from .data import Bar
from .strategies import Strategy


@dataclass
class Trade:
    entry_time: datetime
    exit_time: datetime
    side: str  # "long" | "short"
    entry_price: float
    exit_price: float
    units: float
    pnl: float


@dataclass
class EquityPoint:
    time: datetime
    equity: float
    equity_high: float
    equity_low: float


@dataclass
class BacktestResult:
    account_size: float
    final_equity: float
    equity_curve: List[EquityPoint]
    trades: List[Trade]
    stats: Dict

    def to_dict(self) -> Dict:
        return {
            "account_size": self.account_size,
            "final_equity": self.final_equity,
            "equity_curve": [
                {
                    "time": p.time.isoformat(),
                    "equity": round(p.equity, 2),
                    "equity_high": round(p.equity_high, 2),
                    "equity_low": round(p.equity_low, 2),
                }
                for p in self.equity_curve
            ],
            "trades": [
                {**asdict(t), "entry_time": t.entry_time.isoformat(), "exit_time": t.exit_time.isoformat()}
                for t in self.trades
            ],
            "stats": self.stats,
        }


def run_backtest(
    bars: List[Bar],
    strategy: Strategy,
    account_size: float = 100_000.0,
    leverage: float = 10.0,
    fee_pct: float = 0.0002,
) -> BacktestResult:
    """Run `strategy` over `bars` starting from `account_size`."""
    if not bars:
        raise ValueError("No bars provided")

    realized_pnl = 0.0
    position = 0.0  # signed units
    entry_price = 0.0
    open_trade: Optional[Dict] = None

    equity_curve: List[EquityPoint] = []
    trades: List[Trade] = []

    def equity_at(price: float) -> float:
        return account_size + realized_pnl + position * (price - entry_price)

    for i, bar in enumerate(bars):
        desired = strategy.target_position(bars[:i]) if i > 0 else 0
        current_sign = 0 if position == 0 else (1 if position > 0 else -1)

        if desired != current_sign:
            # Close existing position at this bar's open.
            if position != 0 and open_trade is not None:
                exit_price = bar.open
                gross = position * (exit_price - entry_price)
                fees = abs(position) * (entry_price + exit_price) * fee_pct
                pnl = gross - fees
                realized_pnl += pnl
                trades.append(
                    Trade(
                        entry_time=open_trade["time"],
                        exit_time=bar.time,
                        side="long" if position > 0 else "short",
                        entry_price=round(entry_price, 6),
                        exit_price=round(exit_price, 6),
                        units=round(abs(position), 6),
                        pnl=round(pnl, 2),
                    )
                )
                position = 0.0
                open_trade = None

            # Open new position at this bar's open.
            if desired != 0:
                entry_price = bar.open
                units = (account_size * leverage) / entry_price
                position = units * desired
                open_trade = {"time": bar.time}

        # Mark to market across the bar's range.
        eq_close = equity_at(bar.close)
        eq_high = equity_at(bar.high)
        eq_low = equity_at(bar.low)
        equity_curve.append(
            EquityPoint(
                time=bar.time,
                equity=eq_close,
                equity_high=max(eq_high, eq_low, eq_close),
                equity_low=min(eq_high, eq_low, eq_close),
            )
        )

    final_equity = equity_curve[-1].equity
    stats = _compute_stats(account_size, final_equity, equity_curve, trades)
    return BacktestResult(account_size, final_equity, equity_curve, trades, stats)


def _compute_stats(
    account_size: float,
    final_equity: float,
    equity_curve: List[EquityPoint],
    trades: List[Trade],
) -> Dict:
    wins = [t for t in trades if t.pnl > 0]
    peak = account_size
    max_dd = 0.0
    for p in equity_curve:
        peak = max(peak, p.equity_high)
        dd = (peak - p.equity_low) / peak
        max_dd = max(max_dd, dd)

    return {
        "total_return_pct": round((final_equity / account_size - 1) * 100, 2),
        "num_trades": len(trades),
        "win_rate_pct": round(100 * len(wins) / len(trades), 2) if trades else 0.0,
        "max_drawdown_pct": round(max_dd * 100, 2),
        "gross_profit": round(sum(t.pnl for t in trades if t.pnl > 0), 2),
        "gross_loss": round(sum(t.pnl for t in trades if t.pnl < 0), 2),
    }
