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
        ("fahrer_id", "INTEGER REFERENCES fahrer(id)"),
    ],
    "trips": [
        ("kommentar", "TEXT"),
        ("begleitung", "TEXT"),
        ("fahrtzweck", "TEXT"),
        ("ist_freigegeben", "INTEGER NOT NULL DEFAULT 0"),
    ],
}

NEUE_TABELLEN = """
CREATE TABLE IF NOT EXISTS fahrer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS routen_vorlagen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    waypoints TEXT NOT NULL,
    route TEXT NOT NULL,
    distanz_km REAL,
    erstellt_am INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS sondereffekte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_datum TEXT NOT NULL,
    end_datum TEXT NOT NULL,
    beschreibung TEXT,
    erstellt_am INTEGER NOT NULL
);
"""

if __name__ == "__main__":
    conn = sqlite3.connect(settings.db_path)

    conn.executescript(NEUE_TABELLEN)
    print("Tabellen fahrer, routen_vorlagen sichergestellt")

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

    vorhanden = conn.execute(
        "SELECT COUNT(*) FROM sondereffekte WHERE name = 'Tankrabatt Mai/Juni 2026'"
    ).fetchone()[0]
    if vorhanden == 0:
        import time
        conn.execute(
            "INSERT INTO sondereffekte (name, start_datum, end_datum, beschreibung, erstellt_am) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                "Tankrabatt Mai/Juni 2026",
                "2026-05-01",
                "2026-06-30",
                "Befristete Energiesteuersenkung (~17 Ct/L), automatisch bei der Migration eingetragen.",
                int(time.time()),
            ),
        )
        print("Sondereffekt 'Tankrabatt Mai/Juni 2026' angelegt")
    else:
        print("Sondereffekt 'Tankrabatt Mai/Juni 2026' existiert bereits - übersprungen")

    conn.commit()
    conn.close()
    print("Migration abgeschlossen.")
