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

Zeiträume aus der Tabelle "sondereffekte" (z.B. Tankrabatt) werden vom
Training ausgeschlossen, siehe app/sondereffekte.py - dort auch neue,
zukünftige Sondereffekte eintragbar (z.B. falls es wieder einen Tankrabatt
gibt), ohne dass dieses Skript angepasst werden muss.
"""
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from app.config import settings
from app.database import get_connection
from app.sondereffekte import lade_ausschlusszeitraeume, ist_ausgeschlossen

MODEL_DIR = Path(settings.db_path).resolve().parent / "modelle"
MIN_DATENPUNKTE = 200


def _merkmale(timestamp: int) -> list[float]:
    dt = datetime.fromtimestamp(timestamp)
    stunde = dt.hour
    wochentag = dt.weekday()
    tag_absolut = timestamp // 86400  # grober Langzeittrend (z.B. steigende/fallende Rohölpreise)
    return [stunde, wochentag, tag_absolut]


def trainiere_alle_stationen():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    ausschluesse = lade_ausschlusszeitraeume()
    stationen = conn.execute("SELECT id, name FROM stations WHERE ist_favorit = 1").fetchall()

    for station in stationen:
        alle_rows = conn.execute(
            "SELECT price, timestamp FROM fuel_prices WHERE station_id = ? AND is_open = 1 ORDER BY timestamp",
            (station["id"],),
        ).fetchall()
        rows = [r for r in alle_rows if not ist_ausgeschlossen(r["timestamp"], ausschluesse)]

        if len(rows) < MIN_DATENPUNKTE:
            print(f"{station['name']}: nur {len(rows)} Datenpunkte außerhalb von Sondereffekt-Zeiträumen "
                  f"(mind. {MIN_DATENPUNKTE} nötig) - übersprungen")
            continue

        X = np.array([_merkmale(r["timestamp"]) for r in rows])
        y = np.array([r["price"] for r in rows])

        modell = GradientBoostingRegressor(n_estimators=100, max_depth=3, learning_rate=0.1)
        modell.fit(X, y)

        modell_pfad = MODEL_DIR / f"station_{station['id']}.pkl"
        with open(modell_pfad, "wb") as f:
            pickle.dump(modell, f)
        print(f"{station['name']}: Modell trainiert mit {len(rows)} Datenpunkten "
              f"(von {len(alle_rows)} insgesamt, {len(alle_rows) - len(rows)} durch Sondereffekte ausgeschlossen) "
              f"-> {modell_pfad.name}")

    conn.close()


if __name__ == "__main__":
    trainiere_alle_stationen()
