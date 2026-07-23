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


def prognose_24h(station_id: int, aktueller_preis: float | None = None) -> dict | None:
    """Gibt None zurück, wenn (noch) kein Modell existiert (siehe ml_train.py).

    aktueller_preis: der tatsächlich beobachtete Live-Preis (nicht vom Modell
    geschätzt). Wird mit der 24h-Prognose verglichen - falls der reale Preis
    schon jetzt günstiger ist als jede Vorhersage für die kommenden 24h, wird
    "jetzt" empfohlen statt eines unsicher vorhergesagten, aber schlechteren
    Zukunftswerts. Ohne diesen Abgleich könnte die Prognose einen Zeitpunkt
    empfehlen, der tatsächlich teurer ist als der Preis gerade jetzt.
    """
    modell = _modell_laden(station_id)
    if modell is None:
        return None

    jetzt = datetime.now()
    beste_zeit = None
    bester_preis = None

    # 1 bis 24 Stunden voraus scannen (nicht ab 0 - "jetzt" wird separat mit
    # dem echten aktuellen Preis verglichen, nicht mit einer Modell-Schätzung
    # für den aktuellen Zeitpunkt, die vom echten Wert abweichen kann).
    for stunden_versatz in range(1, 25):
        zeitpunkt = jetzt + timedelta(hours=stunden_versatz)
        tag_absolut = int(zeitpunkt.timestamp() // 86400)
        merkmale = [[zeitpunkt.hour, zeitpunkt.weekday(), tag_absolut]]
        vorhersage = float(modell.predict(merkmale)[0])

        if bester_preis is None or vorhersage < bester_preis:
            bester_preis = vorhersage
            beste_zeit = zeitpunkt

    if aktueller_preis is not None and aktueller_preis <= bester_preis:
        return {
            "beste_uhrzeit": "jetzt",
            "prognostizierter_preis": round(aktueller_preis, 3),
            "in_stunden": 0,
            "jetzt_am_besten": True,
        }

    return {
        "beste_uhrzeit": beste_zeit.strftime("%a %H:%M"),
        "prognostizierter_preis": round(bester_preis, 3),
        "in_stunden": round((beste_zeit - jetzt).total_seconds() / 3600, 1),
        "jetzt_am_besten": False,
    }
