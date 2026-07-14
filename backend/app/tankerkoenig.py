import httpx

BASE_URL = "https://creativecommons.tankerkoenig.de/json"


class TankerkoenigClient:
    """Schlanker Client für die Tankerkönig-API.

    Hinweis: laut Tankerkönig nicht zu häufig pollen (empfohlen: alle 5 Minuten),
    sonst antwortet die API mit HTTP 503 (Limit überschritten). Preise für mehrere
    Stationen sollen laut Tankerkönig-Team immer über EINEN Aufruf mit mehreren
    IDs abgefragt werden, nicht einzeln.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("TANKERKOENIG_API_KEY ist nicht gesetzt (.env prüfen)")
        self.api_key = api_key

    def get_prices(self, station_ids: list[str]) -> dict:
        """Preise für bis zu 10 Stationen auf einmal abfragen."""
        if not station_ids:
            return {}
        resp = httpx.get(
            f"{BASE_URL}/prices.php",
            params={"ids": ",".join(station_ids), "apikey": self.api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Tankerkönig-Fehler: {data.get('message')}")
        return data["prices"]

    def find_stations_near(self, lat: float, lng: float, radius_km: int = 10) -> list[dict]:
        """Hilfsfunktion: einmalig Tankstellen in der Nähe suchen, um deren ID zu finden."""
        resp = httpx.get(
            f"{BASE_URL}/list.php",
            params={
                "lat": lat,
                "lng": lng,
                "rad": min(radius_km, 25),
                "sort": "dist",
                "type": "all",
                "apikey": self.api_key,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Tankerkönig-Fehler: {data.get('message')}")
        return data["stations"]
