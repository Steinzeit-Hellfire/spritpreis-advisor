import hmac

from fastapi import APIRouter, Response, Request, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..auth import erstelle_session_token, ist_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    passwort: str


@router.post("/login")
def login(daten: LoginRequest, response: Response):
    if not settings.admin_password or not settings.session_secret:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_PASSWORD/SESSION_SECRET sind auf dem Server nicht konfiguriert (.env prüfen).",
        )
    if not hmac.compare_digest(daten.passwort, settings.admin_password):
        raise HTTPException(status_code=401, detail="Falsches Passwort")

    token = erstelle_session_token(settings.session_secret)
    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=30 * 24 * 60 * 60,
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}


@router.get("/status")
def status(request: Request):
    return {"admin": ist_admin(request)}
