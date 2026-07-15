const API = "/api";
let istAdmin = false;

async function pruefeAdminStatus() {
  try {
    const res = await fetch(`${API}/auth/status`);
    const data = await res.json();
    istAdmin = !!data.admin;
  } catch (e) {
    istAdmin = false;
  }
  document.getElementById("refuel-form-card").style.display = istAdmin ? "" : "none";
  document.getElementById("refuel-table-card").style.display = istAdmin ? "" : "none";
  document.getElementById("refuel-admin-hinweis").style.display = istAdmin ? "none" : "";
}

function ampelKlasse(status) {
  if (status.includes("günstig")) return "guenstig";
  if (status.includes("teurer")) return "teuer";
  if (status.includes("üblichen")) return "ueblich";
  return "unbekannt";
}

const WAZE_ICON = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align:-2px;">
  <path d="M12 3 L20 12 L12 21 L4 12 Z" fill="#33ccff"/>
  <path d="M12 7 L12 17 M7 12 L17 12" stroke="#0b1120" stroke-width="1.6" stroke-linecap="round"/>
</svg>`;

function wazeLink(lat, lng, containerId) {
  if (lat == null || lng == null) return "";
  return `<a href="https://waze.com/ul?ll=${lat}%2C${lng}&navigate=yes" target="_blank" class="waze-link">${WAZE_ICON} In Waze navigieren</a>
          <p class="hinweis" id="${containerId}" style="margin:4px 0 0;"></p>`;
}

// Hinweis: navigator.geolocation braucht einen "sicheren Kontext" (HTTPS oder
// localhost). Über http://<lan-ip>:port liefert der Browser hier grundsätzlich
// keinen Standort - Browser-Sicherheitsregel, kein Bug. Fällt dann sauber
// zurück auf "kein ETA", ohne Fehlermeldung.
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

async function ladePreisvergleich() {
  const container = document.getElementById("stationen-liste");
  try {
    const res = await fetch(`${API}/prices/comparison`);
    const data = await res.json();

    if (!data.stationen.length) {
      container.innerHTML = `<p class="leer">Noch keine Favoriten-Stationen hinterlegt. Siehe README, um Stationen anzulegen.</p>`;
      return;
    }

    container.innerHTML = data.stationen.map(s => {
      const titel = (s.marke && !s.name.includes(s.marke)) ? `${s.marke} – ${s.name}` : s.name;
      return `
      <div class="glass-card station-card">
        <div class="info">
          <h3>${titel}</h3>
          <p>${s.adresse ?? ""}</p>
          <span class="ampel ${ampelKlasse(s.status)}">${s.status}</span>
          ${s.basis ? `<p class="hinweis" style="margin-top:6px;">${s.basis}</p>` : ""}
          ${s.lat != null ? `<p style="margin-top:8px;">${wazeLink(s.lat, s.lng, `eta-station-${s.station_id}`)}</p>` : ""}
        </div>
        <div class="preis">${s.aktueller_preis != null ? s.aktueller_preis.toFixed(3) + " €" : "–"}</div>
      </div>
    `;
    }).join("");

    if (meinStandort) {
      data.stationen.forEach(s => {
        if (s.lat != null) etaAnzeigen(s.lat, s.lng, `eta-station-${s.station_id}`);
      });
    }
  } catch (e) {
    container.innerHTML = `<p class="leer">Preise konnten nicht geladen werden. Läuft der Poller? Ist der API-Key gesetzt?</p>`;
  }
}

async function ladeStationenDropdown() {
  const select = document.getElementById("f-station");
  const res = await fetch(`${API}/stations`);
  const stationen = await res.json();
  select.innerHTML = stationen.map(s => {
    const label = (s.marke && !s.name.includes(s.marke)) ? `${s.marke} ${s.name}` : s.name;
    return `<option value="${s.id}">${label}</option>`;
  }).join("");
}

async function ladeFahrerDropdown() {
  if (!istAdmin) return;
  const select = document.getElementById("f-fahrer");
  const res = await fetch(`${API}/fahrer`);
  if (!res.ok) return;
  const fahrerListe = await res.json();
  select.innerHTML = `<option value="">– kein Fahrer angegeben –</option>` +
    fahrerListe.map(f => `<option value="${f.id}">${f.name}</option>`).join("");
}

document.getElementById("fahrer-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const nameFeld = document.getElementById("neuer-fahrer-name");
  await fetch(`${API}/fahrer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: nameFeld.value }),
  });
  nameFeld.value = "";
  ladeFahrerDropdown();
});

async function ladeTankvorgaenge() {
  if (!istAdmin) return;
  const tbody = document.querySelector("#refuel-table tbody");
  const res = await fetch(`${API}/refuels`);
  if (res.status === 401) {
    tbody.innerHTML = `<tr><td colspan="12" class="leer">Nur für Admin sichtbar.</td></tr>`;
    return;
  }
  const eintraege = await res.json();

  if (!eintraege.length) {
    tbody.innerHTML = `<tr><td colspan="12" class="leer">Noch keine Tankvorgänge eingetragen.</td></tr>`;
    return;
  }

  tbody.innerHTML = eintraege.map(e => `
    <tr>
      <td>${e.datum}</td>
      <td>${e.fahrer_name ?? "–"}</td>
      <td>${e.station_name ?? "–"}</td>
      <td class="zahl">${e.odometer_km}</td>
      <td class="zahl">${e.liter.toFixed(2)}</td>
      <td class="zahl">${e.preis_pro_liter.toFixed(3)}</td>
      <td class="zahl">${e.gesamtkosten.toFixed(2)} €</td>
      <td class="zahl">${e.verbrauch_l_100km ?? "–"}</td>
      <td class="zahl">${e.kosten_pro_km ?? "–"}</td>
      <td class="zahl">${e.bordcomputer_km ?? "–"}</td>
      <td class="zahl">${e.bordcomputer_verbrauch ?? "–"}</td>
      <td>${e.foto_pfad ? `<a href="${e.foto_pfad}" target="_blank">📷</a>` : "–"}</td>
    </tr>
  `).join("");
}

document.getElementById("refuel-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const payload = {
    station_id: Number(document.getElementById("f-station").value) || null,
    fahrer_id: document.getElementById("f-fahrer").value ? Number(document.getElementById("f-fahrer").value) : null,
    datum: document.getElementById("f-datum").value,
    odometer_km: Number(document.getElementById("f-km").value),
    liter: Number(document.getElementById("f-liter").value),
    preis_pro_liter: Number(document.getElementById("f-preis").value),
    bordcomputer_km: document.getElementById("f-bc-km").value ? Number(document.getElementById("f-bc-km").value) : null,
    bordcomputer_verbrauch: document.getElementById("f-bc-verbrauch").value ? Number(document.getElementById("f-bc-verbrauch").value) : null,
  };
  const res = await fetch(`${API}/refuels`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (res.status === 401) {
    alert("Nur als Admin möglich - bitte auf der Strecken-Seite einloggen.");
    return;
  }
  const { id } = await res.json();

  const fotoInput = document.getElementById("f-foto");
  if (fotoInput.files.length) {
    const formData = new FormData();
    formData.append("datei", fotoInput.files[0]);
    await fetch(`${API}/refuels/${id}/foto`, { method: "POST", body: formData });
  }

  ev.target.reset();
  ladeTankvorgaenge();
});

ladePreisvergleich();
ladeStationenDropdown();
setInterval(ladePreisvergleich, 60_000); // Ansicht minütlich auffrischen

(async () => {
  await pruefeAdminStatus();
  ladeFahrerDropdown();
  ladeTankvorgaenge();
  meinStandort = await standortAnfordern();
  if (meinStandort) ladePreisvergleich(); // ETA nachladen, sobald Standort da ist
})();
