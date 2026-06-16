import { useEffect, useState } from "react";
import { fetchHistory, login, register } from "../api";
import type { AuthResponse } from "../api";

type History = Awaited<ReturnType<typeof fetchHistory>>;

const TOKEN_KEY = "fondeo_token";

export function ClientPanel() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [trader, setTrader] = useState<AuthResponse["trader"] | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token) fetchHistory(token).then(setHistory).catch(() => logout());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function submit() {
    setError(null);
    try {
      const res = mode === "register" ? await register(name, email, password) : await login(email, password);
      localStorage.setItem(TOKEN_KEY, res.token);
      setTrader(res.trader);
      setToken(res.token);
    } catch (e) {
      setError(String(e));
    }
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setTrader(null);
    setHistory(null);
  }

  if (!token) {
    return (
      <section className="card">
        <h2 className="section-title">Mi cuenta</h2>
        <nav className="tabs">
          <button className={mode === "login" ? "tab active" : "tab"} onClick={() => setMode("login")}>
            Iniciar sesión
          </button>
          <button className={mode === "register" ? "tab active" : "tab"} onClick={() => setMode("register")}>
            Registrarme
          </button>
        </nav>
        <div className="grid">
          {mode === "register" && (
            <label>
              Nombre
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </label>
          )}
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Contraseña
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
        </div>
        <button onClick={submit}>{mode === "register" ? "Crear cuenta" : "Entrar"}</button>
        {error && <p className="error">{error}</p>}
      </section>
    );
  }

  return (
    <>
      <section className="card">
        <div className="plan-head">
          <h2 className="section-title">Hola{trader ? `, ${trader.name}` : ""} 👋</h2>
          <button className="tab" onClick={logout}>Cerrar sesión</button>
        </div>
        <p className="muted small">Tu historial en las tres líneas del negocio, en un solo lugar.</p>
      </section>

      {history && (
        <section className="card">
          <h3 className="section-title">Cuentas de fondeo</h3>
          {history.accounts.length === 0 ? (
            <p className="muted small">Aún no tienes cuentas. Abre una en la pestaña Fondeo.</p>
          ) : (
            <ul className="history">
              {history.accounts.map((a) => (
                <li key={a.id}>
                  Cuenta #{a.id} · plan {a.plan_id} · <strong>{a.status}</strong>
                  {a.return_pct != null && ` · ${a.return_pct}%`}
                </li>
              ))}
            </ul>
          )}

          <h3 className="section-title">Licencias del bot</h3>
          {history.licenses.length === 0 ? (
            <p className="muted small">Sin licencias activas.</p>
          ) : (
            <ul className="history">
              {history.licenses.map((l) => (
                <li key={l.id}>Licencia #{l.id} · tier {l.tier_id} · <strong>{l.status}</strong></li>
              ))}
            </ul>
          )}

          <h3 className="section-title">Servicios de pase</h3>
          {history.pass_orders.length === 0 ? (
            <p className="muted small">Sin órdenes de pase.</p>
          ) : (
            <ul className="history">
              {history.pass_orders.map((o) => (
                <li key={o.id}>
                  Orden #{o.id} · plan {o.plan_id} · <strong>{o.status}</strong> · {o.attempts} intento(s)
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  );
}
