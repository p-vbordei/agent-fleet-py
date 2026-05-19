"""Tests for fleet.yaml loader/validator (mirrors TS tests/config.test.ts)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from agent_fleet.config import FleetConfigError, load_fleet_config


def _write(content: str) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="agent-fleet-"))
    p = tmp / "fleet.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def test_parses_valid_1_entry_fleet():
    yaml = """fleet:
  - name: agent-id
    repo: p-vbordei/agent-id
    path: ../agent-id
    template: typescript-bun
"""
    cfg = load_fleet_config(_write(yaml))
    assert len(cfg.fleet) == 1
    e = cfg.fleet[0]
    assert e.name == "agent-id"
    assert e.repo == "p-vbordei/agent-id"
    assert e.path == "../agent-id"
    assert e.template == "typescript-bun"


def test_rejects_empty_fleet_array():
    with pytest.raises(FleetConfigError):
        load_fleet_config(_write("fleet: []\n"))


def test_rejects_missing_required_field_path():
    yaml = """fleet:
  - name: x
    repo: o/r
    template: typescript-bun
"""
    with pytest.raises(FleetConfigError, match=r"path"):
        load_fleet_config(_write(yaml))


def test_rejects_unknown_template():
    yaml = """fleet:
  - name: x
    repo: o/r
    path: ../r
    template: rust-cargo
"""
    with pytest.raises(FleetConfigError, match=r"template"):
        load_fleet_config(_write(yaml))


def test_rejects_extra_unknown_keys_strict_mode():
    yaml = """fleet:
  - name: x
    repo: o/r
    path: ../r
    template: typescript-bun
    extra: nope
"""
    with pytest.raises(FleetConfigError, match=r"extra|unknown|unrecognized"):
        load_fleet_config(_write(yaml))


def test_rejects_invalid_name_pattern_uppercase():
    yaml = """fleet:
  - name: Agent_ID
    repo: o/r
    path: ../r
    template: typescript-bun
"""
    with pytest.raises(FleetConfigError, match=r"name"):
        load_fleet_config(_write(yaml))


def test_rejects_malformed_repo_no_slash():
    yaml = """fleet:
  - name: x
    repo: norepo
    path: ../r
    template: typescript-bun
"""
    with pytest.raises(FleetConfigError, match=r"repo"):
        load_fleet_config(_write(yaml))
