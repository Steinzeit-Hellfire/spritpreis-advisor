import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..database import get_connection
from ..auth import ist_admin

router = APIRouter(prefix="/api/sondereffekte", tags=["sondereffekte"])


def _require_admin(request: Request):
    if not ist_admin(request):
        raise HTTPException(status_code=401, detail="Nur als Admin möglich - bitte einloggen.")


class SondereffektCreate(BaseModel):
    name: str
    start_datum: str  # ISO-Datum, z.B. 2026-05-01
    end_datum: str    # ISO-Datum, inklusive
    beschreibung: str | None = None


@router.get("")
def sondereffekte_liste():
    """Öffentlich lesbar - reine Metadaten, nichts Privates, hilfreich als
    Transparenz, warum die Prognose an bestimmten Tagen Lücken/Sprünge zeigt."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM sondereffekte ORDER BY start_datum DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("")
def sondereffekt_anlegen(effekt: SondereffektCreate, request: Request):
    _require_admin(request)
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO sondereffekte (name, start_datum, end_datum, beschreibung, erstellt_am) VALUES (?, ?, ?, ?, ?)",
        (effekt.name, effekt.start_datum, effekt.end_datum, effekt.beschreibung, int(time.time())),
    )
    conn.commit()
    neue_id = cur.lastrowid
    conn.close()
    return {"id": neue_id}


@router.delete("/{effekt_id}")
def sondereffekt_loeschen(effekt_id: int, request: Request):
    _require_admin(request)
    conn = get_connection()
    cur = conn.execute("DELETE FROM sondereffekte WHERE id = ?", (effekt_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Sondereffekt nicht gefunden")
    return {"ok": True}
