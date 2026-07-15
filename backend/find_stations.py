"""
Einmaliges Hilfsskript, um die Tankerkönig-Stations-ID deiner Shell-Tankstellen
herauszufinden (wird für stations.tankerkoenig_id gebraucht).

Aufruf-Beispiel (Koordinaten von Lemgo bzw. Bad Salzuflen anpassen):
    python find_stations.py 52.0286 8.8996 --radius 5
"""
import argparse
from app.config import settings
from app.tankerkoenig import TankerkoenigClient

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("lat", type=float)
    parser.add_argument("lng", type=float)
    parser.add_argument("--radius", type=int, default=5, help="Suchradius in km (max 25)")
    args = parser.parse_args()

    client = TankerkoenigClient(settings.tankerkoenig_api_key)
    stationen = client.find_stations_near(args.lat, args.lng, args.radius)

    for s in stationen:
        print(f"{s['id']}  |  {s.get('brand', '?'):10s}  |  {s.get('name', '')}  |  "
              f"{s.get('street', '')} {s.get('houseNumber', '')}  |  {s.get('dist')} km  |  "
              f"lat={s.get('lat')} lng={s.get('lng')}")
