from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import get_connection
from ..recommend import get_comparison
from ..tankerkoenig import TankerkoenigClient
from ..config import settings

router = APIRouter(prefix="/api", tags=["preise"])


class StationCreate(BaseModel):
    tankerkoenig_id: str
    name: str
    marke: str | None = None
    adresse: str | None = None
    lat: float | None = None
    lng: float | None = None
    ist_favorit: bool = True


@router.get("/prices/comparison")
def preisvergleich():
    """Aktueller Vergleich aller Favoriten-Stationen inkl. Einschätzung."""
    return get_comparison()


@router.get("/stations")
def stationen_liste():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM stations ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/stations")
def station_anlegen(station: StationCreate):
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO stations (tankerkoenig_id, name, marke, adresse, lat, lng, ist_favorit)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                station.tankerkoenig_id,
                station.name,
                station.marke,
                station.adresse,
                station.lat,
                station.lng,
                int(station.ist_favorit),
            ),
        )
        conn.commit()
        neue_id = cur.lastrowid
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()
    return {"id": neue_id}


class StationKoordinaten(BaseModel):
    lat: float
    lng: float


@router.patch("/stations/{station_id}/koordinaten")
def station_koordinaten_setzen(station_id: int, koordinaten: StationKoordinaten):
    conn = get_connection()
    cur = conn.execute(
        "UPDATE stations SET lat = ?, lng = ? WHERE id = ?",
        (koordinaten.lat, koordinaten.lng, station_id),
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Station nicht gefunden")
    return {"ok": True}


@router.get("/stations/suche")
def stationen_suche(lat: float, lng: float, radius_km: int = 10):
    """Sucht Tankstellen in der Nähe über Tankerkönig, um deren ID herauszufinden
    (einmalig nötig, bevor eine Station als Favorit angelegt wird)."""
    client = TankerkoenigClient(settings.tankerkoenig_api_key)
    try:
        return client.find_stations_near(lat, lng, radius_km)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
