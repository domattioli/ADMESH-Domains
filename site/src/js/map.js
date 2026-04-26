// Thin Leaflet wrapper. Assumes window.L is loaded.

export function createMap(elementId, { center = [20, 0], zoom = 2 } = {}) {
  const map = L.map(elementId, { center, zoom, scrollWheelZoom: true });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 18,
  }).addTo(map);
  return map;
}

export function bboxToLatLngBounds(bbox) {
  return [[bbox.min_lat, bbox.min_lon], [bbox.max_lat, bbox.max_lon]];
}

export function addDomainBboxes(map, domains, { onClick } = {}) {
  const layer = L.featureGroup().addTo(map);
  for (const d of domains) {
    const meshBboxes = (d.meshes || []).filter((m) => m.geographic && m.bounding_box);
    if (!meshBboxes.length) continue;
    const lons = meshBboxes.flatMap((m) => [m.bounding_box.min_lon, m.bounding_box.max_lon]);
    const lats = meshBboxes.flatMap((m) => [m.bounding_box.min_lat, m.bounding_box.max_lat]);
    const bbox = {
      min_lon: Math.min(...lons), max_lon: Math.max(...lons),
      min_lat: Math.min(...lats), max_lat: Math.max(...lats),
    };
    const rect = L.rectangle(bboxToLatLngBounds(bbox), {
      color: "#0b6cd1", weight: 2, fillOpacity: 0.12,
    }).bindTooltip(`<strong>${d.name}</strong><br>${d.full_name || ""}`);
    if (onClick) rect.on("click", () => onClick(d));
    rect.addTo(layer);
  }
  if (layer.getLayers().length) {
    map.fitBounds(layer.getBounds(), { padding: [20, 20], maxZoom: 6 });
  }
  return layer;
}

export function addBbox(map, bbox, opts = {}) {
  const rect = L.rectangle(bboxToLatLngBounds(bbox), {
    color: opts.color || "#c62828",
    weight: opts.weight || 3,
    fillOpacity: opts.fillOpacity ?? 0.25,
    dashArray: opts.dashArray,
  });
  if (opts.label) rect.bindTooltip(opts.label);
  rect.addTo(map);
  return rect;
}
