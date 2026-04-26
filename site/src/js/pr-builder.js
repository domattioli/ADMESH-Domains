// Composes a TOML fragment + GitHub URL for adding a Mesh (or Mesh+Domain).

const REPO = "domattioli/ADMESH-Domains";
const MANIFEST_PATH = "registry_data/manifest.toml";
const URL_LIMIT = 7000; // browsers cap around 8 KB; keep margin

function tomlString(s) {
  return `"${String(s).replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
}
function tomlList(arr) {
  return "[" + (arr || []).map(tomlString).join(", ") + "]";
}

export function buildMeshFragment({ domain_name, mesh }) {
  const lines = [`[[domains.meshes]]`];
  lines.push(`id = ${tomlString(mesh.id)}`);
  lines.push(`filename = ${tomlString(mesh.filename)}`);
  if (mesh.license) lines.push(`license = ${tomlString(mesh.license)}`);
  if (mesh.size_mb !== undefined && mesh.size_mb !== "") lines.push(`size_mb = ${Number(mesh.size_mb)}`);
  if (mesh.description) lines.push(`description = ${tomlString(mesh.description)}`);
  if (mesh.contributor) lines.push(`contributor = ${tomlString(mesh.contributor)}`);
  if (mesh.bounding_box) {
    const b = mesh.bounding_box;
    lines.push(`bounding_box = { min_lon = ${b.min_lon}, min_lat = ${b.min_lat}, max_lon = ${b.max_lon}, max_lat = ${b.max_lat} }`);
  }
  return lines.join("\n");
}

export function buildDomainFragment({ domain, mesh }) {
  const lines = [`[[domains]]`];
  lines.push(`name = ${tomlString(domain.name)}`);
  lines.push(`full_name = ${tomlString(domain.full_name || domain.name)}`);
  lines.push(`category = ${tomlString(domain.category || "real-world")}`);
  if (domain.region) lines.push(`region = ${tomlString(domain.region)}`);
  lines.push(`applications = ${tomlList(domain.applications)}`);
  lines.push("");
  lines.push(buildMeshFragment({ domain_name: domain.name, mesh }));
  return lines.join("\n");
}

export function buildPrUrl({ fragment, title, body }) {
  // GitHub's "edit existing file" URL pre-fills the editor; user appends and commits.
  // We embed the fragment in the PR body instead of attempting to splice the file —
  // it's a more reliable handoff (the user pastes it under the right Domain header).
  const fullBody = `${body}\n\n---\n\n**Add the following block to \`${MANIFEST_PATH}\`:**\n\n\`\`\`toml\n${fragment}\n\`\`\``;
  const params = new URLSearchParams({
    title,
    body: fullBody,
    labels: "data,mesh-submission",
  });
  return `https://github.com/${REPO}/issues/new?${params.toString()}`;
}

export function buildSubmission(form, suggestion) {
  const isNewDomain = form.mode === "new-domain";
  const mesh = {
    id: form.mesh_id || "default@v1",
    filename: form.filename,
    license: form.license,
    size_mb: form.size_mb,
    description: form.description,
    contributor: form.contributor,
    bounding_box: form.bounding_box,
  };
  const domainName = isNewDomain ? form.new_domain_name : suggestion;
  const fragment = isNewDomain
    ? buildDomainFragment({
        domain: {
          name: form.new_domain_name,
          full_name: form.new_domain_full_name,
          category: form.new_domain_category,
          region: form.new_domain_region,
          applications: (form.new_domain_applications || "").split(",").map((s) => s.trim()).filter(Boolean),
        },
        mesh,
      })
    : buildMeshFragment({ domain_name: domainName, mesh });

  const title = isNewDomain
    ? `Add new domain ${form.new_domain_name} (${form.filename})`
    : `Add ${form.filename} to ${domainName}`;
  const body = `Submission from the web form. Contributor: ${form.contributor || "(not provided)"}.`;
  const url = buildPrUrl({ fragment, title, body });
  const overflow = url.length > URL_LIMIT;
  return { fragment, url, overflow, title };
}
