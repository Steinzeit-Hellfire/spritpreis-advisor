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

let markers = [];    // Leaflet-Marker in Reihenfolge der Pins
let polyline = null;

function pinsAlsRoute() {
  return markers.map(m => {
    const ll = m.getLatLng();
    return [ll.lat, ll.lng];
  });
}

function polylineNeuZeichnen() {
  const punkte = pinsAlsRoute();
  if (polyline) map.removeLayer(polyline);
  if (punkte.length >= 2) {
    polyline = L.polyline(punkte, { color: "#38bdf8", weight: 4 }).addTo(map);
  }
  distanzAnzeigen(punkte);
}

function distanzAnzeigen(punkte) {
  const anzeige = document.getElementById("distanz-anzeige");
  if (punkte.length < 2) {
    anzeige.textContent = `${punkte.length} Pin(s) gesetzt.`;
    return;
  }
  let gesamt = 0;
  for (let i = 0; i < punkte.length - 1; i++) {
    gesamt += haversineKm(punkte[i], punkte[i + 1]);
  }
  anzeige.textContent = `${punkte.length} Pins · ca. ${gesamt.toFixed(1)} km (Luftlinie zwischen den Pins)`;
}

function haversineKm(p1, p2) {
  const R = 6371;
  const dLat = (p2[0] - p1[0]) * Math.PI / 180;
  const dLng = (p2[1] - p1[1]) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(p1[0] * Math.PI / 180) * Math.cos(p2[0] * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function pinHinzufuegen(latlng) {
  const marker = L.marker(latlng, { draggable: true }).addTo(map);
  marker.on("drag", polylineNeuZeichnen);
  marker.on("contextmenu", () => {
    map.removeLayer(marker);
    markers = markers.filter(m => m !== marker);
    polylineNeuZeichnen();
  });
  markers.push(marker);
  polylineNeuZeichnen();
}

map.on("click", (ev) => pinHinzufuegen(ev.latlng));

document.getElementById("btn-letzten-loeschen").addEventListener("click", () => {
  const letzter = markers.pop();
  if (letzter) map.removeLayer(letzter);
  polylineNeuZeichnen();
});

document.getElementById("btn-reset").addEventListener("click", () => {
  markers.forEach(m => map.removeLayer(m));
  markers = [];
  polylineNeuZeichnen();
});

// Adresssuche über Nominatim (OpenStreetMap) - setzt die Karte auf den Fundort,
// fügt aber selbst keinen Pin hinzu (das macht der Klick auf die Karte).
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
  const route = pinsAlsRoute();
  if (route.length < 2) {
    alert("Mindestens 2 Pins setzen, bevor die Strecke gespeichert wird.");
    return;
  }
  const payload = {
    titel: document.getElementById("t-titel").value || null,
    datum: document.getElementById("t-datum").value || null,
    route,
  };
  await fetch(`${API}/trips`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  ev.target.reset();
  markers.forEach(m => map.removeLayer(m));
  markers = [];
  polylineNeuZeichnen();
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
      <thead><tr><th>Titel</th><th>Datum</th><th class="zahl">Distanz</th><th></th></tr></thead>
      <tbody>
        ${trips.map(t => `
          <tr>
            <td>${t.titel ?? "–"}</td>
            <td>${t.datum ?? "–"}</td>
            <td class="zahl">${t.distanz_km ?? "–"} km</td>
            <td><button class="secondary" data-id="${t.id}">Auf Karte zeigen</button></td>
          </tr>
        `).join("")}
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

  markers.forEach(m => map.removeLayer(m));
  markers = [];
  trip.route.forEach(([lat, lng]) => pinHinzufuegen(L.latLng(lat, lng)));

  if (markers.length) {
    map.fitBounds(L.latLngBounds(trip.route));
  }
}

ladeTrips();
