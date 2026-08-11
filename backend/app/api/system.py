"""Owner-only agent control: login, run cycle, status."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.auth import login
from app.agents import deepseek_worker, finance
from app.db import SessionLocal
from app.config import get_settings


router = APIRouter()


class LoginIn(BaseModel):
    password: str


@router.post("/login")
def do_login(body: LoginIn):
    return login(body.password)


@router.get("/owner/status")
def status():
    db = SessionLocal()
    try:
        sl = finance.check_stop_loss(db)
        return {
            "environment": get_settings().app_env,
            "model": get_settings().openai_model,
            "wallet": finance.get_balance(db),
            "stop_loss": sl,
            "notifications": finance.list_notifications(db, unread_only=True),
        }
    finally:
        db.close()


@router.post("/agent/run-cycle")
def run_cycle():
    db = SessionLocal()
    try:
        return deepseek_worker.run_cycle(db)
    finally:
        db.close()


@router.post("/agent/health")
def health():
    return {"status": "ok"}
