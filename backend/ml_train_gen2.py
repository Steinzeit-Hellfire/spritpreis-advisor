"""
GEN2 - ALPHA: Experimentelles Zweitmodell, das parallel zum bestehenden
(Gen1, ml_train.py) läuft und dieses NICHT ersetzt. Drei Verbesserungen
gegenüber Gen1:

1. Echter Out-of-Sample-Test: ein Hilfsmodell wird NUR mit Daten bis vor
   HOLDOUT_TAGE trainiert und dann gegen die tatsächlichen (dem Modell nie
   gezeigten) Preise dieser letzten Tage geprüft - ehrlichere Genauigkeit
   als Gen1s Rückblick (der dasselbe Modell nutzt, das die Daten schon kennt).
2. Zusätzliches Trend-Merkmal: gleitender 3-Tage-Schnitt (kausal berechnet,
   nutzt für jeden Zeitpunkt nur Daten VOR diesem Zeitpunkt, keine
   Zukunftsdaten-Leckage).
3. Konfidenzband statt Punktschätzung: drei Quantil-Modelle (10%/50%/90%)
   statt einem einzelnen Wert - ehrlicher, weil es eine Bandbreite statt
   Schein-Präzision zeigt.

Status ALPHA: weniger erprobt als Gen1, kann sich noch ändern. Läuft
zusätzlich zu ml_train.py, ersetzt es nicht.
"""
import pickle
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from app.config import settings
from app.database import get_connection
from app.sondereffekte import lade_ausschlusszeitraeume, ist_ausgeschlossen

MODEL_DIR = Path(settings.db_path).resolve().parent / "modelle"
MIN_DATENPUNKTE = 200
HOLDOUT_TAGE = 7
KRAFTSTOFFARTEN = ("e5", "e10", "diesel")


def _rollender_schnitt_3tage(rows: list[dict]) -> list[dict]:
    """Fügt jeder Zeile kausal einen gleitenden 3-Tage-Schnitt hinzu - nutzt
    für Zeile N nur Daten VOR dem Zeitpunkt von Zeile N (keine Leckage)."""
    ergebnisse = []
    fenster = deque()  # (timestamp, price)
    summe = 0.0
    for r in rows:
        ts, preis = r["timestamp"], r["price"]
        grenze = ts - 3 * 86400
        while fenster and fenster[0][0] < grenze:
            alt_ts, alt_preis = fenster.popleft()
            summe -= alt_preis
        schnitt_3tage = (summe / len(fenster)) if fenster else preis
        ergebnisse.append({"timestamp": ts, "price": preis, "schnitt_3tage": schnitt_3tage})
        fenster.append((ts, preis))
        summe += preis
    return ergebnisse


def _merkmale(zeile: dict) -> list[float]:
    dt = datetime.fromtimestamp(zeile["timestamp"])
    return [dt.hour, dt.weekday(), zeile["timestamp"] // 86400, zeile["schnitt_3tage"]]


def trainiere_alle_stationen():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    stationen = conn.execute("SELECT id, name FROM stations WHERE ist_favorit = 1").fetchall()
    jetzt = int(datetime.now().timestamp())
    holdout_grenze = jetzt - HOLDOUT_TAGE * 86400

    for station in stationen:
        for kraftstoff in KRAFTSTOFFARTEN:
            ausschluesse = lade_ausschlusszeitraeume(kraftstoff)
            alle_rows = conn.execute(
                "SELECT price, timestamp FROM fuel_prices WHERE station_id = ? AND fuel_type = ? "
                "AND is_open = 1 ORDER BY timestamp",
                (station["id"], kraftstoff),
            ).fetchall()
            rows = [dict(r) for r in alle_rows if not ist_ausgeschlossen(r["timestamp"], ausschluesse)]

            if len(rows) < MIN_DATENPUNKTE:
                print(f"{station['name']} ({kraftstoff}) GEN2: nur {len(rows)} Datenpunkte - übersprungen")
                continue

            rows_mit_trend = _rollender_schnitt_3tage(rows)

            # --- Echter Out-of-Sample-Test ---
            trainings_rows = [r for r in rows_mit_trend if r["timestamp"] < holdout_grenze]
            holdout_rows = [r for r in rows_mit_trend if r["timestamp"] >= holdout_grenze]

            holdout_ergebnis = None
            if len(trainings_rows) >= MIN_DATENPUNKTE and holdout_rows:
                X_train = np.array([_merkmale(r) for r in trainings_rows])
                y_train = np.array([r["price"] for r in trainings_rows])
                testmodell = GradientBoostingRegressor(n_estimators=100, max_depth=3, learning_rate=0.1)
                testmodell.fit(X_train, y_train)

                abweichungen = []
                for r in holdout_rows:
                    vorhersage = float(testmodell.predict([_merkmale(r)])[0])
                    abweichungen.append(abs(vorhersage - r["price"]))

                mittlere_abweichung = float(sum(abweichungen) / len(abweichungen))
                mittlerer_preis = float(sum(r["price"] for r in holdout_rows) / len(holdout_rows))
                holdout_ergebnis = {
                    "mae_ct": round(mittlere_abweichung * 100, 1),
                    "genauigkeit_prozent": round(max(0.0, 100 - (mittlere_abweichung / mittlerer_preis * 100)), 1),
                    "n": len(holdout_rows),
                    "holdout_tage": HOLDOUT_TAGE,
                }
                print(f"{station['name']} ({kraftstoff}) GEN2 Out-of-Sample: "
                      f"{holdout_ergebnis['genauigkeit_prozent']}% auf {holdout_ergebnis['n']} nie gesehenen Punkten")
            else:
                print(f"{station['name']} ({kraftstoff}) GEN2: zu wenig Daten für Holdout-Test - "
                      f"Konfidenzmodelle trainieren trotzdem, aber ohne Out-of-Sample-Zahl")

            # --- Produktionsmodelle: Quantile 10/50/90%, mit ALLEN Daten ---
            X = np.array([_merkmale(r) for r in rows_mit_trend])
            y = np.array([r["price"] for r in rows_mit_trend])

            modelle = {}
            for quantil, name in [(0.1, "lower"), (0.5, "median"), (0.9, "upper")]:
                m = GradientBoostingRegressor(
                    loss="quantile", alpha=quantil, n_estimators=100, max_depth=3, learning_rate=0.1
                )
                m.fit(X, y)
                modelle[name] = m

            letzter_schnitt_3tage = rows_mit_trend[-1]["schnitt_3tage"] if rows_mit_trend else None

            paket = {
                "modelle": modelle,
                "holdout": holdout_ergebnis,
                "letzter_schnitt_3tage": letzter_schnitt_3tage,
                "version": "gen2-alpha",
            }
            modell_pfad = MODEL_DIR / f"station_{station['id']}_{kraftstoff}_gen2.pkl"
            with open(modell_pfad, "wb") as f:
                pickle.dump(paket, f)
            print(f"{station['name']} ({kraftstoff}) GEN2: Konfidenzmodelle trainiert "
                  f"({len(rows_mit_trend)} Datenpunkte) -> {modell_pfad.name}")

    conn.close()


if __name__ == "__main__":
    trainiere_alle_stationen()
