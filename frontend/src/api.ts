import type {
  Account,
  AgencyResult,
  AgencyRoster,
  EvaluateResult,
  Meta,
  Plan,
  RunResult,
} from "./types";

const BASE = "/api";

export async function fetchMeta(): Promise<Meta> {
  const res = await fetch(`${BASE}/meta`);
  if (!res.ok) throw new Error(`meta failed: ${res.status}`);
  return res.json();
}

export interface RunPayload {
  market: string;
  symbol: string;
  timeframe: string;
  bars: number;
  strategy: string;
  strategy_params: Record<string, unknown>;
  leverage: number;
  source?: string;
  preset?: string | null;
  challenge?: unknown;
}

export async function runBacktest(payload: RunPayload): Promise<RunResult> {
  const res = await fetch(`${BASE}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `run failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchRoster(): Promise<AgencyRoster> {
  const res = await fetch(`${BASE}/agency/roster`);
  if (!res.ok) throw new Error(`roster failed: ${res.status}`);
  return res.json();
}

export async function askAgency(payload: {
  question: string;
  max_agents?: number;
  run?: RunPayload;
}): Promise<AgencyResult> {
  const res = await fetch(`${BASE}/agency/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `ask failed: ${res.status}`);
  }
  return res.json();
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `request failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchPlans(): Promise<Plan[]> {
  const res = await fetch(`${BASE}/fondeo/plans`);
  if (!res.ok) throw new Error(`plans failed: ${res.status}`);
  return res.json();
}

export const registerTrader = (name: string, email: string) =>
  postJSON<{ id: number }>("/fondeo/traders", { name, email });

export const openAccount = (trader_id: number, plan_id: number) =>
  postJSON<Account>("/fondeo/accounts", { trader_id, plan_id });

export const evaluateAccount = (accountId: number) =>
  postJSON<EvaluateResult>(`/fondeo/accounts/${accountId}/evaluate`, {
    strategy: "breakout",
    leverage: 3,
  });
