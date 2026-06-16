"""FastAPI application entry point."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .agency.orchestrator import deliberate
from .agency.providers import get_provider
from .agency.roster import list_roster
from .engine.challenge import PRESETS
from .engine.data import supported_markets, supported_timeframes
from .engine.strategies import list_strategies
from .schemas import AgencyRequest, RunRequest
from .service import run_pipeline

app = FastAPI(
    title="Fondeo Bot API",
    version=__version__,
    description="Backtesting and prop-firm challenge evaluation engine.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "version": __version__}


@app.get("/api/meta")
def meta():
    """Everything the frontend needs to build its forms."""
    return {
        "markets": supported_markets(),
        "timeframes": supported_timeframes(),
        "strategies": list_strategies(),
        "presets": {k: asdict(v) for k, v in PRESETS.items()},
    }


@app.post("/api/run")
def run(req: RunRequest):
    try:
        return run_pipeline(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/agency/roster")
def agency_roster():
    """The AI Agency roster and which LLM backend is active."""
    return {"backend": get_provider().backend, "roster": list_roster()}


@app.post("/api/agency/ask")
def agency_ask(req: AgencyRequest):
    """Ask the AI Agency to deliberate on a dilemma.

    If `run` is provided, a backtest is executed first and its results are passed
    to the agents as concrete context.
    """
    context = None
    if req.run is not None:
        try:
            out = run_pipeline(req.run)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        stats = out["backtest"]["stats"]
        ch = out["challenge"]
        context = (
            f"Backtest {req.run.market}/{req.run.symbol} estrategia={req.run.strategy}: "
            f"retorno={stats['total_return_pct']}%, drawdown_max={stats['max_drawdown_pct']}%, "
            f"operaciones={stats['num_trades']}, aciertos={stats['win_rate_pct']}%. "
            f"Veredicto challenge: {ch['status']}"
            + (f", regla violada={ch['breached_rule']}" if ch.get("breached_rule") else "")
            + "."
        )
    return deliberate(req.question, context=context, max_agents=req.max_agents)
