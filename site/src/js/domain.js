import { renderNav, renderFooter } from "./nav.js";
import { loadManifest, findDomain } from "./manifest-loader.js";
import { createMap, addBbox } from "./map.js";
import { fmtContributor, fmtDate } from "./format.js";

renderNav();
renderFooter();

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function meshRow(d, m) {
  const detail = `mesh.html?d=${encodeURIComponent(d.name)}&m=${encodeURIComponent(m.id)}`;
  const kindLabel = m.kind === "boundary" ? "Boundary" : "Mesh";
  const date = m.modified_date || m.uploaded_date;
  return `<tr>
    <td><a href="${detail}"><code>${esc(m.id)}</code></a></td>
    <td>${kindLabel}</td>
    <td>${esc(m.filename)}</td>
    <td>${esc(m.type || "")}</td>
    <td>${m.size_mb != null ? m.size_mb.toFixed(2) : "—"}</td>
    <td>${esc(m.license || "")}</td>
    <td>${esc(fmtDate(m.modified_date))}</td>
    <td>${esc(fmtContributor(m.contributor, date))}</td>
  </tr>`;
}

(async () => {
  const params = new URLSearchParams(location.search);
  const name = params.get("d");
  document.title = `${name || "Domain"} — ADMESH-Domains`;

  try {
    const manifest = await loadManifest();
    const d = findDomain(manifest, name);
    const root = document.getElementById("domain-content");
    if (!d) {
      root.innerHTML = `<p class="error">Domain "${esc(name)}" not found.</p>`;
      return;
    }
    root.innerHTML = `
      <h1>${esc(d.name)}</h1>
      <p class="muted">${esc(d.full_name || "")}</p>
      <p>
        <strong>Category:</strong> ${esc(d.category)} ·
        <strong>Region:</strong> ${esc(d.region || "—")} ·
        <strong>Applications:</strong> ${(d.applications || []).map(esc).join(", ") || "—"}
      </p>
      ${d.description ? `<p>${esc(d.description)}</p>` : ""}
      <h2>Meshes (${d.meshes.length})</h2>
      <table>
        <thead><tr><th>ID</th><th>Kind</th><th>File</th><th>Type</th><th>Size (MB)</th><th>License</th><th>Modified</th><th>Contributor</th></tr></thead>
        <tbody>${d.meshes.map((m) => meshRow(d, m)).join("")}</tbody>
      </table>
    `;

    const map = createMap("map");
    let any = false;
    for (const m of d.meshes) {
      if (m.geographic && m.bounding_box) {
        addBbox(map, m.bounding_box, { label: m.id, color: "#0b6cd1", fillOpacity: 0.15 });
        any = true;
      }
    }
    if (!any) {
      document.getElementById("map").outerHTML = `<p class="muted">No geographic bounding boxes for this domain.</p>`;
    } else {
      const lons = d.meshes.filter((m) => m.geographic).flatMap((m) => [m.bounding_box.min_lon, m.bounding_box.max_lon]);
      const lats = d.meshes.filter((m) => m.geographic).flatMap((m) => [m.bounding_box.min_lat, m.bounding_box.max_lat]);
      map.fitBounds([[Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]],
        { padding: [20, 20], maxZoom: 8 });
    }
  } catch (err) {
    document.getElementById("domain-content").innerHTML = `<p class="error">${esc(err.message)}</p>`;
  }
})();
