"""Command-line interface for admesh-domains."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from .manifest import (
    ManifestNotFoundError,
    ManifestValidationError,
    load_manifest,
)
from .query import (
    find_domains,
    find_meshes,
    get_domain,
    get_mesh,
    list_regions,
    list_applications,
)


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else None
    try:
        m = load_manifest(path)
    except ManifestNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except ManifestValidationError as e:
        print(f"VALIDATION FAILED: {e}", file=sys.stderr)
        return 1

    print(f"OK: {m.source_path}")
    print(f"  metadata.version = {m.metadata.version}")
    print(f"  domains          = {len(m.domains)}")
    print(f"  meshes           = {m.total_meshes}")

    missing = [mesh.full_id for mesh in m.all_meshes() if not mesh.exists()]
    if missing:
        print(f"  WARNING: {len(missing)} mesh files not found locally")
        for full_id in missing[:5]:
            print(f"    - {full_id}")
        if len(missing) > 5:
            print(f"    ... and {len(missing) - 5} more")
    return 0


def cmd_domains(args: argparse.Namespace) -> int:
    domains = find_domains(
        category=args.category,
        region=args.region,
        application=args.application,
    )
    if not domains:
        print("(no domains matched)")
        return 0
    name_w = max(len(d.name) for d in domains)
    for d in domains:
        full = d.full_name or "-"
        region = d.region or "-"
        n = len(d.meshes)
        print(f"  {d.name:<{name_w}}  {n:>2} mesh(es)  {region:<15}  {full}")
    print(f"\n{len(domains)} domain(s)")
    return 0


def cmd_meshes(args: argparse.Namespace) -> int:
    meshes = find_meshes(
        domain=args.domain,
        contributor=args.contributor,
        type=args.type,
        element_type=args.element_type,
        refinement_level=args.refinement_level,
        min_size_mb=args.min_size,
        max_size_mb=args.max_size,
        min_node_count=args.min_nodes,
    )
    if not meshes:
        print("(no meshes matched)")
        return 0
    id_w = max(len(m.full_id) for m in meshes)
    for mesh in meshes:
        size = f"{mesh.size_mb:6.2f} MB"
        kind = mesh.element_type or mesh.type
        print(f"  {mesh.full_id:<{id_w}}  {size}  {kind}")
    print(f"\n{len(meshes)} mesh(es)")
    return 0


def cmd_show_domain(args: argparse.Namespace) -> int:
    try:
        d = get_domain(args.name)
    except KeyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"Domain: {d.name}")
    if d.full_name:
        print(f"  full_name:    {d.full_name}")
    if d.description:
        print(f"  description:  {d.description}")
    print(f"  category:     {d.category}")
    if d.region:
        print(f"  region:       {d.region}")
    if d.applications:
        print(f"  applications: {', '.join(d.applications)}")
    print(f"  meshes ({len(d.meshes)}):")
    for m in d.meshes:
        size = f"{m.size_mb:6.2f} MB"
        print(f"    - {m.id:<25} {size}  {m.filename}")
    return 0


def cmd_show_mesh(args: argparse.Namespace) -> int:
    try:
        mesh = get_mesh(args.id)
    except KeyError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"Mesh: {mesh.full_id}")
    for k, v in mesh.to_dict().items():
        print(f"  {k:<18} {v}")
    if mesh.path is not None:
        status = "exists" if mesh.exists() else "missing"
        print(f"  {'path':<18} {mesh.path} ({status})")
    return 0


def cmd_regions(_args: argparse.Namespace) -> int:
    for r in list_regions():
        print(r)
    return 0


def cmd_applications(_args: argparse.Namespace) -> int:
    for a in list_applications():
        print(a)
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    """Publish the bundled manifest to HuggingFace Datasets."""
    try:
        from .publisher import (
            publish, PublisherError, PublishTokenError,
            PublishValidationError, DEFAULT_HF_REPO,
        )
    except ImportError as e:
        print(f"ERROR: publisher unavailable: {e}", file=sys.stderr)
        print("Install with: pip install admesh-domains[publish]", file=sys.stderr)
        return 1

    try:
        manifest = load_manifest(Path(args.manifest) if args.manifest else None)
    except (ManifestNotFoundError, ManifestValidationError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    tag = args.tag
    if not tag:
        from datetime import datetime, timezone
        tag = f"data-{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S')}"
        print(f"(no --tag provided; using data-only tag: {tag})")

    repo = args.repo or DEFAULT_HF_REPO
    try:
        result = publish(
            manifest=manifest,
            tag=tag,
            hf_repo=repo,
            dry_run=args.dry_run,
        )
    except (PublishTokenError, PublishValidationError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except PublisherError as e:
        print(f"PUBLISH FAILED: {e}", file=sys.stderr)
        return 2

    print(result.summary())
    if args.verbose:
        for hp in result.uploaded:
            print(f"  + {hp}")
        for hp in result.skipped:
            print(f"  = {hp}")
        for hp in result.deleted:
            print(f"  - {hp}")
    if result.commit_sha:
        print(f"  commit: {result.commit_sha}")
        print(f"  view:   https://huggingface.co/datasets/{repo}/tree/{tag}")
    return 0


def cmd_domain_suggest(args: argparse.Namespace) -> int:
    """Suggest the best Domain for a candidate mesh file."""
    from .geometry import (
        bbox_from_mesh_file, suggest_domain, CONFIDENT_THRESHOLD,
    )
    import json as _json

    path = Path(args.path)
    if not path.exists():
        print(f"ERROR: mesh file not found: {path}", file=sys.stderr)
        return 3

    bb = bbox_from_mesh_file(path)
    if bb is None:
        print(f"ERROR: could not parse mesh file: {path}", file=sys.stderr)
        return 3

    manifest = load_manifest(Path(args.manifest) if args.manifest else None)
    scores = suggest_domain(bb, manifest)

    confident = [s for s in scores if s.confidence == "confident"]
    exit_code = 0 if len(confident) == 1 else (2 if len(confident) > 1 else 1)

    if args.json:
        out = {
            "path": str(path),
            "bbox": [bb.min_lon, bb.min_lat, bb.max_lon, bb.max_lat],
            "candidates": [s.to_dict() for s in scores],
            "exit_code": exit_code,
        }
        print(_json.dumps(out, indent=2))
        return exit_code

    use_color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    GREEN = "\033[32m" if use_color else ""
    YELLOW = "\033[33m" if use_color else ""
    GRAY = "\033[90m" if use_color else ""
    RESET = "\033[0m" if use_color else ""

    print(
        f"Suggestions for {path.name} "
        f"(bbox: {bb.min_lon:.2f}, {bb.min_lat:.2f}, {bb.max_lon:.2f}, {bb.max_lat:.2f}):"
    )
    if not scores:
        print("  (no Domains have geographic-bbox meshes; cannot rank)")
    for i, s in enumerate(scores[:10], 1):
        color = (
            GREEN if s.confidence == "confident"
            else YELLOW if s.confidence == "uncertain"
            else GRAY
        )
        print(
            f"  {i}. {color}{s.domain_name:20}{RESET}  "
            f"per_mesh IoU={s.per_mesh_iou:.3f}  union IoU={s.union_iou:.3f}  "
            f"({s.confidence})"
        )

    is_no_match = not scores or scores[0].per_mesh_iou < CONFIDENT_THRESHOLD
    if is_no_match:
        # Fall to interactive prompt unless --non-interactive or stdin not a tty.
        non_interactive = args.non_interactive or not sys.stdin.isatty()
        print()
        if non_interactive:
            print(_render_new_domain_stub(path, bb, interactive=False))
        else:
            try:
                stub = _interactive_new_domain_prompt(path, bb)
                print()
                print(stub)
            except (EOFError, KeyboardInterrupt):
                print("\n(interrupted)")
                return exit_code
    return exit_code


def _render_new_domain_stub(path: Path, bb, *, interactive: bool, answers: dict | None = None) -> str:
    a = answers or {}
    name = a.get("name", "<TBD>")
    full_name = a.get("full_name", "<TBD>")
    category = a.get("category", "real-world")
    region = a.get("region")
    apps = a.get("applications", [])
    apps_repr = "[" + ", ".join(f'"{x}"' for x in apps) + "]" if apps else "[]"

    header = "# Paste this into registry_data/manifest.toml AND admesh_domains/data/manifest.toml"
    lines = [
        header,
        "[[domains]]",
        f'name = "{name}"',
        f'full_name = "{full_name}"',
        f'category = "{category}"',
    ]
    if region:
        lines.append(f'region = "{region}"')
    elif category == "real-world":
        lines.append('region = "<TBD>"')
    lines.append(f"applications = {apps_repr}")
    lines.append("")
    lines.append("[[domains.meshes]]")
    lines.append('id = "default@v1"')
    lines.append(f'filename = "{path.name}"')
    lines.append('license = "MIT"   # or another VALID_LICENSES value')
    lines.append(
        f"bounding_box = {{ min_lon = {bb.min_lon}, min_lat = {bb.min_lat}, "
        f"max_lon = {bb.max_lon}, max_lat = {bb.max_lat} }}"
    )
    lines.append('description = "<TBD>"')
    return "\n".join(lines)


def _interactive_new_domain_prompt(path: Path, bb) -> str:
    print("No confident match. Let's propose a new Domain.")
    name = input("  Domain name (e.g. 'GulfOfMexico'): ").strip() or "<TBD>"
    full_name = input(f"  Full name [{name}]: ").strip() or name
    category = input("  Category (real-world|synthetic) [real-world]: ").strip() or "real-world"
    region = ""
    if category == "real-world":
        region = input("  Region (e.g. 'North America'): ").strip()
    apps_raw = input("  Applications (comma-separated, optional): ").strip()
    apps = [a.strip() for a in apps_raw.split(",") if a.strip()] if apps_raw else []
    return _render_new_domain_stub(
        path, bb, interactive=True,
        answers={"name": name, "full_name": full_name, "category": category,
                 "region": region or None, "applications": apps},
    )


def cmd_domain_audit(args: argparse.Namespace) -> int:
    """Run the suggester against every mesh and report disagreements."""
    from .geometry import suggest_domain
    import json as _json

    manifest = load_manifest()
    disagreements = []
    for d in manifest.domains:
        for mesh in d.meshes:
            if mesh.bounding_box is None:
                continue
            scores = suggest_domain(mesh.bounding_box, manifest)
            if not scores:
                continue
            top = scores[0]
            if top.domain_name != d.name and top.per_mesh_iou >= args.threshold:
                disagreements.append({
                    "mesh": mesh.full_id,
                    "current": d.name,
                    "suggested": top.domain_name,
                    "per_mesh_iou": round(top.per_mesh_iou, 4),
                })
    disagreements.sort(key=lambda x: -x["per_mesh_iou"])

    if args.json:
        print(_json.dumps({"disagreements": disagreements, "count": len(disagreements)}, indent=2))
    else:
        if not disagreements:
            print(f"0 disagreements in {manifest.total_meshes} meshes (threshold={args.threshold}).")
        else:
            print(f"{len(disagreements)} disagreement(s) (threshold={args.threshold}):")
            for d_ in disagreements:
                print(
                    f"  {d_['mesh']:40} current={d_['current']:15} "
                    f"suggested={d_['suggested']:15} IoU={d_['per_mesh_iou']:.3f}"
                )
    return 0 if not disagreements else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="admesh-domains",
        description="ADCIRC mesh registry CLI",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pv = sub.add_parser("validate", help="Validate a manifest file")
    pv.add_argument("path", nargs="?", default=None, help="Path to manifest.toml")
    pv.set_defaults(func=cmd_validate)

    pd = sub.add_parser("domains", help="List domains")
    pd.add_argument("--category")
    pd.add_argument("--region")
    pd.add_argument("--application")
    pd.set_defaults(func=cmd_domains)

    pm = sub.add_parser("meshes", help="List meshes (across all domains)")
    pm.add_argument("--domain")
    pm.add_argument("--contributor")
    pm.add_argument("--type")
    pm.add_argument("--element-type", dest="element_type")
    pm.add_argument("--refinement-level", dest="refinement_level")
    pm.add_argument("--min-size", type=float, dest="min_size")
    pm.add_argument("--max-size", type=float, dest="max_size")
    pm.add_argument("--min-nodes", type=int, dest="min_nodes")
    pm.set_defaults(func=cmd_meshes)

    psd = sub.add_parser("show-domain", help="Show details for one domain")
    psd.add_argument("name")
    psd.set_defaults(func=cmd_show_domain)

    psm = sub.add_parser("show-mesh", help="Show details for one mesh (e.g. 'WNAT/hagen@v1')")
    psm.add_argument("id")
    psm.set_defaults(func=cmd_show_mesh)

    pr = sub.add_parser("regions", help="List unique regions")
    pr.set_defaults(func=cmd_regions)

    pa = sub.add_parser("applications", help="List unique applications")
    pa.set_defaults(func=cmd_applications)

    pp = sub.add_parser("publish", help="Publish the registry to HuggingFace Datasets")
    pp.add_argument(
        "--tag",
        default=None,
        help=(
            "Release tag. Use 'vX.Y.Z' for code releases (paired with PyPI), or omit "
            "for a data-only update (defaults to 'data-YYYY-MM-DD-HHMMSS')."
        ),
    )
    pp.add_argument("--repo", default=None, help="HF dataset slug (default: DEFAULT_HF_REPO)")
    pp.add_argument("--manifest", default=None, help="Manifest path (default: bundled)")
    pp.add_argument("--dry-run", action="store_true", help="Print plan only; do not write to HF")
    pp.add_argument("-v", "--verbose", action="store_true", help="Print per-file actions")
    pp.set_defaults(func=cmd_publish)

    # 'domain' command group (verb-noun grouping per spec 007 C-9).
    pdom = sub.add_parser(
        "domain",
        help="Domain operations: suggest, audit, list",
    )
    dom_sub = pdom.add_subparsers(dest="domain_command", required=True)

    pds = dom_sub.add_parser(
        "suggest",
        help="Suggest the best Domain for a candidate mesh file",
    )
    pds.add_argument("path", help="Path to a fort.14 / .grd / .2dm mesh file")
    pds.add_argument("--manifest", default=None, help="Manifest path (default: bundled)")
    pds.add_argument("--json", action="store_true", help="Emit JSON output")
    pds.add_argument(
        "--non-interactive", action="store_true",
        help="Skip the new-Domain prompt; print TOML stub with <TBD> placeholders",
    )
    pds.set_defaults(func=cmd_domain_suggest)

    pda = dom_sub.add_parser(
        "audit",
        help="Run suggester against every mesh; report disagreements with current Domain assignment",
    )
    pda.add_argument(
        "--threshold", type=float, default=UNCERTAIN_THRESHOLD_DEFAULT,
        help="Minimum per-mesh IoU to count as a real disagreement (default 0.05)",
    )
    pda.add_argument("--json", action="store_true", help="Emit JSON output")
    pda.set_defaults(func=cmd_domain_audit)

    pdl = dom_sub.add_parser(
        "list",
        help="List domains (alias for the top-level 'domains' command)",
    )
    pdl.add_argument("--category")
    pdl.add_argument("--region")
    pdl.add_argument("--application")
    pdl.set_defaults(func=cmd_domains)

    return p


# Default threshold for `domain audit` matches the suggester's "uncertain" floor.
UNCERTAIN_THRESHOLD_DEFAULT = 0.05


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
