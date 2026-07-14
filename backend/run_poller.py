"""Wird per Cronjob alle 5 Minuten aufgerufen, siehe README.md."""
from app.poller import poll_once

if __name__ == "__main__":
    anzahl = poll_once()
    print(f"{anzahl} Preis-Datenpunkte gespeichert.")
