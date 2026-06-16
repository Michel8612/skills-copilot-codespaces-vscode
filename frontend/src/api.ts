import type { AgencyResult, AgencyRoster, Meta, RunResult } from "./types";

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
