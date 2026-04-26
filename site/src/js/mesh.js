import { renderNav, renderFooter } from "./nav.js";
import { loadManifest, findDomain, findMesh } from "./manifest-loader.js";
import { createMap, addBbox, bboxToLatLngBounds } from "./map.js";

renderNav();
renderFooter();

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function row(label, value) {
  if (value === undefined || value === null || value === "") return "";
  return `<tr><th>${esc(label)}</th><td>${esc(value)}</td></tr>`;
}

(async () => {
  const params = new URLSearchParams(location.search);
  const dn = params.get("d"), mid = params.get("m");

  try {
    const manifest = await loadManifest();
    const d = findDomain(manifest, dn);
    const m = findMesh(d, mid);
    const root = document.getElementById("mesh-content");
    if (!d || !m) {
      root.innerHTML = `<p class="error">Mesh not found: ${esc(dn)}/${esc(mid)}</p>`;
      return;
    }
    document.title = `${d.name}/${m.id} — ADMESH-Domains`;
    document.getElementById("breadcrumb").innerHTML =
      `<a href="./">All domains</a> &rarr; <a href="domain.html?d=${encodeURIComponent(d.name)}">${esc(d.name)}</a> &rarr; <code>${esc(m.id)}</code>`;

    const bb = m.bounding_box;
    root.innerHTML = `
      <h1><code>${esc(d.name)}/${esc(m.id)}</code></h1>
      <p>${esc(m.description || "")}</p>
      <p>
        ${m.download_url ? `<a class="btn" href="${esc(m.download_url)}" download>Download ${esc(m.filename)}</a>` : ""}
      </p>
      <table>
        <tbody>
          ${row("Filename", m.filename)}
          ${row("Type", m.type)}
          ${row("Size (MB)", m.size_mb)}
          ${row("Nodes", m.node_count)}
          ${row("Element type", m.element_type)}
          ${row("Refinement", m.refinement_level)}
          ${row("License", m.license)}
          ${row("Contributor", m.contributor)}
          ${bb ? row("Bounding box", `(${bb.min_lon}, ${bb.min_lat}) – (${bb.max_lon}, ${bb.max_lat})`) : ""}
          ${row("Geographic?", m.geographic ? "yes" : "no (projected coords)")}
        </tbody>
      </table>
    `;

    if (m.geographic && bb) {
      const map = createMap("map");
      addBbox(map, bb, { label: m.id });
      map.fitBounds(bboxToLatLngBounds(bb), { padding: [40, 40], maxZoom: 9 });
    } else {
      document.getElementById("map").outerHTML =
        `<p class="muted">No geographic preview (mesh is in projected coordinates).</p>`;
    }
  } catch (err) {
    document.getElementById("mesh-content").innerHTML = `<p class="error">${esc(err.message)}</p>`;
  }
})();
