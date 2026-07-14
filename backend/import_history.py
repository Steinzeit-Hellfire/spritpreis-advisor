"""
Importiert historische Tankerkönig-Preisdaten (aus dem offiziellen
tankerkoenig-data-Repository, https://dev.azure.com/tankerkoenig/_git/tankerkoenig-data)
für die eigenen Favoriten-Stationen in die lokale Datenbank.

Die CSV-Dateien aus dem Repo enthalten ALLE Tankstellen Deutschlands - dieses
Skript filtert automatisch nur die Zeilen heraus, deren station_uuid zu einer
deiner in der DB hinterlegten Favoriten-Stationen passt.

Erwartetes CSV-Format (so wie es im tankerkoenig-data-Repo vorliegt):
    date,station_uuid,diesel,e5,e10,dieselchange,e5change,e10change

Aufruf:
    python import_history.py ~/tankerkoenig-import/prices/2026/07

Der Pfad kann eine einzelne CSV-Datei oder ein Ordner sein (dann werden alle
*.csv-Dateien darin, auch in Unterordnern, verarbeitet).
"""
import csv
import sys
from datetime import datetime
from pathlib import Path

from app.database import get_connection


def parse_datum(wert: str) -> int:
    """Wandelt das Datum aus der CSV (z.B. '2026-07-01 05:32:12+02') in einen
    Unix-Timestamp um. Tankerkönig nutzt manchmal '+02' statt '+02:00' -
    beides wird hier abgefangen."""
    wert = wert.strip()
    if len(wert) >= 3 and wert[-3] in "+-" and ":" not in wert[-3:]:
        wert = wert + ":00"  # "+02" -> "+02:00"
    try:
        dt = datetime.fromisoformat(wert)
    except ValueError:
        # Fallback ohne Zeitzone
        dt = datetime.strptime(wert.split("+")[0].split("Z")[0].strip(), "%Y-%m-%d %H:%M:%S")
    return int(dt.timestamp())


def importiere_datei(pfad: Path, uuid_zu_id: dict, conn) -> int:
    gespeichert = 0
    with pfad.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for zeile in reader:
            uuid = zeile.get("station_uuid", "").strip()
            if uuid not in uuid_zu_id:
                continue
            if zeile.get("e5change", "0") != "1":
                continue  # E5-Preis hat sich in dieser Zeile nicht geändert
            try:
                preis = float(zeile["e5"])
            except (KeyError, ValueError):
                continue
            if preis <= 0:
                continue  # -1 o.ä. = ungültiger Preis
            try:
                timestamp = parse_datum(zeile["date"])
            except Exception as e:
                print(f"  Konnte Datum nicht parsen: {zeile.get('date')!r} ({e}) - übersprungen")
                continue

            cur = conn.execute(
                "INSERT OR IGNORE INTO fuel_prices (station_id, fuel_type, price, is_open, timestamp) "
                "VALUES (?, 'e5', ?, 1, ?)",
                (uuid_zu_id[uuid], preis, timestamp),
            )
            if cur.rowcount:
                gespeichert += 1
    return gespeichert


def main(pfad_arg: str):
    pfad = Path(pfad_arg).expanduser()
    if not pfad.exists():
        print(f"Pfad nicht gefunden: {pfad}")
        sys.exit(1)

    dateien = [pfad] if pfad.is_file() else sorted(pfad.rglob("*.csv"))
    if not dateien:
        print("Keine CSV-Dateien gefunden.")
        sys.exit(1)

    conn = get_connection()
    stationen = conn.execute("SELECT id, tankerkoenig_id FROM stations WHERE ist_favorit = 1").fetchall()
    uuid_zu_id = {row["tankerkoenig_id"]: row["id"] for row in stationen}

    if not uuid_zu_id:
        print("Keine Favoriten-Stationen in der Datenbank gefunden - erst über /api/stations anlegen.")
        sys.exit(1)

    print(f"Suche nach {len(uuid_zu_id)} Stations-ID(s) in {len(dateien)} Datei(en)...")

    gesamt = 0
    for i, datei in enumerate(dateien, 1):
        anzahl = importiere_datei(datei, uuid_zu_id, conn)
        gesamt += anzahl
        if anzahl:
            print(f"  [{i}/{len(dateien)}] {datei.name}: {anzahl} Preise importiert")
        if i % 10 == 0:
            conn.commit()  # zwischendurch sichern bei vielen Dateien

    conn.commit()
    conn.close()
    print(f"\nFertig. Insgesamt {gesamt} neue Preis-Datenpunkte importiert.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Aufruf: python import_history.py <Pfad zu CSV-Datei oder -Ordner>")
        sys.exit(1)
    main(sys.argv[1])
