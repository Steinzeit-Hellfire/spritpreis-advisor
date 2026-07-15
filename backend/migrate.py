"""
Einmalig ausführen, um eine bestehende Datenbank auf das neue Schema zu
bringen (fügt fehlende Spalten hinzu, ohne vorhandene Daten zu löschen).

Aufruf:
    python migrate.py
"""
import sqlite3
from app.config import settings

NEUE_SPALTEN = {
    "refuels": [
        ("bordcomputer_km", "REAL"),
        ("bordcomputer_verbrauch", "REAL"),
        ("foto_pfad", "TEXT"),
    ],
    "trips": [
        ("kommentar", "TEXT"),
        ("begleitung", "TEXT"),
        ("fahrtzweck", "TEXT"),
        ("ist_freigegeben", "INTEGER NOT NULL DEFAULT 0"),
    ],
}

if __name__ == "__main__":
    conn = sqlite3.connect(settings.db_path)
    for tabelle, spalten in NEUE_SPALTEN.items():
        vorhandene = {row[1] for row in conn.execute(f"PRAGMA table_info({tabelle})")}
        for spalte, typ in spalten:
            if spalte not in vorhandene:
                conn.execute(f"ALTER TABLE {tabelle} ADD COLUMN {spalte} {typ}")
                print(f"{tabelle}.{spalte} ({typ}) ergänzt")
            else:
                print(f"{tabelle}.{spalte} existiert bereits - übersprungen")

    try:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_fuel_prices_unique "
            "ON fuel_prices(station_id, fuel_type, timestamp)"
        )
        print("Unique-Index auf fuel_prices ergänzt (verhindert Duplikate beim Import)")
    except sqlite3.IntegrityError as e:
        print(f"Konnte Unique-Index nicht anlegen, vermutlich existierende Duplikate: {e}")

    conn.commit()
    conn.close()
    print("Migration abgeschlossen.")
