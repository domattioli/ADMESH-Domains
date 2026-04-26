// Loads ./manifest.json once and caches it in sessionStorage.
let _cache = null;

export async function loadManifest() {
  if (_cache) return _cache;
  const cached = sessionStorage.getItem("admesh-manifest");
  if (cached) {
    try {
      _cache = JSON.parse(cached);
      return _cache;
    } catch {}
  }
  const res = await fetch("./manifest.json");
  if (!res.ok) throw new Error(`manifest fetch failed: ${res.status}`);
  _cache = await res.json();
  try {
    sessionStorage.setItem("admesh-manifest", JSON.stringify(_cache));
  } catch {}
  return _cache;
}

export function findDomain(manifest, name) {
  if (!name) return null;
  const lower = name.toLowerCase();
  return manifest.domains.find((d) => d.name.toLowerCase() === lower) || null;
}

export function findMesh(domain, id) {
  if (!domain || !id) return null;
  return domain.meshes.find((m) => m.id === id) || null;
}
