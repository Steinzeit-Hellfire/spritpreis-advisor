"""
Trainiert pro Favoriten-Station ein kleines Machine-Learning-Modell, das aus
der Preishistorie lernt, wie sich der Preis über Wochentag/Uhrzeit typischerweise
verhält - und daraus eine Vorhersage für die nächsten 24h ableiten kann
(nicht nur "über/unter Durchschnitt" wie die einfache Statistik in recommend.py,
sondern eine echte gelernte Prognose).

Läuft nachts per Cronjob (siehe README) und schreibt die Modelle nach
<db-ordner>/modelle/station_<id>.pkl - kein Server-Neustart nötig, das
Backend lädt die Datei bei jeder Anfrage frisch.

Braucht mindestens MIN_DATENPUNKTE Preiswerte pro Station, sonst wird die
Station übersprungen (Modell würde sonst nur raten).
"""
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from app.config import settings
from app.database import get_connection

MODEL_DIR = Path(settings.db_path).resolve().parent / "modelle"
MIN_DATENPUNKTE = 200

# Siehe app/recommend.py für Details: Tankrabatt-Zeitraum verzerrt die Preise
# künstlich um ~17 Ct/L und soll nicht als "normales" Muster gelernt werden.
TANKRABATT_START = int(datetime(2026, 5, 1).timestamp())
TANKRABATT_ENDE = int(datetime(2026, 7, 1).timestamp())


def _merkmale(timestamp: int) -> list[float]:
    dt = datetime.fromtimestamp(timestamp)
    stunde = dt.hour
    wochentag = dt.weekday()
    tag_absolut = timestamp // 86400  # grober Langzeittrend (z.B. steigende/fallende Rohölpreise)
    return [stunde, wochentag, tag_absolut]


def trainiere_alle_stationen():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    stationen = conn.execute("SELECT id, name FROM stations WHERE ist_favorit = 1").fetchall()

    for station in stationen:
        rows = conn.execute(
            """SELECT price, timestamp FROM fuel_prices
               WHERE station_id = ? AND is_open = 1
                 AND (timestamp < ? OR timestamp >= ?)
               ORDER BY timestamp""",
            (station["id"], TANKRABATT_START, TANKRABATT_ENDE),
        ).fetchall()

        if len(rows) < MIN_DATENPUNKTE:
            print(f"{station['name']}: nur {len(rows)} Datenpunkte außerhalb des Tankrabatt-Zeitraums "
                  f"(mind. {MIN_DATENPUNKTE} nötig) - übersprungen")
            continue

        X = np.array([_merkmale(r["timestamp"]) for r in rows])
        y = np.array([r["price"] for r in rows])

        modell = GradientBoostingRegressor(n_estimators=100, max_depth=3, learning_rate=0.1)
        modell.fit(X, y)

        modell_pfad = MODEL_DIR / f"station_{station['id']}.pkl"
        with open(modell_pfad, "wb") as f:
            pickle.dump(modell, f)
        print(f"{station['name']}: Modell trainiert mit {len(rows)} Datenpunkten -> {modell_pfad.name}")

    conn.close()


if __name__ == "__main__":
    trainiere_alle_stationen()
