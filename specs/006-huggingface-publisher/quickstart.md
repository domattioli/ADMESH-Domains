# Quickstart: Releasing the registry

A maintainer-facing recipe for cutting and verifying a new release.

## One-time setup (do once per fork)

1. **Create the HF dataset.**
   - Go to https://huggingface.co/new-dataset
   - Owner: your account; Name: `admesh-domains`; Public; License: leave default.
   - Confirm it exists at `huggingface.co/datasets/<you>/admesh-domains`.

2. **Generate an HF write token.**
   - https://huggingface.co/settings/tokens → "New token"
   - Type: Write (or Fine-grained scoped to the dataset).
   - Copy the `hf_...` value.

3. **Generate a project-scoped PyPI token.**
   - https://pypi.org/manage/account/token/ → "Add API token"
   - Scope: "Project: admesh-domains"
   - Copy the `pypi-...` value.

4. **Add both tokens as repo Actions secrets.**
   - Repo → Settings → Secrets and variables → **Actions** → New repository secret
   - Names: `HF_TOKEN`, `PYPI_API_TOKEN`

5. **Update `DEFAULT_HF_REPO`** in `admesh_domains/publisher.py` if your slug isn't `domattioli/admesh-domains`.

## Cutting a release

```bash
# Confirm clean working tree, on main, fully synced
git status
git pull origin main

# Bump version in two places
$EDITOR pyproject.toml admesh_domains/__init__.py
# (set both to e.g. 0.2.0)

# Validate the manifest before pushing
admesh-domains validate

# Commit, tag, push
git add pyproject.toml admesh_domains/__init__.py
git commit -m "Bump to 0.2.0"
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

The tag push triggers `.github/workflows/release.yml`. Watch progress at:
https://github.com/<you>/ADMESH-Domains/actions

Expected run time: ≤ 5 minutes (mostly mesh upload).

## Verifying the release

After the workflow goes green:

- **PyPI**: https://pypi.org/project/admesh-domains/0.2.0/ — wheel + sdist visible.
- **HF dataset**:
  - https://huggingface.co/datasets/<you>/admesh-domains/tree/v0.2.0 — every mesh under `meshes/<domain>/<filename>`.
  - https://huggingface.co/datasets/<you>/admesh-domains — dataset card renders with current totals.
  - https://huggingface.co/datasets/<you>/admesh-domains/tree/main — points at the new `v0.2.0` revision.
- **Local round-trip** from a clean machine:
  ```bash
  pip install admesh-domains[hf]
  python -c "
  from admesh_domains import get_mesh
  m = get_mesh('WNAT/hagen@v1')
  p = m.load()
  print('downloaded to:', p)
  "
  ```

## Manual ops (no tag)

To publish without cutting a PyPI release (e.g. fixing a dataset-card typo):

```bash
pip install -e ".[publish]"
export HF_TOKEN=hf_...
admesh-domains publish --tag v0.2.0 --dry-run    # see plan first
admesh-domains publish --tag v0.2.0              # actually publish
```

## Rollback

PyPI versions are immutable. To "undo" a bad release:

1. Yank from PyPI: https://pypi.org/manage/project/admesh-domains/release/0.2.0/ → "Yank".
2. On HF: revert main to the prior revision via `huggingface_hub` CLI:
   ```bash
   huggingface-cli repo-files --repo-type dataset <you>/admesh-domains revert v0.1.1
   ```
   (Or use the HF web UI to delete the bad tag.)
3. Cut a fixed `v0.2.1` and re-run the flow.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Workflow fails at `twine check` | Built sdist/wheel has bad metadata | Run `python -m build` locally and inspect |
| `403 Forbidden` from HF | Token lacks write to target dataset | Regenerate token with broader scope, update secret |
| `400 Bad Request: file too large` from HF | Mesh > HF per-file limit (~50 GB; LFS handles up to ~100 GB) | Move giant meshes to a separate LFS-backed dataset, link from manifest |
| Tag push doesn't trigger workflow | Tag doesn't match `v[0-9]+.[0-9]+.[0-9]+` | Use strict semver — no pre-release suffixes |
| `Mesh.load()` returns stale file | HF cache is stale | Delete `~/.cache/huggingface/hub/datasets--<you>--admesh-domains/` and retry |
