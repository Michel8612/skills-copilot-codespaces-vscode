"""Tests for Myfxbook parsing and the forward-logger (no network)."""

import io
import json

import pytest

from app.engine.myfxbook import fetch_community_outlook, parse_community_outlook


def test_parse_community_outlook_extracts_long_pct():
    payload = {
        "error": False,
        "symbols": [
            {"name": "EURUSD", "longPercentage": 62.5, "shortPercentage": 37.5},
            {"name": "usdjpy", "longPercentage": 30, "shortPercentage": 70},
        ],
    }
    out = parse_community_outlook(payload)
    assert out == {"EURUSD": 62.5, "USDJPY": 30.0}


def test_parse_community_outlook_raises_on_error():
    with pytest.raises(RuntimeError):
        parse_community_outlook({"error": True, "message": "bad session"})


def test_fetch_community_outlook_with_fake_opener():
    responses = {
        "login": {"error": False, "session": "abc"},
        "outlook": {"error": False, "symbols": [{"name": "XAUUSD", "longPercentage": 80}]},
    }

    def fake_opener(url, timeout=0):
        body = responses["login"] if "login.json" in url else responses["outlook"]
        return io.BytesIO(json.dumps(body).encode("utf-8"))

    out = fetch_community_outlook("a@b.c", "pw", opener=fake_opener)
    assert out == {"XAUUSD": 80.0}


def test_logger_is_noop_without_credentials(monkeypatch):
    monkeypatch.delenv("MYFXBOOK_EMAIL", raising=False)
    monkeypatch.delenv("MYFXBOOK_PASSWORD", raising=False)
    import importlib

    log_sentiment = importlib.import_module("scripts.log_sentiment")
    assert log_sentiment.main() == 0
