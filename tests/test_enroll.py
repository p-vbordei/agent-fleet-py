"""Tests for enroll (mirrors TS tests/enroll.test.ts)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from agent_fleet.config import FleetEntry
from agent_fleet.enroll import EnrollError, enroll
from tests.conftest import TEMPLATES_ROOT


def _entry(path: str) -> FleetEntry:
    return FleetEntry(
        name="agent-id",
        repo="p-vbordei/agent-id",
        path=path,
        template="typescript-bun",
    )


def test_writes_renovate_json_to_target():
    with tempfile.TemporaryDirectory(prefix="agent-fleet-target-") as d:
        enroll(_entry(d), TEMPLATES_ROOT)
        target = Path(d)
        assert (target / "renovate.json").exists()
        content = json.loads((target / "renovate.json").read_text())
        assert content["$schema"] == "https://docs.renovatebot.com/renovate-schema.json"


def test_idempotent_second_enroll_byte_identical_c1():
    with tempfile.TemporaryDirectory(prefix="agent-fleet-target-") as d:
        enroll(_entry(d), TEMPLATES_ROOT)
        first = (Path(d) / "renovate.json").read_text()
        enroll(_entry(d), TEMPLATES_ROOT)
        second = (Path(d) / "renovate.json").read_text()
        assert second == first


def test_rejects_missing_target_dir():
    with pytest.raises(EnrollError):
        enroll(_entry("/no/such/dir/please"), TEMPLATES_ROOT)


def test_returns_list_of_relative_paths_written():
    with tempfile.TemporaryDirectory(prefix="agent-fleet-target-") as d:
        result = enroll(_entry(d), TEMPLATES_ROOT)
        assert "renovate.json" in result["written"]


def test_writes_all_5_kit_files_spec_2_2():
    with tempfile.TemporaryDirectory(prefix="agent-fleet-target-") as d:
        enroll(_entry(d), TEMPLATES_ROOT)
        target = Path(d)
        expected = [
            "renovate.json",
            "release-please-config.json",
            ".github/workflows/ci.yml",
            ".github/workflows/claude-review.yml",
            ".github/workflows/release-please.yml",
        ]
        for rel in expected:
            assert (target / rel).exists(), f"missing {rel}"


def test_bootstraps_release_please_manifest_from_package_json_version():
    with tempfile.TemporaryDirectory(prefix="agent-fleet-target-") as d:
        (Path(d) / "package.json").write_text(json.dumps({"name": "x", "version": "0.4.2"}))
        enroll(_entry(d), TEMPLATES_ROOT)
        manifest_path = Path(d) / ".release-please-manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest == {".": "0.4.2"}


def test_skips_manifest_bootstrap_when_no_package_json():
    with tempfile.TemporaryDirectory(prefix="agent-fleet-target-") as d:
        enroll(_entry(d), TEMPLATES_ROOT)
        assert not (Path(d) / ".release-please-manifest.json").exists()


def test_renders_mustache_name_and_repo_vars():
    with tempfile.TemporaryDirectory(prefix="agent-fleet-target-") as d:
        enroll(_entry(d), TEMPLATES_ROOT)
        target = Path(d)
        ci = (target / ".github/workflows/ci.yml").read_text()
        assert "--outfile agent-id" in ci
        assert "{{name}}" not in ci
        review = (target / ".github/workflows/claude-review.yml").read_text()
        assert "repo: p-vbordei/agent-id" in review
        rp = json.loads((target / "release-please-config.json").read_text())
        assert rp["packages"]["."]["package-name"] == "agent-id"
