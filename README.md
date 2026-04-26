# ADMESH Domains

A Python package for managing and validating ADCIRC mesh registry data. This project provides tools for domain management, mesh validation, and registry operations for coastal simulation models.

## Features

- **40 Consolidated Mesh Domains**: Real-world and synthetic ADCIRC meshes
- **Registry Management**: Query and manage mesh registry data
- **Schema Validation**: Validate mesh data against defined schemas
- **Lineage Tracking**: Track mesh evolution and dependencies
- **Publishing**: Publish meshes to external repositories
- **CLI Tools**: Command-line interface for common operations

## Mesh Registry

The registry contains **40 unique mesh domains** consolidated from multiple sources:

### Real-World Domains (12)
- **Great Lakes** (15.16 MB) - Great Lakes region mesh
- **Western North Atlantic** (15.32 MB) - WNAT_Onur variant for hurricane/storm surge
- **Chesapeake Bay** (9.47 MB) - Chesapeake Bay region coastal mesh
- **WNAT_Hagen** (5.48 MB) - Alternative Western North Atlantic mesh (53K nodes)
- **Lake Michigan** (2.47 MB) - Lake Michigan circulation mesh
- **Italy** (1.45 MB) - Mediterranean coast mesh
- **Lake Erie** (1.57 MB) - Lake Erie mesh (5k nodes variant)
- **Delaware Bay** (1.72 MB) - Delaware Bay coastal mesh
- **Delaware Bay (Refined)** (1.72 MB) - High-resolution variant (hmin=100, hmax=20000)
- **Lake Erie (Refined)** (0.57 MB) - Medium-resolution variant
- **Baranja Hill** (0.08 MB) - European region mesh
- **Baranja Hill v2** (0.09 MB) - ADMESH v2 variant

### Test & Synthetic Domains (28)
- 6 numbered test cases (Test_Case_1 through Test_Case_4.2)
- 10 structured mesh variants
- 12 rectangular and geometric test meshes
- Various element types (triangles, quadrilaterals)

**Total Data**: 59 MB of mesh data  
**Sources**: Consolidated from CHILmesh, QuADMesh-MATLAB, and chil_mesh repositories  
**Format**: ADCIRC-format (.14 and .2dm files)

See [registry_data/manifest.toml](registry_data/manifest.toml) for complete domain metadata.

## Installation

```bash
# Base install — query the bundled manifest, no mesh downloads
pip install admesh-domains

# With HuggingFace runtime download for Mesh.load()
pip install admesh-domains[hf]

# Maintainer-only: includes pyarrow, jinja2, twine for publishing
pip install admesh-domains[publish]
```

## Quick Start

```python
from admesh_domains import find_domains, find_meshes, get_mesh

# Find all real-world domains
for d in find_domains(category="real-world"):
    print(d.name, "->", len(d.meshes), "meshes")

# Look up a specific mesh by composite ID
mesh = get_mesh("WNAT/hagen@v1")
print(mesh.full_id, mesh.size_mb, "MB")

# Download the actual mesh file from the HuggingFace mirror
local_path = mesh.load()   # requires pip install admesh-domains[hf]
```

## HuggingFace Mirror

All 40 meshes (~59 MB) are mirrored to a HuggingFace Dataset and downloaded
on demand via `Mesh.load()`. Browse it directly at:

**https://huggingface.co/datasets/domattioli/ADMESH-Domains**

The `manifest.parquet` sidecar at the dataset root lets you query metadata
without the Python loader.

## Documentation

See [docs/](docs/) for detailed documentation and guides.

## Development

### Setup

```bash
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
black admesh_domains/
ruff check admesh_domains/
mypy admesh_domains/
```

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details

## Citation

If you use this package in research, please cite it appropriately.

## Status

**Version**: 0.1.0 (MVP)  
**Status**: Alpha - API subject to change

## Repository

- **Source**: https://github.com/domattioli/ADMESH-Domains
- **Issues**: https://github.com/domattioli/ADMESH-Domains/issues
