import { renderNav, renderFooter } from "./nav.js";

renderNav();
renderFooter();

const form = document.getElementById("form");
const referrer = document.referrer || "(direct)";
form.elements.page.value = referrer;

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const fd = new FormData(form);
  const category = fd.get("category");
  const title = fd.get("title");
  const body = `**Category:** ${category}\n**From page:** ${fd.get("page") || "(unknown)"}\n\n${fd.get("body")}`;
  const params = new URLSearchParams({
    title,
    body,
    labels: `feedback,${category}`,
  });
  window.open(
    `https://github.com/domattioli/ADMESH-Domains/issues/new?${params.toString()}`,
    "_blank",
    "noopener",
  );
});
