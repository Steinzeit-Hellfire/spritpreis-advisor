const API = "/api";

// Karte zentriert auf Lippe/Dörentrup-Region
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
// Eigene Wegpunkt-Liste im Code führen (statt inkrementell auf der internen
// Liste des Routing-Controls herumzusplicen - das war der Bug) und bei jeder
// Änderung komplett neu an setWaypoints() übergeben. Robuster und deutlich
// leichter nachzuvollziehen.

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
  addWaypoints: true,       // Ziehen der Linie selbst fügt einen Zwischenpunkt ein
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

// Hält unsere eigene Wegpunkt-Liste synchron, auch wenn ein Pin gezogen oder
// über das Ziehen der Linie ein neuer Zwischenpunkt eingefügt wurde.
routingControl.on("waypointschanged", (ev) => {
  wegpunkte = ev.waypoints.filter(w => w.latLng).map(w => w.latLng);
  if (wegpunkte.length < 2) {
    letzteRoute = null;
  }
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

// Klick auf die Karte hängt einen neuen Wegpunkt ans Ende an
map.on("click", (ev) => {
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

// Adresssuche über Nominatim (OpenStreetMap) - zentriert die Karte auf den Fundort,
// fügt aber selbst keinen Wegpunkt hinzu (das macht der Klick auf die Karte).
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
  await fetch(`${API}/trips`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  ev.target.reset();
  wegpunkte = [];
  routingControl.setWaypoints([]);
  letzteRoute = null;
  distanzAnzeigen();
  ladeTrips();
});

async function ladeTrips() {
  const container = document.getElementById("trips-liste");
  const res = await fetch(`${API}/trips`);
  const trips = await res.json();

  if (!trips.length) {
    container.innerHTML = `<p class="leer">Noch keine Strecken gespeichert.</p>`;
    return;
  }

  container.innerHTML = `
    <table>
      <thead><tr><th>Titel</th><th>Datum</th><th>Zweck</th><th>Begleitung</th><th class="zahl">Distanz</th><th></th><th></th></tr></thead>
      <tbody>
        ${trips.map(t => {
          const ziel = t.route && t.route.length ? t.route[t.route.length - 1] : null;
          return `
          <tr>
            <td>${t.titel ?? "–"}</td>
            <td>${t.datum ? t.datum.replace("T", " ") : "–"}</td>
            <td>${t.fahrtzweck ?? "–"}</td>
            <td>${t.begleitung ?? "–"}</td>
            <td class="zahl">${t.distanz_km ?? "–"} km</td>
            <td><button class="secondary" data-id="${t.id}">Auf Karte zeigen</button></td>
            <td>${ziel ? `<a href="https://waze.com/ul?ll=${ziel[0]}%2C${ziel[1]}&navigate=yes" target="_blank" class="waze-link">🧭 Waze</a>` : ""}</td>
          </tr>
        `;
        }).join("")}
      </tbody>
    </table>
  `;

  container.querySelectorAll("button[data-id]").forEach(btn => {
    btn.addEventListener("click", () => tripAufKarteLaden(btn.dataset.id));
  });
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

distanzAnzeigen();
ladeTrips();
