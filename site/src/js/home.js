import { renderNav, renderFooter } from "./nav.js";
import { loadManifest } from "./manifest-loader.js";
import { createMap, addDomainBboxes } from "./map.js";

renderNav();
renderFooter();

const fmt = (n) => (n == null ? "—" : Number(n).toLocaleString());

function computeSuperlatives(manifest) {
  const allMeshes = manifest.domains.flatMap((d) =>
    (d.meshes || []).map((m) => ({ ...m, _domain: d.name }))
  );
  const contributors = new Map();
  for (const m of allMeshes) {
    if (m.contributor) {
      contributors.set(m.contributor, (contributors.get(m.contributor) || 0) + 1);
    }
  }
  const topContributors = [...contributors.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  const byNodes = [...allMeshes].filter((m) => m.node_count != null)
    .sort((a, b) => b.node_count - a.node_count)[0];
  const bySize = [...allMeshes].filter((m) => m.size_mb != null)
    .sort((a, b) => b.size_mb - a.size_mb)[0];
  const refOrder = { coarse: 1, medium: 2, fine: 3, "very fine": 4 };
  const byRefinement = [...allMeshes].filter((m) => m.refinement_level)
    .sort((a, b) => (refOrder[b.refinement_level?.toLowerCase()] || 0) - (refOrder[a.refinement_level?.toLowerCase()] || 0))[0];

  return { contributors: contributors.size, topContributors, byNodes, bySize, byRefinement };
}

function meshLink(m) {
  if (!m) return "—";
  return `<a href="mesh.html?d=${encodeURIComponent(m._domain)}&m=${encodeURIComponent(m.id)}">${m._domain}/${m.id}</a>`;
}

function renderSuperlatives(s) {
  const el = document.getElementById("superlatives");
  const contribList = s.topContributors.length
    ? s.topContributors.map(([name, n]) => `<li>${name} <span class="muted">(${n})</span></li>`).join("")
    : '<li class="muted">No contributors recorded yet.</li>';
  el.innerHTML = `
    <div class="card">
      <h3>Largest by nodes</h3>
      <div>${meshLink(s.byNodes)}</div>
      <div class="meta">${fmt(s.byNodes?.node_count)} nodes</div>
    </div>
    <div class="card">
      <h3>Largest by file size</h3>
      <div>${meshLink(s.bySize)}</div>
      <div class="meta">${s.bySize?.size_mb != null ? s.bySize.size_mb.toFixed(2) + " MB" : "—"}</div>
    </div>
    <div class="card">
      <h3>Most refined</h3>
      <div>${meshLink(s.byRefinement)}</div>
      <div class="meta">${s.byRefinement?.refinement_level || "—"}</div>
    </div>
    <div class="card">
      <h3>Top contributors</h3>
      <ol class="tight">${contribList}</ol>
    </div>
  `;
}

(async () => {
  try {
    const manifest = await loadManifest();
    document.getElementById("total-domains").textContent = fmt(manifest.totals.domains);
    document.getElementById("total-meshes").textContent = fmt(manifest.totals.meshes);
    document.getElementById("total-size").textContent = fmt(manifest.totals.size_mb);

    const s = computeSuperlatives(manifest);
    document.getElementById("total-contributors").textContent = fmt(s.contributors);
    renderSuperlatives(s);

    const map = createMap("map");
    addDomainBboxes(map, manifest.domains, {
      onClick: (d) => { location.href = `domain.html?d=${encodeURIComponent(d.name)}`; },
    });
  } catch (err) {
    document.querySelector("main").insertAdjacentHTML("afterbegin",
      `<p class="error">Failed to load registry: ${err.message}</p>`);
  }
})();
