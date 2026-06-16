# Resultados de validación con datos reales

Ejecutado en GitHub Actions (red abierta), datos reales de Binance.

## BTCUSDT · 4h · 3000 velas · apalancamiento 3

| Estrategia     | Veredicto      | Sharpe | Profit factor | Eficiencia WFO | % tramos OOS rentables | Retorno OOS medio |
|----------------|----------------|-------:|--------------:|---------------:|-----------------------:|------------------:|
| breakout       | sin_evidencia  | -0.256 | 0.884         | -19.57         | 20.0                   | -9.36%            |
| rsi_reversion  | sin_evidencia  |  0.523 | 0.852         | -0.17          | 40.0                   | -5.87%            |
| momentum       | sin_evidencia  | -0.400 | 0.847         | -1.93          | 40.0                   | -34.02%           |
| ma_crossover   | sin_evidencia  |  1.023 | 0.881         | -0.56          | 40.0                   | -21.26%           |

### Lectura honesta

- **Ninguna de las 4 estrategias básicas tiene edge en BTC real.** El profit factor de todas es < 1
  (pierden dinero neto) y la eficiencia walk-forward es negativa (sin señal fuera de muestra).
- `ma_crossover` engaña con Sharpe 1.0 *en muestra*, pero su profit factor < 1 y su rendimiento
  fuera de muestra negativo lo delatan: es un espejismo de backtest. **Esto es exactamente lo que el
  arnés debe atrapar — y lo atrapó.**
- En real, con comisiones y deslizamiento, el resultado sería aún peor.

### Conclusión

El sistema de validación **funciona y es honesto**. Las estrategias de referencia (simples, un solo
instrumento, sin filtros de régimen ni gestión de posición avanzada) **no sirven para producción**.
El siguiente paso es construir/generar estrategias con ventaja real y volver a pasarlas por este filtro.

> Reproducible: workflow `.github/workflows/validate-real.yml` (push o ejecución manual).
