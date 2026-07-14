import json
import time
from math import radians, sin, cos, asin, sqrt

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import get_connection

router = APIRouter(prefix="/api/trips", tags=["strecken"])


class TripCreate(BaseModel):
    titel: str | None = None
    datum: str | None = None
    start_name: str | None = None
    ziel_name: str | None = None
    route: list[list[float]]  # [[lat, lng], [lat, lng], ...] - Reihenfolge der Pins


def _haversine_km(p1: list[float], p2: list[float]) -> float:
    lat1, lng1, lat2, lng2 = map(radians, [p1[0], p1[1], p2[0], p2[1]])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


def _distanz_gesamt_km(punkte: list[list[float]]) -> float:
    return sum(_haversine_km(punkte[i], punkte[i + 1]) for i in range(len(punkte) - 1))


@router.get("")
def trips_liste():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM trips ORDER BY erstellt_am DESC").fetchall()
    conn.close()
    ergebnisse = []
    for row in rows:
        eintrag = dict(row)
        eintrag["route"] = json.loads(eintrag.pop("route_geojson"))
        ergebnisse.append(eintrag)
    return ergebnisse


@router.get("/{trip_id}")
def trip_detail(trip_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Strecke nicht gefunden")
    eintrag = dict(row)
    eintrag["route"] = json.loads(eintrag.pop("route_geojson"))
    return eintrag


@router.post("")
def trip_anlegen(trip: TripCreate):
    if len(trip.route) < 2:
        raise HTTPException(status_code=400, detail="Route braucht mindestens 2 Punkte")

    distanz = round(_distanz_gesamt_km(trip.route), 2)
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO trips (titel, datum, start_name, ziel_name, distanz_km, route_geojson, erstellt_am)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            trip.titel,
            trip.datum,
            trip.start_name,
            trip.ziel_name,
            distanz,
            json.dumps(trip.route),
            int(time.time()),
        ),
    )
    conn.commit()
    neue_id = cur.lastrowid
    conn.close()
    return {"id": neue_id, "distanz_km": distanz}


@router.delete("/{trip_id}")
def trip_loeschen(trip_id: int):
    conn = get_connection()
    cur = conn.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Strecke nicht gefunden")
    return {"ok": True}
