# ADMESH Domains

A Python package for managing and validating ADCIRC mesh registry data. This project provides tools for domain management, mesh validation, and registry operations for coastal simulation models.

## Features

- **Registry Management**: Query and manage mesh registry data
- **Schema Validation**: Validate mesh data against defined schemas
- **Lineage Tracking**: Track mesh evolution and dependencies
- **Publishing**: Publish meshes to external repositories
- **CLI Tools**: Command-line interface for common operations

## Installation

```bash
pip install admesh-domains
```

## Quick Start

```python
from admesh_domains import query, validator

# Query registry
meshes = query.get_meshes()

# Validate mesh data
validator.validate(mesh_data)
```

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
