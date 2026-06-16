# Fondeo Bot

Sistema de **trading algorítmico + evaluación de pruebas de fondeo (prop-firm challenges)**.

El objetivo del proyecto es construir, primero, un **motor de trading confiable y verificable**, y
sobre esa base habilitar tres líneas de negocio:

1. **Servicio de pase** — pasar challenges de fondeo para clientes.
2. **Venta del bot** — distribuir el bot como producto con licencias.
3. **Empresa de fondeo** — operar una prop firm propia.

> ⚠️ **Aviso importante.** Ningún bot puede *garantizar* pasar un challenge ni generar beneficios.
> El trading conlleva riesgo real de pérdida. Este software sirve para **construir, medir y verificar
> objetivamente** estrategias antes de arriesgar capital. Los datos de mercado del MVP son **sintéticos**
> (para que todo corra sin claves de API); conectar datos/brokers reales es un paso posterior.

---

## Qué incluye este MVP

| Componente | Estado | Descripción |
|---|---|---|
| Motor de datos | ✅ | OHLCV sintético determinista (forex/futuros/crypto) **+ datos reales de crypto** vía Binance público (`source="binance"`). |
| Framework de estrategias | ✅ | Estrategias basadas en posición objetivo. Incluye cruce de medias y breakout. |
| Backtester | ✅ | Event-driven, sin look-ahead, marca a mercado con máximos/mínimos intrabar. |
| **Motor de reglas de challenge** ⭐ | ✅ | Evalúa profit target, pérdida diaria, drawdown total (estático/trailing), días mínimos y límite de tiempo. |
| **Agencia de IA** 🤖 | ✅ | Sistema multi-agente (estrategia, riesgo, datos, cumplimiento, negocio + director) que resuelve dilemas. Funciona offline (determinista) o con Claude. |
| **Empresa de fondeo** 🏦 | ✅ | Base de datos propia (SQLite): planes honestos publicados, traders, cuentas y evaluación auditable. Reparto de beneficios transparente. |
| **3 líneas de negocio** | ✅ | Fondeo + venta del bot (licencias) + servicio de pase (con reintentos y reembolso honestos). |
| **Panel de cliente** 👤 | ✅ | Registro/login (contraseña con PBKDF2 + token de sesión) e historial unificado de las 3 líneas. |
| API REST (FastAPI) | ✅ | `/api/run`, `/api/agency/*`, `/api/fondeo/*`, `/api/bot/*`, `/api/pase/*`, `/api/auth/*`, `/api/me/*`. |
| Frontend (React + Vite) | ✅ | Pestañas: Backtest & Challenge, Agencia IA, Fondeo y Mi cuenta. |
| Tests | ✅ | 37 tests (motor, reglas, agencia, fondeo, líneas, datos reales y auth). |

Ver el plan completo hacia las 3 líneas de negocio en [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## Estructura

```
backend/
  app/
    main.py            # FastAPI app y endpoints
    service.py         # pipeline: datos -> estrategia -> backtest -> challenge
    schemas.py         # modelos de request/response
    engine/
      data.py          # proveedores de datos de mercado (sintético + interfaz)
      strategies.py    # framework + estrategias de referencia
      backtest.py      # backtester event-driven
      challenge.py     # motor de reglas de prop-firm  ⭐
    agency/
      providers.py     # proveedor LLM enchufable (offline / Claude)
      roster.py        # roles de agentes especializados
      orchestrator.py  # deliberación multi-agente + síntesis  🤖
    fondeo/
      models.py        # tablas: Plan, Trader, Account, Payout
      db.py            # base de datos SQLite propia
      service.py       # planes, cuentas y evaluación auditable  🏦
  tests/               # pytest
frontend/
  src/                 # React + TypeScript (Vite)
docs/
  ROADMAP.md
```

---

## Cómo ejecutarlo en local

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API en `http://localhost:8000` · documentación interactiva en `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Panel en `http://localhost:5173` (hace proxy de `/api` al backend en el puerto 8000).

### Tests

```bash
cd backend && source .venv/bin/activate && pytest -q
```

---

## Ejemplo de uso de la API

```bash
curl -s -X POST http://localhost:8000/api/run \
  -H 'Content-Type: application/json' \
  -d '{
    "market": "forex",
    "symbol": "EURUSD",
    "timeframe": "4h",
    "bars": 1200,
    "strategy": "breakout",
    "strategy_params": {"lookback": 15},
    "leverage": 10,
    "preset": "forex_2step_p1"
  }'
```

Devuelve el resultado del backtest **y** el veredicto del challenge (`passed` / `failed` / `in_progress`),
incluida la regla que se violó y en qué momento.

## Agencia de IA

Un equipo de agentes especializados delibera sobre un dilema y un director sintetiza una recomendación.

```bash
curl -s -X POST http://localhost:8000/api/agency/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "¿Cómo valido que la estrategia tiene edge antes de venderla?"}'
```

- **Sin configuración** funciona en modo *offline* (respuestas deterministas basadas en reglas, sin gastar tokens).
- Si defines la variable de entorno `ANTHROPIC_API_KEY`, usa **Claude** (`claude-opus-4-8`) automáticamente —
  instala primero el extra opcional con `pip install anthropic`.

## Empresa de fondeo (honesta)

Una prop firm propia con **base de datos propia** y reglas transparentes, evaluadas por el mismo motor
auditable. Principios de honestidad codificados en el sistema: reglas públicas e iguales para todos,
veredicto determinista y reproducible, reparto de beneficios transparente y reglas congeladas por cuenta.

```bash
# Planes publicados (sembrados al arrancar)
curl -s http://localhost:8000/api/fondeo/plans

# Flujo: registrar trader -> abrir cuenta -> evaluar con el bot
curl -s -X POST http://localhost:8000/api/fondeo/traders \
  -H 'Content-Type: application/json' -d '{"name":"Ada","email":"ada@x.com"}'
# (usa el id devuelto)
curl -s -X POST http://localhost:8000/api/fondeo/accounts \
  -H 'Content-Type: application/json' -d '{"trader_id":1,"plan_id":1}'
curl -s -X POST http://localhost:8000/api/fondeo/accounts/1/evaluate \
  -H 'Content-Type: application/json' -d '{"strategy":"breakout","symbol":"EURUSD","leverage":3}'
```

La base de datos es SQLite (`fondeo.sqlite`, configurable con `FONDEO_DB_URL`).
