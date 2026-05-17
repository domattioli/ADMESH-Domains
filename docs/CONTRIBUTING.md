# Contributing to ADMESH-Domains

Short reference for anyone working on this repo. The authoritative rules
live in `.specify/memory/constitution.md` (seven principles) — this file
covers day-to-day mechanics.

## Set up a dev environment

```bash
git clone https://github.com/domattioli/ADMESH-Domains.git
cd ADMESH-Domains
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,publish]"
```

`[dev]` ships `pytest`, `pytest-cov`, `black`, `ruff`, `mypy`, `shapely`.
`[publish]` adds `huggingface_hub`, `pyarrow`, `jinja2`, `twine`, `build`,
`matplotlib`. Use both together when running the full suite — three
publisher tests need the publish extras.

## Run the test suite

```bash
pytest tests/ -q                          # full suite
pytest tests/test_public_api.py -v        # one file
pytest tests/ -k "test_get_mesh"          # by keyword
pytest tests/ --cov=admesh_domains        # with coverage (matches CI)
```

Live-manifest dependency: `tests/conftest.py` loads
`registry_data/manifest.toml` directly. Adding/removing meshes can
change a handful of tests' inputs. See `docs/TEST-AUDIT.md` §2.3 [M3]
for the planned decoupling.

## Validate the manifest

```bash
admesh-domains validate                                  # bundled manifest
admesh-domains validate registry_data/manifest.toml      # dev manifest
```

CI runs both — failing either blocks the PR.

## Branch policy

Two long-lived branches only:

- `main` — protected; tags cut from here.
- `daily-issue-fixing` — staging branch where active routine work lands.
  Merges to `main` are explicit, batched, and reviewed.

No long-lived feature branches. Open a focused issue, work on
`daily-issue-fixing`, ship.

## Issue → fix workflow

1. Open an issue with reproduction (`pytest` output, file:line refs).
2. Land the fix as a separate commit referencing the issue.
3. Close the issue with a one-line evidence comment (test run, command
   output, or commit SHA).

## Release tracks

Code and data ship on independent tracks. Code → PyPI tag bump. Data →
HuggingFace dataset tag from `publish-data.yml`. See
`.specify/memory/constitution.md` Principle IV.

## When in doubt

`docs/TEST-AUDIT.md` and `docs/HOOKS-AUDIT.md` are the current snapshot of
what is healthy vs broken. Open issues track every backlog item.
