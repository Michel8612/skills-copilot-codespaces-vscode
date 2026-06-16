import type { EquityPoint } from "../types";

interface Props {
  curve: EquityPoint[];
  accountSize: number;
}

/**
 * Lightweight inline-SVG equity curve. Avoids a charting dependency while still
 * giving a clear visual of the run, the starting balance and the high-water mark.
 */
export function EquityChart({ curve, accountSize }: Props) {
  if (curve.length === 0) return null;

  const W = 760;
  const H = 280;
  const pad = 40;

  const equities = curve.map((p) => p.equity);
  const min = Math.min(...equities, accountSize);
  const max = Math.max(...equities, accountSize);
  const range = max - min || 1;

  const x = (i: number) => pad + (i / (curve.length - 1)) * (W - 2 * pad);
  const y = (v: number) => H - pad - ((v - min) / range) * (H - 2 * pad);

  const path = curve.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(p.equity).toFixed(1)}`).join(" ");
  const baseY = y(accountSize);

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="chart">
      {/* starting balance line */}
      <line x1={pad} y1={baseY} x2={W - pad} y2={baseY} stroke="#888" strokeDasharray="4 4" />
      <text x={pad} y={baseY - 6} className="chart-label">
        Inicio {accountSize.toLocaleString()}
      </text>
      <path d={path} fill="none" stroke="#2d9cdb" strokeWidth={2} />
      <text x={W - pad} y={y(equities[equities.length - 1]) - 6} textAnchor="end" className="chart-label">
        {equities[equities.length - 1].toLocaleString(undefined, { maximumFractionDigits: 0 })}
      </text>
    </svg>
  );
}
