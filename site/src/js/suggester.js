// JS port of admesh_domains/geometry.py — IoU + ranking.
// All bbox objects use { min_lon, min_lat, max_lon, max_lat }.

export const CONFIDENT_THRESHOLD = 0.5;
export const UNCERTAIN_THRESHOLD = 0.05;

const isWrapping = (b) => b.min_lon > b.max_lon;

const isGeographic = (b) =>
  b && b.min_lon >= -180 && b.max_lon <= 180 && b.min_lat >= -90 && b.max_lat <= 90;

export function area(b) {
  if (!b || isWrapping(b)) return 0;
  const w = b.max_lon - b.min_lon;
  const h = b.max_lat - b.min_lat;
  return w > 0 && h > 0 ? w * h : 0;
}

export function intersection(a, b) {
  if (!a || !b || isWrapping(a) || isWrapping(b)) return null;
  const min_lon = Math.max(a.min_lon, b.min_lon);
  const min_lat = Math.max(a.min_lat, b.min_lat);
  const max_lon = Math.min(a.max_lon, b.max_lon);
  const max_lat = Math.min(a.max_lat, b.max_lat);
  if (max_lon <= min_lon || max_lat <= min_lat) return null;
  return { min_lon, min_lat, max_lon, max_lat };
}

export function union(a, b) {
  return {
    min_lon: Math.min(a.min_lon, b.min_lon),
    min_lat: Math.min(a.min_lat, b.min_lat),
    max_lon: Math.max(a.max_lon, b.max_lon),
    max_lat: Math.max(a.max_lat, b.max_lat),
  };
}

export function computeIoU(a, b) {
  if (!a || !b) return 0;
  if (isWrapping(a) || isWrapping(b)) return 0;
  const inter = intersection(a, b);
  if (!inter) return 0;
  const ai = area(inter);
  const u = area(a) + area(b) - ai;
  return u > 0 ? ai / u : 0;
}

export function centroidDistance(a, b) {
  const ax = (a.min_lon + a.max_lon) / 2, ay = (a.min_lat + a.max_lat) / 2;
  const bx = (b.min_lon + b.max_lon) / 2, by = (b.min_lat + b.max_lat) / 2;
  const dx = ax - bx, dy = ay - by;
  return Math.sqrt(dx * dx + dy * dy);
}

export function domainUnionBbox(domain) {
  const geos = (domain.meshes || []).map((m) => m.bounding_box).filter((b) => b && isGeographic(b));
  if (!geos.length) return null;
  return geos.reduce((acc, b) => acc ? union(acc, b) : b, null);
}

export function perMeshIoU(targetBbox, domain) {
  let best = 0;
  for (const m of (domain.meshes || [])) {
    if (!m.bounding_box || !isGeographic(m.bounding_box)) continue;
    const score = computeIoU(targetBbox, m.bounding_box);
    if (score > best) best = score;
  }
  return best;
}

function classify(score) {
  if (score >= CONFIDENT_THRESHOLD) return "confident";
  if (score >= UNCERTAIN_THRESHOLD) return "uncertain";
  return "low";
}

export function suggestDomain(targetBbox, manifest) {
  if (!isGeographic(targetBbox)) return [];
  const scores = [];
  for (const d of manifest.domains) {
    const u = domainUnionBbox(d);
    const perMesh = perMeshIoU(targetBbox, d);
    const unionIoU = u ? computeIoU(targetBbox, u) : 0;
    const cd = u ? centroidDistance(targetBbox, u) : Infinity;
    scores.push({
      domain: d.name,
      per_mesh_iou: perMesh,
      union_iou: unionIoU,
      centroid_distance: cd,
      confidence: classify(perMesh),
    });
  }
  // Rank by per-mesh IoU desc, then union IoU desc, then centroid distance asc.
  scores.sort((a, b) => (b.per_mesh_iou - a.per_mesh_iou)
    || (b.union_iou - a.union_iou)
    || (a.centroid_distance - b.centroid_distance));
  return scores;
}
