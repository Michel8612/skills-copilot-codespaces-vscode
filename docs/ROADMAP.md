# Roadmap

El proyecto avanza por fases. Cada fase deja algo **funcional y verificable** antes de pasar a la
siguiente. La regla rectora viene del chat original: *"siempre que todo esté comprobado y verificado
que funciona"*.

## Fase 0 — Núcleo verificable ✅ (este MVP)

- [x] Motor de datos sintético determinista (forex / futuros / crypto).
- [x] Framework de estrategias + 2 estrategias de referencia.
- [x] Backtester event-driven sin look-ahead.
- [x] Motor de reglas de challenge (profit target, pérdida diaria, drawdown estático/trailing, días mín, límite de tiempo).
- [x] API REST + frontend de panel.
- [x] **Agencia de IA**: capa multi-agente (estrategia, riesgo, datos, cumplimiento, negocio + director) con proveedor LLM enchufable (offline determinista / Claude).
- [x] Suite de tests.

> La Agencia de IA es el "cerebro" que coordina el proyecto y resuelve dilemas. Hoy razona con reglas
> (offline) o con Claude; en fases siguientes se le conectarán como herramientas el motor de backtest,
> los datos reales y la ejecución, para que pueda *actuar* y no solo aconsejar.

## Fase 1 — Datos y estrategias reales

- [ ] Conectar datos históricos reales (p. ej. APIs de crypto, datos de forex/futuros).
- [ ] Más estrategias + optimización de parámetros y validación *walk-forward*.
- [ ] Métricas de robustez: Sharpe, Sortino, expectativa, Monte Carlo sobre orden de trades.
- [ ] Comparar resultados contra reglas reales de varias prop firms.

## Fase 2 — Ejecución en demo (paper trading)

- [ ] Adaptadores de broker (MetaTrader 5, exchanges de crypto, etc.) con modo demo.
- [ ] Motor de ejecución en vivo con gestión de riesgo (stop diario, kill-switch).
- [ ] Registro y monitoreo en tiempo real de la cuenta de challenge.

## Fase 3 — Línea de negocio: servicio de pase

- [ ] Multiusuario: cuentas, roles, credenciales de challenge por cliente.
- [ ] Pipeline de gestión de cuentas (asignar bot, monitorear, reportar).
- [ ] Pagos y facturación.
- [ ] Cumplimiento: términos de cada prop firm (muchas prohíben copy-trading/EA compartido — revisar caso por caso).

## Fase 4 — Línea de negocio: venta del bot

- [ ] Empaquetado del bot como producto + sistema de licencias.
- [ ] Portal de cliente: descarga, claves, documentación, soporte.
- [ ] Versionado y actualizaciones.

## Fase 5 — Línea de negocio: empresa de fondeo (prop firm)

- [ ] Definir reglas propias de challenge y planes de cuenta.
- [ ] Panel de traders, cuentas demo, evaluación automática con el motor de reglas.
- [ ] Gestión de payouts y tesorería.
- [ ] Marco legal y regulatorio (asesoría profesional imprescindible).

---

## Notas y riesgos a tener presentes

- **Legal/regulatorio:** operar una empresa de fondeo o un servicio de pase puede estar regulado según
  el país. Requiere asesoría legal antes de lanzar.
- **Términos de las prop firms:** muchas prohíben automatización compartida o "account passing". Hay que
  leer y respetar los términos de cada una.
- **Sin garantías:** el rendimiento pasado (incluido el de un backtest) no garantiza resultados futuros.
