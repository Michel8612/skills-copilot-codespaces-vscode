import { useEffect, useState } from "react";
import { fetchMeta, runBacktest } from "./api";
import type { Meta, RunResult } from "./types";
import { EquityChart } from "./components/EquityChart";
import { AgencyPanel } from "./components/AgencyPanel";

const STATUS_LABELS: Record<string, string> = {
  passed: "PASÓ ✅",
  failed: "FALLÓ ❌",
  in_progress: "EN CURSO ⏳",
};

export function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [tab, setTab] = useState<"backtest" | "agency">("backtest");

  // Form state
  const [market, setMarket] = useState("forex");
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("4h");
  const [bars, setBars] = useState(1200);
  const [strategy, setStrategy] = useState("breakout");
  const [leverage, setLeverage] = useState(10);
  const [preset, setPreset] = useState("forex_2step_p1");

  useEffect(() => {
    fetchMeta()
      .then((m) => {
        setMeta(m);
        if (m.markets[0]) setMarket(m.markets[0]);
        if (m.strategies[0]) setStrategy(m.strategies[0].name);
        const firstPreset = Object.keys(m.presets)[0];
        if (firstPreset) setPreset(firstPreset);
      })
      .catch((e) => setError(String(e)));
  }, []);

  async function onRun() {
    setLoading(true);
    setError(null);
    try {
      const res = await runBacktest({
        market,
        symbol,
        timeframe,
        bars,
        strategy,
        strategy_params: {},
        leverage,
        preset,
      });
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  if (!meta) {
    return (
      <div className="app">
        <h1>Fondeo Bot</h1>
        {error ? <p className="error">No se pudo conectar al backend: {error}</p> : <p>Cargando…</p>}
      </div>
    );
  }

  const cfg = meta.presets[preset];

  return (
    <div className="app">
      <header>
        <h1>Fondeo Bot</h1>
        <p className="muted">
          Motor de trading + evaluación de challenges, y una agencia de IA que resuelve los dilemas del proyecto.
        </p>
        <nav className="tabs">
          <button className={tab === "backtest" ? "tab active" : "tab"} onClick={() => setTab("backtest")}>
            Backtest &amp; Challenge
          </button>
          <button className={tab === "agency" ? "tab active" : "tab"} onClick={() => setTab("agency")}>
            Agencia IA
          </button>
        </nav>
      </header>

      {tab === "agency" && <AgencyPanel />}

      {tab === "backtest" && (
      <>
      <section className="card form">
        <div className="grid">
          <label>
            Mercado
            <select value={market} onChange={(e) => setMarket(e.target.value)}>
              {meta.markets.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </label>
          <label>
            Símbolo
            <input value={symbol} onChange={(e) => setSymbol(e.target.value)} />
          </label>
          <label>
            Timeframe
            <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
              {meta.timeframes.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>
          <label>
            Nº de velas
            <input type="number" value={bars} onChange={(e) => setBars(Number(e.target.value))} />
          </label>
          <label>
            Estrategia
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
              {meta.strategies.map((s) => (
                <option key={s.name} value={s.name}>{s.name}</option>
              ))}
            </select>
          </label>
          <label>
            Apalancamiento
            <input type="number" value={leverage} onChange={(e) => setLeverage(Number(e.target.value))} />
          </label>
          <label>
            Challenge (preset)
            <select value={preset} onChange={(e) => setPreset(e.target.value)}>
              {Object.keys(meta.presets).map((k) => (
                <option key={k} value={k}>{meta.presets[k].name}</option>
              ))}
            </select>
          </label>
        </div>

        {cfg && (
          <p className="muted small">
            Objetivo {cfg.profit_target_pct}% · Pérdida diaria máx {cfg.max_daily_loss_pct}% · Drawdown máx{" "}
            {cfg.max_total_drawdown_pct}% ({cfg.drawdown_mode}) · Días mín {cfg.min_trading_days}
          </p>
        )}

        <button onClick={onRun} disabled={loading}>
          {loading ? "Ejecutando…" : "Ejecutar backtest"}
        </button>
        {error && <p className="error">{error}</p>}
      </section>

      {result && (
        <section className="card">
          <div className={`status status-${result.challenge.status}`}>
            {STATUS_LABELS[result.challenge.status] || result.challenge.status}
          </div>
          {result.challenge.breach_detail && (
            <p className="error">{result.challenge.breach_detail}</p>
          )}

          <div className="metrics">
            <Metric label="Equity final" value={result.backtest.final_equity.toLocaleString()} />
            <Metric label="Retorno" value={`${result.backtest.stats.total_return_pct}%`} />
            <Metric label="Drawdown máx" value={`${result.backtest.stats.max_drawdown_pct}%`} />
            <Metric label="Operaciones" value={String(result.backtest.stats.num_trades)} />
            <Metric label="% Aciertos" value={`${result.backtest.stats.win_rate_pct}%`} />
            <Metric label="Días operados" value={String(result.challenge.metrics.trading_days ?? "-")} />
          </div>

          <EquityChart curve={result.backtest.equity_curve} accountSize={result.backtest.account_size} />
        </section>
      )}
      </>
      )}

      <footer className="muted small">
        ⚠️ Datos simulados para fines de validación. El trading conlleva riesgo real de pérdida; ningún
        backtest garantiza resultados futuros.
      </footer>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span className="metric-value">{value}</span>
      <span className="metric-label">{label}</span>
    </div>
  );
}
