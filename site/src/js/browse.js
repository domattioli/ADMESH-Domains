import { renderNav, renderFooter } from "./nav.js";
import { loadManifest } from "./manifest-loader.js";

renderNav();
renderFooter();

function matchesQuery(d, lower) {
  if (!lower) return true;
  const haystack = [
    d.name, d.full_name, d.region, d.category, d.description,
    ...(d.applications || []),
    ...(d.meshes || []).flatMap((m) => [m.id, m.filename, m.contributor, m.license, m.description]),
  ].filter(Boolean).join(" ").toLowerCase();
  return haystack.includes(lower);
}

function renderCards(domains, q = "") {
  const el = document.getElementById("domain-cards");
  const count = document.getElementById("result-count");
  const lower = q.trim().toLowerCase();
  const matches = domains.filter((d) => matchesQuery(d, lower));
  count.textContent = `${matches.length} of ${domains.length} domains`;
  el.innerHTML = matches.map((d) => `
    <a class="card" href="domain.html?d=${encodeURIComponent(d.name)}">
      <h3>${d.name}</h3>
      <div class="meta">${d.full_name || ""}</div>
      <div class="meta">${d.region || d.category || ""} · ${(d.meshes || []).length} mesh${d.meshes.length === 1 ? "" : "es"}</div>
    </a>
  `).join("");
}

function renderTable(domains, q = "") {
  const tbody = document.querySelector("#mesh-table tbody");
  const count = document.getElementById("result-count");
  const lower = q.trim().toLowerCase();
  const rows = [];
  for (const d of domains) {
    if (!matchesQuery(d, lower)) continue;
    for (const m of d.meshes || []) {
      rows.push({ d, m });
    }
  }
  count.textContent = `${rows.length} mesh${rows.length === 1 ? "" : "es"} across ${new Set(rows.map((r) => r.d.name)).size} domain${rows.length === 1 ? "" : "s"}`;
  tbody.innerHTML = rows.map(({ d, m }) => `
    <tr>
      <td><a href="domain.html?d=${encodeURIComponent(d.name)}">${d.name}</a></td>
      <td><a href="mesh.html?d=${encodeURIComponent(d.name)}&m=${encodeURIComponent(m.id)}">${m.id}</a></td>
      <td>${m.type || ""}</td>
      <td>${m.node_count != null ? m.node_count.toLocaleString() : "—"}</td>
      <td>${m.size_mb != null ? m.size_mb.toFixed(2) : "—"}</td>
      <td>${m.license || ""}</td>
      <td><a href="${m.download_url}">${m.filename}</a></td>
    </tr>
  `).join("");
}

(async () => {
  try {
    const manifest = await loadManifest();
    let mode = "cards";

    const renderAll = (q) => (mode === "cards" ? renderCards(manifest.domains, q) : renderTable(manifest.domains, q));
    renderAll("");

    const q = document.getElementById("q");
    let t;
    q.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(() => renderAll(q.value), 100);
    });

    const cardsBtn = document.getElementById("view-cards");
    const tableBtn = document.getElementById("view-table");
    const cardsWrap = document.getElementById("domain-cards");
    const tableWrap = document.getElementById("mesh-table-wrap");
    function setMode(next) {
      mode = next;
      const isCards = next === "cards";
      cardsBtn.setAttribute("aria-pressed", String(isCards));
      tableBtn.setAttribute("aria-pressed", String(!isCards));
      cardsWrap.hidden = !isCards;
      tableWrap.hidden = isCards;
      renderAll(q.value);
    }
    cardsBtn.addEventListener("click", () => setMode("cards"));
    tableBtn.addEventListener("click", () => setMode("table"));
  } catch (err) {
    document.querySelector("main").insertAdjacentHTML("afterbegin",
      `<p class="error">Failed to load registry: ${err.message}</p>`);
  }
})();
