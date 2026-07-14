from datetime import datetime
from .database import get_connection


def get_comparison() -> dict:
    """Vergleicht die aktuellen Preise aller Favoriten-Stationen und gibt für jede
    eine Einschätzung zurück, ob der Preis gerade günstig ist (verglichen mit dem
    historischen Schnitt zu dieser Wochentag+Uhrzeit-Kombination).
    """
    conn = get_connection()

    aktuelle_preise = conn.execute(
        """
        SELECT s.id, s.name, s.marke, s.adresse, fp.price, fp.is_open, fp.timestamp
        FROM stations s
        JOIN fuel_prices fp ON fp.station_id = s.id
        WHERE s.ist_favorit = 1
          AND fp.timestamp = (
              SELECT MAX(timestamp) FROM fuel_prices WHERE station_id = s.id
          )
        ORDER BY fp.price ASC
        """
    ).fetchall()

    jetzt = datetime.now()
    stunde = f"{jetzt.hour:02d}"
    wochentag = str(jetzt.weekday())  # 0=Montag ... via strftime('%w') ist 0=Sonntag, siehe unten

    ergebnisse = []
    for row in aktuelle_preise:
        stat = conn.execute(
            """
            SELECT AVG(price) AS avg_price, MIN(price) AS min_price, COUNT(*) AS n
            FROM fuel_prices
            WHERE station_id = ?
              AND is_open = 1
              AND strftime('%w', datetime(timestamp, 'unixepoch')) = strftime('%w', 'now')
              AND strftime('%H', datetime(timestamp, 'unixepoch')) = ?
            """,
            (row["id"], stunde),
        ).fetchone()

        avg_price = stat["avg_price"]
        genug_daten = (stat["n"] or 0) >= 5  # erst ab 5 Datenpunkten wird die Einschätzung aussagekräftig

        if not genug_daten or avg_price is None:
            status = "noch keine ausreichende Historie für diese Uhrzeit"
        elif row["price"] <= avg_price - 0.01:
            status = "günstig - jetzt tanken"
        elif row["price"] >= avg_price + 0.02:
            status = "teurer als üblich - eher warten"
        else:
            status = "im üblichen Bereich"

        ergebnisse.append(
            {
                "station_id": row["id"],
                "name": row["name"],
                "marke": row["marke"],
                "adresse": row["adresse"],
                "aktueller_preis": row["price"],
                "geoeffnet": bool(row["is_open"]),
                "durchschnitt_diese_uhrzeit": round(avg_price, 3) if avg_price else None,
                "status": status,
            }
        )

    conn.close()
    guenstigste = ergebnisse[0] if ergebnisse else None
    return {"guenstigste": guenstigste, "stationen": ergebnisse}
