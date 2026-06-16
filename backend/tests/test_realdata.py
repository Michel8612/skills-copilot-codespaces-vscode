"""Tests for the real-data provider — no network (parsing + selection + errors)."""

import pytest

from app.engine.data import (
    BinanceDataProvider,
    SyntheticDataProvider,
    get_data_provider,
    parse_klines,
    supported_sources,
    _normalize_symbol,
)

# A sample of the Binance klines payload shape: [openTime, o, h, l, c, volume, ...]
SAMPLE_KLINES = [
    [1700000000000, "42000.0", "42500.0", "41800.0", "42300.0", "120.5", 1700003599999],
    [1700003600000, "42300.0", "42900.0", "42100.0", "42800.0", "98.2", 1700007199999],
]


def test_parse_klines_maps_fields():
    bars = parse_klines(SAMPLE_KLINES)
    assert len(bars) == 2
    assert bars[0].open == 42000.0
    assert bars[0].high == 42500.0
    assert bars[1].close == 42800.0
    assert bars[1].time > bars[0].time  # chronological


def test_symbol_normalization():
    assert _normalize_symbol("AUTO") == "BTCUSDT"
    assert _normalize_symbol("btc-usd") == "BTCUSDT"
    assert _normalize_symbol("ETHUSDT") == "ETHUSDT"


def test_supported_sources():
    assert set(supported_sources()) == {"synthetic", "binance"}


def test_get_data_provider_selection():
    assert isinstance(get_data_provider("synthetic"), SyntheticDataProvider)
    assert isinstance(get_data_provider("binance"), BinanceDataProvider)
    with pytest.raises(ValueError):
        get_data_provider("nope")


def test_binance_rejects_non_crypto_market():
    with pytest.raises(ValueError):
        BinanceDataProvider().get_bars("forex", "EURUSD", "1h", 100)


def test_binance_network_failure_is_friendly(monkeypatch):
    # Point the provider at an unroutable host so the fetch fails fast, and
    # confirm we surface a clear, actionable ValueError (not a raw URLError).
    provider = BinanceDataProvider(base="http://127.0.0.1:9")  # closed port
    with pytest.raises(ValueError) as exc:
        provider.get_bars("crypto", "BTCUSDT", "1h", 50)
    assert "synthetic" in str(exc.value)
