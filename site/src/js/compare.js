import { renderNav, renderFooter } from "./nav.js";
import { loadManifest } from "./manifest-loader.js";

renderNav();
renderFooter();

const STRATEGIES = [
  { key: "triangle",  label: "Triangle",      typeMatch: "triangle",      nameHint: "tri" },
  { key: "quad",      label: "Quad-Dominant", typeMatch: "quadrilateral", nameHint: "quad" },
  { key: "mixed",     label: "Mixed",         typeMatch: "mixed",         nameHint: "mixed" },
];

function inferStrategy(mesh) {
  const et = (mesh.element_type || "").toLowerCase();
  const fn = (mesh.filename || "").toLowerCase();
  for (const s of STRATEGIES) {
    if (et === s.typeMatch) return s.key;
  }
  for (const s of STRATEGIES) {
    if (fn.includes(s.nameHint)) return s.key;
  }
  return null;
}

function groupVariants(domain) {
  const groups = {};
  for (const mesh of domain.meshes || []) {
    const strategy = inferStrategy(mesh);
    if (!strategy || groups[strategy]) continue;
    groups[strategy] = mesh;
  }
  return STRATEGIES
    .filter(s => groups[s.key])
    .map(s => ({ strategy: s.key, label: s.label, mesh: groups[s.key] }));
}

function bboxSvg(mesh) {
  const bb = mesh.bounding_box;
  if (!bb) {
    return `<svg viewBox="0 0 100 70" class="thumb-svg" aria-hidden="true">
      <rect x="5" y="5" width="90" height="60" fill="none" stroke="currentColor" stroke-dasharray="4 3" opacity="0.4"/>
      <text x="50" y="40" text-anchor="middle" font-size="10" fill="currentColor" opacity="0.5">no bbox</text>
    </svg>`;
  }
  const w = Math.max(1e-9, bb.max_lon - bb.min_lon);
  const h = Math.max(1e-9, bb.max_lat - bb.min_lat);
  const aspect = w / h;
  const pad = 8, vw = 100, vh = 70;
  let rw, rh;
  if (aspect >= (vw - 2 * pad) / (vh - 2 * pad)) {
    rw = vw - 2 * pad; rh = rw / aspect;
  } else {
    rh = vh - 2 * pad; rw = rh * aspect;
  }
  const rx = (vw - rw) / 2, ry = (vh - rh) / 2;
  return `<svg viewBox="0 0 ${vw} ${vh}" class="thumb-svg" aria-hidden="true">
    <rect x="${rx.toFixed(2)}" y="${ry.toFixed(2)}" width="${rw.toFixed(2)}" height="${rh.toFixed(2)}"
      fill="var(--accent)" fill-opacity="0.15" stroke="var(--accent)" stroke-width="1.5"/>
  </svg>`;
}

function fmt(val, unit = "") {
  if (val == null || val === 0) return "—";
  return val.toLocaleString() + (unit ? " " + unit : "");
}

function renderPanels(domain) {
  const panelEl = document.getElementById("compare-panels");
  const bannerEl = document.getElementById("compare-banner");
  const variants = groupVariants(domain);

  if (!variants.length) {
    panelEl.innerHTML = `<p class="compare-empty">No comparable mesh variants found for <strong>${domain.full_name || domain.name}</strong>. Variants are detected by <code>element_type</code> field or filename keywords (tri/quad/mixed).</p>`;
    bannerEl.innerHTML = "";
    return;
  }

  const panels = variants.map(({ label, mesh }) => `
    <div class="compare-panel">
      <h2 class="strategy-label">${label}</h2>
      <div class="panel-svg">${bboxSvg(mesh)}</div>
      <div class="panel-metrics">
        <span><span>Element type</span><strong>${mesh.element_type || "—"}</strong></span>
        <span><span>Elements</span><strong>${fmt(mesh.element_count)}</strong></span>
        <span><span>Nodes</span><strong>${fmt(mesh.node_count)}</strong></span>
        <span><span>File size</span><strong>${mesh.size_mb > 0 ? mesh.size_mb.toFixed(2) + " MB" : "—"}</strong></span>
        <span><span>Contributor</span><strong>${mesh.contributor || "—"}</strong></span>
      </div>
    </div>
  `).join("");

  const missing = STRATEGIES.filter(s => !variants.find(v => v.strategy === s.key));
  const missingNote = missing.length
    ? `<p class="muted" style="margin:0.5rem 0 0;font-size:0.85rem;">Not in registry: ${missing.map(s => s.label).join(", ")}.</p>`
    : "";

  panelEl.innerHTML = `<div class="compare-grid">${panels}</div>${missingNote}`;

  bannerEl.innerHTML = recommend(variants);
}

function recommend(variants) {
  const withCount = variants.filter(v => v.mesh.element_count && v.mesh.element_count > 0);
  if (withCount.length > 1) {
    const best = withCount.reduce((a, b) => a.mesh.element_count <= b.mesh.element_count ? a : b);
    return `<div class="compare-banner">⭐ <strong>${best.label}</strong> has the fewest elements (${best.mesh.element_count.toLocaleString()}) — best for computational efficiency.</div>`;
  }
  const withSize = variants.filter(v => v.mesh.size_mb > 0);
  if (withSize.length > 1) {
    const best = withSize.reduce((a, b) => a.mesh.size_mb <= b.mesh.size_mb ? a : b);
    return `<div class="compare-banner">⭐ <strong>${best.label}</strong> is the smallest file (${best.mesh.size_mb.toFixed(2)} MB).</div>`;
  }
  return "";
}

async function init() {
  const selectEl = document.getElementById("domain-select");
  const compareBtn = document.getElementById("compare-btn");
  const panelEl = document.getElementById("compare-panels");

  panelEl.innerHTML = `<p class="muted">Loading registry…</p>`;
  let manifest;
  try {
    manifest = await loadManifest();
  } catch (e) {
    panelEl.innerHTML = `<p class="error">Failed to load registry: ${e.message}</p>`;
    return;
  }

  const domains = manifest.domains || [];
  selectEl.innerHTML = domains.map(d =>
    `<option value="${d.name}">${d.full_name || d.name}</option>`
  ).join("");
  panelEl.innerHTML = `<p class="muted">Select a domain and click Compare.</p>`;

  compareBtn.addEventListener("click", () => {
    const selected = domains.find(d => d.name === selectEl.value);
    if (selected) renderPanels(selected);
  });
}

init();
