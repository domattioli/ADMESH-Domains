import { renderNav, renderFooter } from "./nav.js";
import { loadManifest, findDomain, findMesh } from "./manifest-loader.js";
import { createMap, addBbox, bboxToLatLngBounds } from "./map.js";
import { parseFort14Full } from "./mesh-parser.js";
import { renderMesh } from "./geometry-render.js";
import { fmtContributor, fmtDate } from "./format.js";

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
    const kindLabel = m.kind === "boundary" ? "Boundary" : "Mesh";
    document.title = `${d.name}/${m.id} — ${kindLabel} — ADMESH-Domains`;
    document.getElementById("breadcrumb").innerHTML =
      `<a href="./">All domains</a> &rarr; <a href="domain.html?d=${encodeURIComponent(d.name)}">${esc(d.name)}</a> &rarr; <code>${esc(m.id)}</code>`;

    const bb = m.bounding_box;
    root.innerHTML = `
      <h1><code>${esc(d.name)}/${esc(m.id)}</code></h1>
      <p>${esc(m.description || "")}</p>
      <p>
        ${m.download_url ? `<button type="button" class="btn" id="download-btn">Download ${esc(m.filename)}</button>` : ""}
      </p>
      <table>
        <tbody>
          ${row("Filename", m.filename)}
          ${row("Kind", m.kind === "boundary" ? "Boundary outline (no connectivity)" : "Mesh (nodes + element connectivity)")}
          ${row("Type", m.type)}
          ${row("Size (MB)", m.size_mb)}
          ${row("Nodes", m.node_count)}
          ${row("Element type", m.element_type)}
          ${row("Refinement", m.refinement_level)}
          ${row("License", m.license)}
          ${row("Contributor", fmtContributor(m.contributor, m.modified_date || m.uploaded_date))}
          ${row("Modified", fmtDate(m.modified_date))}
          ${row("Uploaded", fmtDate(m.uploaded_date))}
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

    const dlBtn = document.getElementById("download-btn");
    if (dlBtn && m.download_url) {
      dlBtn.addEventListener("click", async () => {
        const orig = dlBtn.textContent;
        dlBtn.disabled = true;
        dlBtn.textContent = "Downloading…";
        try {
          const resp = await fetch(m.download_url);
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          const blob = await resp.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = m.filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
          dlBtn.textContent = "Downloaded ✓";
          setTimeout(() => { dlBtn.textContent = orig; dlBtn.disabled = false; }, 2000);
        } catch (e) {
          dlBtn.textContent = `Failed: ${e.message}`;
          setTimeout(() => { dlBtn.textContent = orig; dlBtn.disabled = false; }, 3000);
        }
      });
    }

    const btn = document.getElementById("render-btn");
    const note = document.getElementById("geometry-note");
    const canvas = document.getElementById("geometry-canvas");
    const isFort14 = /\.(14|grd|fort)$/i.test(m.filename);
    if (m.kind === "boundary") {
      note.textContent = "This is a boundary outline (no element connectivity); geometry rendering is for full meshes only.";
      btn.disabled = true;
    } else if (!isFort14) {
      note.textContent = `Geometry rendering supports fort.14 / .grd files. ${esc(m.filename)} cannot be rendered yet.`;
      btn.disabled = true;
    } else if (!m.download_url) {
      note.textContent = "No download URL available; cannot render geometry.";
      btn.disabled = true;
    } else {
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        const orig = btn.textContent;
        const sizeStr = m.size_mb != null ? ` (${m.size_mb.toFixed(1)} MB)` : "";
        btn.textContent = `Downloading${sizeStr}…`;
        try {
          const resp = await fetch(m.download_url);
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          // Stream + report progress when content-length is known.
          const total = Number(resp.headers.get("content-length") || 0);
          let loaded = 0;
          const reader = resp.body && resp.body.getReader ? resp.body.getReader() : null;
          let text;
          if (reader && total) {
            const chunks = [];
            const decoder = new TextDecoder();
            let buf = "";
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              chunks.push(value);
              loaded += value.length;
              buf += decoder.decode(value, { stream: true });
              btn.textContent = `Downloading… ${Math.round((loaded / total) * 100)}%`;
            }
            text = buf + decoder.decode();
          } else {
            text = await resp.text();
          }
          btn.textContent = "Parsing…";
          const full = parseFort14Full(text);
          const truncated = full.renderedElements < full.elementCount;
          note.textContent = truncated
            ? `Rendered first ${full.renderedElements.toLocaleString()} of ${full.elementCount.toLocaleString()} elements (cap for performance).`
            : `${full.elementCount.toLocaleString()} elements, ${full.nodeCount.toLocaleString()} nodes.`;
          canvas.hidden = false;
          renderMesh(canvas, full);
          btn.textContent = "Re-render";
          btn.disabled = false;
        } catch (e) {
          note.innerHTML = `<span class="error">Failed to render: ${esc(e.message)}</span>`;
          btn.textContent = orig;
          btn.disabled = false;
        }
      });
    }
  } catch (err) {
    document.getElementById("mesh-content").innerHTML = `<p class="error">${esc(err.message)}</p>`;
  }
})();
