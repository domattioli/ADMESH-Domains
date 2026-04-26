"""Tests for the `admesh-domains domain {suggest,audit,list}` CLI surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from admesh_domains.cli import main


def _run(argv: list[str], capsys) -> tuple[int, str, str]:
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


class TestDomainSuggest:
    def test_existing_wnat_mesh_text_output(self, capsys, dev_manifest_path):
        path = dev_manifest_path.parent / "meshes" / "WNAT_Hagen.14"
        code, out, _ = _run(
            ["domain", "suggest", str(path), "--manifest", str(dev_manifest_path), "--non-interactive"],
            capsys,
        )
        assert code == 0
        assert "WNAT" in out
        assert "confident" in out

    def test_json_output_shape(self, capsys, dev_manifest_path):
        path = dev_manifest_path.parent / "meshes" / "ChesapeakeBay/Chesapeake_Bay.14"
        # Path doesn't have nested dir on disk, fix to flat layout
        path = dev_manifest_path.parent / "meshes" / "Chesapeake_Bay.14"
        code, out, _ = _run(
            ["domain", "suggest", str(path), "--manifest", str(dev_manifest_path), "--json"],
            capsys,
        )
        data = json.loads(out)
        assert data["path"].endswith("Chesapeake_Bay.14")
        assert len(data["bbox"]) == 4
        assert isinstance(data["candidates"], list)
        assert data["candidates"][0]["domain"] == "ChesapeakeBay"
        assert data["candidates"][0]["confidence"] == "confident"
        assert data["exit_code"] == 0

    def test_missing_file_returns_3(self, capsys, dev_manifest_path):
        code, _, err = _run(
            ["domain", "suggest", "/no/such/mesh.14",
             "--manifest", str(dev_manifest_path), "--non-interactive"],
            capsys,
        )
        assert code == 3
        assert "not found" in err.lower()

    def test_non_interactive_emits_stub_for_no_match(self, capsys, dev_manifest_path, tmp_path):
        """A small synthetic mesh in projected coords -> no geographic match.

        We construct a tiny fort.14 stub in tmp_path with coords way outside lat/lon.
        """
        synthetic = tmp_path / "synthetic.14"
        synthetic.write_text(
            "synthetic_test\n"
            "1 4\n"
            "1 1000000.0 2000000.0 0.0\n"
            "2 1100000.0 2000000.0 0.0\n"
            "3 1100000.0 2100000.0 0.0\n"
            "4 1000000.0 2100000.0 0.0\n"
        )
        code, out, _ = _run(
            ["domain", "suggest", str(synthetic),
             "--manifest", str(dev_manifest_path), "--non-interactive"],
            capsys,
        )
        # No geographic Domain matches -> exit code 1
        assert code == 1
        # Stub should be printed
        assert "[[domains]]" in out
        assert "<TBD>" in out
        assert "synthetic.14" in out


class TestDomainAudit:
    def test_full_registry_zero_disagreements(self, capsys):
        code, out, _ = _run(["domain", "audit"], capsys)
        assert code == 0
        assert "0 disagreements" in out

    def test_audit_json(self, capsys):
        code, out, _ = _run(["domain", "audit", "--json"], capsys)
        data = json.loads(out)
        assert data["count"] == 0
        assert data["disagreements"] == []


class TestDomainList:
    def test_alias_for_top_level_domains(self, capsys):
        code, out, _ = _run(["domain", "list"], capsys)
        assert code == 0
        assert "WNAT" in out
        assert "ChesapeakeBay" in out
