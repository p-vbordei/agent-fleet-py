"""Conformance suite — mirrors TS conformance/ directory.

C1 — enroll idempotency.
C2 — enroll writes only the 5 declared kit files.
C3 — tick at-most-one issue.
C4 — tick read-only on code (sandbox forbids mutations).
C5 — fleet.yaml strict schema.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from agent_fleet.config import FleetConfigError, FleetEntry, load_fleet_config
from agent_fleet.enroll import enroll
from agent_fleet.sandbox import is_allowed_command
from agent_fleet.tick import ExecResult, TickDeps, tick_one
from tests.conftest import TEMPLATES_ROOT


def _snapshot(d: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in d.rglob("*"):
        if p.is_file():
            out[str(p.relative_to(d)).replace("\\", "/")] = p.read_text(encoding="utf-8")
    return out


# C1
def test_c1_running_enroll_twice_byte_identical():
    with tempfile.TemporaryDirectory(prefix="c1-") as d:
        entry = FleetEntry(
            name="agent-id",
            repo="p-vbordei/agent-id",
            path=d,
            template="typescript-bun",
        )
        enroll(entry, TEMPLATES_ROOT)
        first = _snapshot(Path(d))
        enroll(entry, TEMPLATES_ROOT)
        second = _snapshot(Path(d))
        assert first == second


# C2
EXPECTED_KIT = {
    "renovate.json",
    "release-please-config.json",
    ".github/workflows/ci.yml",
    ".github/workflows/claude-review.yml",
    ".github/workflows/release-please.yml",
}


def test_c2_enroll_only_writes_5_kit_files_preserves_unrelated():
    with tempfile.TemporaryDirectory(prefix="c2-") as d:
        (Path(d) / "README.md").write_text("# pre-existing\n")
        enroll(
            FleetEntry(
                name="agent-id",
                repo="p-vbordei/agent-id",
                path=d,
                template="typescript-bun",
            ),
            TEMPLATES_ROOT,
        )
        assert (Path(d) / "README.md").read_text() == "# pre-existing\n"
        added: set[str] = set()
        for p in Path(d).rglob("*"):
            if p.is_file():
                rel = str(p.relative_to(d)).replace("\\", "/")
                if rel != "README.md":
                    added.add(rel)
        assert added == EXPECTED_KIT


# C3
def test_c3_even_if_model_attempts_two_issue_creates_only_one_actually_runs():
    issue_creates = {"count": 0}

    from datetime import datetime, timezone

    class TwoCreateMessages:
        def __init__(self):
            self.turn = 0

        def create(self, **kwargs):
            import json as _json

            msgs = kwargs.get("messages", [])
            serial = _json.dumps(msgs, default=str)
            if "only one issue" in serial:
                return {"content": [{"type": "text", "text": "done"}], "stop_reason": "end_turn"}
            is_first = "https://github.com/o/r/issues/" not in serial
            cmd = (
                "gh issue create --repo o/r --title T1 --body B1"
                if is_first
                else "gh issue create --repo o/r --title T2 --body B2"
            )
            return {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "a" if is_first else "b",
                        "name": "bash",
                        "input": {"command": cmd},
                    }
                ],
                "stop_reason": "tool_use",
            }

    class Client:
        messages = TwoCreateMessages()

    def fake_exec(cmd: str) -> ExecResult:
        if "gh issue create" in cmd:
            issue_creates["count"] += 1
            return ExecResult(
                f"https://github.com/o/r/issues/{issue_creates['count']}\n", "", 0
            )
        return ExecResult("", "", 0)

    deps = TickDeps(
        anthropic=Client(),
        exec=fake_exec,
        now=lambda: datetime(2026, 4, 25, 9, 0, 0, tzinfo=timezone.utc),
    )
    r = tick_one(
        FleetEntry(name="a", repo="o/r", path="../r", template="typescript-bun"),
        deps,
    )
    assert issue_creates["count"] == 1
    assert r.outcome == "issue-created"
    assert r.url == "https://github.com/o/r/issues/1"


# C4 — read-only sandbox.
FORBIDDEN_SAMPLES = [
    "gh pr create --title x",
    "gh pr close 1",
    "gh pr merge 1",
    "gh pr review 1 --approve",
    "gh issue close 1",
    "gh issue comment 1 --body x",
    "gh issue edit 1 --add-label x",
    "gh issue reopen 1",
    "gh release create v1",
    "gh release edit v1",
    "gh repo edit --description x",
    "gh repo delete o/r",
    "gh workflow run weekly",
    "gh secret set TOKEN --body x",
    "gh variable set FOO --body bar",
    "gh label create new",
    "gh api -X POST /repos/o/r/pulls -f title=x",
    "gh api -X DELETE /repos/o/r/issues/1/comments/2",
    "gh api -X PATCH /repos/o/r/issues/1 -f state=closed",
    "gh api -X PUT /repos/o/r/contents/README.md -f content=x",
]


@pytest.mark.parametrize("cmd", FORBIDDEN_SAMPLES)
def test_c4_rejects_each_forbidden_sample(cmd):
    assert not is_allowed_command(cmd).allowed


def test_c4_allows_read_only_inspections():
    for c in [
        "gh pr list --state open",
        "gh issue list --state open",
        "gh run list --limit 1",
        "gh api repos/o/r/dependabot/alerts",
    ]:
        assert is_allowed_command(c).allowed, c


def test_c4_allows_the_one_permitted_mutation_issue_create():
    assert is_allowed_command("gh issue create --repo o/r --title T --body B").allowed
    assert is_allowed_command("gh api -X POST /repos/o/r/issues -f title=T").allowed


# C5
def test_c5_rejects_empty_fleet_array():
    with tempfile.TemporaryDirectory(prefix="c5-") as d:
        p = Path(d) / "fleet.yaml"
        p.write_text("fleet: []\n")
        with pytest.raises(FleetConfigError):
            load_fleet_config(p)


def test_c5_rejects_missing_fleet_key():
    with tempfile.TemporaryDirectory(prefix="c5-") as d:
        p = Path(d) / "fleet.yaml"
        p.write_text("foo: bar\n")
        with pytest.raises(FleetConfigError):
            load_fleet_config(p)


def test_c5_rejects_extra_unknown_top_level_key():
    with tempfile.TemporaryDirectory(prefix="c5-") as d:
        p = Path(d) / "fleet.yaml"
        p.write_text("fleet: []\nextra: x\n")
        with pytest.raises(FleetConfigError):
            load_fleet_config(p)


def test_c5_rejects_missing_per_entry_field_path():
    with tempfile.TemporaryDirectory(prefix="c5-") as d:
        p = Path(d) / "fleet.yaml"
        p.write_text(
            """fleet:
  - name: x
    repo: o/r
    template: typescript-bun
"""
        )
        with pytest.raises(FleetConfigError, match=r"path"):
            load_fleet_config(p)


def test_c5_rejects_extra_per_entry_field():
    with tempfile.TemporaryDirectory(prefix="c5-") as d:
        p = Path(d) / "fleet.yaml"
        p.write_text(
            """fleet:
  - name: x
    repo: o/r
    path: ../x
    template: typescript-bun
    extra: y
"""
        )
        with pytest.raises(FleetConfigError):
            load_fleet_config(p)


def test_c5_rejects_unknown_template_id():
    with tempfile.TemporaryDirectory(prefix="c5-") as d:
        p = Path(d) / "fleet.yaml"
        p.write_text(
            """fleet:
  - name: x
    repo: o/r
    path: ../x
    template: rust-cargo
"""
        )
        with pytest.raises(FleetConfigError, match=r"template"):
            load_fleet_config(p)


def test_c5_rejects_empty_string_fields():
    with tempfile.TemporaryDirectory(prefix="c5-") as d:
        p = Path(d) / "fleet.yaml"
        p.write_text(
            """fleet:
  - name: ""
    repo: o/r
    path: ../x
    template: typescript-bun
"""
        )
        with pytest.raises(FleetConfigError, match=r"name"):
            load_fleet_config(p)
