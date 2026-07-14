import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from ..database import get_connection
from ..config import settings

router = APIRouter(prefix="/api/refuels", tags=["tankvorgaenge"])

UPLOAD_DIR = Path(settings.db_path).resolve().parent / "uploads" / "refuels"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class RefuelCreate(BaseModel):
    station_id: int | None = None
    datum: str  # ISO, z.B. "2026-07-14"
    odometer_km: float
    liter: float
    preis_pro_liter: float
    notiz: str | None = None
    bordcomputer_km: float | None = None         # vom Bordcomputer: gefahrene km seit letztem Tanken
    bordcomputer_verbrauch: float | None = None   # vom Bordcomputer: Durchschnittsverbrauch L/100km


@router.get("")
def refuels_liste():
    """Liste aller Tankvorgänge, jeweils mit Verbrauch (L/100km) und Kosten/km
    seit dem vorherigen Tankvorgang."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT r.*, s.name AS station_name, s.marke AS station_marke
           FROM refuels r
           LEFT JOIN stations s ON s.id = r.station_id
           ORDER BY r.odometer_km ASC"""
    ).fetchall()
    conn.close()

    ergebnisse = []
    vorheriger_km = None
    for row in rows:
        eintrag = dict(row)
        if vorheriger_km is not None:
            distanz = eintrag["odometer_km"] - vorheriger_km
            if distanz > 0:
                eintrag["verbrauch_l_100km"] = round(eintrag["liter"] / distanz * 100, 2)
                eintrag["kosten_pro_km"] = round(eintrag["gesamtkosten"] / distanz, 4)
            else:
                eintrag["verbrauch_l_100km"] = None
                eintrag["kosten_pro_km"] = None
        else:
            eintrag["verbrauch_l_100km"] = None
            eintrag["kosten_pro_km"] = None
        ergebnisse.append(eintrag)
        vorheriger_km = row["odometer_km"]

    return list(reversed(ergebnisse))  # neuestes zuerst


@router.post("")
def refuel_anlegen(eintrag: RefuelCreate):
    gesamtkosten = round(eintrag.liter * eintrag.preis_pro_liter, 2)
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO refuels (station_id, datum, odometer_km, liter, preis_pro_liter, gesamtkosten,
                                 notiz, bordcomputer_km, bordcomputer_verbrauch)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            eintrag.station_id,
            eintrag.datum,
            eintrag.odometer_km,
            eintrag.liter,
            eintrag.preis_pro_liter,
            gesamtkosten,
            eintrag.notiz,
            eintrag.bordcomputer_km,
            eintrag.bordcomputer_verbrauch,
        ),
    )
    conn.commit()
    neue_id = cur.lastrowid
    conn.close()
    return {"id": neue_id, "gesamtkosten": gesamtkosten}


@router.post("/{refuel_id}/foto")
async def foto_hochladen(refuel_id: int, datei: UploadFile = File(...)):
    conn = get_connection()
    vorhanden = conn.execute("SELECT id FROM refuels WHERE id = ?", (refuel_id,)).fetchone()
    if vorhanden is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Tankvorgang nicht gefunden")

    endung = Path(datei.filename or "foto.jpg").suffix or ".jpg"
    dateiname = f"refuel_{refuel_id}_{int(time.time())}{endung}"
    zielpfad = UPLOAD_DIR / dateiname

    inhalt = await datei.read()
    zielpfad.write_bytes(inhalt)

    relativer_pfad = f"/uploads/refuels/{dateiname}"
    conn.execute("UPDATE refuels SET foto_pfad = ? WHERE id = ?", (relativer_pfad, refuel_id))
    conn.commit()
    conn.close()
    return {"foto_pfad": relativer_pfad}


@router.delete("/{refuel_id}")
def refuel_loeschen(refuel_id: int):
    conn = get_connection()
    cur = conn.execute("DELETE FROM refuels WHERE id = ?", (refuel_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Tankvorgang nicht gefunden")
    return {"ok": True}
