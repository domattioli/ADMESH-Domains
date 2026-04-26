"""Tests for admesh_domains.publisher — sha256, sidecar, card, publish dry-run."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from admesh_domains import load_manifest
from admesh_domains.publisher import (
    DEFAULT_HF_REPO,
    PublishResult,
    PublishTokenError,
    PublishValidationError,
    PublisherError,
    build_parquet_sidecar,
    compute_sha256,
    fetch_prior_hashes,
    hf_path_for,
    publish,
    render_dataset_card,
)


class TestComputeSha256:
    def test_matches_known_hash(self, tmp_path: Path):
        f = tmp_path / "x.txt"
        f.write_bytes(b"hello world")
        # echo -n "hello world" | shasum -a 256
        assert compute_sha256(f) == (
            "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
        )

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            compute_sha256(tmp_path / "no-such-file")


class TestHfPathFor:
    def test_uses_domain_and_filename(self, loaded_manifest):
        wnat_hagen = next(
            m for m in loaded_manifest.all_meshes() if m.id == "hagen@v1"
        )
        assert hf_path_for(wnat_hagen) == "meshes/WNAT/WNAT_Hagen.14"


class TestBuildParquetSidecar:
    def test_writes_one_row_per_mesh(self, loaded_manifest):
        hashes = {
            hf_path_for(m): "deadbeef" * 8 for m in loaded_manifest.all_meshes()
        }
        blob = build_parquet_sidecar(loaded_manifest, hashes, tag="v1.2.3")
        assert isinstance(blob, bytes)
        assert len(blob) > 0

        import pyarrow.parquet as pq
        table = pq.read_table(io.BytesIO(blob))
        assert table.num_rows == loaded_manifest.total_meshes

    def test_includes_bbox_columns(self, loaded_manifest):
        hashes = {hf_path_for(m): "x" * 64 for m in loaded_manifest.all_meshes()}
        blob = build_parquet_sidecar(loaded_manifest, hashes, tag="v0.0.0")

        import pyarrow.parquet as pq
        table = pq.read_table(io.BytesIO(blob))
        for col in ("bbox_min_lon", "bbox_min_lat", "bbox_max_lon", "bbox_max_lat"):
            assert col in table.schema.names

    def test_includes_license_columns(self, loaded_manifest):
        hashes = {hf_path_for(m): "x" * 64 for m in loaded_manifest.all_meshes()}
        blob = build_parquet_sidecar(loaded_manifest, hashes, tag="v0.0.0")

        import pyarrow.parquet as pq
        table = pq.read_table(io.BytesIO(blob))
        assert "license" in table.schema.names
        assert "mirror_eligible" in table.schema.names
        # All current meshes are MIT and mirror-eligible
        licenses = set(table["license"].to_pylist())
        assert licenses == {"MIT"}
        assert all(table["mirror_eligible"].to_pylist())

    def test_metadata_includes_tag_and_schema(self, loaded_manifest):
        hashes = {hf_path_for(m): "x" * 64 for m in loaded_manifest.all_meshes()}
        blob = build_parquet_sidecar(loaded_manifest, hashes, tag="v9.9.9")

        import pyarrow.parquet as pq
        table = pq.read_table(io.BytesIO(blob))
        meta = table.schema.metadata
        assert meta is not None
        assert meta[b"admesh_publish_tag"] == b"v9.9.9"
        assert meta[b"admesh_schema_version"] == b"0.2"


class TestRenderDatasetCard:
    def test_includes_totals(self, loaded_manifest):
        out = render_dataset_card(loaded_manifest, tag="v1.0.0")
        assert "v1.0.0" in out
        assert str(loaded_manifest.total_meshes) in out
        assert "ADMESH Domains" in out

    def test_no_attribution_text(self, loaded_manifest):
        """Regression: 'sourced from public GitHub repositories' was scrubbed."""
        out = render_dataset_card(loaded_manifest, tag="v1.0.0")
        assert "CHILmesh" not in out
        assert "QuADMesh-MATLAB" not in out
        assert "chil_mesh" not in out
        assert "sourced from public" not in out

    def test_includes_quickstart_code(self, loaded_manifest):
        out = render_dataset_card(loaded_manifest, tag="v1.0.0")
        assert "pip install admesh-domains" in out
        assert "from admesh_domains import" in out


class TestPublishDryRun:
    def test_dry_run_no_token_required(self, loaded_manifest, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        # First publish: prior dict is empty -> all meshes uploaded.
        with patch("admesh_domains.publisher.fetch_prior_hashes", return_value={}):
            result = publish(
                loaded_manifest, tag="v0.0.1-test", dry_run=True
            )
        assert isinstance(result, PublishResult)
        assert result.dry_run is True
        assert result.commit_sha is None
        assert len(result.uploaded) == loaded_manifest.total_meshes
        assert len(result.skipped) == 0

    def test_dry_run_dedups_against_prior(self, loaded_manifest):
        first_mesh = next(loaded_manifest.all_meshes())
        # Compute the actual hash so dedup picks it up.
        hp = hf_path_for(first_mesh)
        prior = {hp: compute_sha256(first_mesh.path)}
        with patch("admesh_domains.publisher.fetch_prior_hashes", return_value=prior):
            result = publish(
                loaded_manifest, tag="v0.0.0-test", dry_run=True, token="dummy"
            )
        assert hp in result.skipped
        assert hp not in result.uploaded

    def test_dry_run_detects_stale_files_for_deletion(self, loaded_manifest):
        prior = {"meshes/Old/Removed.14": "x" * 64}
        with patch("admesh_domains.publisher.fetch_prior_hashes", return_value=prior):
            result = publish(
                loaded_manifest, tag="v0.0.0-test", dry_run=True, token="dummy"
            )
        assert "meshes/Old/Removed.14" in result.deleted


class TestPublishErrors:
    def test_real_publish_without_token_raises(self, loaded_manifest, monkeypatch):
        monkeypatch.delenv("HF_TOKEN", raising=False)
        with pytest.raises(PublishTokenError):
            publish(loaded_manifest, tag="v1.0.0", dry_run=False)

    def test_missing_mesh_files_raise_validation_error(
        self, dev_manifest_path: Path, tmp_path: Path
    ):
        """Manifest validates locally but no files exist where it expects."""
        # Move the meshes dir away temporarily
        import shutil
        src_text = dev_manifest_path.read_text()
        new_manifest = tmp_path / "manifest.toml"
        new_manifest.write_text(src_text)
        # Don't copy the meshes dir → all paths missing
        m = load_manifest(new_manifest)
        with pytest.raises(PublishValidationError):
            publish(m, tag="v1.0.0", dry_run=True, token="dummy")


def _make_hf_error(exc_cls):
    """Construct an HF error across huggingface_hub versions.

    Older versions: ``cls(message)`` works. Newer versions require ``response=``
    as a keyword-only argument.
    """
    response = MagicMock()
    response.status_code = 404
    response.headers = {}
    try:
        return exc_cls("not found", response=response)
    except TypeError:
        return exc_cls("not found")


class TestFetchPriorHashes:
    def test_returns_empty_on_404(self):
        from huggingface_hub.errors import EntryNotFoundError
        mock = MagicMock(side_effect=_make_hf_error(EntryNotFoundError))
        with patch("huggingface_hub.hf_hub_download", mock):
            assert fetch_prior_hashes("foo/bar", token="x") == {}

    def test_returns_empty_on_repo_404(self):
        from huggingface_hub.errors import RepositoryNotFoundError
        mock = MagicMock(side_effect=_make_hf_error(RepositoryNotFoundError))
        with patch("huggingface_hub.hf_hub_download", mock):
            assert fetch_prior_hashes("foo/bar", token="x") == {}

    def test_returns_empty_on_other_errors(self):
        """Any unexpected failure should fall through to empty (first-publish behavior)."""
        mock = MagicMock(side_effect=RuntimeError("network broke"))
        with patch("huggingface_hub.hf_hub_download", mock):
            assert fetch_prior_hashes("foo/bar", token="x") == {}
