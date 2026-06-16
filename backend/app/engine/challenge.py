"""Prop-firm challenge rules engine.

This is the core differentiator of the project: given an equity curve, it
decides — objectively and reproducibly — whether a run would have *passed* a
funding challenge, or which rule it breached and when.

Rules modelled (configurable, generic — not tied to any specific firm):
  * profit_target_pct      profit needed to pass (e.g. 8%)
  * max_daily_loss_pct     max loss within a single day vs the day's start
  * max_total_drawdown_pct max overall drawdown
  * drawdown_mode          "static" (from initial balance) or "trailing" (from peak)
  * min_trading_days       distinct days with activity required to pass
  * max_calendar_days      optional time limit (0 = no limit)

Drawdown and daily-loss checks use intrabar worst-case equity, so a breach is
caught even if price recovered by the bar close — exactly how real firms
evaluate accounts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

from .backtest import EquityPoint


@dataclass
class ChallengeConfig:
    name: str = "Custom Challenge"
    account_size: float = 100_000.0
    profit_target_pct: float = 8.0
    max_daily_loss_pct: float = 5.0
    max_total_drawdown_pct: float = 10.0
    drawdown_mode: str = "trailing"  # "static" | "trailing"
    min_trading_days: int = 4
    max_calendar_days: int = 30

    def __post_init__(self):
        if self.drawdown_mode not in ("static", "trailing"):
            raise ValueError("drawdown_mode must be 'static' or 'trailing'")


# Generic presets inspired by common industry rule sets (not affiliated with,
# nor named after, any specific firm).
PRESETS: Dict[str, ChallengeConfig] = {
    "forex_2step_p1": ChallengeConfig(
        name="Forex 2-Step · Phase 1",
        account_size=100_000.0,
        profit_target_pct=8.0,
        max_daily_loss_pct=5.0,
        max_total_drawdown_pct=10.0,
        drawdown_mode="static",
        min_trading_days=4,
        max_calendar_days=30,
    ),
    "futures_1step": ChallengeConfig(
        name="Futures 1-Step",
        account_size=50_000.0,
        profit_target_pct=6.0,
        max_daily_loss_pct=4.0,
        max_total_drawdown_pct=6.0,
        drawdown_mode="trailing",
        min_trading_days=1,
        max_calendar_days=0,
    ),
    "crypto_1step": ChallengeConfig(
        name="Crypto 1-Step",
        account_size=25_000.0,
        profit_target_pct=10.0,
        max_daily_loss_pct=5.0,
        max_total_drawdown_pct=8.0,
        drawdown_mode="trailing",
        min_trading_days=3,
        max_calendar_days=0,
    ),
}


@dataclass
class ChallengeResult:
    status: str  # "passed" | "failed" | "in_progress"
    breached_rule: Optional[str] = None
    breach_detail: Optional[str] = None
    breach_time: Optional[str] = None
    pass_time: Optional[str] = None
    metrics: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "breached_rule": self.breached_rule,
            "breach_detail": self.breach_detail,
            "breach_time": self.breach_time,
            "pass_time": self.pass_time,
            "metrics": self.metrics,
        }


def evaluate_challenge(
    equity_curve: List[EquityPoint],
    config: ChallengeConfig,
    trading_days_with_activity: Optional[int] = None,
) -> ChallengeResult:
    """Walk the equity curve chronologically and apply the rules in order."""
    if not equity_curve:
        return ChallengeResult(status="in_progress", metrics={})

    acct = config.account_size
    profit_target = acct * (1 + config.profit_target_pct / 100)
    static_floor = acct * (1 - config.max_total_drawdown_pct / 100)

    peak_equity = acct
    start_date: date = equity_curve[0].time.date()

    # Track per-day starting equity for the daily-loss rule.
    current_day: Optional[date] = None
    day_start_equity = acct

    distinct_days = set()
    worst_daily_loss_pct = 0.0
    max_dd_pct = 0.0
    profit_reached_time: Optional[str] = None

    for point in equity_curve:
        d = point.time.date()
        distinct_days.add(d)

        if current_day != d:
            current_day = d
            # The day starts from the equity at the close of the previous bar.
            day_start_equity = _prev_equity(equity_curve, point) or acct

        # --- Calendar limit ---
        if config.max_calendar_days > 0:
            elapsed = (d - start_date).days
            if elapsed > config.max_calendar_days:
                return ChallengeResult(
                    status="failed",
                    breached_rule="max_calendar_days",
                    breach_detail=f"Exceeded {config.max_calendar_days} day time limit ({elapsed} days)",
                    breach_time=point.time.isoformat(),
                    metrics=_metrics(acct, equity_curve, distinct_days, worst_daily_loss_pct, max_dd_pct),
                )

        # --- Daily loss (worst-case intrabar) ---
        daily_loss_pct = (day_start_equity - point.equity_low) / acct * 100
        worst_daily_loss_pct = max(worst_daily_loss_pct, daily_loss_pct)
        if daily_loss_pct >= config.max_daily_loss_pct:
            return ChallengeResult(
                status="failed",
                breached_rule="max_daily_loss",
                breach_detail=f"Daily loss {daily_loss_pct:.2f}% >= limit {config.max_daily_loss_pct}%",
                breach_time=point.time.isoformat(),
                metrics=_metrics(acct, equity_curve, distinct_days, worst_daily_loss_pct, max_dd_pct),
            )

        # --- Total drawdown (worst-case intrabar) ---
        peak_equity = max(peak_equity, point.equity_high)
        if config.drawdown_mode == "static":
            floor = static_floor
        else:
            floor = peak_equity * (1 - config.max_total_drawdown_pct / 100)
        dd_pct = (peak_equity - point.equity_low) / peak_equity * 100
        max_dd_pct = max(max_dd_pct, dd_pct)
        if point.equity_low <= floor:
            return ChallengeResult(
                status="failed",
                breached_rule="max_total_drawdown",
                breach_detail=(
                    f"Equity {point.equity_low:.2f} breached {config.drawdown_mode} "
                    f"floor {floor:.2f} ({config.max_total_drawdown_pct}% drawdown)"
                ),
                breach_time=point.time.isoformat(),
                metrics=_metrics(acct, equity_curve, distinct_days, worst_daily_loss_pct, max_dd_pct),
            )

        # --- Profit target (only the first time it is reached) ---
        if profit_reached_time is None and point.equity_high >= profit_target:
            profit_reached_time = point.time.isoformat()

    days_count = trading_days_with_activity if trading_days_with_activity is not None else len(distinct_days)
    metrics = _metrics(acct, equity_curve, distinct_days, worst_daily_loss_pct, max_dd_pct)
    metrics["trading_days"] = days_count

    # No rule breached: did it hit the profit target with enough trading days?
    if profit_reached_time is not None and days_count >= config.min_trading_days:
        return ChallengeResult(
            status="passed",
            pass_time=profit_reached_time,
            metrics=metrics,
        )

    detail = None
    if profit_reached_time is not None and days_count < config.min_trading_days:
        detail = f"Profit target hit but only {days_count}/{config.min_trading_days} trading days"
    return ChallengeResult(status="in_progress", breach_detail=detail, metrics=metrics)


def _prev_equity(curve: List[EquityPoint], point: EquityPoint) -> Optional[float]:
    """Equity at the close of the bar before the first bar of `point`'s day."""
    target_day = point.time.date()
    prev = None
    for p in curve:
        if p.time.date() == target_day:
            break
        prev = p.equity
    return prev


def _metrics(acct, curve, distinct_days, worst_daily_loss_pct, max_dd_pct) -> Dict:
    final = curve[-1].equity
    return {
        "final_equity": round(final, 2),
        "return_pct": round((final / acct - 1) * 100, 2),
        "trading_days": len(distinct_days),
        "worst_daily_loss_pct": round(worst_daily_loss_pct, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
    }
