"""
Verwaltung von "Sondereffekten" - befristeten Ereignissen (z.B. eine
Steuersenkung/Tankrabatt), die den Preis künstlich verzerren und deshalb
aus Statistik und ML-Training ausgeschlossen werden sollen.

Der Admin pflegt diese selbst über die Weboberfläche/API - kein Code-Update
nötig, wenn z.B. ein neuer Tankrabatt angekündigt wird. Ein Sondereffekt
kann sich auf eine einzelne Kraftstoffart beschränken (z.B. nur Diesel) oder,
wenn kein Kraftstoff angegeben ist, für alle Sorten gelten.
"""
from datetime import datetime, timedelta

from .database import get_connection


def lade_ausschlusszeitraeume(kraftstoff: str) -> list[tuple[int, int]]:
    """Gibt eine Liste von (start_ts, end_ts) Unix-Zeitstempel-Paaren zurück,
    die für die angegebene Kraftstoffart gelten (kraftstoffspezifische
    Einträge + Einträge ohne Kraftstoffangabe, die für alle Sorten gelten).
    end_ts jeweils exklusiv (also bis Ende des end_datum-Tages)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT start_datum, end_datum FROM sondereffekte WHERE kraftstoff IS NULL OR kraftstoff = ?",
        (kraftstoff,),
    ).fetchall()
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
