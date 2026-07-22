"""
Lädt historische Tankerkönig-Preisdateien gezielt für einen Zeitraum herunter,
per Direktzugriff auf einzelne Tages-CSVs - OHNE das komplette Git-Repository
zu klonen (das wäre >100GB entpackt, viel zu groß für unseren Bedarf).

Zugangsdaten aus .env: TANKERKOENIG_GIT_USER, TANKERKOENIG_GIT_PASSWORD
(das ist ein separater Zugang, NICHT der TANKERKOENIG_API_KEY für die Live-API).

Bereits heruntergeladene Tage werden übersprungen - das Skript kann also
gefahrlos mehrfach mit größerem --tage-Wert erneut aufgerufen werden, um
die Historie schrittweise zu erweitern.

Aufruf:
    python download_history.py --tage 90
    python download_history.py --von 2025-11-01 --bis 2026-01-31
"""
import argparse
import time
from datetime import date, timedelta
from pathlib import Path

import httpx

from app.config import settings

BASE_URL = "https://data.tankerkoenig.de/tankerkoenig-organization/tankerkoenig-data/raw/branch/master"


def lade_tag(tag: date, zielordner: Path) -> str:
    relativer_pfad = f"prices/{tag.year}/{tag.month:02d}/{tag.isoformat()}-prices.csv"
    ziel = zielordner / relativer_pfad
    if ziel.exists() and ziel.stat().st_size > 0:
        return "übersprungen (schon vorhanden)"

    ziel.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}/{relativer_pfad}"
    try:
        resp = httpx.get(
            url,
            auth=(settings.tankerkoenig_git_user, settings.tankerkoenig_git_password),
            timeout=30,
            follow_redirects=True,
        )
    except httpx.RequestError as e:
        return f"Netzwerkfehler: {e}"

    if resp.status_code == 200:
        ziel.write_bytes(resp.content)
        return f"OK ({len(resp.content) // 1024} KB)"
    if resp.status_code == 404:
        return "nicht vorhanden (Tag existiert im Archiv nicht, z.B. zu alt oder zu neu)"
    return f"Fehler: HTTP {resp.status_code}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tage", type=int, default=None, help="Anzahl Tage rückwirkend ab gestern")
    parser.add_argument("--von", type=str, default=None, help="Startdatum YYYY-MM-DD")
    parser.add_argument("--bis", type=str, default=None, help="Enddatum YYYY-MM-DD (Standard: gestern)")
    parser.add_argument("--ziel", type=str, default="~/tankerkoenig-import", help="Zielordner")
    args = parser.parse_args()

    if not settings.tankerkoenig_git_user or not settings.tankerkoenig_git_password:
        print("TANKERKOENIG_GIT_USER / TANKERKOENIG_GIT_PASSWORD sind nicht gesetzt (.env prüfen).")
        raise SystemExit(1)

    gestern = date.today() - timedelta(days=1)  # heutiger Tag ist im Archiv oft noch nicht fertig

    if args.tage:
        bis = gestern
        von = bis - timedelta(days=args.tage - 1)
    elif args.von:
        von = date.fromisoformat(args.von)
        bis = date.fromisoformat(args.bis) if args.bis else gestern
    else:
        print("Entweder --tage oder --von angeben (siehe --help).")
        raise SystemExit(1)

    zielordner = Path(args.ziel).expanduser()
    print(f"Lade Preisdaten von {von} bis {bis} nach {zielordner} ...")

    tag = von
    anzahl_ok = 0
    while tag <= bis:
        ergebnis = lade_tag(tag, zielordner)
        print(f"  {tag.isoformat()}: {ergebnis}")
        if ergebnis.startswith("OK"):
            anzahl_ok += 1
        tag += timedelta(days=1)
        time.sleep(0.3)  # kein Ansturm auf den Server

    print(f"\nFertig. {anzahl_ok} neue Dateien heruntergeladen.")
    print(f"Jetzt importieren mit:\n  python import_history.py {zielordner}")


if __name__ == "__main__":
    main()
