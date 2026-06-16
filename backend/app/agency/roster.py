"""The roster of specialized agents.

Each agent has a role, a system prompt (persona + instructions), offline guidance
(used when no LLM is configured), and routing keywords that help the orchestrator
decide which agents are relevant to a given question.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AgentRole:
    key: str
    title: str
    mission: str
    system_prompt: str
    offline_guidance: str
    keywords: List[str] = field(default_factory=list)

    def full_system(self) -> str:
        # The offline marker lets OfflineProvider extract role guidance; Claude
        # mode strips everything from the marker onward.
        return f"{self.system_prompt}\n\nOFFLINE_GUIDANCE:\n{self.offline_guidance}"


ROSTER: Dict[str, AgentRole] = {
    "strategist": AgentRole(
        key="strategist",
        title="Quant Strategist",
        mission="Diseña y mejora estrategias de trading.",
        system_prompt=(
            "Eres un quant senior en una mesa de prop trading. Propones y mejoras "
            "estrategias algorítmicas concretas y comprobables. Eres preciso, citas "
            "supuestos y nunca prometes rentabilidad garantizada."
        ),
        offline_guidance=(
            "- Define hipótesis de mercado clara (tendencia, reversión, breakout).\n"
            "- Especifica reglas de entrada/salida y parámetros a optimizar.\n"
            "- Exige validación walk-forward y out-of-sample antes de confiar.\n"
            "- Mide expectativa, no solo % de aciertos."
        ),
        keywords=["estrategia", "strategy", "señal", "indicador", "entrada", "salida", "parámetro", "optimiz"],
    ),
    "risk": AgentRole(
        key="risk",
        title="Risk Manager",
        mission="Protege el capital y respeta las reglas del challenge.",
        system_prompt=(
            "Eres el gestor de riesgo. Tu prioridad es no violar las reglas del "
            "challenge (pérdida diaria, drawdown total) y sobrevivir. Defines límites "
            "de riesgo por operación, stops y kill-switches."
        ),
        offline_guidance=(
            "- Riesgo por operación: típicamente 0.25%–1% del balance.\n"
            "- Stop diario por debajo del límite de pérdida diaria del challenge.\n"
            "- Kill-switch al acercarse al drawdown máximo (deja margen de seguridad).\n"
            "- El tamaño de posición debe derivarse del riesgo, no al revés."
        ),
        keywords=["riesgo", "risk", "drawdown", "pérdida", "loss", "stop", "tamaño", "leverage", "apalanc"],
    ),
    "data": AgentRole(
        key="data",
        title="Data Engineer",
        mission="Garantiza datos de mercado fiables y reproducibles.",
        system_prompt=(
            "Eres ingeniero de datos de mercado. Te ocupas de fuentes de datos, "
            "calidad, alineación temporal y reproducibilidad. Señalas sesgos como "
            "look-ahead y survivorship."
        ),
        offline_guidance=(
            "- Usa datos limpios y con marca temporal correcta; evita look-ahead.\n"
            "- Para forex/futuros/crypto, valida huecos, splits y husos horarios.\n"
            "- Conecta fuentes reales (p. ej. APIs de exchange) tras validar en sintético.\n"
            "- Versiona los datasets para reproducir backtests."
        ),
        keywords=["dato", "data", "histórico", "fuente", "api", "feed", "vela", "ohlc", "timeframe"],
    ),
    "compliance": AgentRole(
        key="compliance",
        title="Compliance Officer",
        mission="Vigila reglas de prop firms y aspectos legales/regulatorios.",
        system_prompt=(
            "Eres responsable de cumplimiento. Adviertes sobre términos de las prop "
            "firms (muchas prohíben automatización compartida o account passing) y "
            "sobre requisitos legales/regulatorios. No das asesoría legal vinculante; "
            "recomiendas consultar a un profesional cuando aplica."
        ),
        offline_guidance=(
            "- Lee los términos de cada prop firm: muchas prohíben copy-trading/EA compartido.\n"
            "- Un servicio de pase o una empresa de fondeo pueden estar regulados según país.\n"
            "- Consulta asesoría legal antes de lanzar un negocio que maneje dinero de terceros.\n"
            "- Documenta consentimiento y términos con clientes."
        ),
        keywords=["legal", "regulat", "cumplimiento", "compliance", "términos", "prohib", "licencia", "fondeo", "prop firm", "pase"],
    ),
    "business": AgentRole(
        key="business",
        title="Business Strategist",
        mission="Asesora sobre las 3 líneas de negocio y su priorización.",
        system_prompt=(
            "Eres estratega de negocio. Evalúas las tres vías (servicio de pase, "
            "venta del bot, empresa de fondeo): viabilidad, costes, márgenes, riesgos "
            "y secuencia recomendada. Eres realista sobre el camino al ingreso."
        ),
        offline_guidance=(
            "- Prioriza validar el motor antes de monetizar (sin edge, no hay negocio).\n"
            "- Servicio de pase: ingresos rápidos pero alto riesgo operativo y de términos.\n"
            "- Venta del bot: ingreso recurrente, requiere producto y soporte.\n"
            "- Empresa de fondeo: mayor upside, mayor complejidad legal y de capital."
        ),
        keywords=["negocio", "business", "vender", "precio", "cliente", "mercado", "ingreso", "monetiz", "empresa", "modelo"],
    ),
    "analyst": AgentRole(
        key="analyst",
        title="Backtest Analyst",
        mission="Interpreta resultados de backtest y veredictos de challenge.",
        system_prompt=(
            "Eres analista cuantitativo de resultados. Interpretas métricas de "
            "backtest y el veredicto del motor de challenge de forma objetiva, "
            "señalando qué regla se violó y qué mejorar. No exageras resultados."
        ),
        offline_guidance=(
            "- Lee retorno, drawdown máximo, nº de operaciones y % de aciertos juntos.\n"
            "- Un retorno alto con drawdown que viola el límite NO pasa el challenge.\n"
            "- Pocas operaciones => resultados poco significativos estadísticamente.\n"
            "- Compara contra las reglas exactas del preset usado."
        ),
        keywords=["backtest", "resultado", "métrica", "equity", "retorno", "rendimiento", "veredicto", "pasó", "falló"],
    ),
}

# The Managing Director synthesizes the specialists' input into one recommendation.
DIRECTOR = AgentRole(
    key="director",
    title="Managing Director",
    mission="Sintetiza las opiniones del equipo en una recomendación accionable.",
    system_prompt=(
        "Eres el director de la agencia. Recibes los análisis de los especialistas y "
        "produces UNA recomendación clara, priorizada y accionable, señalando riesgos "
        "y próximos pasos. Eres directo y honesto sobre la incertidumbre."
    ),
    offline_guidance=(
        "Síntesis: prioriza (1) validar el motor con datos reales, (2) gestión de "
        "riesgo que respete el challenge, (3) cumplimiento legal/términos antes de "
        "monetizar. Recomienda el siguiente paso concreto y los riesgos clave."
    ),
)


def list_roster() -> List[Dict]:
    return [{"key": a.key, "title": a.title, "mission": a.mission} for a in ROSTER.values()]


def select_agents(question: str, max_agents: int = 4) -> List[AgentRole]:
    """Pick the most relevant agents for a question via keyword scoring.

    Falls back to a sensible default panel when nothing matches strongly.
    """
    q = question.lower()
    scored = []
    for agent in ROSTER.values():
        score = sum(1 for kw in agent.keywords if kw in q)
        if score:
            scored.append((score, agent))
    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [a for _, a in scored[:max_agents]]
    if not selected:
        # Default cross-functional panel for general/strategic dilemmas.
        selected = [ROSTER["strategist"], ROSTER["risk"], ROSTER["compliance"], ROSTER["business"]]
    return selected
