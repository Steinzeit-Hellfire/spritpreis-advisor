from datetime import datetime
from .database import get_connection
from .ml_predict import prognose_24h

# Tankrabatt (befristete Energiesteuersenkung, ~17 Ct/L brutto) galt vom
# 1. Mai bis 30. Juni 2026 - danach wieder regulärer Steuersatz. Diese Preise
# sind kein normales Stunden-/Wochentagsmuster, sondern reine Steuerpolitik,
# und würden Vergleichswert + Modell ohne Ausschluss künstlich nach unten
# verzerren. Bei Bedarf hier anpassen, falls es zukünftig weitere befristete
# Steuersenkungen gibt.
TANKRABATT_START = int(datetime(2026, 5, 1).timestamp())
TANKRABATT_ENDE = int(datetime(2026, 7, 1).timestamp())  # exklusiv, 1. Juli zählt schon wieder normal


def get_comparison() -> dict:
    """Vergleicht die aktuellen Preise aller Favoriten-Stationen und gibt für jede
    eine Einschätzung zurück, ob der Preis gerade günstig ist.

    Zweistufig, damit von Anfang an eine brauchbare Aussage da ist:
    1. Sobald an mind. 3 verschiedenen Tagen zur selben Uhrzeit Daten vorliegen
       (braucht ein paar Tage Laufzeit): Vergleich gegen den Schnitt genau
       dieser Wochenstunde - das ist die eigentlich aussagekräftige Einschätzung.
    2. Bis dahin: Vergleich gegen den bisherigen Gesamtschnitt der Station
       (braucht nur 3 Datenpunkte, also ~15 Minuten Laufzeit) - grob, aber
       besser als "keine Historie".
    """
    conn = get_connection()

    aktuelle_preise = conn.execute(
        """
        SELECT s.id, s.name, s.marke, s.adresse, s.lat, s.lng, fp.price, fp.is_open, fp.timestamp
        FROM stations s
        JOIN fuel_prices fp ON fp.station_id = s.id
        WHERE s.ist_favorit = 1
          AND fp.timestamp = (
              SELECT MAX(timestamp) FROM fuel_prices WHERE station_id = s.id
          )
        ORDER BY fp.price ASC
        """
    ).fetchall()

    stunde = f"{datetime.now().hour:02d}"

    ergebnisse = []
    for row in aktuelle_preise:
        # Feinere Statistik: gleiche Uhrzeit, aber nur wenn Daten von mehreren
        # verschiedenen Tagen vorliegen (sonst ist "Durchschnitt" nur der
        # heutige Wert selbst und damit bedeutungslos). Tankrabatt-Zeitraum
        # ausgeschlossen, da sonst künstlich verzerrt (siehe Konstanten oben).
        stunden_stat = conn.execute(
            """
            SELECT AVG(price) AS avg_price,
                   COUNT(DISTINCT date(timestamp, 'unixepoch')) AS tage
            FROM fuel_prices
            WHERE station_id = ? AND is_open = 1
              AND strftime('%H', datetime(timestamp, 'unixepoch')) = ?
              AND (timestamp < ? OR timestamp >= ?)
            """,
            (row["id"], stunde, TANKRABATT_START, TANKRABATT_ENDE),
        ).fetchone()

        # Grobe Statistik: einfach alle bisherigen Preise dieser Station
        # (ebenfalls ohne Tankrabatt-Zeitraum).
        gesamt_stat = conn.execute(
            """
            SELECT AVG(price) AS avg_price, COUNT(*) AS n
            FROM fuel_prices
            WHERE station_id = ? AND is_open = 1
              AND (timestamp < ? OR timestamp >= ?)
            """,
            (row["id"], TANKRABATT_START, TANKRABATT_ENDE),
        ).fetchone()

        if stunden_stat["tage"] and stunden_stat["tage"] >= 3:
            vergleichswert = stunden_stat["avg_price"]
            basis = f"Schnitt dieser Uhrzeit (Daten von {stunden_stat['tage']} Tagen)"
        elif gesamt_stat["n"] and gesamt_stat["n"] >= 3:
            vergleichswert = gesamt_stat["avg_price"]
            basis = "bisheriger Gesamtschnitt (noch wenig Historie)"
        else:
            vergleichswert = None
            basis = None

        if vergleichswert is None:
            status = "sammle noch Daten…"
        elif row["price"] <= vergleichswert - 0.01:
            status = "günstig"
        elif row["price"] >= vergleichswert + 0.02:
            status = "teurer als üblich"
        else:
            status = "im üblichen Bereich"

        ergebnisse.append(
            {
                "station_id": row["id"],
                "name": row["name"],
                "marke": row["marke"],
                "adresse": row["adresse"],
                "lat": row["lat"],
                "lng": row["lng"],
                "aktueller_preis": row["price"],
                "geoeffnet": bool(row["is_open"]),
                "vergleichswert": round(vergleichswert, 3) if vergleichswert else None,
                "basis": basis,
                "status": status,
                "prognose": prognose_24h(row["id"], aktueller_preis=row["price"]),
            }
        )

    conn.close()
    guenstigste = ergebnisse[0] if ergebnisse else None
    return {"guenstigste": guenstigste, "stationen": ergebnisse}
