"""Pluggable LLM providers for the agency.

Two implementations:
  * AnthropicProvider — uses the official `anthropic` SDK with Claude. Activated
    only when the package is installed AND an API key is configured.
  * OfflineProvider — deterministic, rule-based responses. No network, no tokens.
    This is the default so the whole system runs and is testable without a key.

`get_provider()` picks the best available option and is the single entry point.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

# Latest, most capable Claude model. Adaptive thinking is the recommended mode.
DEFAULT_MODEL = "claude-opus-4-8"


class LLMProvider(ABC):
    name: str = "base"
    backend: str = "base"

    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        """Return the assistant's text response for a single turn."""


class OfflineProvider(LLMProvider):
    """Deterministic responder used when no LLM API is configured.

    It does not fabricate analysis it cannot do — instead each agent returns a
    structured, role-specific checklist of what it would examine, plus any
    concrete figures passed in via the prompt context. Honest and reproducible.
    """

    name = "offline"
    backend = "offline (rule-based)"

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        # The role's guidance is embedded in the system prompt after the marker.
        guidance = system.split("OFFLINE_GUIDANCE:", 1)[-1].strip()
        return (
            "(Modo offline · sin LLM) Análisis basado en reglas para esta consulta.\n\n"
            f"{guidance}\n\n"
            "Para un análisis razonado y específico, configura ANTHROPIC_API_KEY "
            "y se usará Claude automáticamente."
        )


class AnthropicProvider(LLMProvider):
    """Claude-backed provider via the official Anthropic SDK."""

    name = "anthropic"

    def __init__(self, model: str = DEFAULT_MODEL):
        import anthropic  # imported lazily; optional dependency

        self.model = model
        self.backend = f"Claude ({model})"
        self._client = anthropic.Anthropic()

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        # Strip the offline-only guidance marker before sending to Claude.
        system = system.split("OFFLINE_GUIDANCE:", 1)[0].strip()
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in response.content if b.type == "text").strip()


def anthropic_available() -> bool:
    if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def get_provider() -> LLMProvider:
    if anthropic_available():
        try:
            return AnthropicProvider()
        except Exception:
            # Any SDK/init issue falls back to offline rather than failing the request.
            return OfflineProvider()
    return OfflineProvider()
