"""Auth dependency extracted from main.py for use in sub-routers."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
_TOKEN_EXPIRE_DAYS = 30
_bearer = HTTPBearer(auto_error=False)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _decode_token(token: str) -> Dict[str, Any]:
    try:
        header, payload, sig = token.split(".")
        expected = _b64url(
            hmac.new(_SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        data = json.loads(base64.urlsafe_b64decode(payload + "=="))
        if data.get("exp", 0) < int(datetime.utcnow().timestamp()):
            raise ValueError("expired")
        return data
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token invalide") from exc


def _create_token(user_id: int, email: str) -> str:
    _TOKEN_EXPIRE_DAYS = 30
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    from datetime import timedelta
    exp = int((datetime.utcnow() + timedelta(days=_TOKEN_EXPIRE_DAYS)).timestamp())
    payload = _b64url(json.dumps({"sub": str(user_id), "email": email, "exp": exp}).encode())
    sig = _b64url(
        hmac.new(_SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{sig}"


async def current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=401, detail="Non authentifié")
    data = _decode_token(credentials.credentials)
    return {"id": int(data["sub"]), "email": data["email"]}
