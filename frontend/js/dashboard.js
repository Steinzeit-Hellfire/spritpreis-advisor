const API = "/api";

function ampelKlasse(status) {
  if (status.includes("günstig")) return "guenstig";
  if (status.includes("teurer")) return "teuer";
  if (status.includes("üblichen")) return "ueblich";
  return "unbekannt";
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

    container.innerHTML = data.stationen.map(s => `
      <div class="glass-card station-card">
        <div class="info">
          <h3>${s.marke ? s.marke + " – " : ""}${s.name}</h3>
          <p>${s.adresse ?? ""}</p>
          <span class="ampel ${ampelKlasse(s.status)}">${s.status}</span>
          ${s.basis ? `<p class="hinweis" style="margin-top:6px;">${s.basis}</p>` : ""}
        </div>
        <div class="preis">${s.aktueller_preis != null ? s.aktueller_preis.toFixed(3) + " €" : "–"}</div>
      </div>
    `).join("");
  } catch (e) {
    container.innerHTML = `<p class="leer">Preise konnten nicht geladen werden. Läuft der Poller? Ist der API-Key gesetzt?</p>`;
  }
}

async function ladeStationenDropdown() {
  const select = document.getElementById("f-station");
  const res = await fetch(`${API}/stations`);
  const stationen = await res.json();
  select.innerHTML = stationen.map(s => `<option value="${s.id}">${s.marke ?? ""} ${s.name}</option>`).join("");
}

async function ladeTankvorgaenge() {
  const tbody = document.querySelector("#refuel-table tbody");
  const res = await fetch(`${API}/refuels`);
  const eintraege = await res.json();

  if (!eintraege.length) {
    tbody.innerHTML = `<tr><td colspan="11" class="leer">Noch keine Tankvorgänge eingetragen.</td></tr>`;
    return;
  }

  tbody.innerHTML = eintraege.map(e => `
    <tr>
      <td>${e.datum}</td>
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
ladeTankvorgaenge();
setInterval(ladePreisvergleich, 60_000); // Ansicht minütlich auffrischen
