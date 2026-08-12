"""Agent Experts - FastAPI app entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db import init_db, SessionLocal
from app.strategies.scheduler import ensure_default_strategies
from app.api import chat, finance, system, strategies as strategy_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Seed default earning strategies
    db = SessionLocal()
    try:
        ensure_default_strategies(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Agent Experts", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, tags=["chat"])
app.include_router(finance.router, prefix="/api", tags=["finance"])
app.include_router(system.router, tags=["system"])
app.include_router(strategy_api.router, prefix="/api", tags=["strategies"])


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "app": "Agent Experts"}
