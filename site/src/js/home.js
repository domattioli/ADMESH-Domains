import { renderNav, renderFooter } from "./nav.js";
import { loadManifest } from "./manifest-loader.js";
import { createMap, addDomainBboxes } from "./map.js";

renderNav();
renderFooter();

function fmtNum(n) { return n.toLocaleString(); }

function renderCards(domains, q = "") {
  const el = document.getElementById("domain-cards");
  const count = document.getElementById("result-count");
  const lower = q.trim().toLowerCase();
  const matches = domains.filter((d) => {
    if (!lower) return true;
    return [d.name, d.full_name, d.region, d.category, ...(d.applications || [])]
      .filter(Boolean).some((s) => String(s).toLowerCase().includes(lower));
  });
  count.textContent = `${matches.length} of ${domains.length} domains`;
  el.innerHTML = matches.map((d) => `
    <a class="card" href="domain.html?d=${encodeURIComponent(d.name)}">
      <h3>${d.name}</h3>
      <div class="meta">${d.full_name || ""}</div>
      <div class="meta">${d.region || d.category || ""} · ${(d.meshes || []).length} mesh${d.meshes.length === 1 ? "" : "es"}</div>
    </a>
  `).join("");
}

(async () => {
  try {
    const manifest = await loadManifest();
    document.getElementById("total-domains").textContent = fmtNum(manifest.totals.domains);
    document.getElementById("total-meshes").textContent = fmtNum(manifest.totals.meshes);
    document.getElementById("total-size").textContent = fmtNum(manifest.totals.size_mb);

    const map = createMap("map");
    addDomainBboxes(map, manifest.domains, {
      onClick: (d) => { location.href = `domain.html?d=${encodeURIComponent(d.name)}`; },
    });

    renderCards(manifest.domains);
    const q = document.getElementById("q");
    let t;
    q.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(() => renderCards(manifest.domains, q.value), 100);
    });
  } catch (err) {
    document.querySelector("main").insertAdjacentHTML("afterbegin",
      `<p class="error">Failed to load registry: ${err.message}</p>`);
  }
})();
