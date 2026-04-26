"""Command-line interface for admesh-domains."""

from __future__ import annotations

import argparse
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

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
