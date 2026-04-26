// Renders mesh geometry to a 2D canvas. Lon/lat -> canvas pixels with
// equal-aspect projection (no real reprojection — fine for v1).

export function renderMesh(canvas, parsed) {
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth, cssH = canvas.clientHeight;
  canvas.width = cssW * dpr;
  canvas.height = cssH * dpr;
  ctx.scale(dpr, dpr);

  // Theme colors
  const styles = getComputedStyle(document.body);
  const fg = styles.getPropertyValue("--fg").trim() || "#111";
  const bg = styles.getPropertyValue("--card-bg").trim() || "#f7f8fa";
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, cssW, cssH);

  if (!parsed || !parsed.elements || !parsed.nodes) return;

  const { nodes, elements, renderedElements } = parsed;
  // bbox
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (let i = 0; i < nodes.length; i += 2) {
    const x = nodes[i], y = nodes[i + 1];
    if (x < minX) minX = x; if (x > maxX) maxX = x;
    if (y < minY) minY = y; if (y > maxY) maxY = y;
  }
  const padding = 12;
  const sx = (cssW - 2 * padding) / Math.max(1e-9, maxX - minX);
  const sy = (cssH - 2 * padding) / Math.max(1e-9, maxY - minY);
  const s = Math.min(sx, sy);
  const ox = padding + ((cssW - 2 * padding) - (maxX - minX) * s) / 2;
  const oy = padding + ((cssH - 2 * padding) - (maxY - minY) * s) / 2;

  const proj = (i) => [ox + (nodes[i * 2] - minX) * s, cssH - (oy + (nodes[i * 2 + 1] - minY) * s)];

  ctx.lineWidth = 0.5;
  ctx.strokeStyle = fg;
  ctx.globalAlpha = 0.8;
  ctx.beginPath();
  for (let e = 0; e < renderedElements; e++) {
    const a = elements[e * 3], b = elements[e * 3 + 1], c = elements[e * 3 + 2];
    if (a < 0 || b < 0 || c < 0) continue;
    const [ax, ay] = proj(a), [bx, by] = proj(b), [cx, cy] = proj(c);
    ctx.moveTo(ax, ay); ctx.lineTo(bx, by);
    ctx.lineTo(cx, cy); ctx.lineTo(ax, ay);
  }
  ctx.stroke();
  ctx.globalAlpha = 1;
}
