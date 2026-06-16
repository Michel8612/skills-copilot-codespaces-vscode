export interface StrategyInfo {
  name: string;
  params: Record<string, unknown>;
}

export interface ChallengeConfig {
  name: string;
  account_size: number;
  profit_target_pct: number;
  max_daily_loss_pct: number;
  max_total_drawdown_pct: number;
  drawdown_mode: "static" | "trailing";
  min_trading_days: number;
  max_calendar_days: number;
}

export interface Meta {
  markets: string[];
  timeframes: string[];
  strategies: StrategyInfo[];
  presets: Record<string, ChallengeConfig>;
}

export interface EquityPoint {
  time: string;
  equity: number;
  equity_high: number;
  equity_low: number;
}

export interface RunResult {
  backtest: {
    account_size: number;
    final_equity: number;
    equity_curve: EquityPoint[];
    trades: unknown[];
    stats: Record<string, number>;
  };
  challenge: {
    status: "passed" | "failed" | "in_progress";
    breached_rule: string | null;
    breach_detail: string | null;
    breach_time: string | null;
    pass_time: string | null;
    metrics: Record<string, number>;
  };
  challenge_config: ChallengeConfig;
}
