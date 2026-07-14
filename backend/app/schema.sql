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

CREATE TABLE IF NOT EXISTS refuels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id INTEGER REFERENCES stations(id),
    datum TEXT NOT NULL,           -- ISO-Datum, z.B. 2026-07-14
    odometer_km REAL NOT NULL,
    liter REAL NOT NULL,
    preis_pro_liter REAL NOT NULL,
    gesamtkosten REAL,
    notiz TEXT
);

CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titel TEXT,
    datum TEXT,
    start_name TEXT,
    ziel_name TEXT,
    distanz_km REAL,
    route_geojson TEXT NOT NULL,   -- JSON-Liste von [lat, lng]-Punkten (per Hand/Pins gesetzt)
    hoehenmeter_auf REAL,          -- für später: Elevation-API-Anbindung
    hoehenmeter_ab REAL,
    erstellt_am INTEGER NOT NULL
);
