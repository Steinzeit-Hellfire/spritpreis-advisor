import time
from .config import settings
from .database import get_connection
from .tankerkoenig import TankerkoenigClient


def poll_once() -> int:
    """Fragt einmalig die Preise aller Favoriten-Stationen ab und speichert sie.
    Gibt die Anzahl gespeicherter Preis-Datenpunkte zurück."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, tankerkoenig_id FROM stations WHERE ist_favorit = 1"
    ).fetchall()

    if not rows:
        conn.close()
        print("Keine Favoriten-Stationen hinterlegt - nichts zu tun.")
        return 0

    id_map = {row["tankerkoenig_id"]: row["id"] for row in rows}
    client = TankerkoenigClient(settings.tankerkoenig_api_key)
    prices = client.get_prices(list(id_map.keys()))

    now = int(time.time())
    gespeichert = 0
    for tk_id, info in prices.items():
        local_id = id_map.get(tk_id)
        if local_id is None:
            continue
        is_open = 1 if info.get("status") == "open" else 0
        preis = info.get("e5")
        conn.execute(
            "INSERT INTO fuel_prices (station_id, fuel_type, price, is_open, timestamp) "
            "VALUES (?, 'e5', ?, ?, ?)",
            (local_id, preis, is_open, now),
        )
        gespeichert += 1

    conn.commit()
    conn.close()
    return gespeichert


if __name__ == "__main__":
    anzahl = poll_once()
    print(f"{anzahl} Preis-Datenpunkte gespeichert.")
