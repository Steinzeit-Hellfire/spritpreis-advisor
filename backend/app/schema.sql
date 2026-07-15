-- Spritpreis-Advisor · Datenbankschema

CREATE TABLE IF NOT EXISTS stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tankerkoenig_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    marke TEXT,
    adresse TEXT,
    lat REAL,
    lng REAL,
    ist_favorit INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fuel_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id INTEGER NOT NULL REFERENCES stations(id),
    fuel_type TEXT NOT NULL DEFAULT 'e5',
    price REAL,
    is_open INTEGER NOT NULL DEFAULT 1,
    timestamp INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fuel_prices_station_time ON fuel_prices(station_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_fuel_prices_unique ON fuel_prices(station_id, fuel_type, timestamp);

CREATE TABLE IF NOT EXISTS fahrer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS refuels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id INTEGER REFERENCES stations(id),
    fahrer_id INTEGER REFERENCES fahrer(id),
    datum TEXT NOT NULL,                    -- ISO-Datum, z.B. 2026-07-14
    odometer_km REAL NOT NULL,
    liter REAL NOT NULL,
    preis_pro_liter REAL NOT NULL,
    gesamtkosten REAL,
    notiz TEXT,
    bordcomputer_km REAL,                   -- vom Bordcomputer: gefahrene km seit letztem Tanken
    bordcomputer_verbrauch REAL,            -- vom Bordcomputer: Durchschnittsverbrauch L/100km
    foto_pfad TEXT                          -- Pfad zum hochgeladenen Beleg-/Bordcomputer-Foto
);

CREATE TABLE IF NOT EXISTS routen_vorlagen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    waypoints TEXT NOT NULL,       -- JSON [[lat,lng],...]
    route TEXT NOT NULL,           -- JSON dichte, straßenfolgende Punkte
    distanz_km REAL,
    erstellt_am INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titel TEXT,
    datum TEXT,                    -- ISO-Datetime, z.B. 2026-07-14T18:30
    start_name TEXT,
    ziel_name TEXT,
    distanz_km REAL,
    route_geojson TEXT NOT NULL,   -- JSON: {"waypoints": [...], "route": [...]}
    hoehenmeter_auf REAL,          -- für später: Elevation-API-Anbindung
    hoehenmeter_ab REAL,
    kommentar TEXT,
    begleitung TEXT,               -- z.B. "allein", "mit Partner/in"
    fahrtzweck TEXT,               -- z.B. "Arbeit / Pendeln", "Privat"
    ist_freigegeben INTEGER NOT NULL DEFAULT 0,  -- 0 = privat (nur Admin), 1 = öffentlich sichtbar
    erstellt_am INTEGER NOT NULL
);
