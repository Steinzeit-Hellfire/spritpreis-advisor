"""Nutzt die von ml_train.py trainierten Modelle für 24h-Prognosen und für
einen Rückblick-Vergleich (wie gut hätte das Modell die Vergangenheit erklärt)."""
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path

from .config import settings
from .database import get_connection

MODEL_DIR = Path(settings.db_path).resolve().parent / "modelle"


def _modell_laden(station_id: int, kraftstoff: str):
    pfad = MODEL_DIR / f"station_{station_id}_{kraftstoff}.pkl"
    if not pfad.exists():
        return None
    with open(pfad, "rb") as f:
        return pickle.load(f)


def _vorhersage_fuer_zeitpunkt(modell, zeitpunkt: datetime) -> float:
    tag_absolut = int(zeitpunkt.timestamp() // 86400)
    merkmale = [[zeitpunkt.hour, zeitpunkt.weekday(), tag_absolut]]
    return float(modell.predict(merkmale)[0])


def prognose_24h(station_id: int, kraftstoff: str = "e5", aktueller_preis: float | None = None) -> dict | None:
    """Gibt None zurück, wenn (noch) kein Modell existiert (siehe ml_train.py).

    aktueller_preis: der tatsächlich beobachtete Live-Preis (nicht vom Modell
    geschätzt). Wird mit der 24h-Prognose verglichen - falls der reale Preis
    schon jetzt günstiger ist als jede Vorhersage für die kommenden 24h, wird
    "jetzt" empfohlen statt eines unsicher vorhergesagten, aber schlechteren
    Zukunftswerts.
    """
    modell = _modell_laden(station_id, kraftstoff)
    if modell is None:
        return None

    jetzt = datetime.now()
    beste_zeit = None
    bester_preis = None

    for stunden_versatz in range(1, 25):
        zeitpunkt = jetzt + timedelta(hours=stunden_versatz)
        vorhersage = _vorhersage_fuer_zeitpunkt(modell, zeitpunkt)
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


def verlauf_und_prognose(station_id: int, kraftstoff: str = "e5", tage_zurueck: int = 14) -> dict:
    """Tatsächliche Preishistorie der letzten X Tage, das, was das AKTUELLE
    Modell für exakt diese vergangenen Zeitpunkte vorhergesagt hätte (Rückblick-
    Vergleich, um die Modellqualität sichtbar zu machen), plus die 24h-Prognose
    in die Zukunft. Dazu eine grobe Genauigkeits-Kennzahl.

    Wichtig zur Einordnung: Der Rückblick nutzt das AKTUELLE, mit allen
    verfügbaren Daten trainierte Modell auch für die Vergangenheit - das ist
    kein echter Out-of-Sample-Test (das Modell "kennt" diese Daten ja aus dem
    Training), sondern zeigt, wie gut das gelernte Wochentag/Uhrzeit-Muster
    zur Realität passt. Für einen strengeren Test bräuchte es eine zeitliche
    Trainings-/Test-Aufteilung.
    """
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

    modell = _modell_laden(station_id, kraftstoff)
    modell_rueckblick = []
    genauigkeit = None

    if modell is not None and rows:
        abweichungen = []
        for r in rows:
            zeitpunkt = datetime.fromtimestamp(r["timestamp"])
            geschaetzt = _vorhersage_fuer_zeitpunkt(modell, zeitpunkt)
            modell_rueckblick.append({"zeitpunkt": zeitpunkt.isoformat(), "preis": round(geschaetzt, 3)})
            abweichungen.append(abs(geschaetzt - r["price"]))

        mittlere_abweichung = sum(abweichungen) / len(abweichungen)
        mittlerer_preis = sum(r["price"] for r in rows) / len(rows)
        genauigkeit_prozent = max(0.0, 100 - (mittlere_abweichung / mittlerer_preis * 100))

        genauigkeit = {
            "mittlere_abweichung_ct": round(mittlere_abweichung * 100, 1),
            "genauigkeit_prozent": round(genauigkeit_prozent, 1),
            "basis_anzahl_punkte": len(rows),
        }

    prognose_kurve = []
    if modell is not None:
        jetzt = datetime.now()
        for stunden_versatz in range(25):  # inkl. "jetzt" (0) bis +24h
            zeitpunkt = jetzt + timedelta(hours=stunden_versatz)
            vorhersage = _vorhersage_fuer_zeitpunkt(modell, zeitpunkt)
            prognose_kurve.append({"zeitpunkt": zeitpunkt.isoformat(), "preis": round(vorhersage, 3)})

    return {
        "tatsaechlich": tatsaechlich,
        "modell_rueckblick": modell_rueckblick,
        "prognose": prognose_kurve,
        "genauigkeit": genauigkeit,
    }
