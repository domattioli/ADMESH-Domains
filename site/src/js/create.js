import { renderNav, renderFooter } from "./nav.js";
import { bboxFromFile, parseFort14Full } from "./mesh-parser.js";

renderNav();
renderFooter();

const term = document.getElementById("terminal");
const file = document.getElementById("file");
const dropzone = document.getElementById("dropzone");

function write(line, cls = "") {
  const span = document.createElement("span");
  if (cls) span.className = cls;
  span.textContent = line + "\n";
  term.appendChild(span);
  term.scrollTop = term.scrollHeight;
}

function prompt(cmd) {
  write(`$ ${cmd}`, "muted");
}

async function handleFile(f) {
  if (!f) return;
  term.innerHTML = "";
  prompt(`admesh-create analyze ${f.name}`);
  write(`reading ${(f.size / 1024).toFixed(1)} KB...`);
  const text = await f.text();

  const bbox = bboxFromFile(f.name, text);
  if (bbox) {
    write(`bbox: lon [${bbox.minLon.toFixed(4)}, ${bbox.maxLon.toFixed(4)}], lat [${bbox.minLat.toFixed(4)}, ${bbox.maxLat.toFixed(4)}]`, "success");
    const isGeo = bbox.minLon >= -180 && bbox.maxLon <= 180 && bbox.minLat >= -90 && bbox.maxLat <= 90;
    write(`coordinate system: ${isGeo ? "geographic (lon/lat)" : "projected / synthetic"}`);
  } else {
    write(`could not parse bounding box`, "error");
  }

  if (/\.(14|grd|fort)$/i.test(f.name)) {
    try {
      const parsed = parseFort14Full(text);
      write(`nodes: ${parsed.nodeCount.toLocaleString()}`);
      write(`elements: ${parsed.elementCount.toLocaleString()}${parsed.renderedElements < parsed.elementCount ? ` (rendered first ${parsed.renderedElements.toLocaleString()})` : ""}`);
    } catch (e) {
      write(`parser error: ${e.message}`, "error");
    }
  }

  prompt(`admesh-create boundary --interactive  # SAM-style waterbody select`);
  write(`not yet implemented — see issue #1`, "muted");
  prompt(`admesh-create draw  # freehand polygon → fort.14`);
  write(`not yet implemented — see issue #2`, "muted");
}

file.addEventListener("change", () => handleFile(file.files[0]));

dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("drag"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag");
  const f = e.dataTransfer.files[0];
  if (f) handleFile(f);
});
