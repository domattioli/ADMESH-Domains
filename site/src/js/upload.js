import { renderNav, renderFooter } from "./nav.js";
import { loadManifest } from "./manifest-loader.js";
import { bboxFromFile, parseFort14Full } from "./mesh-parser.js";
import { suggestDomain } from "./suggester.js";
import { buildSubmission } from "./pr-builder.js";
import { renderMesh } from "./geometry-render.js";

renderNav();
renderFooter();

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file");
const formSection = document.getElementById("form-section");
const form = document.getElementById("form");
const errEl = document.getElementById("error");
const newDomainFields = document.getElementById("new-domain-fields");

let parsedBbox = null;
let topSuggestion = null;
let manifestPromise = loadManifest();
let parsedNodeCount = null;

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("drag"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault(); dropzone.classList.remove("drag");
  if (e.dataTransfer.files[0]) handle(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => fileInput.files[0] && handle(fileInput.files[0]));

form.elements.mode.forEach?.((r) => r.addEventListener("change", syncMode));
form.querySelectorAll('input[name="mode"]').forEach((r) => r.addEventListener("change", syncMode));

function syncMode() {
  const mode = new FormData(form).get("mode");
  newDomainFields.disabled = mode !== "new-domain";
}

async function handle(file) {
  errEl.hidden = true;
  let text;
  try { text = await file.text(); }
  catch (e) { errEl.textContent = e.message; errEl.hidden = false; return; }

  const bbox = bboxFromFile(file.name, text);
  if (!bbox) {
    errEl.textContent = "Could not parse a bounding box from this file.";
    errEl.hidden = false;
    return;
  }
  parsedBbox = bbox;

  // Parse node count for fort.14 files (for comparison & preview)
  parsedNodeCount = null;
  let parsedMesh = null;
  if (file.name.endsWith(".14") || file.name.endsWith(".fort")) {
    parsedMesh = parseFort14Full(text);
    if (parsedMesh) {
      parsedNodeCount = parsedMesh.nodeCount;
      // Render mesh preview
      renderMeshPreview(parsedMesh);
    }
  }

  const manifest = await manifestPromise;
  const scores = suggestDomain(bbox, manifest);
  topSuggestion = scores[0];

  const sugEl = document.getElementById("suggestions");
  if (!scores.length || scores[0].confidence === "low") {
    sugEl.innerHTML = `<p class="muted">No confident match. Consider proposing a new domain below.</p>`;
    form.elements.mode.value = "new-domain";
    form.querySelector('input[name="mode"][value="new-domain"]').checked = true;
    document.getElementById("comparison-results").style.display = "none";
  } else {
    sugEl.innerHTML = `<p>Top match: <strong>${scores[0].domain}</strong>
      <span class="confidence-${scores[0].confidence}">(${scores[0].confidence}, IoU ${scores[0].per_mesh_iou.toFixed(3)})</span></p>`;

    // Show mesh comparison for the suggested domain
    if (topSuggestion && parsedNodeCount !== null) {
      showMeshComparison(topSuggestion.domain, manifest, bbox, parsedNodeCount);
    }
  }
  syncMode();

  form.elements.filename.value = file.name;
  form.elements.size_mb = form.elements.size_mb;
  formSection.hidden = false;

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

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const fd = new FormData(form);
  const data = Object.fromEntries(fd.entries());
  data.bounding_box = parsedBbox;
  data.size_mb = data.size_mb || "";

  const submission = buildSubmission(data, topSuggestion?.domain);

  if (submission.overflow) {
    document.getElementById("frag").textContent = submission.fragment;
    document.getElementById("overflow").hidden = false;
    const params = new URLSearchParams({ title: submission.title, labels: "data,mesh-submission" });
    document.getElementById("empty-issue").href =
      `https://github.com/domattioli/ADMESH-Domains/issues/new?${params}`;
  } else {
    window.open(submission.url, "_blank", "noopener");
  }
});

document.getElementById("copy-frag")?.addEventListener("click", async () => {
  const text = document.getElementById("frag").textContent;
  await navigator.clipboard.writeText(text);
});

// Bare-bones mesh comparison: show IoU and node count delta for similar meshes
function showMeshComparison(domainName, manifest, uploadedBbox, uploadedNodeCount) {
  const domain = manifest.domains.find(d => d.name === domainName);
  if (!domain || !domain.meshes) {
    document.getElementById("comparison-results").style.display = "none";
    return;
  }

  // Compute IoU with each existing mesh
  const meshesWithIou = domain.meshes.map(mesh => {
    const iou = computeIoU(uploadedBbox, mesh.bounding_box);
    const nodeDelta = uploadedNodeCount - (mesh.node_count || 0);
    return {
      id: mesh.id,
      iou,
      nodeDelta,
      nodeCount: mesh.node_count || 0,
      sizeMb: mesh.size_mb,
    };
  });

  // Sort by IoU descending (most similar first)
  meshesWithIou.sort((a, b) => b.iou - a.iou);

  // Populate table
  const tbody = document.getElementById("comparison-tbody");
  tbody.innerHTML = meshesWithIou.map(m => {
    const nodeDeltaStr = m.nodeDelta > 0 ? `+${m.nodeDelta}` : `${m.nodeDelta}`;
    const nodeDeltaClass = m.nodeDelta > 0 ? "class='positive'" : m.nodeDelta < 0 ? "class='negative'" : "";
    return `<tr>
      <td>${m.id}</td>
      <td>${m.iou.toFixed(3)}</td>
      <td ${nodeDeltaClass}>${nodeDeltaStr}</td>
      <td>${m.sizeMb.toFixed(2)} MB</td>
    </tr>`;
  }).join("");

  document.getElementById("comp-domain").textContent = domainName;
  document.getElementById("comp-count").textContent = domain.meshes.length;
  document.getElementById("comparison-results").style.display = "block";
}

// Mesh preview state for zoom/pan
let meshPreviewState = {
  zoom: 1,
  panX: 0,
  panY: 0,
  parsedMesh: null,
};

// Render mesh geometry preview to canvas with zoom/pan support
function renderMeshPreview(parsedMesh) {
  const canvas = document.getElementById("mesh-canvas");
  const statsEl = document.getElementById("mesh-stats");
  const previewEl = document.getElementById("mesh-preview");

  if (!canvas || !parsedMesh) {
    previewEl.style.display = "none";
    return;
  }

  try {
    meshPreviewState.parsedMesh = parsedMesh;
    meshPreviewState.zoom = 1;
    meshPreviewState.panX = 0;
    meshPreviewState.panY = 0;

    renderMeshWithTransform();

    // Display mesh statistics with controls
    const elemCount = parsedMesh.elementCount || parsedMesh.renderedElements || "?";
    const nodeCount = parsedMesh.nodeCount || "?";
    const statsText = `<strong>${nodeCount.toLocaleString()}</strong> nodes, ` +
                      `<strong>${elemCount.toLocaleString()}</strong> elements` +
                      (parsedMesh.renderedElements && parsedMesh.renderedElements < parsedMesh.elementCount
                        ? ` (showing first ${parsedMesh.renderedElements.toLocaleString()} for performance)`
                        : "") +
                      ` <span style="color:#999; font-size:0.85rem;">· Scroll to zoom, drag to pan, double-click to reset</span>`;
    statsEl.innerHTML = statsText;

    // Setup canvas interactions
    setupMeshInteraction(canvas);
    previewEl.style.display = "block";
  } catch (e) {
    console.error("Mesh preview error:", e);
    previewEl.style.display = "none";
  }
}

// Render mesh with current zoom/pan transform
function renderMeshWithTransform() {
  const canvas = document.getElementById("mesh-canvas");
  if (!canvas || !meshPreviewState.parsedMesh) return;

  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth, cssH = canvas.clientHeight;
  canvas.width = cssW * dpr;
  canvas.height = cssH * dpr;
  ctx.scale(dpr, dpr);

  // Apply zoom and pan
  ctx.translate(meshPreviewState.panX, meshPreviewState.panY);
  ctx.scale(meshPreviewState.zoom, meshPreviewState.zoom);
  ctx.translate(cssW / (2 * meshPreviewState.zoom), cssH / (2 * meshPreviewState.zoom));

  renderMesh(canvas, meshPreviewState.parsedMesh);
}

// Setup mouse interactions for zoom/pan
function setupMeshInteraction(canvas) {
  let isDragging = false;
  let dragStartX = 0, dragStartY = 0;

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    meshPreviewState.zoom *= zoomFactor;
    meshPreviewState.zoom = Math.max(0.1, Math.min(10, meshPreviewState.zoom));
    renderMeshWithTransform();
  }, { passive: false });

  canvas.addEventListener("mousedown", (e) => {
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
  });

  canvas.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    meshPreviewState.panX += e.clientX - dragStartX;
    meshPreviewState.panY += e.clientY - dragStartY;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    renderMeshWithTransform();
  });

  canvas.addEventListener("mouseup", () => { isDragging = false; });
  canvas.addEventListener("mouseleave", () => { isDragging = false; });

  canvas.addEventListener("dblclick", () => {
    meshPreviewState.zoom = 1;
    meshPreviewState.panX = 0;
    meshPreviewState.panY = 0;
    renderMeshWithTransform();
  });
}

// Compute Intersection over Union (IoU) for two bboxes
// Format: { min_lon, min_lat, max_lon, max_lat }
function computeIoU(bbox1, bbox2) {
  if (!bbox1 || !bbox2) return 0;

  const x_inter_min = Math.max(bbox1.min_lon, bbox2.min_lon);
  const x_inter_max = Math.min(bbox1.max_lon, bbox2.max_lon);
  const y_inter_min = Math.max(bbox1.min_lat, bbox2.min_lat);
  const y_inter_max = Math.min(bbox1.max_lat, bbox2.max_lat);

  if (x_inter_min >= x_inter_max || y_inter_min >= y_inter_max) {
    return 0; // No intersection
  }

  const interArea = (x_inter_max - x_inter_min) * (y_inter_max - y_inter_min);
  const area1 = (bbox1.max_lon - bbox1.min_lon) * (bbox1.max_lat - bbox1.min_lat);
  const area2 = (bbox2.max_lon - bbox2.min_lon) * (bbox2.max_lat - bbox2.min_lat);
  const unionArea = area1 + area2 - interArea;

  return unionArea > 0 ? interArea / unionArea : 0;
}
