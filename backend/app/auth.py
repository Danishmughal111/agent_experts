"""Auth: owner uses a master password; the chatbot endpoint uses an agent token.
Kept simple & secure - no user registration (personal assistant, single owner)."""
from fastapi import Depends, Header, HTTPException
from datetime import datetime, timezone, timedelta

from app.config import get_settings

import jwt


def create_owner_token():
    settings = get_settings()
    payload = {"sub": "owner", "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_owner(authorization: str = Header(default="")):
    settings = get_settings()
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("sub") != "owner":
        raise HTTPException(status_code=401, detail="Not owner")
    return payload


def verify_agent_token(x_agent_token: str = Header(default="")):
    settings = get_settings()
    if not x_agent_token or x_agent_token != settings.agent_token:
        raise HTTPException(status_code=403, detail="Invalid agent token")
    return True


def login(owner_password: str):
    settings = get_settings()
    if owner_password != settings.owner_password:
        raise HTTPException(status_code=401, detail="Wrong password")
    return {"token": create_owner_token()}
