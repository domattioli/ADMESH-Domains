#!/usr/bin/env python3
"""Publish Release CLI - Automated GitHub release + PyPI publishing

This script orchestrates the full release workflow:
1. Validates prerequisites (gh, twine, git state, dist packages)
2. Creates GitHub release with release notes from CHANGELOG.md
3. Uploads to PyPI
4. Reports final URLs and success status

Usage:
    python scripts/publish_release.py                    # Auto-detect version
    python scripts/publish_release.py 0.3.4              # Explicit version
    python scripts/publish_release.py 0.3.4 --draft      # Draft release
    python scripts/publish_release.py 0.3.4 --no-pypi    # GitHub only
    python scripts/publish_release.py --help             # Show options
"""

import sys
import subprocess
import re
from pathlib import Path
import argparse
from typing import Tuple, Optional

# Colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def log(msg: str) -> None:
    print(f"{BLUE}→{NC} {msg}")

def success(msg: str) -> None:
    print(f"{GREEN}✓{NC} {msg}")

def error(msg: str) -> None:
    print(f"{RED}✗{NC} {msg}", file=sys.stderr)

def warn(msg: str) -> None:
    print(f"{YELLOW}⚠{NC} {msg}")

def run(cmd: list, check: bool = True) -> Tuple[int, str, str]:
    """Run command and return (exit_code, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"

def detect_version() -> Optional[str]:
    """Auto-detect version from pyproject.toml"""
    try:
        with open("pyproject.toml") as f:
            for line in f:
                if line.startswith("version = "):
                    match = re.search(r'version = "([^"]+)"', line)
                    if match:
                        return match.group(1)
        return None
    except FileNotFoundError:
        return None

def validate_version(version: str) -> bool:
    """Validate semantic version format X.Y.Z"""
    return bool(re.match(r'^\d+\.\d+\.\d+$', version))

def validate_prerequisites(skip_pypi: bool = False) -> bool:
    """Validate all prerequisites before release"""
    log("Validating prerequisites...")

    # Check gh CLI
    code, _, _ = run(["gh", "--version"])
    if code != 0:
        error("gh CLI not found. Install with: https://cli.github.com")
        return False
    success("gh CLI found")

    # Check gh auth
    code, _, _ = run(["gh", "auth", "status"])
    if code != 0:
        error("gh CLI not authenticated. Run: gh auth login")
        return False
    success("gh CLI authenticated")

    # Check git
    code, _, _ = run(["git", "rev-parse", "--is-inside-work-tree"])
    if code != 0:
        error("Not in a git repository")
        return False

    # Check working directory
    code, out, _ = run(["git", "diff-index", "--quiet", "HEAD", "--"])
    if code != 0:
        error("Working directory has uncommitted changes")
        return False
    success("Git working directory clean")

    # Check twine if PyPI upload enabled
    if not skip_pypi:
        code, _, _ = run(["twine", "--version"])
        if code != 0:
            error("twine not found. Install with: pip install twine")
            return False
        success("twine found")

        # Check dist packages
        dist_path = Path("dist")
        packages = list(dist_path.glob("*.whl")) + list(dist_path.glob("*.tar.gz"))
        if not packages:
            error("No distribution packages found in dist/")
            error("Build packages with: python -m build")
            return False
        success(f"Distribution packages found ({len(packages)} files)")

    return True

def call_bash_script(args: argparse.Namespace) -> int:
    """Delegate to bash script for actual release"""
    script_path = Path(__file__).parent / "publish-release.sh"

    cmd = [str(script_path)]
    if args.version:
        cmd.append(args.version)
    if args.no_pypi:
        cmd.append("--no-pypi")
    if args.draft:
        cmd.append("--draft")
    if args.repo:
        cmd.append("--repo")
        cmd.append(args.repo)
    if args.notes:
        cmd.append("--notes")
        cmd.append(args.notes)
    if args.dry_run:
        cmd.append("--dry-run")

    code, stdout, stderr = run(cmd, check=False)

    # Print output
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)

    return code

def main():
    parser = argparse.ArgumentParser(
        description="Publish release to GitHub and PyPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                         Auto-detect version, full release
  %(prog)s 0.3.4                   Explicit version
  %(prog)s 0.3.4 --draft           Draft release on GitHub
  %(prog)s 0.3.4 --no-pypi         GitHub release only (skip PyPI)
  %(prog)s 0.3.4 --dry-run         Show what would happen (no changes)
        """
    )

    parser.add_argument(
        "version",
        nargs="?",
        help="Release version (X.Y.Z format). Auto-detect from pyproject.toml if omitted"
    )
    parser.add_argument(
        "--no-pypi",
        action="store_true",
        help="Skip PyPI upload (GitHub release only)"
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Create GitHub release as draft"
    )
    parser.add_argument(
        "--repo",
        help="Override GitHub repository (owner/name)"
    )
    parser.add_argument(
        "--notes",
        help="Override release notes file path"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes"
    )

    args = parser.parse_args()

    # Auto-detect version if not provided
    if not args.version:
        log("Auto-detecting version from pyproject.toml...")
        args.version = detect_version()
        if not args.version:
            error("Could not detect version from pyproject.toml")
            error("Specify version explicitly: publish-release 0.3.4")
            return 1
        success(f"Version: {args.version}")

    # Validate version format
    if not validate_version(args.version):
        error(f"Invalid version format: {args.version} (expected X.Y.Z)")
        return 1

    # Validate prerequisites
    if not validate_prerequisites(skip_pypi=args.no_pypi):
        return 1

    print("")

    # Call bash script
    return call_bash_script(args)

if __name__ == "__main__":
    sys.exit(main())
