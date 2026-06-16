# Resultados de validación con datos reales

Ejecutado en GitHub Actions (red abierta), datos reales de Binance.

## BTCUSDT · 4h · 3000 velas · apalancamiento 3

| Estrategia      | Veredicto      | Sharpe | Profit factor | Eficiencia WFO | % tramos OOS rentables | Retorno OOS medio |
|-----------------|----------------|-------:|--------------:|---------------:|-----------------------:|------------------:|
| breakout        | sin_evidencia  | -0.256 | 0.884         | -19.57         | 20.0                   | -9.36%            |
| rsi_reversion   | sin_evidencia  |  0.523 | 0.852         | -0.17          | 40.0                   | -5.87%            |
| momentum        | sin_evidencia  | -0.400 | 0.847         | -1.93          | 40.0                   | -34.09%           |
| ma_crossover    | sin_evidencia  |  1.025 | 0.881         | -0.56          | 40.0                   | -21.19%           |
| trend_breakout  | sin_evidencia  | -0.624 | 0.763         |  0.00          | 0.0                    | -9.39%            |
| trend_rsi       | sin_evidencia  |  0.175 | 0.979         | -0.39          | 40.0                   | -4.60%            |
| oracle_trend_rsi| sin_evidencia  | -0.324 | 0.762         | **+0.29**      | 40.0                   | **+1.83%**        |

### Lectura honesta

- **Ninguna de las 6 estrategias tiene edge en BTC real.** Todas con profit factor < 1 (pierden neto)
  y eficiencia walk-forward ≤ 0 (sin señal fuera de muestra).
- El **filtro de tendencia ayudó algo**: `trend_rsi` quedó con profit factor 0.98 (casi a la par antes
  de comisiones) — la "menos mala" —, pero sigue sin pasar.
- `ma_crossover` engaña con Sharpe 1.0 en muestra pero pierde fuera de muestra: espejismo de backtest.

### Conclusión estratégica

El arnés funciona y es honesto: **la táctica técnica simple sobre un solo instrumento no genera ventaja.**
Esto confirma empíricamente lo que dijo José al inicio: *"el dinero no está en el trading; está en vender
el bot o el servicio de pase"*. Encontrar un edge real es un proyecto de investigación cuantitativa en sí
mismo, sin garantías.

**Caminos posibles** (ninguno garantiza edge):
1. Estrategias más sofisticadas (multi-activo, cartera, estadística/ML) — esfuerzo alto.
2. Generación masiva con StrategyQuant X + filtrado con este arnés — búsqueda más rápida, riesgo de overfitting.
3. Asumir el hallazgo y centrar el valor en la **plataforma y los servicios** (lo ya construido), tratando
   la estrategia como I+D continua.

### Pista del oráculo (señal externa)

`oracle_trend_rsi` es la única de las 7 con **eficiencia walk-forward positiva (+0.29)** y **retorno OOS
positivo (+1.83%)**, pese a seguir sin pasar (PF 0.76). El motivo: el *gating* del oráculo filtra
operaciones malas. Y eso usando solo un oráculo mock (que re-lee el precio, sin información nueva).

→ La hipótesis a probar: un oráculo con **información real** que el precio no descuenta — p. ej. el
**sentimiento contrario** del Community Outlook de Myfxbook (cuando la masa minorista está larga, suele ser
bajista). Ya está implementado `ContrarianSentimentOracle`; falta alimentarlo con datos.

**Limitación honesta**: Myfxbook publica el sentimiento *actual*, no un histórico libre. Para backtestear
hace falta **registrar el sentimiento hacia adelante** (forward-logging) durante semanas y validar sobre
ese periodo. Es el método científico correcto, pero lleva tiempo de calendario.

**Cómo activar el registro** (arranca el reloj de datos):
1. En GitHub → Settings → Secrets and variables → Actions, añade `MYFXBOOK_EMAIL` y `MYFXBOOK_PASSWORD`.
2. El workflow `.github/workflows/log-sentiment.yml` corre cada hora y va guardando
   `data/sentiment/<SYMBOL>.json` (`{fecha: % largos}`). Sin los secretos es un no-op (queda en verde).
3. Tras unas semanas, cargamos esos datos (`load_sentiment_json`) en `ContrarianSentimentOracle` y
   validamos con walk-forward sobre el periodo registrado.

> Reproducible vía `.github/workflows/validate-real.yml`.
