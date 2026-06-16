"""Minimal Myfxbook Community Outlook client (stdlib only).

Myfxbook publishes the *current* retail positioning per symbol (% of accounts
long vs short) through its public API. It does NOT offer a free history, so to
backtest a sentiment strategy we must log this forward over time (see
`scripts/log_sentiment.py`). This module isolates the HTTP call from parsing so
the parsing is unit-testable without network access.

API (current at time of writing):
  POST /api/login.json?email=&password=            -> {"error":false,"session":...}
  GET  /api/get-community-outlook.json?session=     -> {"symbols":[{name,longPercentage,...}]}
"""

from __future__ import annotations

import json
from typing import Callable, Dict
from urllib.parse import urlencode
from urllib.request import urlopen

BASE = "https://www.myfxbook.com/api"


def parse_community_outlook(payload: dict) -> Dict[str, float]:
    """Turn a community-outlook response into {symbol: long_percentage}."""
    if payload.get("error"):
        raise RuntimeError(f"Myfxbook error: {payload.get('message')}")
    out: Dict[str, float] = {}
    for sym in payload.get("symbols", []):
        name = sym.get("name")
        if name is None:
            continue
        out[str(name).upper()] = float(sym.get("longPercentage", 0.0))
    return out


def _get_json(url: str, opener: Callable = urlopen) -> dict:
    with opener(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def login(email: str, password: str, opener: Callable = urlopen) -> str:
    url = f"{BASE}/login.json?" + urlencode({"email": email, "password": password})
    data = _get_json(url, opener)
    if data.get("error") or not data.get("session"):
        raise RuntimeError(f"Myfxbook login failed: {data.get('message')}")
    return str(data["session"])


def fetch_community_outlook(email: str, password: str, opener: Callable = urlopen) -> Dict[str, float]:
    """Log in and return the current {symbol: long_percentage} snapshot."""
    session = login(email, password, opener)
    url = f"{BASE}/get-community-outlook.json?" + urlencode({"session": session})
    return parse_community_outlook(_get_json(url, opener))
