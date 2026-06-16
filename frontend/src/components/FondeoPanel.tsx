import { useEffect, useState } from "react";
import { evaluateAccount, fetchPlans, openAccount, registerTrader } from "../api";
import type { EvaluateResult, Plan } from "../types";

const STATUS_LABELS: Record<string, string> = {
  evaluation: "EN EVALUACIÓN ⏳",
  passed: "PASÓ ✅",
  failed: "FALLÓ ❌",
  funded: "FINANCIADA 🏦",
};

export function FondeoPanel() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("Ada Lovelace");
  const [email, setEmail] = useState("ada@example.com");
  const [busy, setBusy] = useState<number | null>(null);
  const [result, setResult] = useState<EvaluateResult | null>(null);

  useEffect(() => {
    fetchPlans().then(setPlans).catch((e) => setError(String(e)));
  }, []);

  async function tryPlan(plan: Plan) {
    setBusy(plan.id);
    setError(null);
    setResult(null);
    try {
      const trader = await registerTrader(name, email);
      const account = await openAccount(trader.id, plan.id);
      setResult(await evaluateAccount(account.id));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <section className="card">
        <h2 className="section-title">Empresa de fondeo (honesta)</h2>
        <p className="muted small">
          Reglas públicas e idénticas para todos, evaluadas por el mismo motor auditable. Registra un
          trader, abre una cuenta en un plan y deja que el bot la evalúe — verás el veredicto exacto.
        </p>
        <div className="grid">
          <label>
            Trader
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      <section className="card">
        <h3 className="section-title">Planes publicados</h3>
        <div className="plans">
          {plans.map((p) => (
            <div key={p.id} className="plan">
              <div className="plan-head">
                <strong>{p.name}</strong>
                <span className="agent-chip">{p.market}</span>
              </div>
              <ul className="plan-rules">
                <li>Cuenta: {p.account_size.toLocaleString()} · Precio: {p.price}</li>
                <li>El trader se queda el <strong>{p.profit_split_pct}%</strong> del beneficio</li>
                <li>Objetivo {p.profit_target_pct}% · Pérdida diaria máx {p.max_daily_loss_pct}%</li>
                <li>Drawdown máx {p.max_total_drawdown_pct}% ({p.drawdown_mode}) · Días mín {p.min_trading_days}</li>
              </ul>
              <button onClick={() => tryPlan(p)} disabled={busy !== null}>
                {busy === p.id ? "Evaluando…" : "Probar con el bot"}
              </button>
            </div>
          ))}
        </div>
      </section>

      {result && (
        <section className="card">
          <div className={`status status-${result.account.status}`}>
            {STATUS_LABELS[result.account.status] || result.account.status}
          </div>
          {result.verdict.breach_detail && <p className="error">{result.verdict.breach_detail}</p>}
          <div className="metrics">
            <Metric label="Equity final" value={(result.account.final_equity ?? 0).toLocaleString()} />
            <Metric label="Retorno" value={`${result.account.return_pct ?? 0}%`} />
            <Metric label="Drawdown máx" value={`${result.account.max_drawdown_pct ?? 0}%`} />
            <Metric label="Operaciones" value={String(result.backtest_stats.num_trades)} />
          </div>
        </section>
      )}
    </>
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
