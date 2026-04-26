#!/usr/bin/env python3
"""Import and consolidate mesh data from multiple sources."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


def calculate_checksum(filepath: Path) -> str:
    """Calculate MD5 checksum of a file."""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5.update(chunk)
    return md5.hexdigest()


def scan_directory(directory: Path) -> Dict[str, Path]:
    """Scan directory for mesh files."""
    meshes = {}
    for ext in ['*.14', '*.2dm', '*.fort.14']:
        for mesh_file in directory.glob(f'**/{ext}'):
            name = mesh_file.name
            if name not in meshes:
                meshes[name] = mesh_file
    return meshes


def consolidate_meshes(source_dirs: List[Path], output_dir: Path) -> Dict[str, Dict]:
    """
    Consolidate meshes from multiple sources, deduplicating by content.

    Returns dict mapping filename to metadata including checksum and sources.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Map checksum -> (filename, paths)
    checksums: Dict[str, Tuple[str, List[Path]]] = {}
    filename_sources: Dict[str, List[str]] = defaultdict(list)

    print("Scanning source directories...")
    for source_dir in source_dirs:
        print(f"  {source_dir.name}...")
        meshes = scan_directory(source_dir)

        for filename, filepath in meshes.items():
            checksum = calculate_checksum(filepath)
            source_name = source_dir.name

            if checksum not in checksums:
                checksums[checksum] = (filename, [])

            checksums[checksum][1].append(filepath)
            filename_sources[filename].append(source_name)

    # Copy unique files and build metadata
    metadata = {}
    copied_count = 0

    print(f"\nFound {len(checksums)} unique mesh files (by content)")
    print("Copying files to registry_data...\n")

    for checksum, (canonical_name, source_paths) in sorted(checksums.items()):
        source_file = source_paths[0]
        dest_file = output_dir / canonical_name

        # Copy file
        shutil.copy2(source_file, dest_file)
        copied_count += 1

        # Get file size
        size = source_file.stat().st_size

        # Track metadata
        metadata[canonical_name] = {
            'checksum': checksum,
            'size': size,
            'size_mb': round(size / (1024 * 1024), 2),
            'sources': list(set(
                source.name for source_paths_list in
                [source_paths] for source in source_paths_list
            )),
            'source_paths': [str(p.relative_to(p.parent.parent.parent))
                            for p in source_paths],
            'duplicates': [
                name for name, srcs in filename_sources.items()
                if name != canonical_name and
                any(src in srcs for src in [p.parent.parent.name for p in source_paths])
            ]
        }

        print(f"  {canonical_name:50} {metadata[canonical_name]['size_mb']:8.2f} MB")

    return metadata, copied_count


def main():
    """Main import function."""
    repo_dir = Path(__file__).parent.parent
    registry_data = repo_dir / 'registry_data'
    meshes_dir = registry_data / 'meshes'

    # Source directories
    sources = [
        Path('/tmp/CHILmesh/src/chilmesh/data'),
        Path('/tmp/QuADMesh-MATLAB/03_CHILMesh_Test_Cases/01_.14_Files'),
        Path('/tmp/chil_mesh/data/01_.14_Files'),
    ]

    print("=" * 70)
    print("MESH CONSOLIDATION AND IMPORT")
    print("=" * 70 + "\n")

    # Consolidate meshes
    metadata, count = consolidate_meshes(sources, meshes_dir)

    print(f"\n✓ Copied {count} unique mesh files")
    print(f"✓ Total size: {sum(m['size'] for m in metadata.values()) / (1024**2):.1f} MB")

    # Save metadata
    metadata_file = registry_data / 'meshes_metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"\n✓ Saved metadata to {metadata_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY BY MESH")
    print("=" * 70)
    for name in sorted(metadata.keys()):
        m = metadata[name]
        sources_str = ', '.join(m['sources'])
        print(f"\n{name}")
        print(f"  Size: {m['size_mb']} MB")
        print(f"  Checksum: {m['checksum'][:12]}...")
        print(f"  Found in: {sources_str}")
        if m['duplicates']:
            print(f"  Filename variants: {', '.join(m['duplicates'])}")


if __name__ == '__main__':
    main()
