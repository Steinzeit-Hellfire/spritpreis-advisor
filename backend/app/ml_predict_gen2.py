"""GEN2 - ALPHA: Nutzt die von ml_train_gen2.py trainierten Konfidenz-Modelle
für Vorhersagen mit Bandbreite (statt Einzelwert) und liefert die echte
Out-of-Sample-Genauigkeit aus dem Training mit."""
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path

from .config import settings
from .database import get_connection

MODEL_DIR = Path(settings.db_path).resolve().parent / "modelle"


def _paket_laden(station_id: int, kraftstoff: str) -> dict | None:
    pfad = MODEL_DIR / f"station_{station_id}_{kraftstoff}_gen2.pkl"
    if not pfad.exists():
        return None
    with open(pfad, "rb") as f:
        return pickle.load(f)


def _merkmale(zeitpunkt: datetime, schnitt_3tage: float) -> list[float]:
    tag_absolut = int(zeitpunkt.timestamp() // 86400)
    return [zeitpunkt.hour, zeitpunkt.weekday(), tag_absolut, schnitt_3tage]


def _vorhersage_band(paket: dict, zeitpunkt: datetime) -> dict:
    merkmale = [_merkmale(zeitpunkt, paket["letzter_schnitt_3tage"])]
    return {
        "lower": round(float(paket["modelle"]["lower"].predict(merkmale)[0]), 3),
        "median": round(float(paket["modelle"]["median"].predict(merkmale)[0]), 3),
        "upper": round(float(paket["modelle"]["upper"].predict(merkmale)[0]), 3),
    }


def verlauf_und_prognose_gen2(station_id: int, kraftstoff: str = "e5", tage_zurueck: int = 14) -> dict | None:
    """Gibt None zurück, wenn noch kein Gen2-Modell trainiert wurde."""
    paket = _paket_laden(station_id, kraftstoff)
    if paket is None:
        return None

    conn = get_connection()
    ab_zeitpunkt = int(time.time()) - tage_zurueck * 86400
    rows = conn.execute(
        """SELECT price, timestamp FROM fuel_prices
           WHERE station_id = ? AND fuel_type = ? AND is_open = 1 AND timestamp >= ?
           ORDER BY timestamp""",
        (station_id, kraftstoff, ab_zeitpunkt),
    ).fetchall()
    conn.close()

    tatsaechlich = [
        {"zeitpunkt": datetime.fromtimestamp(r["timestamp"]).isoformat(), "preis": r["price"]}
        for r in rows
    ]

    prognose_kurve = []
    jetzt = datetime.now()
    for stunden_versatz in range(25):
        zeitpunkt = jetzt + timedelta(hours=stunden_versatz)
        band = _vorhersage_band(paket, zeitpunkt)
        prognose_kurve.append({"zeitpunkt": zeitpunkt.isoformat(), **band})

    return {
        "tatsaechlich": tatsaechlich,
        "prognose_band": prognose_kurve,
        "out_of_sample_genauigkeit": paket["holdout"],
        "version": paket.get("version", "gen2-alpha"),
    }
