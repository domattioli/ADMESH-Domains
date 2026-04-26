// JS port of admesh_domains/geometry.py mesh-file parsers.
// Returns { minLon, minLat, maxLon, maxLat } or null.

export function bboxFromFort14(text) {
  const lines = text.split(/\r?\n/);
  if (lines.length < 3) return null;
  const counts = lines[1].trim().split(/\s+/);
  if (counts.length < 2) return null;
  const ne = parseInt(counts[0], 10);
  const nn = parseInt(counts[1], 10);
  if (!Number.isFinite(ne) || !Number.isFinite(nn) || nn <= 0) return null;

  let minLon = Infinity, minLat = Infinity;
  let maxLon = -Infinity, maxLat = -Infinity;
  let parsed = 0;
  for (let i = 2; i < lines.length && parsed < nn; i++) {
    const parts = lines[i].trim().split(/\s+/);
    if (parts.length < 3) continue;
    const lon = parseFloat(parts[1]);
    const lat = parseFloat(parts[2]);
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
    if (lon < minLon) minLon = lon;
    if (lat < minLat) minLat = lat;
    if (lon > maxLon) maxLon = lon;
    if (lat > maxLat) maxLat = lat;
    parsed++;
  }
  if (parsed === 0) return null;
  return { min_lon: minLon, min_lat: minLat, max_lon: maxLon, max_lat: maxLat, _node_count: parsed };
}

export function bboxFrom2dm(text) {
  const lines = text.split(/\r?\n/);
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
  let parsed = 0;
  for (const line of lines) {
    if (!line.startsWith("ND ")) continue;
    const parts = line.trim().split(/\s+/);
    if (parts.length < 4) continue;
    const lon = parseFloat(parts[2]);
    const lat = parseFloat(parts[3]);
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
    if (lon < minLon) minLon = lon;
    if (lat < minLat) minLat = lat;
    if (lon > maxLon) maxLon = lon;
    if (lat > maxLat) maxLat = lat;
    parsed++;
  }
  if (parsed === 0) return null;
  return { min_lon: minLon, min_lat: minLat, max_lon: maxLon, max_lat: maxLat, _node_count: parsed };
}

export function bboxFromFile(filename, text) {
  const lower = filename.toLowerCase();
  if (lower.endsWith(".2dm")) return bboxFrom2dm(text);
  // .14, .grd, .fort.14 all dispatch to the fort14 parser
  return bboxFromFort14(text);
}

// Yields elements [n1, n2, n3] (0-indexed). Caller passes the nodes array
// returned by parseFort14Full. Used by geometry-render.js.
export function parseFort14Full(text, { maxElements = 200000 } = {}) {
  const lines = text.split(/\r?\n/);
  if (lines.length < 3) return null;
  const counts = lines[1].trim().split(/\s+/);
  const ne = parseInt(counts[0], 10);
  const nn = parseInt(counts[1], 10);
  if (!Number.isFinite(ne) || !Number.isFinite(nn)) return null;

  const nodes = new Float64Array(nn * 2);
  let li = 2;
  for (let i = 0; i < nn && li < lines.length; i++, li++) {
    const p = lines[li].trim().split(/\s+/);
    nodes[i * 2] = parseFloat(p[1]);
    nodes[i * 2 + 1] = parseFloat(p[2]);
  }
  const cap = Math.min(ne, maxElements);
  const elements = new Int32Array(cap * 3);
  for (let i = 0; i < cap && li < lines.length; i++, li++) {
    const p = lines[li].trim().split(/\s+/);
    // fort.14 element line: id  nverts n1 n2 n3
    elements[i * 3] = parseInt(p[2], 10) - 1;
    elements[i * 3 + 1] = parseInt(p[3], 10) - 1;
    elements[i * 3 + 2] = parseInt(p[4], 10) - 1;
  }
  return { nodes, elements, nodeCount: nn, elementCount: ne, renderedElements: cap };
}
