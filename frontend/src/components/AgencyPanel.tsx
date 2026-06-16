import { useEffect, useState } from "react";
import { askAgency, fetchRoster } from "../api";
import type { AgencyResult, AgencyRoster } from "../types";

export function AgencyPanel() {
  const [roster, setRoster] = useState<AgencyRoster | null>(null);
  const [question, setQuestion] = useState(
    "¿Por dónde empezamos para que el bot pase challenges de forma comprobada y luego montar el negocio?"
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AgencyResult | null>(null);

  useEffect(() => {
    fetchRoster().then(setRoster).catch((e) => setError(String(e)));
  }, []);

  async function onAsk() {
    setLoading(true);
    setError(null);
    try {
      setResult(await askAgency({ question }));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className="card">
        <h2 className="section-title">Agencia de IA</h2>
        <p className="muted small">
          Un equipo de agentes especializados delibera sobre tus dilemas y un director sintetiza una
          recomendación. {roster && <>Backend activo: <strong>{roster.backend}</strong>.</>}
        </p>
        {roster && (
          <div className="roster">
            {roster.roster.map((a) => (
              <span key={a.key} className="agent-chip" title={a.mission}>
                {a.title}
              </span>
            ))}
          </div>
        )}
        <label>
          Tu pregunta o dilema
          <textarea rows={3} value={question} onChange={(e) => setQuestion(e.target.value)} />
        </label>
        <button onClick={onAsk} disabled={loading}>
          {loading ? "Deliberando…" : "Consultar a la agencia"}
        </button>
        {error && <p className="error">{error}</p>}
      </section>

      {result && (
        <section className="card">
          <h3 className="section-title">Recomendación del director</h3>
          <pre className="reco">{result.recommendation}</pre>

          <h3 className="section-title">Aportes del equipo</h3>
          {result.contributions.map((c) => (
            <details key={c.key} className="contribution">
              <summary>{c.title}</summary>
              <pre className="reco">{c.response}</pre>
            </details>
          ))}
        </section>
      )}
    </>
  );
}
