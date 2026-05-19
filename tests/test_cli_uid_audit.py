"""Tests for `admesh-domains uid-audit` (Issue #65, spec 064 §A)."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from admesh_domains.cli import main


def _make_manifest_with_meshes(root: Path, mesh_files: dict[str, bytes]) -> Path:
    """Create a minimal manifest + mesh files under ``root``.

    Returns the manifest path. ``mesh_files`` maps ``<id>:<filename>`` → bytes.
    """
    meshes_dir = root / "meshes"
    meshes_dir.mkdir(exist_ok=True)
    entries = []
    for key, payload in mesh_files.items():
        mesh_id, filename = key.split(":", 1)
        (meshes_dir / filename).write_bytes(payload)
        entries.append(
            textwrap.dedent(
                f'''
                [[domains.meshes]]
                id = "{mesh_id}"
                filename = "{filename}"
                license = "MIT"
                '''
            ).strip()
        )
    manifest = root / "manifest.toml"
    manifest.write_text(
        textwrap.dedent(
            '''
            [metadata]
            version = "0.3"
            description = "test"

            [[domains]]
            name = "TestDomain"
            category = "synthetic"

            '''
        ).lstrip()
        + "\n\n".join(entries)
        + "\n"
    )
    return manifest


class TestUidAuditRead:
    def test_reports_clean_run_exit_zero(self, tmp_path, capsys):
        manifest = _make_manifest_with_meshes(
            tmp_path,
            {"a@v1:a.14": b"alpha\n", "b@v1:b.14": b"beta\n"},
        )
        rc = main(["uid-audit", str(manifest)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "meshes scanned: 2" in out
        assert "duplicates:     none" in out

    def test_flags_duplicates_exit_one(self, tmp_path, capsys):
        manifest = _make_manifest_with_meshes(
            tmp_path,
            {"a@v1:a.14": b"same\n", "b@v1:b.14": b"same\n"},
        )
        rc = main(["uid-audit", str(manifest)])
        assert rc == 1
        out = capsys.readouterr().out
        assert "duplicates:     1 group" in out
        assert "TestDomain/a@v1" in out
        assert "TestDomain/b@v1" in out

    def test_flags_duplicates_across_rename(self, tmp_path, capsys):
        """Two byte-identical files registered under different filenames."""
        manifest = _make_manifest_with_meshes(
            tmp_path,
            {
                "original@v1:original.14": b"payload\n",
                "renamed@v1:copy.14": b"payload\n",
            },
        )
        rc = main(["uid-audit", str(manifest)])
        assert rc == 1
        out = capsys.readouterr().out
        assert "duplicates:     1 group" in out

    def test_json_output(self, tmp_path, capsys):
        manifest = _make_manifest_with_meshes(
            tmp_path,
            {"a@v1:a.14": b"x\n", "b@v1:b.14": b"x\n", "c@v1:c.14": b"y\n"},
        )
        rc = main(["uid-audit", str(manifest), "--json"])
        assert rc == 1
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["total"] == 3
        assert parsed["missing"] == []
        assert len(parsed["duplicates"]) == 1
        dup_group = next(iter(parsed["duplicates"].values()))
        assert set(dup_group) == {"TestDomain/a@v1", "TestDomain/b@v1"}

    def test_missing_file_reported(self, tmp_path, capsys):
        manifest = _make_manifest_with_meshes(
            tmp_path,
            {"a@v1:a.14": b"x\n"},
        )
        # Remove the file but keep the manifest entry.
        (tmp_path / "meshes" / "a.14").unlink()
        rc = main(["uid-audit", str(manifest), "--json"])
        assert rc == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["missing"] == ["TestDomain/a@v1"]
        assert parsed["uids"] == {}


class TestUidAuditWrite:
    def test_write_persists_uid_and_is_idempotent(self, tmp_path, capsys):
        pytest.importorskip("tomlkit")
        manifest = _make_manifest_with_meshes(
            tmp_path,
            {"a@v1:a.14": b"alpha\n", "b@v1:b.14": b"beta\n"},
        )
        rc = main(["uid-audit", str(manifest), "--write"])
        assert rc == 0
        text = manifest.read_text()
        assert text.count('content_uid = "sha256-v1:') == 2

        capsys.readouterr()
        rc = main(["uid-audit", str(manifest), "--write"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "wrote 0 content_uid entries" in out

    def test_write_then_read_preserves_uid(self, tmp_path):
        pytest.importorskip("tomlkit")
        manifest = _make_manifest_with_meshes(
            tmp_path,
            {"a@v1:a.14": b"hello\n"},
        )
        main(["uid-audit", str(manifest), "--write"])
        from admesh_domains import load_manifest
        reloaded = load_manifest(manifest)
        mesh = next(reloaded.all_meshes())
        assert mesh.content_uid is not None
        assert mesh.content_uid.startswith("sha256-v1:")
        # Recomputing from disk matches the persisted value.
        assert mesh.compute_content_uid() == mesh.content_uid

    def test_write_requires_tomlkit(self, tmp_path, monkeypatch, capsys):
        manifest = _make_manifest_with_meshes(
            tmp_path,
            {"a@v1:a.14": b"x\n"},
        )
        # Simulate tomlkit being unavailable.
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "tomlkit":
                raise ImportError("simulated missing tomlkit")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        rc = main(["uid-audit", str(manifest), "--write"])
        assert rc == 4
        err = capsys.readouterr().err
        assert "[publish]" in err
