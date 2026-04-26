import { renderNav, renderFooter } from "./nav.js";
import { loadManifest } from "./manifest-loader.js";
import { bboxFromFile } from "./mesh-parser.js";
import { suggestDomain } from "./suggester.js";
import { buildSubmission } from "./pr-builder.js";

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

  const manifest = await manifestPromise;
  const scores = suggestDomain(bbox, manifest);
  topSuggestion = scores[0];

  const sugEl = document.getElementById("suggestions");
  if (!scores.length || scores[0].confidence === "low") {
    sugEl.innerHTML = `<p class="muted">No confident match. Consider proposing a new domain below.</p>`;
    form.elements.mode.value = "new-domain";
    form.querySelector('input[name="mode"][value="new-domain"]').checked = true;
  } else {
    sugEl.innerHTML = `<p>Top match: <strong>${scores[0].domain}</strong>
      <span class="confidence-${scores[0].confidence}">(${scores[0].confidence}, IoU ${scores[0].per_mesh_iou.toFixed(3)})</span></p>`;
  }
  syncMode();

  form.elements.filename.value = file.name;
  form.elements.size_mb = form.elements.size_mb;
  formSection.hidden = false;
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
