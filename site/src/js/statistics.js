import { renderNav, renderFooter } from "./nav.js";
import { loadManifest } from "./manifest-loader.js";

renderNav();
renderFooter();

const fmt = (n) => (n == null ? "—" : Number(n).toLocaleString());

function flattenMeshes(manifest) {
  return manifest.domains.flatMap((d) =>
    (d.meshes || []).map((m) => ({ ...m, _domain: d.name, _applications: d.applications || [] }))
  );
}

// Element density (elements/km²) using equirectangular bbox area.
// Returns null for non-geographic, antimeridian-wrapping, or missing-element-count meshes.
function computeDensity(m) {
  if (m.element_count == null) return null;
  if (!m.geographic) return null;
  const bb = m.bounding_box;
  if (!bb || bb.min_lon > bb.max_lon) return null;
  const meanLat = (bb.min_lat + bb.max_lat) / 2;
  const widthKm = (bb.max_lon - bb.min_lon) * 111.0 * Math.cos(meanLat * Math.PI / 180);
  const heightKm = (bb.max_lat - bb.min_lat) * 111.0;
  const area = widthKm * heightKm;
  return area > 0 ? m.element_count / area : null;
}

function topN(rows, key, n = 5) {
  return rows.filter((r) => r[key] != null).sort((a, b) => b[key] - a[key]).slice(0, n);
}

function renderTopTable(elId, rows, key, fmtVal) {
  const el = document.getElementById(elId);
  if (!rows.length) {
    el.innerHTML = '<p class="muted">No data.</p>';
    return;
  }
  el.innerHTML = `
    <table>
      <thead><tr><th>#</th><th>Mesh</th><th>${key}</th></tr></thead>
      <tbody>${rows.map((m, i) => `
        <tr>
          <td>${i + 1}</td>
          <td><a href="mesh.html?d=${encodeURIComponent(m._domain)}&m=${encodeURIComponent(m.id)}">${m._domain}/${m.id}</a></td>
          <td>${fmtVal(m)}</td>
        </tr>`).join("")}
      </tbody>
    </table>
  `;
}

function tally(rows, getter) {
  const counts = new Map();
  for (const r of rows) {
    const vals = getter(r);
    for (const v of (Array.isArray(vals) ? vals : [vals])) {
      if (!v) continue;
      counts.set(v, (counts.get(v) || 0) + 1);
    }
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

function renderBarChart(elId, entries, label) {
  const el = document.getElementById(elId);
  if (!entries.length) {
    el.innerHTML = '<p class="muted">No data.</p>';
    return;
  }
  if (typeof uPlot === "undefined") {
    el.innerHTML = `<ul class="tight">${entries.map(([k, v]) => `<li>${k} <span class="muted">(${v})</span></li>`).join("")}</ul>`;
    return;
  }
  // uPlot doesn't ship a built-in bar plugin out of the box; render a horizontal HTML bar chart.
  const max = Math.max(...entries.map(([, v]) => v));
  el.innerHTML = `
    <div class="bars">
      ${entries.map(([k, v]) => `
        <div class="bar-row" title="${k}: ${v}">
          <div class="bar-label">${k}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${(v / max * 100).toFixed(1)}%"></div></div>
          <div class="bar-value">${v}</div>
        </div>`).join("")}
    </div>
  `;
}

function renderContributors(elId, entries) {
  const el = document.getElementById(elId);
  if (!entries.length) {
    el.innerHTML = '<p class="muted">No contributors recorded yet.</p>';
    return;
  }
  el.innerHTML = `
    <table>
      <thead><tr><th>Contributor</th><th>Meshes</th></tr></thead>
      <tbody>${entries.map(([name, n]) => `<tr><td>${name}</td><td>${n}</td></tr>`).join("")}</tbody>
    </table>
  `;
}

(async () => {
  try {
    const manifest = await loadManifest();
    const rows = flattenMeshes(manifest);

    document.getElementById("t-domains").textContent = fmt(manifest.totals.domains);
    document.getElementById("t-meshes").textContent = fmt(manifest.totals.meshes);
    document.getElementById("t-bytes").textContent = fmt(manifest.totals.size_mb);
    document.getElementById("t-nodes").textContent = fmt(rows.reduce((s, m) => s + (m.node_count || 0), 0));
    const contribs = tally(rows, (r) => r.contributor);
    document.getElementById("t-contribs").textContent = fmt(contribs.length);

    renderTopTable("top-nodes", topN(rows, "node_count"), "node_count", (m) => fmt(m.node_count));
    renderTopTable("top-elements", topN(rows, "element_count"), "element_count", (m) => fmt(m.element_count));
    renderTopTable("top-size", topN(rows, "size_mb"), "size_mb", (m) => `${m.size_mb.toFixed(2)} MB`);

    // Element density (elements/km²) — derived proxy for mesh refinement.
    for (const r of rows) r._density = computeDensity(r);
    renderTopTable(
      "top-density",
      topN(rows, "_density"),
      "elements/km²",
      (m) => `${m._density >= 1000 ? Math.round(m._density).toLocaleString() : m._density.toFixed(1)} elem/km²`,
    );

    renderBarChart("refinement-chart", tally(rows, (r) => r.refinement_level || "unspecified"));
    renderBarChart("license-chart", tally(rows, (r) => r.license || "unknown"));
    renderBarChart("application-chart", tally(rows, (r) => r._applications.length ? r._applications : ["(none)"]));

    renderContributors("contributors", contribs);
  } catch (err) {
    document.querySelector("main").insertAdjacentHTML("afterbegin",
      `<p class="error">Failed to load registry: ${err.message}</p>`);
  }
})();
