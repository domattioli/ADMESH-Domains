import { renderNav, renderFooter } from "./nav.js";
import { loadManifest } from "./manifest-loader.js";
import { createMap, addBbox, addDomainBboxes, bboxToLatLngBounds } from "./map.js";
import { bboxFromFile, parseFort14Full } from "./mesh-parser.js";
import { suggestDomain } from "./suggester.js";
import { renderMesh } from "./geometry-render.js";

renderNav();
renderFooter();

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file");
const result = document.getElementById("result");
const errEl = document.getElementById("error");

let manifestPromise = loadManifest();
let map = null;

function showError(msg) {
  errEl.textContent = msg;
  errEl.hidden = false;
  result.hidden = true;
}
function clearError() { errEl.hidden = true; errEl.textContent = ""; }

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("drag"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag");
  if (e.dataTransfer.files[0]) handle(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handle(fileInput.files[0]);
});

async function handle(file) {
  clearError();
  let text;
  try { text = await file.text(); }
  catch (e) { showError(`Could not read file: ${e.message}`); return; }

  const bbox = bboxFromFile(file.name, text);
  if (!bbox) {
    showError("Could not parse a bounding box from this file. Check that it's a valid fort.14 / .grd / .2dm.");
    return;
  }

  const manifest = await manifestPromise;
  const scores = suggestDomain(bbox, manifest);

  const sugEl = document.getElementById("suggestions");
  if (!scores.length) {
    sugEl.innerHTML = `<p class="muted">No geographic match — bbox is in projected coordinates. Treat as a synthetic domain.</p>`;
  } else {
    const top = scores.slice(0, 5);
    sugEl.innerHTML = `
      <table>
        <thead><tr><th>Domain</th><th>Per-mesh IoU</th><th>Union IoU</th><th>Confidence</th></tr></thead>
        <tbody>
          ${top.map((s) => `<tr>
            <td><a href="domain.html?d=${encodeURIComponent(s.domain)}">${s.domain}</a></td>
            <td>${s.per_mesh_iou.toFixed(3)}</td>
            <td>${s.union_iou.toFixed(3)}</td>
            <td class="confidence-${s.confidence}">${s.confidence}</td>
          </tr>`).join("")}
        </tbody>
      </table>
    `;
  }

  if (map) { map.remove(); map = null; }
  document.getElementById("preview-map").innerHTML = "";
  result.hidden = false;

  const isGeo = bbox.min_lon >= -180 && bbox.max_lon <= 180 && bbox.min_lat >= -90 && bbox.max_lat <= 90;
  if (isGeo) {
    map = createMap("preview-map");
    addDomainBboxes(map, manifest.domains);
    addBbox(map, bbox, { color: "#c62828", weight: 3, fillOpacity: 0.3, label: file.name });
    map.fitBounds(bboxToLatLngBounds(bbox), { padding: [40, 40], maxZoom: 9 });
  } else {
    document.getElementById("preview-map").outerHTML =
      `<p class="muted">Bbox is in projected coordinates — no map preview.</p>`;
  }

  const geomNote = document.getElementById("geom-note");
  const canvas = document.getElementById("geometry-canvas");
  if (file.name.toLowerCase().endsWith(".2dm")) {
    geomNote.textContent = "Geometry rendering for .2dm is not implemented yet.";
    canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
    return;
  }
  const full = parseFort14Full(text);
  if (!full) {
    geomNote.textContent = "Could not parse mesh elements.";
    return;
  }
  const truncated = full.renderedElements < full.elementCount;
  geomNote.textContent = truncated
    ? `Rendering first ${full.renderedElements.toLocaleString()} of ${full.elementCount.toLocaleString()} elements.`
    : `${full.elementCount.toLocaleString()} elements, ${full.nodeCount.toLocaleString()} nodes.`;
  renderMesh(canvas, full);
}
