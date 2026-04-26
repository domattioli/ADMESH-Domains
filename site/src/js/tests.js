import { renderNav, renderFooter } from "./nav.js";
import { loadManifest } from "./manifest-loader.js";

renderNav();
renderFooter();

let allTestMeshes = [];
let tool = "curl";

function snippet(meshes, t) {
  if (t === "wget") return meshes.map((m) => `wget '${m.download_url}'`).join("\n");
  return meshes.map((m) => `curl -L -O '${m.download_url}'`).join("\n");
}

function renderSnippet() {
  document.getElementById("bulk-snippet").textContent = snippet(allTestMeshes, tool);
}

function renderTable(meshes) {
  const tbody = document.querySelector("#tests-table tbody");
  if (!meshes.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="muted">No meshes flagged <code>test_case = true</code> yet.</td></tr>`;
    return;
  }
  tbody.innerHTML = meshes.map((m) => `
    <tr>
      <td><a href="domain.html?d=${encodeURIComponent(m._domain)}">${m._domain}</a></td>
      <td><a href="mesh.html?d=${encodeURIComponent(m._domain)}&m=${encodeURIComponent(m.id)}">${m.id}</a></td>
      <td>${m.filename}</td>
      <td>${m.node_count != null ? m.node_count.toLocaleString() : "—"}</td>
      <td>${m.size_mb != null ? m.size_mb.toFixed(2) : "—"}</td>
      <td><a href="${m.download_url}">download</a></td>
    </tr>
  `).join("");
}

(async () => {
  try {
    const manifest = await loadManifest();
    allTestMeshes = manifest.domains.flatMap((d) =>
      (d.meshes || []).filter((m) => m.test_case === true).map((m) => ({ ...m, _domain: d.name }))
    );
    renderTable(allTestMeshes);
    renderSnippet();

    const curlBtn = document.getElementById("tool-curl");
    const wgetBtn = document.getElementById("tool-wget");
    const setTool = (t) => {
      tool = t;
      curlBtn.setAttribute("aria-pressed", String(t === "curl"));
      wgetBtn.setAttribute("aria-pressed", String(t === "wget"));
      renderSnippet();
    };
    curlBtn.addEventListener("click", () => setTool("curl"));
    wgetBtn.addEventListener("click", () => setTool("wget"));

    document.getElementById("copy-bulk").addEventListener("click", async () => {
      const text = snippet(allTestMeshes, tool);
      try {
        await navigator.clipboard.writeText(text);
        const btn = document.getElementById("copy-bulk");
        const orig = btn.textContent;
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = orig; }, 1500);
      } catch (e) {
        alert("Clipboard blocked; select the snippet manually.");
      }
    });
  } catch (err) {
    document.querySelector("main").insertAdjacentHTML("afterbegin",
      `<p class="error">Failed to load registry: ${err.message}</p>`);
  }
})();
