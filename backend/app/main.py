"""FastAPI application entry point."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .engine.challenge import PRESETS
from .engine.data import supported_markets, supported_timeframes
from .engine.strategies import list_strategies
from .schemas import RunRequest
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
