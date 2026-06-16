"""Edge-validation harness.

Provider-agnostic statistics to judge whether a strategy has a genuine edge —
not just one lucky run. Three pillars:

  * compute_metrics   — Sharpe, Sortino, profit factor, expectancy, drawdown, ...
  * walk_forward      — run the strategy across contiguous out-of-sample folds and
                        measure consistency across market regimes
  * monte_carlo       — bootstrap-resample the trade PnLs to get a distribution of
                        outcomes (prob. of profit, drawdown percentiles)

The verdict is deliberately conservative and never claims a guarantee.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from .backtest import BacktestResult, run_backtest
from .data import _BARS_PER_YEAR
from .strategies import Strategy


def _bars_per_year(timeframe: str) -> float:
    return float(_BARS_PER_YEAR.get(timeframe, 365))


def compute_metrics(result: BacktestResult, timeframe: str) -> Dict:
    eq = np.array([p.equity for p in result.equity_curve], dtype=float)
    trades = result.trades
    bpy = _bars_per_year(timeframe)

    # Per-bar simple returns, only where the previous equity is positive.
    prev, cur = eq[:-1], eq[1:]
    mask = prev > 0
    rets = np.where(mask, (cur - prev) / np.where(mask, prev, 1.0), 0.0)

    mean_r = float(np.mean(rets)) if rets.size else 0.0
    std_r = float(np.std(rets, ddof=1)) if rets.size > 1 else 0.0
    downside = rets[rets < 0]
    dstd = float(np.std(downside, ddof=1)) if downside.size > 1 else 0.0

    sharpe = (mean_r / std_r * np.sqrt(bpy)) if std_r > 0 else 0.0
    sortino = (mean_r / dstd * np.sqrt(bpy)) if dstd > 0 else 0.0

    pnls = np.array([t.pnl for t in trades], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    gross_profit = float(wins.sum()) if wins.size else 0.0
    gross_loss = float(losses.sum()) if losses.size else 0.0
    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss < 0 else (float("inf") if gross_profit > 0 else 0.0)
    expectancy = float(pnls.mean()) if pnls.size else 0.0

    return {
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "profit_factor": round(profit_factor, 3) if np.isfinite(profit_factor) else None,
        "expectancy": round(expectancy, 2),
        "win_rate_pct": round(100 * wins.size / pnls.size, 2) if pnls.size else 0.0,
        "num_trades": int(pnls.size),
        "total_return_pct": result.stats["total_return_pct"],
        "max_drawdown_pct": result.stats["max_drawdown_pct"],
    }


def walk_forward(
    bars: list,
    strategy: Strategy,
    account_size: float,
    leverage: float,
    folds: int = 4,
) -> Dict:
    """Run the strategy on each contiguous fold (out-of-sample regimes)."""
    folds = max(2, min(folds, len(bars) // 50 or 2))
    size = len(bars) // folds
    fold_returns: List[float] = []
    for i in range(folds):
        start = i * size
        end = len(bars) if i == folds - 1 else (i + 1) * size
        segment = bars[start:end]
        if len(segment) < 20:
            continue
        bt = run_backtest(segment, strategy, account_size=account_size, leverage=leverage)
        fold_returns.append(bt.stats["total_return_pct"])

    profitable = [r for r in fold_returns if r > 0]
    return {
        "folds": len(fold_returns),
        "fold_returns_pct": [round(r, 2) for r in fold_returns],
        "pct_folds_profitable": round(100 * len(profitable) / len(fold_returns), 1) if fold_returns else 0.0,
        "mean_fold_return_pct": round(float(np.mean(fold_returns)), 2) if fold_returns else 0.0,
    }


def monte_carlo(
    result: BacktestResult,
    account_size: float,
    runs: int = 2000,
    dd_breach_pct: float = 10.0,
    seed: int = 12345,
) -> Dict:
    """Bootstrap the trade PnL sequence to estimate the outcome distribution."""
    pnls = np.array([t.pnl for t in result.trades], dtype=float)
    if pnls.size < 5:
        return {"runs": 0, "note": "Muy pocas operaciones para un Monte Carlo fiable."}

    rng = np.random.default_rng(seed)
    n = pnls.size
    samples = rng.choice(pnls, size=(runs, n), replace=True)
    paths = account_size + np.cumsum(samples, axis=1)
    starts = np.full((runs, 1), account_size)
    full = np.concatenate([starts, paths], axis=1)

    finals = full[:, -1]
    peaks = np.maximum.accumulate(full, axis=1)
    drawdowns = (peaks - full) / peaks
    max_dd = drawdowns.max(axis=1) * 100

    final_return = (finals / account_size - 1) * 100
    return {
        "runs": runs,
        "prob_profit_pct": round(float(np.mean(finals > account_size) * 100), 1),
        "return_p05_pct": round(float(np.percentile(final_return, 5)), 2),
        "return_median_pct": round(float(np.percentile(final_return, 50)), 2),
        "return_p95_pct": round(float(np.percentile(final_return, 95)), 2),
        "max_drawdown_median_pct": round(float(np.percentile(max_dd, 50)), 2),
        "max_drawdown_p95_pct": round(float(np.percentile(max_dd, 95)), 2),
        "prob_dd_breach_pct": round(float(np.mean(max_dd >= dd_breach_pct) * 100), 1),
        "dd_breach_threshold_pct": dd_breach_pct,
    }


def edge_verdict(metrics: Dict, wf: Dict, mc: Dict) -> Dict:
    """Conservative, honest classification of the evidence for an edge."""
    score = 0
    reasons = []

    if metrics["expectancy"] > 0:
        score += 1; reasons.append("Expectativa por operación positiva")
    else:
        reasons.append("Expectativa por operación no positiva")

    pf = metrics["profit_factor"]
    if pf is not None and pf > 1.1:
        score += 1; reasons.append(f"Profit factor {pf} > 1.1")

    if metrics["sharpe"] > 0.5:
        score += 1; reasons.append(f"Sharpe {metrics['sharpe']} razonable")

    if wf.get("pct_folds_profitable", 0) >= 60:
        score += 1; reasons.append(f"{wf['pct_folds_profitable']}% de tramos rentables")

    if mc.get("runs", 0) and mc["prob_profit_pct"] >= 60:
        score += 1; reasons.append(f"Monte Carlo: {mc['prob_profit_pct']}% prob. de beneficio")

    if score >= 4:
        label = "edge_prometedor"
        summary = "Evidencia consistente de ventaja; validar luego en datos reales y demo."
    elif score >= 2:
        label = "edge_debil"
        summary = "Señales mixtas; no es concluyente. Iterar estrategia/parámetros."
    else:
        label = "sin_evidencia"
        summary = "Sin evidencia de ventaja. No usar con dinero real en este estado."

    return {"score": score, "max_score": 5, "label": label, "summary": summary, "reasons": reasons}
