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
    conn.commit()
    conn.close()
    print("Migration abgeschlossen.")
