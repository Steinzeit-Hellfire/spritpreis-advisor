from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import get_connection
from ..recommend import get_comparison
from ..ml_predict import verlauf_und_prognose
from ..ml_predict_gen2 import verlauf_und_prognose_gen2
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
def preisvergleich(kraftstoff: str = "e5"):
    """Aktueller Vergleich aller Favoriten-Stationen inkl. Einschätzung,
    für die angegebene Kraftstoffart (e5/e10/diesel)."""
    return get_comparison(kraftstoff)


@router.get("/prices/verlauf/{station_id}")
def preis_verlauf(station_id: int, kraftstoff: str = "e5", tage_zurueck: int = 14):
    """Tatsächliche Preishistorie + Modell-Rückblick + 24h-KI-Prognose zum
    Nachvollziehen, wie die Prognose zustande kommt (Transparenz statt Blackbox)."""
    return verlauf_und_prognose(station_id, kraftstoff, tage_zurueck)


@router.get("/prices/verlauf-gen2/{station_id}")
def preis_verlauf_gen2(station_id: int, kraftstoff: str = "e5", tage_zurueck: int = 14):
    """ALPHA: Experimentelles Zweitmodell mit Konfidenzband (10/50/90%-Quantile),
    gleitendem 3-Tage-Trend-Merkmal und echter Out-of-Sample-Genauigkeit
    (Holdout der letzten 7 Tage). Gibt null zurück, wenn noch nicht trainiert -
    siehe ml_train_gen2.py."""
    ergebnis = verlauf_und_prognose_gen2(station_id, kraftstoff, tage_zurueck)
    if ergebnis is None:
        raise HTTPException(status_code=404, detail="Noch kein Gen2-Modell trainiert (siehe ml_train_gen2.py)")
    return ergebnis


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
