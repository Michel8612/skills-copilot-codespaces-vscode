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

export interface AgentInfo {
  key: string;
  title: string;
  mission: string;
}

export interface AgencyRoster {
  backend: string;
  roster: AgentInfo[];
}

export interface AgencyResult {
  backend: string;
  question: string;
  panel: { key: string; title: string }[];
  contributions: { key: string; title: string; response: string }[];
  recommendation: string;
}

export interface Plan {
  id: number;
  name: string;
  line: string;
  market: string;
  account_size: number;
  price: number;
  profit_split_pct: number;
  profit_target_pct: number;
  max_daily_loss_pct: number;
  max_total_drawdown_pct: number;
  drawdown_mode: string;
  min_trading_days: number;
  max_calendar_days: number;
}

export interface Account {
  id: number;
  trader_id: number;
  plan_id: number;
  status: string;
  starting_balance: number;
  final_equity: number | null;
  return_pct: number | null;
  max_drawdown_pct: number | null;
  breached_rule: string | null;
}

export interface EvaluateResult {
  account: Account;
  verdict: { status: string; breached_rule: string | null; breach_detail: string | null };
  backtest_stats: Record<string, number>;
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
