"""Tests for CLI dispatch (mirrors TS tests/cli.test.ts)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from agent_fleet.cli import app


def _write_fleet(work: Path, body: str) -> None:
    (work / "fleet.yaml").write_text(body)


def test_enroll_writes_templates_into_target(monkeypatch):
    runner = CliRunner()
    with tempfile.TemporaryDirectory(prefix="agent-fleet-cli-") as work_s:
        with tempfile.TemporaryDirectory(prefix="agent-fleet-target-") as target:
            work = Path(work_s)
            _write_fleet(
                work,
                f"""fleet:
  - name: x
    repo: o/r
    path: {target}
    template: typescript-bun
""",
            )
            monkeypatch.chdir(work)
            res = runner.invoke(app, ["enroll", "x"])
            assert res.exit_code == 0, res.output
            assert "enrolled x" in res.output
            assert (Path(target) / "renovate.json").exists()


def test_enroll_exits_1_when_name_not_in_fleet(monkeypatch):
    runner = CliRunner()
    with tempfile.TemporaryDirectory(prefix="agent-fleet-cli-") as work_s:
        work = Path(work_s)
        _write_fleet(
            work,
            """fleet:
  - name: a
    repo: o/r
    path: /tmp/x
    template: typescript-bun
""",
        )
        monkeypatch.chdir(work)
        res = runner.invoke(app, ["enroll", "b"])
        assert res.exit_code == 1


def test_enroll_exits_1_when_fleet_yaml_missing(monkeypatch):
    runner = CliRunner()
    with tempfile.TemporaryDirectory(prefix="agent-fleet-cli-") as work_s:
        monkeypatch.chdir(work_s)
        res = runner.invoke(app, ["enroll", "x"])
        assert res.exit_code == 1


def test_exits_64_with_usage_on_missing_command(monkeypatch):
    runner = CliRunner()
    with tempfile.TemporaryDirectory(prefix="agent-fleet-cli-") as work_s:
        work = Path(work_s)
        _write_fleet(
            work,
            """fleet:
  - name: a
    repo: o/r
    path: /tmp/x
    template: typescript-bun
""",
        )
        monkeypatch.chdir(work)
        res = runner.invoke(app, [])
        assert res.exit_code == 64
