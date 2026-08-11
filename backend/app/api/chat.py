"""Chatbot endpoint for the agent. Authenticated via agent token, so it can be
called from the frontend without a login page."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth import verify_agent_token
from app.agents import deepseek_worker
from app.db import SessionLocal


router = APIRouter()


class ChatIn(BaseModel):
    message: str


class ChatOut(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, _=Depends(verify_agent_token)):
    db = SessionLocal()
    try:
        reply = deepseek_worker.ask(db, body.message)
        return ChatOut(reply=reply)
    finally:
        db.close()
