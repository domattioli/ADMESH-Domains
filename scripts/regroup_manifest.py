#!/usr/bin/env python3
"""Convert flat [[domain]] manifest into nested Domain -> Meshes structure."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# Maps each existing flat-entry name to (domain_name, mesh_id).
# Domains group meshes that represent the same conceptual region.
GROUPING: dict[str, tuple[str, str]] = {
    # Real-world: Western North Atlantic
    "WNAT_Hagen":             ("WNAT",            "hagen@v1"),
    "WNAT_Onur":              ("WNAT",            "onur@v1"),
    "WNAT_Test":              ("WNAT",            "test@v1"),
    # Real-world: Great Lakes
    "Great_Lakes":            ("GreatLakes",      "default@v1"),
    # Real-world: Lake Erie
    "LakeErie_5k_500":        ("LakeErie",        "5k-nodes@v1"),
    "Lake_Erie_refined":      ("LakeErie",        "refined@v1"),
    # Real-world: Lake Michigan
    "Lake_Michigan_mesh":     ("LakeMichigan",    "default@v1"),
    # Real-world: Chesapeake Bay
    "Chesapeake_Bay":         ("ChesapeakeBay",   "default@v1"),
    # Real-world: Delaware Bay
    "Deleware_Bay":           ("DelawareBay",     "default@v1"),
    "Deleware_Bay_refined":   ("DelawareBay",     "refined-100-20000@v1"),
    # Real-world: Italy
    "Italy":                  ("Italy",           "default@v1"),
    # Real-world: Baranja Hill (Europe)
    "Baranja_Hill":           ("BaranjaHill",     "default@v1"),
    "Baranja_Hill_ADMESH_v2": ("BaranjaHill",     "admesh-v2@v1"),
    # Synthetic: numbered test cases
    "Test_Case_1":            ("TestCases",       "case-1@v1"),
    "Test_Case_2":            ("TestCases",       "case-2@v1"),
    "Test_Case_3":            ("TestCases",       "case-3@v1"),
    "Test_Case_4":            ("TestCases",       "case-4@v1"),
    "Test_Case_4.2":          ("TestCases",       "case-4.2@v1"),
    # Synthetic: structured grid meshes
    "structuredMesh1":        ("StructuredGrids", "v1@v1"),
    "structuredMesh2":        ("StructuredGrids", "v2@v1"),
    "structuredMesh3":        ("StructuredGrids", "v3@v1"),
    "structuredMesh4":        ("StructuredGrids", "v4@v1"),
    # Synthetic: rectangular reference meshes
    "rectangular_mesh_triangle1":             ("Rectangles", "tri@v1"),
    "rectangular_mesh_quadrilateral1":        ("Rectangles", "quad@v1"),
    "rectangular_skewed_mesh_triangle1":      ("Rectangles", "tri-skewed@v1"),
    "rectangular_skewed_mesh_quadrilateral1": ("Rectangles", "quad-skewed@v1"),
    # Synthetic: simple geometric shapes
    "Block_O":                ("Shapes",          "block-o@v1"),
    "circle":                 ("Shapes",          "circle@v1"),
    "annulus_200pts":         ("Shapes",          "annulus-200pts@v1"),
    "donut_domain":           ("Shapes",          "donut@v1"),
    "islands1":               ("Shapes",          "islands@v1"),
    "square_mesh_test":       ("Shapes",          "square@v1"),
    # Synthetic: misc tests / scratch
    "test1":                  ("MiscTests",       "test1@v1"),
    "test2":                  ("MiscTests",       "test2@v1"),
    "test3":                  ("MiscTests",       "test3@v1"),
    "test4":                  ("MiscTests",       "test4@v1"),
    "simple_test_case":       ("MiscTests",       "simple@v1"),
    "wetting_and_drying_test":("MiscTests",       "wetting-drying@v1"),
    "Mixed_Test":             ("MiscTests",       "mixed@v1"),
    "dom_2dm":                ("MiscTests",       "sms-2dm@v1"),
}

DOMAIN_META: dict[str, dict] = {
    "WNAT": dict(
        full_name="Western North Atlantic",
        description="Western North Atlantic Ocean basin for hurricane and storm-surge modeling",
        category="real-world",
        region="Atlantic Ocean",
        applications=["Hurricane/Storm Surge", "Coastal Circulation"],
    ),
    "GreatLakes": dict(
        full_name="Great Lakes",
        description="Combined Great Lakes basin",
        category="real-world",
        region="North America",
        applications=["Lake Circulation"],
    ),
    "LakeErie": dict(
        full_name="Lake Erie",
        category="real-world",
        region="North America",
        applications=["Lake Circulation"],
    ),
    "LakeMichigan": dict(
        full_name="Lake Michigan",
        category="real-world",
        region="North America",
        applications=["Lake Circulation"],
    ),
    "ChesapeakeBay": dict(
        full_name="Chesapeake Bay",
        category="real-world",
        region="North America",
        applications=["Coastal Circulation"],
    ),
    "DelawareBay": dict(
        full_name="Delaware Bay",
        category="real-world",
        region="North America",
        applications=["Coastal Circulation"],
    ),
    "Italy": dict(
        full_name="Italy coastal region",
        category="real-world",
        region="Mediterranean",
        applications=["Coastal Circulation"],
    ),
    "BaranjaHill": dict(
        full_name="Baranja Hill",
        category="real-world",
        region="Europe",
        applications=["Coastal Circulation"],
    ),
    "TestCases": dict(
        full_name="Numbered test cases",
        description="Synthetic numbered test cases used for validation",
        category="synthetic",
    ),
    "StructuredGrids": dict(
        full_name="Structured grid meshes",
        description="Regular structured grid variants used for testing",
        category="synthetic",
    ),
    "Rectangles": dict(
        full_name="Rectangular reference meshes",
        description="Rectangular triangular and quadrilateral reference meshes",
        category="synthetic",
    ),
    "Shapes": dict(
        full_name="Simple geometric shapes",
        description="Circles, donuts, islands, and other primitive geometries",
        category="synthetic",
    ),
    "MiscTests": dict(
        full_name="Miscellaneous test meshes",
        description="Scratch and misc test fixtures",
        category="synthetic",
    ),
}


def emit_value(v):
    """Render a Python value as TOML scalar."""
    if isinstance(v, str):
        escaped = v.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "[" + ", ".join(emit_value(x) for x in v) + "]"
    return str(v)


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    src_path = repo / "registry_data" / "manifest.toml"
    with open(src_path, "rb") as f:
        old = tomllib.load(f)

    flat_entries = {e["name"]: e for e in old.get("domain", [])}
    if set(flat_entries) - set(GROUPING):
        missing = sorted(set(flat_entries) - set(GROUPING))
        print(f"ERROR: no GROUPING entry for: {missing}", file=sys.stderr)
        return 1

    # Build domain -> list of (mesh_id, flat_entry) preserving manifest order
    grouped: dict[str, list[tuple[str, dict]]] = {}
    for flat_name, entry in flat_entries.items():
        domain_name, mesh_id = GROUPING[flat_name]
        grouped.setdefault(domain_name, []).append((mesh_id, entry))

    total_domains = len(grouped)
    total_meshes = sum(len(v) for v in grouped.values())
    total_size = sum(e.get("size_mb", 0) for e in flat_entries.values())

    out: list[str] = []
    out.append("# ADMESH Domain Registry Manifest")
    out.append("# Two-level model: Domain -> Meshes (one mesh per .14 file)")
    out.append("")
    out.append("schema_version = \"0.2\"")
    out.append("")
    out.append("[metadata]")
    out.append('version = "1.0.0"')
    out.append('description = "ADCIRC mesh domain registry"')
    out.append('created = "2026-04-25"')
    out.append("source_repositories = [")
    for url in old["metadata"].get("source_repositories", []):
        out.append(f'    "{url}",')
    out.append("]")
    out.append(f"total_domains = {total_domains}")
    out.append(f"total_meshes = {total_meshes}")
    out.append(f"total_size_mb = {round(total_size, 1)}")
    out.append("")

    for domain_name in sorted(grouped):
        meta = DOMAIN_META[domain_name]
        out.append(f"# Domain: {meta.get('full_name', domain_name)}")
        out.append("[[domains]]")
        out.append(f'name = "{domain_name}"')
        for k in ("full_name", "description", "category", "region"):
            if meta.get(k) is not None:
                out.append(f"{k} = {emit_value(meta[k])}")
        if meta.get("applications"):
            out.append(f"applications = {emit_value(meta['applications'])}")
        out.append("")

        for mesh_id, entry in grouped[domain_name]:
            out.append(f'[[domains.meshes]]')
            out.append(f'id = "{mesh_id}"')
            out.append(f'filename = {emit_value(entry["filename"])}')
            if entry.get("description"):
                out.append(f'description = {emit_value(entry["description"])}')
            out.append(f'size_mb = {entry.get("size_mb", 0)}')
            if entry.get("type") and entry["type"] != "ADCIRC":
                out.append(f'type = {emit_value(entry["type"])}')
            for k in ("element_type", "refinement_level"):
                if entry.get(k):
                    out.append(f'{k} = {emit_value(entry[k])}')
            if entry.get("aliases"):
                out.append(f'aliases = {emit_value(entry["aliases"])}')
            out.append("")

    text = "\n".join(out) + "\n"
    dest_repo = repo / "registry_data" / "manifest.toml"
    dest_pkg = repo / "admesh_domains" / "data" / "manifest.toml"
    dest_repo.write_text(text)
    dest_pkg.write_text(text)
    print(f"Wrote {dest_repo} ({len(text)} bytes)")
    print(f"Wrote {dest_pkg}")
    print(f"  domains: {total_domains}, meshes: {total_meshes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
