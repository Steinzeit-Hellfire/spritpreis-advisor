from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..database import get_connection
from ..auth import ist_admin

router = APIRouter(prefix="/api/fahrer", tags=["fahrer"])


def _require_admin(request: Request):
    if not ist_admin(request):
        raise HTTPException(status_code=401, detail="Nur als Admin möglich - bitte einloggen.")


class FahrerCreate(BaseModel):
    name: str


@router.get("")
def fahrer_liste(request: Request):
    _require_admin(request)
    conn = get_connection()
    rows = conn.execute("SELECT * FROM fahrer ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("")
def fahrer_anlegen(fahrer: FahrerCreate, request: Request):
    _require_admin(request)
    conn = get_connection()
    cur = conn.execute("INSERT INTO fahrer (name) VALUES (?)", (fahrer.name,))
    conn.commit()
    neue_id = cur.lastrowid
    conn.close()
    return {"id": neue_id}


@router.delete("/{fahrer_id}")
def fahrer_loeschen(fahrer_id: int, request: Request):
    _require_admin(request)
    conn = get_connection()
    cur = conn.execute("DELETE FROM fahrer WHERE id = ?", (fahrer_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Fahrer nicht gefunden")
    return {"ok": True}
