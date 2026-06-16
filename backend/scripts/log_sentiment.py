"""Forward-log Myfxbook retail sentiment so we can backtest it later.

Each run appends the current long% for the configured symbols to
`data/sentiment/<SYMBOL>.json` as {iso_timestamp: long_pct}. Intended to run on
a schedule (e.g. hourly via GitHub Actions). It is a deliberate NO-OP when
credentials are absent, so the scheduled job stays green until configured.

Env:
  MYFXBOOK_EMAIL, MYFXBOOK_PASSWORD  - credentials (set as repo secrets)
  SENTIMENT_SYMBOLS                  - comma list (default majors + gold)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine.myfxbook import fetch_community_outlook  # noqa: E402

DEFAULT_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US30"]
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sentiment"


def _append(symbol: str, ts: str, long_pct: float) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{symbol}.json"
    series = json.loads(path.read_text()) if path.exists() else {}
    series[ts] = round(long_pct, 2)
    path.write_text(json.dumps(series, indent=0, sort_keys=True))


def main() -> int:
    email = os.environ.get("MYFXBOOK_EMAIL")
    password = os.environ.get("MYFXBOOK_PASSWORD")
    if not email or not password:
        print("MYFXBOOK_EMAIL/PASSWORD not set — skipping (no-op).")
        return 0

    symbols = [s.strip().upper() for s in
               os.environ.get("SENTIMENT_SYMBOLS", ",".join(DEFAULT_SYMBOLS)).split(",") if s.strip()]
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    snapshot = fetch_community_outlook(email, password)

    logged = 0
    for sym in symbols:
        if sym in snapshot:
            _append(sym, ts, snapshot[sym])
            logged += 1
            print(f"{sym}: long {snapshot[sym]:.1f}% @ {ts}")
        else:
            print(f"{sym}: not in Myfxbook outlook, skipped")
    print(f"Logged {logged}/{len(symbols)} symbols.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
