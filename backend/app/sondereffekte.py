"""
Verwaltung von "Sondereffekten" - befristeten Ereignissen (z.B. eine
Steuersenkung/Tankrabatt), die den Preis künstlich verzerren und deshalb
aus Statistik und ML-Training ausgeschlossen werden sollen.

Der Admin pflegt diese selbst über die Weboberfläche/API - kein Code-Update
nötig, wenn z.B. ein neuer Tankrabatt angekündigt wird.
"""
from datetime import datetime, timedelta

from .database import get_connection


def lade_ausschlusszeitraeume() -> list[tuple[int, int]]:
    """Gibt eine Liste von (start_ts, end_ts) Unix-Zeitstempel-Paaren zurück,
    end_ts jeweils exklusiv (also bis Ende des end_datum-Tages)."""
    conn = get_connection()
    rows = conn.execute("SELECT start_datum, end_datum FROM sondereffekte").fetchall()
    conn.close()

    zeitraeume = []
    for row in rows:
        try:
            start = int(datetime.fromisoformat(row["start_datum"]).timestamp())
            ende = int((datetime.fromisoformat(row["end_datum"]) + timedelta(days=1)).timestamp())
            zeitraeume.append((start, ende))
        except ValueError:
            continue  # falsch formatiertes Datum ignorieren statt abzustürzen
    return zeitraeume


def ist_ausgeschlossen(timestamp: int, zeitraeume: list[tuple[int, int]]) -> bool:
    return any(start <= timestamp < ende for start, ende in zeitraeume)
