# Publish-Release Skill

Automated GitHub release creation + PyPI publishing with full validation and error handling.

## Features

✅ **Auto-detect version** from `pyproject.toml`  
✅ **Extract release notes** from `CHANGELOG.md` (or custom source)  
✅ **Validate prerequisites** (gh, twine, git state, dist packages)  
✅ **Create GitHub release** with assets  
✅ **Upload to PyPI** with twine  
✅ **Graceful error handling** with helpful messages  
✅ **Dry-run support** (--dry-run shows what would happen)  
✅ **Report final URLs** (GitHub release + PyPI)

## Installation

The script is included in `scripts/`. Make it executable:

```bash
chmod +x scripts/publish-release.sh scripts/publish_release.py
```

## Usage

### Python CLI (recommended)

```bash
# Auto-detect version, full release
python scripts/publish_release.py

# Explicit version
python scripts/publish_release.py 0.3.4

# Draft release (GitHub only)
python scripts/publish_release.py 0.3.4 --draft

# Skip PyPI (GitHub release only)
python scripts/publish_release.py 0.3.4 --no-pypi

# Dry run (preview without changes)
python scripts/publish_release.py 0.3.4 --dry-run

# Custom release notes
python scripts/publish_release.py 0.3.4 --notes path/to/notes.md

# Override repo
python scripts/publish_release.py 0.3.4 --repo owner/repo
```

### Bash Script (direct)

```bash
scripts/publish-release.sh
scripts/publish-release.sh 0.3.4
scripts/publish-release.sh 0.3.4 --draft --no-pypi
```

## Workflow

### 1. **Validation Phase**

Checks before any changes:

- `gh` CLI installed and authenticated
- `twine` installed (if --no-pypi not set)
- Git working directory clean (no uncommitted changes)
- Tag doesn't already exist
- Distribution packages exist in `dist/` (if --no-pypi not set)
- Version format is valid (X.Y.Z)

### 2. **Release Notes Extraction**

Looks for release notes in this order:

1. `--notes FILE` (if provided)
2. `CHANGELOG.md` section for version `## [X.Y.Z]`
3. Fallback: "Release version X.Y.Z"

### 3. **GitHub Release**

Creates release with:
- Tag: `vX.Y.Z`
- Title: "Release X.Y.Z"
- Notes: Extracted from CHANGELOG
- Assets: Distribution packages (if available)
- Draft: Yes (if `--draft` set)

### 4. **PyPI Upload**

Uploads with:
- `twine upload dist/*.{whl,tar.gz}`
- `--skip-existing` to handle retry safely

### 5. **Success Report**

Reports:
- GitHub release URL
- PyPI package URL
- Installation command for users

## Error Handling

### gh CLI not found

```
Error: gh CLI not found. Install with: https://cli.github.com
```

**Fix:** Install GitHub CLI, then authenticate:
```bash
gh auth login
```

### twine not found

```
Error: twine not found. Install with: pip install twine
```

**Fix:**
```bash
pip install twine
```

### No distribution packages

```
Error: No distribution packages found in dist/
Build packages with: python -m build
```

**Fix:**
```bash
python -m build
python scripts/publish_release.py 0.3.4
```

### Working directory has uncommitted changes

```
Error: Working directory has uncommitted changes
Commit or stash changes before releasing
```

**Fix:**
```bash
git add -A
git commit -m "Release 0.3.4"
git push origin main
python scripts/publish_release.py 0.3.4
```

### PyPI authentication

If PyPI upload fails due to missing credentials:

```bash
python -m twine upload --help
# Check ~/.pypirc or use token-based auth
```

## Dry Run

Preview release without making changes:

```bash
python scripts/publish_release.py 0.3.4 --dry-run
```

Output shows:
- Validation steps
- What would be created/uploaded
- Final URLs (previewed)

**No actual changes** are made (no tags, commits, or uploads).

## Release Tracks

### Code Track (Full Release)

For code, API, schema, or publisher changes:

```bash
# 1. Update version in pyproject.toml + admesh_domains/__init__.py
# 2. Build packages
python -m build

# 3. Release to PyPI + GitHub
python scripts/publish_release.py

# Result:
# - PyPI: pip install admesh-domains==0.3.4
# - GitHub: v0.3.4 tag + release with assets
# - HF: Tagged v0.3.4 (via release.yml workflow)
```

### Data Track (HF Only)

For mesh additions/removals/metadata edits:

```bash
# Skip PyPI, push to main directly
git add registry_data/manifest.toml
git commit -m "Add foo.14 to Domain"
git push origin main

# Result:
# - HF: Tagged data-YYYY-MM-DD-<sha7> (via publish-data.yml workflow)
# - PyPI: Untouched
```

## Integration with CI/CD

### GitHub Actions

Workflows can call the script:

```yaml
- name: Publish release
  if: startsWith(github.ref, 'refs/tags/v')
  run: |
    python -m build
    python scripts/publish_release.py ${{ github.ref#refs/tags/v }}
```

### Claude Code

Use in automated release tasks:

```bash
python scripts/publish_release.py 0.3.4
```

## Troubleshooting

### Release created but PyPI upload failed

Check logs and retry:
```bash
# Verify PyPI credentials
python -m twine upload --help

# Manual upload
python -m twine upload dist/*
```

### GitHub release exists but needs to delete/recreate

```bash
# Delete local tag
git tag -d v0.3.4

# Delete remote tag
git push origin --delete v0.3.4

# Try again
python scripts/publish_release.py 0.3.4
```

### CHANGELOG.md section not found

Ensure section format:
```markdown
## [0.3.4] - 2026-04-27

### Added
- Feature X
- Feature Y

## [0.3.3] - 2026-04-26
...
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Validation failed or release error |
| 127 | Command not found (gh, twine, git) |

## See Also

- `CLAUDE.md` — Release track documentation
- `.github/workflows/release.yml` — PyPI upload workflow
- `.github/workflows/publish-data.yml` — Data publish workflow
- `CHANGELOG.md` — Release notes format
