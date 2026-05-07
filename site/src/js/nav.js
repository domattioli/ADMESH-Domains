// Renders the shared header into <div id="site-header"></div>.
const PAGES = [
  ["", "Home"],
  ["browse.html", "Browse"],
  ["compare.html", "Compare"],
  ["upload.html", "Upload"],
];

// Archived pages (hidden from nav, code preserved for future restoration):
// ["statistics.html", "Statistics"],  // → site/archived/statistics.html.bak
// ["create.html", "Create"],          // → site/archived/create.html.bak
// ["tests.html", "Test Suites"],      // → site/archived/tests.html.bak
// ["feedback.html", "Feedback"],      // → site/archived/feedback.html.bak
// See specs/010-site-mvp-redesign/RETIRED.md for restoration notes.

export function renderNav(currentPath) {
  const el = document.getElementById("site-header");
  if (!el) return;
  const here = (currentPath || location.pathname.split("/").pop() || "").toLowerCase();
  const links = PAGES.map(([href, label]) => {
    const active = (here === href.toLowerCase()) || (href === "" && (here === "" || here === "index.html"));
    return `<a href="${href || "./"}"${active ? ' aria-current="page"' : ""}>${label}</a>`;
  }).join("");
  el.innerHTML = `
    <a class="brand" href="./">ADMESH-Domains</a>
    <nav aria-label="Primary">${links}</nav>
  `;
}

export function renderFooter() {
  const el = document.getElementById("site-footer");
  if (!el) return;
  el.innerHTML = `
    <p>
      <a href="https://github.com/domattioli/ADMESH-Domains">GitHub</a> ·
      <a href="https://huggingface.co/datasets/domattioli/ADMESH-Domains">HuggingFace dataset</a> ·
      <a href="https://pypi.org/project/admesh-domains/">PyPI</a> ·
      <a href="feedback.html">Feedback</a>
    </p>
    <p class="muted">Part of the ADMESH project. Built from <code>manifest.toml</code>; site source under <code>site/src/</code>.</p>
  `;
}
