"""Tests for tick_one (mirrors TS tests/tick.test.ts).

GitHub is NOT contacted: deps.exec is a callable we fully control.
The Anthropic SDK is also stubbed via a fake messages.create.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from agent_fleet.config import FleetEntry
from agent_fleet.tick import ExecResult, TickDeps, tick_one


ENTRY = FleetEntry(name="agent-id", repo="o/r", path="../r", template="typescript-bun")


class FakeMessages:
    def __init__(self, scripts, capture=None):
        self.scripts = scripts
        self.capture = capture
        self.call_count = 0

    def create(self, **kwargs):
        msgs = kwargs.get("messages", [])
        if self.capture is not None:
            self.capture(msgs)
        blocks = (
            self.scripts[self.call_count]
            if self.call_count < len(self.scripts)
            else [{"type": "text", "text": "done"}]
        )
        self.call_count += 1
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        return {"content": blocks, "stop_reason": stop, "model": "claude-opus-4-7"}


class FakeClient:
    def __init__(self, scripts, capture=None):
        self.messages = FakeMessages(scripts, capture)


def _now():
    return datetime(2026, 4, 25, 9, 0, 0, tzinfo=timezone.utc)


def test_returns_no_findings_when_model_emits_text_only():
    deps = TickDeps(
        anthropic=FakeClient([[{"type": "text", "text": "no-findings"}]]),
        exec=lambda c: ExecResult("", "", 0),
        now=_now,
    )
    r = tick_one(ENTRY, deps)
    assert r.outcome == "no-findings"


def test_returns_issue_created_with_url():
    scripts = [
        [
            {
                "type": "tool_use",
                "id": "t1",
                "name": "bash",
                "input": {
                    "command": (
                        'gh issue create --repo o/r --title "Weekly fleet review 2026-04-25"'
                        ' --body "..."'
                    ),
                },
            }
        ],
        [{"type": "text", "text": "done"}],
    ]

    def fake_exec(cmd: str) -> ExecResult:
        if "gh issue create" in cmd:
            return ExecResult("https://github.com/o/r/issues/42\n", "", 0)
        return ExecResult("", "", 0)

    deps = TickDeps(anthropic=FakeClient(scripts), exec=fake_exec, now=_now)
    r = tick_one(ENTRY, deps)
    assert r.outcome == "issue-created"
    assert r.url == "https://github.com/o/r/issues/42"


def test_refuses_forbidden_tool_call_surfaces_error_to_model():
    captured: list = []

    def capture(msgs):
        if len(msgs) > 1:
            captured.append(msgs)

    scripts = [
        [
            {
                "type": "tool_use",
                "id": "t1",
                "name": "bash",
                "input": {"command": "gh pr create --title evil"},
            }
        ],
        [{"type": "text", "text": "no-findings"}],
    ]

    def evil_exec(cmd):
        raise AssertionError("exec must not be called for forbidden cmd")

    deps = TickDeps(
        anthropic=FakeClient(scripts, capture),
        exec=evil_exec,
        now=_now,
    )
    r = tick_one(ENTRY, deps)
    assert r.outcome == "no-findings"
    assert len(captured) >= 1
    serialized = json.dumps(captured[-1], default=str)
    assert "forbidden" in serialized
    assert "is_error" in serialized


def test_refuses_non_gh_command_surfaces_error_to_model():
    scripts = [
        [
            {
                "type": "tool_use",
                "id": "t1",
                "name": "bash",
                "input": {"command": "rm -rf /"},
            }
        ],
        [{"type": "text", "text": "no-findings"}],
    ]

    def evil_exec(cmd):
        raise AssertionError("exec must not be called for non-gh")

    deps = TickDeps(anthropic=FakeClient(scripts), exec=evil_exec, now=_now)
    r = tick_one(ENTRY, deps)
    assert r.outcome == "no-findings"


def test_returns_error_if_budget_exhausted():
    # Infinite tool_use stream; after MAX_TURNS we error.
    class InfiniteMessages:
        def create(self, **kwargs):
            return {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "t",
                        "name": "bash",
                        "input": {"command": "gh pr list"},
                    }
                ],
                "stop_reason": "tool_use",
            }

    class InfiniteClient:
        messages = InfiniteMessages()

    deps = TickDeps(
        anthropic=InfiniteClient(),
        exec=lambda c: ExecResult("[]", "", 0),
        now=_now,
    )
    r = tick_one(ENTRY, deps)
    assert r.outcome == "error"
