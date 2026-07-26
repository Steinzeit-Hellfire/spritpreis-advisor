# Spritpreis-Advisor

Vergleicht die E5-Preise deiner Stammtankstellen und zeigt an, ob's gerade
günstig ist. Zusätzlich: Strecken per Wegpunkten auf einer Karte einzeichnen
(echtes Straßen-Routing), mit Datenschutz-Steuerung (Strecken sind privat,
bis du sie freigibst).

## Setup

```bash
# 1. Projekt holen
git clone <repo-url> spritpreis-advisor
cd spritpreis-advisor/backend

# 2. Abhängigkeiten installieren
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt --break-system-packages

# 3. Konfiguration
cp .env.example .env
nano .env
# TANKERKOENIG_API_KEY einfügen (kostenlos: creativecommons.tankerkoenig.de/api-key)
# DB_PATH auf deinen eigenen Pfad anpassen
# ADMIN_PASSWORD und SESSION_SECRET setzen (siehe Abschnitt "Zugriffsschutz")

# 4. Datenbank anlegen
python -m app.database
```

## Frontend-Konfiguration

```bash
cd ../frontend
cp config.example.js config.js
nano config.js   # ACC_DASHBOARD_URL auf deine eigene Adresse setzen
```

`config.js` ist in `.gitignore` und wird nie committet.

## Deine Stationen eintragen

Erst die Tankerkönig-IDs deiner Wunsch-Tankstellen finden (eigene Koordinaten
einsetzen, hier nur als Beispiel München und Hamburg):

```bash
python find_stations.py 48.1351 11.5820 --radius 5   # Beispiel: München
python find_stations.py 53.5511 9.9937 --radius 5    # Beispiel: Hamburg
```

Zeigt eine Liste mit ID, Name, Adresse, Koordinaten. Passende Zeile raussuchen,
dann je Station:

```bash
curl -X POST http://localhost:8091/api/stations \
  -H "Content-Type: application/json" \
  -d '{"tankerkoenig_id": "<ID>", "name": "<Name>", "marke": "<Marke>", "lat": <LAT>, "lng": <LNG>}'
```

## Starten

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8091
```

Für Dauerbetrieb: als systemd-Service einrichten, der diesen Befehl im
`backend`-Verzeichnis mit aktivierter venv ausführt.

## Preise automatisch abfragen (Cronjob)

```bash
crontab -e
```

Zeile einfügen (Pfad an dein System anpassen):

```
*/5 * * * * cd /pfad/zu/spritpreis-advisor/backend && .venv/bin/python run_poller.py >> poller.log 2>&1
```

## Von außen erreichbar machen

`nginx/spritpreis-advisor.conf` in deine Nginx-Config übernehmen (Port/Domain
nach Wunsch anpassen), dann `sudo nginx -s reload`.

## Zugriffsschutz für Strecken

Strecken (Routen, Kommentare, Begleitung, Fahrtzweck) sind **standardmäßig
privat** und nur sichtbar, wenn du als Admin eingeloggt bist. Andere können
die Preis-Seite weiterhin normal nutzen, sehen aber nur Strecken, die du
explizit freigegeben hast.

In `.env` festlegen:

```
ADMIN_PASSWORD=ein-sicheres-passwort
SESSION_SECRET=eine-zufällige-zeichenkette
```

Login über den "Admin-Login"-Link unten auf der Strecken-Seite. Als Admin
kannst du bei jeder Strecke über "Freigeben/Sperren" steuern, ob sie auch
ohne Login sichtbar ist.

**Wichtig:** Das schützt vor casual-Zugriff im selben Netzwerk, ist aber kein
Ersatz für echte Verschlüsselung. Wenn du die Seite außerhalb deines
Heimnetzes erreichbar machst, unbedingt zusätzlich HTTPS einrichten (z.B.
über einen Reverse Proxy mit Let's Encrypt) - sonst geht das Passwort im
Klartext übers Netz.

## Preis-Prognose (KI-Modell)

Zusätzlich zur einfachen Statistik trainiert `ml_train.py` pro Station ein
kleines Machine-Learning-Modell (Gradient Boosting, scikit-learn), das aus
Wochentag/Uhrzeit-Mustern eine 24h-Prognose ableitet ("voraussichtlich am
günstigsten gegen 20 Uhr"). Braucht mindestens 200 Preis-Datenpunkte pro
Station, sonst wird die Station beim Training übersprungen.

Einmalig manuell anstoßen oder per Cronjob nachts laufen lassen:

```bash
crontab -e
```

Zeile ergänzen (täglich um 3 Uhr):

```
0 3 * * * cd /pfad/zu/spritpreis-advisor/backend && .venv/bin/python ml_train.py >> ml_train.log 2>&1
```

Das Backend liest die trainierten Modelle bei jeder Anfrage automatisch neu
ein - kein Neustart nötig, wenn ein neues Modell dazukommt.

### Einmaligen Testlauf planen (statt bis 3 Uhr nachts zu warten)

`cron` ist für wiederkehrende Jobs gedacht - für einen einmaligen Test zu
einem bestimmten Zeitpunkt (z.B. "heute in 10 Minuten" oder "morgen früh")
ist `at` das richtige Werkzeug:

```bash
sudo apt install at
sudo systemctl enable --now atd
```

Job einplanen:

```bash
echo "cd /pfad/zu/spritpreis-advisor/backend && .venv/bin/python ml_train.py >> ml_train.log 2>&1" | at 09:35
```

Eingeplante Jobs auflisten (zur Bestätigung, dass es geklappt hat):

```bash
atq
```

`at` versteht neben festen Uhrzeiten (`at 09:35`, `at 3pm`) auch relative
und sprachliche Angaben, z.B.:

```
at now + 10 minutes
at now + 2 hours
at tomorrow
at 3pm tomorrow
at noon next monday
```

Vollständige Übersicht der möglichen Zeitangaben:
[How to Use at Command for One-Time Task Scheduling](https://oneuptime.com/blog/post/2026-03-02-how-to-use-at-command-for-one-time-task-scheduling-on-ubuntu/view)
(oder auf dem Pi direkt `man at`, Abschnitt "TIME SPECIFICATION").

Nach der geplanten Zeit prüfen:

```bash
cat /pfad/zu/spritpreis-advisor/backend/ml_train.log
```

Und, falls der Job scheinbar gar nicht lief, ob `at`/`atd` ihn überhaupt
ausgeführt hat:

```bash
grep -i "atd\|CRON" /var/log/syslog | tail -20
```

## Historische Preisdaten importieren (optional, aber empfohlen)

Statt wochenlang auf den Live-Poller zu warten, lassen sich Monate an echter
Historie direkt importieren:

1. Zugang beim Tankerkönig-Team anfragen (siehe deren Doku/Kontakt)
2. `python download_history.py --tage 90` (lädt gezielt einzelne Tage,
   kein Voll-Clone - das Repo ist >100GB entpackt)
3. `python import_history.py ~/tankerkoenig-import`

Danach direkt `python ml_train.py` laufen lassen, um sofort ein Modell mit
echter Historie zu trainieren.

## Funktionsübersicht

- **Preise-Seite**: Live-Vergleich deiner Favoriten-Stationen mit Ampel
  (günstig / üblich / teurer als üblich). Manuelle Tankvorgangs-Erfassung
  inkl. Verbrauchs- und Kosten/km-Berechnung, Bordcomputer-Werten und
  Foto-Upload. "In Waze navigieren"-Link mit Live-Standort-ETA.
- **Strecken-Seite**: Wegpunkte auf der Karte setzen, Route wird automatisch
  über echte Straßen berechnet (OSRM) und lässt sich per Drag&Drop anpassen.
  Datum/Uhrzeit, Zweck, Begleitung, Kommentar. Privat bis zur Freigabe durch
  den Admin.
- **Historischer Preis-Import**: `import_history.py` kann Monate an
  Preishistorie aus dem offiziellen Tankerkönig-Datenarchiv importieren
  (Zugang muss separat bei Tankerkönig angefragt werden, siehe deren
  Dokumentation).

## Später möglich

- Höhenmeter je Strecke (DB-Spalten sind schon vorbereitet)
- Discord-Bot pusht Preis-Empfehlungen automatisch
- KI-gestützte Preisvorhersage, sobald genug Historie vorliegt
