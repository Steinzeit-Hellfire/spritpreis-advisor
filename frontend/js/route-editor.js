const WAZE_ICON = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:-2px;">
  <path d="M12 3 L20 12 L12 21 L4 12 Z" fill="#33ccff"/>
  <path d="M12 7 L12 17 M7 12 L17 12" stroke="#0b1120" stroke-width="1.6" stroke-linecap="round"/>
</svg>`;

const API = "/api";
let istAdmin = false;

// --- Standort & ETA --------------------------------------------------------
// Hinweis: navigator.geolocation funktioniert nur in einem "sicheren Kontext"
// (HTTPS oder localhost). Auf http://<lan-ip>:port liefert der Browser hier
// grundsätzlich keinen Standort - das ist eine Browser-Sicherheitsregel, kein
// Bug. Der Code fällt in dem Fall einfach sauber zurück (kein ETA, kein Fehler).
let meinStandort = null;

function standortAnfordern() {
  return new Promise((resolve) => {
    if (!("geolocation" in navigator)) { resolve(null); return; }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => resolve(null),
      { timeout: 8000, maximumAge: 5 * 60 * 1000 }
    );
  });
}

async function etaAnzeigen(zielLat, zielLng, containerId) {
  if (!meinStandort || zielLat == null || zielLng == null) return;
  const el = document.getElementById(containerId);
  if (!el) return;
  try {
    const url = `https://routing.openstreetmap.de/routed-car/route/v1/driving/` +
      `${meinStandort.lng},${meinStandort.lat};${zielLng},${zielLat}?overview=false`;
    const res = await fetch(url);
    const data = await res.json();
    if (data.code !== "Ok") return;
    const minuten = Math.round(data.routes[0].duration / 60);
    const km = (data.routes[0].distance / 1000).toFixed(1);
    el.textContent = `≈ ${minuten} Min · ${km} km ab deinem Standort (Schätzung, ohne Live-Verkehr)`;
  } catch (e) {
    // ETA ist ein Nice-to-have, kein Fehler-Popup nötig
  }
}

// --- Karte -------------------------------------------------------------
const map = L.map("karte").setView([52.05, 8.85], 11);

const layerOSM = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap-Mitwirkende",
  maxZoom: 19,
});
const layerTopo = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
  attribution: "&copy; OpenStreetMap-Mitwirkende, SRTM | Karte: &copy; OpenTopoMap (CC-BY-SA)",
  maxZoom: 17,
});
const layerVoyager = L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
  attribution: "&copy; OpenStreetMap-Mitwirkende &copy; CARTO",
  maxZoom: 20,
});
layerOSM.addTo(map);
L.control.layers(
  { "OpenStreetMap": layerOSM, "OpenTopoMap": layerTopo, "CartoDB Voyager": layerVoyager },
  {},
  { position: "topright" }
).addTo(map);

// --- Routing: Wegpunkte werden über echte Straßen verbunden (OSRM) -------
let wegpunkte = [];      // Array von L.LatLng
let letzteRoute = null;  // { coordinates: [[lat,lng],...], distanzKm }

function eigenerPinMarker(i, waypoint) {
  const marker = L.marker(waypoint.latLng, { draggable: true });
  marker.on("contextmenu", () => {
    wegpunkte.splice(i, 1);
    routingControl.setWaypoints(wegpunkte);
  });
  return marker;
}

const routingControl = L.Routing.control({
  waypoints: [],
  router: L.Routing.osrmv1({ serviceUrl: "https://routing.openstreetmap.de/routed-car/route/v1" }),
  routeWhileDragging: true,
  draggableWaypoints: true,
  addWaypoints: true,
  fitSelectedRoutes: false,
  show: false,
  createMarker: eigenerPinMarker,
  lineOptions: { styles: [{ color: "#38bdf8", weight: 5, opacity: 0.9 }] },
}).addTo(map);

routingControl.on("routesfound", (ev) => {
  const route = ev.routes[0];
  letzteRoute = {
    coordinates: route.coordinates.map(c => [c.lat, c.lng]),
    distanzKm: route.summary.totalDistance / 1000,
  };
  distanzAnzeigen();
});

routingControl.on("routingerror", (ev) => {
  letzteRoute = null;
  const anzeige = document.getElementById("distanz-anzeige");
  anzeige.textContent = "Route konnte nicht berechnet werden (Routing-Dienst nicht erreichbar). Details in der Browser-Konsole (F12).";
  console.error("Routing-Fehler:", ev.error);
});

routingControl.on("waypointschanged", (ev) => {
  wegpunkte = ev.waypoints.filter(w => w.latLng).map(w => w.latLng);
  if (wegpunkte.length < 2) letzteRoute = null;
  distanzAnzeigen();
});

function distanzAnzeigen() {
  const anzeige = document.getElementById("distanz-anzeige");
  const n = wegpunkte.length;
  if (letzteRoute) {
    anzeige.textContent = `${n} Wegpunkte · ${letzteRoute.distanzKm.toFixed(1)} km über die Straße`;
  } else {
    anzeige.textContent = `${n} Wegpunkt(e) gesetzt – mind. 2 nötig, um eine Route zu berechnen.`;
  }
}

map.on("click", (ev) => {
  if (!istAdmin) return;
  wegpunkte = [...wegpunkte, ev.latlng];
  routingControl.setWaypoints(wegpunkte);
});

document.getElementById("btn-letzten-loeschen").addEventListener("click", () => {
  if (!wegpunkte.length) return;
  wegpunkte = wegpunkte.slice(0, -1);
  routingControl.setWaypoints(wegpunkte);
});

document.getElementById("btn-reset").addEventListener("click", () => {
  wegpunkte = [];
  routingControl.setWaypoints([]);
  letzteRoute = null;
  distanzAnzeigen();
});

document.getElementById("btn-suchen").addEventListener("click", async () => {
  const query = document.getElementById("ziel-suche").value.trim();
  if (!query) return;
  const res = await fetch(
    `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(query)}`,
    { headers: { "Accept-Language": "de" } }
  );
  const treffer = await res.json();
  if (treffer.length) {
    const { lat, lon } = treffer[0];
    map.setView([lat, lon], 14);
  }
});

document.getElementById("trip-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();

  if (wegpunkte.length < 2) {
    alert("Mindestens 2 Wegpunkte setzen, bevor die Strecke gespeichert wird.");
    return;
  }
  if (!letzteRoute) {
    alert("Route wird noch berechnet – kurz warten und nochmal versuchen.");
    return;
  }

  const payload = {
    titel: document.getElementById("t-titel").value || null,
    datum: document.getElementById("t-datum").value || null,
    kommentar: document.getElementById("t-kommentar").value || null,
    begleitung: document.getElementById("t-begleitung").value || null,
    fahrtzweck: document.getElementById("t-zweck").value || null,
    waypoints: wegpunkte.map(w => [w.lat, w.lng]),
    route: letzteRoute.coordinates,
    distanz_km: Math.round(letzteRoute.distanzKm * 10) / 10,
  };
  const res = await fetch(`${API}/trips`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (res.status === 401) {
    alert("Nur als Admin möglich - bitte einloggen.");
    return;
  }
  ev.target.reset();
  wegpunkte = [];
  routingControl.setWaypoints([]);
  letzteRoute = null;
  distanzAnzeigen();
  ladeTrips();
});

// --- Trips laden & anzeigen (Sichtbarkeit macht schon das Backend) -------

async function ladeTrips() {
  const container = document.getElementById("trips-liste");
  const res = await fetch(`${API}/trips`);
  const trips = await res.json();

  if (!trips.length) {
    container.innerHTML = `<p class="leer">${istAdmin ? "Noch keine Strecken gespeichert." : "Keine freigegebenen Strecken vorhanden."}</p>`;
    return;
  }

  const adminSpalten = istAdmin ? `<th>Privat/Öffentlich</th><th></th>` : "";

  container.innerHTML = `
    <table>
      <thead><tr>
        <th>Titel</th><th>Datum</th><th>Zweck</th><th>Begleitung</th><th class="zahl">Distanz</th>
        <th></th><th>Waze</th>${adminSpalten}
      </tr></thead>
      <tbody>
        ${trips.map(t => {
          const ziel = t.route && t.route.length ? t.route[t.route.length - 1] : null;
          const etaId = `eta-trip-${t.id}`;
          const wazeZelle = ziel
            ? `<a href="https://waze.com/ul?ll=${ziel[0]}%2C${ziel[1]}&navigate=yes" target="_blank" class="waze-link">${WAZE_ICON} Waze</a>
               <p class="hinweis" id="${etaId}" style="margin:2px 0 0;"></p>`
            : "";
          const adminZellen = istAdmin ? `
            <td>
              <span class="ampel ${t.ist_freigegeben ? 'guenstig' : 'unbekannt'}">${t.ist_freigegeben ? "öffentlich" : "privat"}</span>
            </td>
            <td><button class="secondary" data-freigabe-id="${t.id}" data-freigegeben="${t.ist_freigegeben ? 1 : 0}">${t.ist_freigegeben ? "Sperren" : "Freigeben"}</button></td>
          ` : "";
          return `
          <tr>
            <td>${t.titel ?? "–"}</td>
            <td>${t.datum ? t.datum.replace("T", " ") : "–"}</td>
            <td>${t.fahrtzweck ?? "–"}</td>
            <td>${t.begleitung ?? "–"}</td>
            <td class="zahl">${t.distanz_km ?? "–"} km</td>
            <td><button class="secondary" data-id="${t.id}">Auf Karte zeigen</button></td>
            <td>${wazeZelle}</td>
            ${adminZellen}
          </tr>
        `;
        }).join("")}
      </tbody>
    </table>
  `;

  container.querySelectorAll("button[data-id]").forEach(btn => {
    btn.addEventListener("click", () => tripAufKarteLaden(btn.dataset.id));
  });
  container.querySelectorAll("button[data-freigabe-id]").forEach(btn => {
    btn.addEventListener("click", () => freigabeUmschalten(btn.dataset.freigabeId, btn.dataset.freigegeben !== "1"));
  });

  // ETA nachladen, falls Standort verfügbar ist (nicht blockierend)
  if (meinStandort) {
    trips.forEach(t => {
      const ziel = t.route && t.route.length ? t.route[t.route.length - 1] : null;
      if (ziel) etaAnzeigen(ziel[0], ziel[1], `eta-trip-${t.id}`);
    });
  }
}

async function freigabeUmschalten(tripId, neuerWert) {
  const res = await fetch(`${API}/trips/${tripId}/freigabe`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ freigegeben: neuerWert }),
  });
  if (res.ok) ladeTrips();
}

async function tripAufKarteLaden(tripId) {
  const res = await fetch(`${API}/trips/${tripId}`);
  const trip = await res.json();

  wegpunkte = (trip.waypoints ?? trip.route).map(([lat, lng]) => L.latLng(lat, lng));
  routingControl.setWaypoints(wegpunkte);

  if (wegpunkte.length) {
    map.fitBounds(L.latLngBounds(wegpunkte));
  }
}

// --- Admin-Login ---------------------------------------------------------

function adminUIAktualisieren() {
  document.getElementById("trip-form-card").style.display = istAdmin ? "" : "none";
  document.getElementById("admin-hinweis").style.display = istAdmin ? "none" : "";
  document.getElementById("login-form-bereich").style.display = istAdmin ? "none" : "";
  document.getElementById("logout-bereich").style.display = istAdmin ? "" : "none";
}

async function pruefeAdminStatus() {
  try {
    const res = await fetch(`${API}/auth/status`);
    const data = await res.json();
    istAdmin = !!data.admin;
  } catch (e) {
    istAdmin = false;
  }
  adminUIAktualisieren();
}

document.getElementById("btn-passwort-toggle").addEventListener("click", () => {
  const feld = document.getElementById("login-passwort");
  const btn = document.getElementById("btn-passwort-toggle");
  const sichtbar = feld.type === "text";
  feld.type = sichtbar ? "password" : "text";
  btn.textContent = sichtbar ? "👁" : "🙈";
});

document.getElementById("login-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const passwort = document.getElementById("login-passwort").value;
  const fehlerEl = document.getElementById("login-fehler");
  fehlerEl.style.display = "none";

  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ passwort }),
  });

  if (!res.ok) {
    fehlerEl.textContent = "Login fehlgeschlagen - Passwort prüfen.";
    fehlerEl.style.display = "";
    return;
  }

  document.getElementById("login-passwort").value = "";
  istAdmin = true;
  adminUIAktualisieren();
  ladeTrips();
});

document.getElementById("btn-logout").addEventListener("click", async () => {
  await fetch(`${API}/auth/logout`, { method: "POST" });
  istAdmin = false;
  adminUIAktualisieren();
  ladeTrips();
});

// --- Start -----------------------------------------------------------

(async () => {
  await pruefeAdminStatus();
  distanzAnzeigen();
  await ladeTrips();
  meinStandort = await standortAnfordern();
  if (meinStandort) ladeTrips(); // ETA nachladen, sobald Standort da ist
})();
