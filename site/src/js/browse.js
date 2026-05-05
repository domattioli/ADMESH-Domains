import { renderNav, renderFooter } from "./nav.js";
import { loadManifest } from "./manifest-loader.js";
import { fmtContributor, fmtDate } from "./format.js";

renderNav();
renderFooter();

function matchesQuery(d, lower) {
  if (!lower) return true;
  const haystack = [
    d.name, d.full_name, d.region, d.category, d.description,
    ...(d.applications || []),
    ...(d.meshes || []).flatMap((m) => [
      m.id, m.filename, m.contributor, m.license, m.description,
      m.kind, m.test_case ? "test_case" : "",
      m.uploaded_date, m.modified_date,
    ]),
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

function bboxSvg(m, thumbnailUrl) {
  if (thumbnailUrl) {
    return `<img src="${thumbnailUrl}" alt="${m.full_id}" class="thumb-img" onerror="this.outerHTML='${bboxSvgFallback(m).replace(/'/g, "\\'")}'"/>`;
  }
  return bboxSvgFallback(m);
}

function bboxSvgFallback(m) {
  if (!m.bounding_box) {
    return `<svg viewBox="0 0 100 70" class="thumb-svg" aria-hidden="true"><rect x="5" y="5" width="90" height="60" fill="none" stroke="currentColor" stroke-dasharray="4 3" opacity="0.4"/><text x="50" y="40" text-anchor="middle" font-size="10" fill="currentColor" opacity="0.5">no bbox</text></svg>`;
  }
  const bb = m.bounding_box;
  const w = Math.max(1e-9, bb.max_lon - bb.min_lon);
  const h = Math.max(1e-9, bb.max_lat - bb.min_lat);
  const aspect = w / h;
  const pad = 8;
  const vw = 100, vh = 70;
  let rw, rh;
  if (aspect >= (vw - 2 * pad) / (vh - 2 * pad)) {
    rw = vw - 2 * pad; rh = rw / aspect;
  } else {
    rh = vh - 2 * pad; rw = rh * aspect;
  }
  const rx = (vw - rw) / 2, ry = (vh - rh) / 2;
  return `<svg viewBox="0 0 ${vw} ${vh}" class="thumb-svg" aria-hidden="true">
    <rect x="${rx.toFixed(2)}" y="${ry.toFixed(2)}" width="${rw.toFixed(2)}" height="${rh.toFixed(2)}" fill="var(--accent)" fill-opacity="0.15" stroke="var(--accent)" stroke-width="1.5"/>
  </svg>`;
}

function renderThumbs(domains, q = "") {
  const el = document.getElementById("mesh-thumbs");
  const count = document.getElementById("result-count");
  const lower = q.trim().toLowerCase();
  const items = [];
  for (const d of domains) {
    if (!matchesQuery(d, lower)) continue;
    for (const m of d.meshes || []) items.push({ d, m });
  }
  count.textContent = `${items.length} mesh${items.length === 1 ? "" : "es"}`;
  el.innerHTML = items.map(({ d, m }) => {
    const thumbUrl = m.thumbnail_url || null;
    const thumbHtml = thumbUrl
      ? `<img src="${thumbUrl}" alt="${m.full_id}" class="thumb-img" onerror="this.outerHTML='${bboxSvgFallback(m).replace(/'/g, "\\'")}'"/>`
      : bboxSvgFallback(m);
    return `
    <a class="thumb-card" href="mesh.html?d=${encodeURIComponent(d.name)}&m=${encodeURIComponent(m.id)}">
      ${thumbHtml}
      <div class="thumb-title">${d.name}/${m.id}</div>
      <div class="meta">${m.kind === "boundary" ? "Boundary" : "Mesh"} · ${m.size_mb != null ? m.size_mb.toFixed(2) + " MB" : "—"}</div>
    </a>
  `;
  }).join("");
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
      <td>${m.kind === "boundary" ? "Boundary" : "Mesh"}</td>
      <td>${m.type || ""}</td>
      <td>${m.node_count != null ? m.node_count.toLocaleString() : "—"}</td>
      <td>${m.size_mb != null ? m.size_mb.toFixed(2) : "—"}</td>
      <td>${m.license || ""}</td>
      <td>${fmtDate(m.modified_date)}</td>
      <td>${fmtDate(m.uploaded_date)}</td>
      <td>${fmtContributor(m.contributor, m.modified_date || m.uploaded_date)}</td>
      <td><a href="${m.download_url}">${m.filename}</a></td>
    </tr>
  `).join("");
}

(async () => {
  try {
    const manifest = await loadManifest();
    let mode = "cards";
    const renderers = {
      cards: renderCards,
      thumbs: renderThumbs,
      table: renderTable,
    };
    const renderAll = (q) => renderers[mode](manifest.domains, q);
    renderAll("");

    const q = document.getElementById("q");
    let t;
    q.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(() => renderAll(q.value), 100);
    });

    const buttons = {
      cards: document.getElementById("view-cards"),
      thumbs: document.getElementById("view-thumbs"),
      table: document.getElementById("view-table"),
    };
    const wraps = {
      cards: document.getElementById("domain-cards"),
      thumbs: document.getElementById("mesh-thumbs"),
      table: document.getElementById("mesh-table-wrap"),
    };
    function setMode(next) {
      mode = next;
      for (const [k, btn] of Object.entries(buttons)) btn.setAttribute("aria-pressed", String(k === next));
      for (const [k, w] of Object.entries(wraps)) w.hidden = k !== next;
      renderAll(q.value);
    }
    for (const [k, btn] of Object.entries(buttons)) btn.addEventListener("click", () => setMode(k));
  } catch (err) {
    document.querySelector("main").insertAdjacentHTML("afterbegin",
      `<p class="error">Failed to load registry: ${err.message}</p>`);
  }
})();
