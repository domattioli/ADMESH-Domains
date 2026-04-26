// Shared formatting helpers.

// "2026-04-26" or "2026/04/26" or "20260426" -> "20260426"; null/empty -> null
export function parseCompactDate(date) {
  if (!date) return null;
  const digits = String(date).replace(/\D+/g, "");
  return digits.length >= 8 ? digits.slice(0, 8) : null;
}

export function fmtDate(date) {
  return parseCompactDate(date) || "—";
}

// "Dominik O Mattioli" + "2026-04-26" -> "D. O. Mattioli (20260426)"
export function fmtContributor(name, date) {
  if (!name) return "—";
  const parts = String(name).trim().split(/\s+/);
  let formatted;
  if (parts.length === 1) {
    formatted = parts[0];
  } else {
    const last = parts.pop();
    const initials = parts.map((p) => (p[0] || "").toUpperCase() + ".").join(" ");
    formatted = `${initials} ${last}`;
  }
  const compact = parseCompactDate(date);
  return compact ? `${formatted} (${compact})` : formatted;
}
