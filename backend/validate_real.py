"""Valida el 'edge' con DATOS REALES de crypto (Binance) desde tu propia PC.

Este script descarga velas reales y corre, para cada estrategia:
  - métricas de robustez + Monte Carlo + veredicto de edge
  - walk-forward optimization (eficiencia anti-overfitting)

Uso (desde la carpeta backend, con el entorno virtual activado):

    python validate_real.py                 # BTCUSDT 4h, 3000 velas
    python validate_real.py ETHUSDT 1h 5000

Requisitos: pip install -r requirements.txt  (y acceso a internet sin bloqueo).
Si la red bloquea Binance, el script lo dirá con claridad.
"""

from __future__ import annotations

import sys

from app.schemas import OptimizeRequest, ValidateRequest
from app.service import optimize, validate_edge

STRATEGIES = ["breakout", "rsi_reversion", "momentum", "ma_crossover", "trend_breakout", "trend_rsi", "oracle_trend_rsi"]


def main() -> int:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "4h"
    bars = int(sys.argv[3]) if len(sys.argv) > 3 else 3000

    print(f"\nValidando con DATOS REALES · {symbol} {timeframe} · {bars} velas (fuente: Binance)\n")
    print(f"{'estrategia':<14} {'veredicto':<16} {'sharpe':>7} {'profit_f':>9} "
          f"{'WFO_efic':>9} {'%OOS_rent':>10} {'ret_OOS%':>9}")
    print("-" * 80)

    for strat in STRATEGIES:
        try:
            v = validate_edge(ValidateRequest(
                market="crypto", symbol=symbol, timeframe=timeframe, bars=bars,
                source="binance", strategy=strat, leverage=3,
            ))
        except ValueError as e:
            print(f"\n⚠️  {e}\n   (Parece que la red bloquea Binance. Prueba en una red sin restricciones.)")
            return 1

        try:
            o = optimize(OptimizeRequest(
                market="crypto", symbol=symbol, timeframe=timeframe, bars=bars,
                source="binance", strategy=strat, leverage=3, metric="return",
            ))
            wfo = o["walk_forward_optimization"]
        except ValueError:
            wfo = {}

        m, ver = v["metrics"], v["verdict"]
        pf = m["profit_factor"] if m["profit_factor"] is not None else "-"
        print(f"{strat:<14} {ver['label']:<16} {m['sharpe']:>7} {str(pf):>9} "
              f"{str(wfo.get('wfo_efficiency','-')):>9} {str(wfo.get('pct_oos_profitable','-')):>10} "
              f"{str(wfo.get('mean_oos_return_pct','-')):>9}")

    print("\nGuía rápida:")
    print("  • WFO_efic ~1 = robusto · <<1 = sobreajustado · <0 = sin señal real")
    print("  • Un edge creíble: veredicto 'edge_prometedor' + WFO_efic alta + %OOS_rent alto.")
    print("  • Recuerda: ningún backtest garantiza resultados futuros.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
