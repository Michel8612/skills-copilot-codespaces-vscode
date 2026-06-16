import { useEffect, useState } from "react";
import { fetchMeta, optimizeStrategy, validateEdge } from "../api";
import type { OptimizeResult, ValidationResult } from "../api";
import type { Meta } from "../types";

const VERDICT: Record<string, { label: string; cls: string }> = {
  edge_prometedor: { label: "EDGE PROMETEDOR ✅", cls: "status-passed" },
  edge_debil: { label: "EDGE DÉBIL / MIXTO ⚠️", cls: "status-evaluation" },
  sin_evidencia: { label: "SIN EVIDENCIA ❌", cls: "status-failed" },
};

export function ValidationPanel() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [market, setMarket] = useState("crypto");
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [source, setSource] = useState("synthetic");
  const [strategy, setStrategy] = useState("breakout");
  const [bars, setBars] = useState(2000);
  const [leverage, setLeverage] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [res, setRes] = useState<ValidationResult | null>(null);
  const [opt, setOpt] = useState<OptimizeResult | null>(null);

  useEffect(() => {
    fetchMeta().then(setMeta).catch((e) => setError(String(e)));
  }, []);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setRes(await validateEdge({ market, symbol, source, strategy, bars, leverage, timeframe: "4h" }));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function runOptimize() {
    setLoading(true);
    setError(null);
    try {
      setOpt(await optimizeStrategy({ market, symbol, source, strategy, bars, leverage, metric: "return", timeframe: "4h" }));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const v = res ? VERDICT[res.verdict.label] : null;

  return (
    <>
      <section className="card">
        <h2 className="section-title">Validación de edge</h2>
        <p className="muted small">
          ¿La estrategia tiene ventaja real o fue suerte? Combina métricas de robustez, walk-forward
          (consistencia entre tramos) y Monte Carlo (distribución de resultados). Para una conclusión
          fiable, ejecútalo con <strong>datos reales</strong> (fuente Binance).
        </p>
        {meta && (
          <div className="grid">
            <label>Mercado
              <select value={market} onChange={(e) => setMarket(e.target.value)}>
                {meta.markets.map((m) => <option key={m}>{m}</option>)}
              </select>
            </label>
            <label>Símbolo
              <input value={symbol} onChange={(e) => setSymbol(e.target.value)} />
            </label>
            <label>Estrategia
              <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                {meta.strategies.map((s) => <option key={s.name} value={s.name}>{s.name}</option>)}
              </select>
            </label>
            <label>Datos
              <select value={source} onChange={(e) => setSource(e.target.value)}>
                {(meta.sources || ["synthetic"]).map((s) => (
                  <option key={s} value={s}>{s === "binance" ? "Binance (real)" : "Sintético"}</option>
                ))}
              </select>
            </label>
            <label>Velas
              <input type="number" value={bars} onChange={(e) => setBars(Number(e.target.value))} />
            </label>
            <label>Apalancamiento
              <input type="number" value={leverage} onChange={(e) => setLeverage(Number(e.target.value))} />
            </label>
          </div>
        )}
        <button onClick={run} disabled={loading}>{loading ? "Analizando…" : "Validar edge"}</button>
        <button className="tab" style={{ marginLeft: 8 }} onClick={runOptimize} disabled={loading}>
          Optimizar parámetros
        </button>
        {error && <p className="error">{error}</p>}
      </section>

      {opt && (
        <section className="card">
          <h3 className="section-title">Optimización de parámetros</h3>
          <p className="muted small">
            Mejor combinación (en muestra): <strong>{JSON.stringify(opt.grid_search.best?.params)}</strong>
            {" "}· entre {opt.grid_search.evaluated} combinaciones.
          </p>
          {opt.walk_forward_optimization.steps ? (
            <ul className="history">
              <li>
                <strong>Eficiencia walk-forward: {opt.walk_forward_optimization.wfo_efficiency}</strong>
                {" "}(≈1 = robusto · ≪1 = sobreajustado · &lt;0 = sin señal real)
              </li>
              <li>Tramos fuera de muestra rentables: {opt.walk_forward_optimization.pct_oos_profitable}%</li>
              <li>Retorno medio fuera de muestra: {opt.walk_forward_optimization.mean_oos_return_pct}%</li>
            </ul>
          ) : (
            <p className="muted small">{opt.walk_forward_optimization.note}</p>
          )}
          <p className="muted small">
            La eficiencia walk-forward es el filtro anti-overfitting: cuánto del rendimiento en muestra
            se mantiene fuera de muestra.
          </p>
        </section>
      )}

      {res && v && (
        <section className="card">
          <div className={`status ${v.cls}`}>{v.label} · {res.verdict.score}/{res.verdict.max_score}</div>
          <p>{res.verdict.summary}</p>

          <div className="metrics">
            <M label="Sharpe" value={res.metrics.sharpe} />
            <M label="Sortino" value={res.metrics.sortino} />
            <M label="Profit factor" value={res.metrics.profit_factor} />
            <M label="Expectativa" value={res.metrics.expectancy} />
            <M label="% Aciertos" value={res.metrics.win_rate_pct} suffix="%" />
            <M label="Operaciones" value={res.metrics.num_trades} />
          </div>

          <h3 className="section-title">Walk-forward (consistencia)</h3>
          <p className="muted small">
            {res.walk_forward.pct_folds_profitable}% de {res.walk_forward.folds} tramos rentables ·
            retornos por tramo: {res.walk_forward.fold_returns_pct.join("%, ")}%
          </p>

          <h3 className="section-title">Monte Carlo</h3>
          {res.monte_carlo.runs ? (
            <ul className="history">
              <li>Probabilidad de beneficio: <strong>{String(res.monte_carlo.prob_profit_pct)}%</strong></li>
              <li>Retorno mediano: {String(res.monte_carlo.return_median_pct)}% · rango P5–P95: {String(res.monte_carlo.return_p05_pct)}% a {String(res.monte_carlo.return_p95_pct)}%</li>
              <li>Drawdown máx mediano: {String(res.monte_carlo.max_drawdown_median_pct)}% · P95: {String(res.monte_carlo.max_drawdown_p95_pct)}%</li>
              <li>Prob. de violar {String(res.monte_carlo.dd_breach_threshold_pct)}% de drawdown: <strong>{String(res.monte_carlo.prob_dd_breach_pct)}%</strong></li>
            </ul>
          ) : (
            <p className="muted small">{String(res.monte_carlo.note || "Sin datos suficientes.")}</p>
          )}

          <ul className="history">
            {res.verdict.reasons.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </section>
      )}
    </>
  );
}

function M({ label, value, suffix = "" }: { label: string; value: number | null; suffix?: string }) {
  return (
    <div className="metric">
      <span className="metric-value">{value == null ? "—" : `${value}${suffix}`}</span>
      <span className="metric-label">{label}</span>
    </div>
  );
}
