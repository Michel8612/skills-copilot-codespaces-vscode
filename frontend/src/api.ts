import type { Meta, RunResult } from "./types";

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
