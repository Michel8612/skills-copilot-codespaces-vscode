"""Parameter optimization and walk-forward optimization (WFO).

Plain grid search finds the parameters that look best *in sample* — which is
exactly how strategies get curve-fit. Walk-forward optimization is the honest
antidote: repeatedly optimize on a past window, then measure performance on the
*next, unseen* window. The gap between in-sample and out-of-sample performance
("WFO efficiency") tells you how much of the backtest was real vs. overfit.
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from .backtest import run_backtest
from .strategies import build_strategy, strategy_param_grid
from .validation import compute_metrics


def _score(bars, params, strategy_name, account_size, leverage, timeframe, metric) -> float:
    strat = build_strategy(strategy_name, params)
    bt = run_backtest(bars, strat, account_size=account_size, leverage=leverage)
    if metric == "return":
        return bt.stats["total_return_pct"]
    return compute_metrics(bt, timeframe).get(metric, 0.0) or 0.0


def grid_search(
    bars: list,
    strategy_name: str,
    account_size: float = 100_000.0,
    leverage: float = 3.0,
    timeframe: str = "4h",
    metric: str = "sharpe",
    top: int = 5,
) -> Dict:
    """Evaluate every parameter set and rank by `metric` (in-sample)."""
    grid = strategy_param_grid(strategy_name)
    results = []
    for params in grid:
        score = _score(bars, params, strategy_name, account_size, leverage, timeframe, metric)
        results.append({"params": params, "score": round(float(score), 3)})
    results.sort(key=lambda r: r["score"], reverse=True)
    return {
        "metric": metric,
        "evaluated": len(results),
        "best": results[0] if results else None,
        "top": results[:top],
    }


def walk_forward_optimize(
    bars: list,
    strategy_name: str,
    account_size: float = 100_000.0,
    leverage: float = 3.0,
    timeframe: str = "4h",
    metric: str = "sharpe",
    windows: int = 5,
) -> Dict:
    """Roll an optimize-then-test window across the data (anti-overfitting test).

    For each step: optimize parameters on window i (in-sample), then trade those
    parameters on window i+1 (out-of-sample). Aggregate the OOS results.
    """
    n = len(bars)
    windows = max(2, min(windows, n // 100 or 2))
    size = n // (windows + 1)
    if size < 50:
        return {"steps": 0, "note": "Datos insuficientes para walk-forward optimization."}

    steps = []
    for i in range(windows):
        is_bars = bars[i * size:(i + 1) * size]
        oos_bars = bars[(i + 1) * size:(i + 2) * size]
        if len(oos_bars) < 30:
            break
        gs = grid_search(is_bars, strategy_name, account_size, leverage, timeframe, metric, top=1)
        best = gs["best"]
        is_score = best["score"]
        oos_score = _score(oos_bars, best["params"], strategy_name, account_size, leverage, timeframe, metric)
        oos_ret = _score(oos_bars, best["params"], strategy_name, account_size, leverage, timeframe, "return")
        steps.append({
            "params": best["params"],
            "in_sample_score": round(float(is_score), 3),
            "out_of_sample_score": round(float(oos_score), 3),
            "out_of_sample_return_pct": round(float(oos_ret), 2),
        })

    if not steps:
        return {"steps": 0, "note": "Datos insuficientes para walk-forward optimization."}

    is_scores = np.array([s["in_sample_score"] for s in steps], dtype=float)
    oos_scores = np.array([s["out_of_sample_score"] for s in steps], dtype=float)
    oos_rets = np.array([s["out_of_sample_return_pct"] for s in steps], dtype=float)
    mean_is = float(np.mean(is_scores))
    mean_oos = float(np.mean(oos_scores))
    efficiency = (mean_oos / mean_is) if mean_is > 0 else 0.0

    return {
        "metric": metric,
        "steps": len(steps),
        "windows": steps,
        "mean_in_sample_score": round(mean_is, 3),
        "mean_out_of_sample_score": round(mean_oos, 3),
        # WFO efficiency: OOS/IS. ~1 = robust; <<1 = overfit; >1 = lucky/under-fit.
        "wfo_efficiency": round(float(efficiency), 2),
        "pct_oos_profitable": round(float(np.mean(oos_rets > 0) * 100), 1),
        "mean_oos_return_pct": round(float(np.mean(oos_rets)), 2),
    }
