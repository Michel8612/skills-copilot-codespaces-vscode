"""FastAPI application entry point."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from . import __version__
from .agency.orchestrator import deliberate
from .agency.providers import get_provider
from .agency.roster import list_roster
from .engine.challenge import PRESETS
from .engine.data import supported_markets, supported_timeframes
from .engine.strategies import list_strategies
from .fondeo import service as fondeo_service
from .fondeo.db import engine as fondeo_engine, get_session, init_db
from .fondeo.models import Plan
from .fondeo.schemas import (
    AccountEvaluate,
    AccountOpen,
    PayoutCreate,
    PlanCreate,
    TraderCreate,
)
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


@app.on_event("startup")
def _startup():
    """Create the funding database and seed honest default plans if empty."""
    init_db()
    with Session(fondeo_engine) as session:
        fondeo_service.seed_default_plans(session)


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


# --- Funding (prop firm) endpoints ---------------------------------------------


@app.get("/api/fondeo/plans")
def fondeo_plans(session: Session = Depends(get_session)):
    return [p.model_dump() for p in fondeo_service.list_plans(session)]


@app.post("/api/fondeo/plans")
def fondeo_create_plan(req: PlanCreate, session: Session = Depends(get_session)):
    plan = Plan(**req.model_dump())
    return fondeo_service.create_plan(session, plan).model_dump()


@app.post("/api/fondeo/traders")
def fondeo_register_trader(req: TraderCreate, session: Session = Depends(get_session)):
    return fondeo_service.register_trader(session, req.name, req.email).model_dump()


@app.get("/api/fondeo/accounts")
def fondeo_accounts(session: Session = Depends(get_session)):
    return [a.model_dump() for a in fondeo_service.list_accounts(session)]


@app.post("/api/fondeo/accounts")
def fondeo_open_account(req: AccountOpen, session: Session = Depends(get_session)):
    try:
        return fondeo_service.open_account(session, req.trader_id, req.plan_id).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/fondeo/accounts/{account_id}/evaluate")
def fondeo_evaluate(account_id: int, req: AccountEvaluate, session: Session = Depends(get_session)):
    try:
        return fondeo_service.evaluate_account(
            session, account_id,
            strategy=req.strategy, strategy_params=req.strategy_params,
            symbol=req.symbol, timeframe=req.timeframe, bars=req.bars, leverage=req.leverage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/fondeo/accounts/{account_id}/fund")
def fondeo_fund(account_id: int, session: Session = Depends(get_session)):
    try:
        return fondeo_service.fund_account(session, account_id).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/fondeo/accounts/{account_id}/payout")
def fondeo_payout(account_id: int, req: PayoutCreate, session: Session = Depends(get_session)):
    try:
        return fondeo_service.record_payout(session, account_id, req.gross_profit).model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
