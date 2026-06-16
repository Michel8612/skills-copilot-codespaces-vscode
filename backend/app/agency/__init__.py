"""The AI Agency: a multi-agent layer that resolves project dilemmas.

Specialized agents (strategy, risk, data, compliance, business) deliberate on a
question and a Managing Director synthesizes a recommendation. The LLM backend is
pluggable: it runs fully offline with deterministic, rule-based responses (no API
key, no token spend — ideal for tests/CI) and uses Claude when configured.
"""
