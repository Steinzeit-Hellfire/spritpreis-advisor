import json
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..database import get_connection
from ..auth import ist_admin

router = APIRouter(prefix="/api/routen-vorlagen", tags=["routen-vorlagen"])


def _require_admin(request: Request):
    if not ist_admin(request):
        raise HTTPException(status_code=401, detail="Nur als Admin möglich - bitte einloggen.")


class VorlageCreate(BaseModel):
    name: str
    waypoints: list[list[float]]
    route: list[list[float]]
    distanz_km: float | None = None


@router.get("")
def vorlagen_liste(request: Request):
    """Vorlagen sind wie Strecken privat - nur der Admin sieht/verwaltet sie."""
    _require_admin(request)
    conn = get_connection()
    rows = conn.execute("SELECT * FROM routen_vorlagen ORDER BY name").fetchall()
    conn.close()
    ergebnisse = []
    for row in rows:
        eintrag = dict(row)
        eintrag["waypoints"] = json.loads(eintrag.pop("waypoints"))
        eintrag["route"] = json.loads(eintrag.pop("route"))
        ergebnisse.append(eintrag)
    return ergebnisse


@router.post("")
def vorlage_anlegen(vorlage: VorlageCreate, request: Request):
    _require_admin(request)
    if len(vorlage.waypoints) < 2 or len(vorlage.route) < 2:
        raise HTTPException(status_code=400, detail="Route braucht mindestens 2 Wegpunkte")
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO routen_vorlagen (name, waypoints, route, distanz_km, erstellt_am) VALUES (?, ?, ?, ?, ?)",
        (
            vorlage.name,
            json.dumps(vorlage.waypoints),
            json.dumps(vorlage.route),
            vorlage.distanz_km,
            int(time.time()),
        ),
    )
    conn.commit()
    neue_id = cur.lastrowid
    conn.close()
    return {"id": neue_id}


@router.put("/{vorlage_id}")
def vorlage_aktualisieren(vorlage_id: int, vorlage: VorlageCreate, request: Request):
    _require_admin(request)
    conn = get_connection()
    cur = conn.execute(
        "UPDATE routen_vorlagen SET name = ?, waypoints = ?, route = ?, distanz_km = ? WHERE id = ?",
        (
            vorlage.name,
            json.dumps(vorlage.waypoints),
            json.dumps(vorlage.route),
            vorlage.distanz_km,
            vorlage_id,
        ),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden")
    return {"ok": True}


@router.delete("/{vorlage_id}")
def vorlage_loeschen(vorlage_id: int, request: Request):
    _require_admin(request)
    conn = get_connection()
    cur = conn.execute("DELETE FROM routen_vorlagen WHERE id = ?", (vorlage_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden")
    return {"ok": True}
