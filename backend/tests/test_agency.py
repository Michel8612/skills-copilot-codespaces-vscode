"""Tests for the AI Agency (offline provider — no API key, no tokens)."""

from app.agency.orchestrator import deliberate
from app.agency.providers import OfflineProvider, get_provider
from app.agency.roster import list_roster, select_agents


def test_roster_is_populated():
    roster = list_roster()
    assert len(roster) >= 5
    assert all("key" in a and "title" in a for a in roster)


def test_routing_picks_relevant_agents():
    agents = select_agents("¿Qué riesgo y drawdown debo permitir por operación?")
    keys = {a.key for a in agents}
    assert "risk" in keys


def test_routing_picks_compliance_for_legal_questions():
    agents = select_agents("¿Es legal montar una empresa de fondeo y vender pases?")
    keys = {a.key for a in agents}
    assert "compliance" in keys


def test_routing_defaults_when_no_keywords():
    agents = select_agents("Hola equipo, ¿por dónde empezamos?")
    assert len(agents) >= 3  # default cross-functional panel


def test_deliberate_offline_returns_structure():
    provider = OfflineProvider()
    out = deliberate(
        "¿Cómo valido que la estrategia tiene edge antes de vender el bot?",
        context="Backtest forex: retorno=-24%, drawdown_max=29%, veredicto=failed.",
        provider=provider,
    )
    assert out["backend"].startswith("offline")
    assert len(out["contributions"]) >= 1
    assert out["recommendation"]
    # Each contribution carries a non-empty response.
    assert all(c["response"] for c in out["contributions"])


def test_get_provider_returns_offline_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    assert get_provider().name == "offline"
