"""Nutzt die von ml_train.py trainierten Modelle, um eine Prognose für die
nächsten 24 Stunden zu erstellen: zu welcher Uhrzeit wird der Preis
voraussichtlich am niedrigsten sein."""
import pickle
from datetime import datetime, timedelta
from pathlib import Path

from .config import settings

MODEL_DIR = Path(settings.db_path).resolve().parent / "modelle"


def _modell_laden(station_id: int):
    pfad = MODEL_DIR / f"station_{station_id}.pkl"
    if not pfad.exists():
        return None
    with open(pfad, "rb") as f:
        return pickle.load(f)


def prognose_24h(station_id: int) -> dict | None:
    """Gibt None zurück, wenn (noch) kein Modell existiert (siehe ml_train.py)."""
    modell = _modell_laden(station_id)
    if modell is None:
        return None

    jetzt = datetime.now()
    beste_zeit = None
    bester_preis = None

    for stunden_versatz in range(24):
        zeitpunkt = jetzt + timedelta(hours=stunden_versatz)
        tag_absolut = int(zeitpunkt.timestamp() // 86400)
        merkmale = [[zeitpunkt.hour, zeitpunkt.weekday(), tag_absolut]]
        vorhersage = float(modell.predict(merkmale)[0])

        if bester_preis is None or vorhersage < bester_preis:
            bester_preis = vorhersage
            beste_zeit = zeitpunkt

    return {
        "beste_uhrzeit": beste_zeit.strftime("%a %H:%M"),
        "prognostizierter_preis": round(bester_preis, 3),
        "in_stunden": round((beste_zeit - jetzt).total_seconds() / 3600, 1),
    }
