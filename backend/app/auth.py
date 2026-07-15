"""
Schlankes Admin-Login: ein einzelnes Passwort (aus .env), eine HMAC-signierte
Session in einem HttpOnly-Cookie. Kein User-System, keine zusätzliche
Abhängigkeit - reicht für "ein Admin (ich), alle anderen Gäste".

Sicherheitshinweis: schützt vor beiläufigem Zugriff im selben Netzwerk, ersetzt
aber kein HTTPS. Siehe README, Abschnitt "Zugriffsschutz".
"""
import hashlib
import hmac
import time

from fastapi import Request

SESSION_GUELTIGKEIT_SEKUNDEN = 30 * 24 * 60 * 60  # 30 Tage


def _signatur(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def erstelle_session_token(secret: str) -> str:
    ablauf = int(time.time()) + SESSION_GUELTIGKEIT_SEKUNDEN
    payload = f"admin:{ablauf}"
    sig = _signatur(payload, secret)
    return f"{payload}:{sig}"


def token_gueltig(token: str | None, secret: str) -> bool:
    if not token or not secret:
        return False
    teile = token.split(":")
    if len(teile) != 3:
        return False
    rolle, ablauf, sig = teile
    payload = f"{rolle}:{ablauf}"
    erwartete_sig = _signatur(payload, secret)
    if not hmac.compare_digest(sig, erwartete_sig):
        return False
    if int(ablauf) < time.time():
        return False
    return rolle == "admin"


def ist_admin(request: Request) -> bool:
    """Nicht-werfende Prüfung - für Endpoints, die für Gäste UND Admin
    funktionieren, aber unterschiedliche Daten zeigen (z.B. Strecken-Liste)."""
    from .config import settings
    token = request.cookies.get("session")
    return token_gueltig(token, settings.session_secret)
