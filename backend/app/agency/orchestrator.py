"""Orchestrates a multi-agent deliberation and synthesizes a recommendation."""

from __future__ import annotations

from typing import Dict, List, Optional

from .providers import LLMProvider, get_provider
from .roster import DIRECTOR, AgentRole, select_agents


def _agent_user_prompt(question: str, context: Optional[str]) -> str:
    parts = [f"Consulta del equipo:\n{question}"]
    if context:
        parts.append(f"\nContexto/datos disponibles:\n{context}")
    parts.append(
        "\nResponde desde tu especialidad, en 4-8 puntos concretos y accionables."
    )
    return "\n".join(parts)


def deliberate(
    question: str,
    context: Optional[str] = None,
    max_agents: int = 4,
    provider: Optional[LLMProvider] = None,
) -> Dict:
    """Run the selected specialists, then the Managing Director's synthesis."""
    provider = provider or get_provider()
    agents: List[AgentRole] = select_agents(question, max_agents=max_agents)

    contributions = []
    for agent in agents:
        text = provider.complete(
            system=agent.full_system(),
            user=_agent_user_prompt(question, context),
            max_tokens=900,
        )
        contributions.append({"key": agent.key, "title": agent.title, "response": text})

    # Director synthesis over the specialists' contributions.
    panel = "\n\n".join(f"## {c['title']}\n{c['response']}" for c in contributions)
    director_user = (
        f"Consulta original:\n{question}\n\n"
        f"Aportes del equipo:\n{panel}\n\n"
        "Sintetiza UNA recomendación priorizada y accionable, con riesgos clave "
        "y el siguiente paso concreto."
    )
    recommendation = provider.complete(
        system=DIRECTOR.full_system(), user=director_user, max_tokens=900
    )

    return {
        "backend": provider.backend,
        "question": question,
        "panel": [{"key": c["key"], "title": c["title"]} for c in contributions],
        "contributions": contributions,
        "recommendation": recommendation,
    }
