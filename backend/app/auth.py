"""Auth: Now open (no login) so the personal dashboard works without a password.
Kept hook-friendly so you can re-enable auth later if needed."""
from fastapi import Depends, Header, HTTPException
from datetime import datetime, timezone, timedelta

from app.config import get_settings

import jwt


def create_owner_token():
    settings = get_settings()
    payload = {"sub": "owner", "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


# Auth is currently DISABLED (open dashboard). Function kept so endpoints don't break.
def verify_owner(authorization: str = Header(default="")):
    return {"sub": "owner", "open_auth": True}


def verify_agent_token(x_agent_token: str = Header(default="")):
    return True


def login(owner_password: str):
    settings = get_settings()
    if owner_password != settings.owner_password:
        raise HTTPException(status_code=401, detail="Wrong password")
    return {"token": create_owner_token()}
