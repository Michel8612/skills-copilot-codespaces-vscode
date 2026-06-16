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

// --- Client panel auth ---

export interface AuthResponse {
  token: string;
  trader: { id: number; name: string; email: string };
}

export const register = (name: string, email: string, password: string) =>
  postJSON<AuthResponse>("/auth/register", { name, email, password });

export const login = (email: string, password: string) =>
  postJSON<AuthResponse>("/auth/login", { email, password });

export interface ValidationResult {
  metrics: Record<string, number | null>;
  walk_forward: { folds: number; fold_returns_pct: number[]; pct_folds_profitable: number; mean_fold_return_pct: number };
  monte_carlo: Record<string, number | string>;
  verdict: { score: number; max_score: number; label: string; summary: string; reasons: string[] };
}

export const validateEdge = (payload: Record<string, unknown>) =>
  postJSON<ValidationResult>("/validate", payload);

export interface OptimizeResult {
  grid_search: { metric: string; evaluated: number; best: { params: Record<string, number>; score: number } | null; top: { params: Record<string, number>; score: number }[] };
  walk_forward_optimization: {
    steps?: number; note?: string; wfo_efficiency?: number;
    pct_oos_profitable?: number; mean_oos_return_pct?: number;
    mean_in_sample_score?: number; mean_out_of_sample_score?: number;
  };
}

export const optimizeStrategy = (payload: Record<string, unknown>) =>
  postJSON<OptimizeResult>("/optimize", payload);

export async function fetchHistory(token: string) {
  const res = await fetch(`${BASE}/me/history`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`history failed: ${res.status}`);
  return res.json() as Promise<{
    accounts: { id: number; plan_id: number; status: string; return_pct: number | null }[];
    licenses: { id: number; tier_id: number; status: string }[];
    pass_orders: { id: number; plan_id: number; status: string; attempts: number }[];
  }>;
}
