# Spritpreis-Advisor

Vergleicht die E5-Preise deiner Stammtankstellen (Shell Lemgo, Shell Bad
Salzuflen) und zeigt an, ob's gerade günstig ist. Zusätzlich: Strecken per
Pins auf einer Karte einzeichnen.

## Setup

```bash
# 1. Projekt auf den Pi holen
cd /home/detrees95
git clone <repo-url> spritpreis-advisor
cd spritpreis-advisor/backend

# 2. Abhängigkeiten installieren
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --break-system-packages

# 3. API-Key eintragen
cp .env.example .env
nano .env    # TANKERKOENIG_API_KEY einfügen (kostenlos: creativecommons.tankerkoenig.de/api-key)

# 4. Datenbank anlegen
python -m app.database
```

## Deine Stationen eintragen

Erst die Tankerkönig-IDs von Shell Lemgo und Shell Bad Salzuflen finden:

```bash
python find_stations.py 52.0286 8.8996 --radius 5   # Lemgo
python find_stations.py 52.0894 8.7508 --radius 5   # Bad Salzuflen
```

Zeigt eine Liste mit ID, Name, Adresse. Shell raussuchen, ID kopieren, dann
je Station:

```bash
curl -X POST http://localhost:8091/api/stations \
  -H "Content-Type: application/json" \
  -d '{"tankerkoenig_id": "<ID>", "name": "Shell Lemgo", "marke": "Shell"}'
```

## Starten

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091
```

Dashboard läuft dann unter `http://<pi-ip>:8091`.

Für Dauerbetrieb: als systemd-Service einrichten, genau wie beim
ACC-Dashboard (`uvicorn app.main:app --host 127.0.0.1 --port 8091`).

## Preise automatisch abfragen (Cronjob)

```bash
crontab -e
```

Zeile einfügen:

```
*/5 * * * * cd /home/detrees95/spritpreis-advisor/backend && .venv/bin/python run_poller.py >> poller.log 2>&1
```

## Von außen erreichbar machen

`nginx/spritpreis-advisor.conf` in deine Nginx-Config übernehmen, dann:

```bash
sudo nginx -s reload
```

Danach in `frontend/index.html` und `frontend/karte.html` die Platzhalter-URL
`acc-dashboard.local` durch die echte Adresse deines ACC-Dashboards ersetzen
(und dort umgekehrt einen Link hierher ergänzen).

## Später möglich

- Höhenmeter je Strecke (DB-Spalten sind schon vorbereitet)
- Discord-Bot pusht Preis-Empfehlungen automatisch
