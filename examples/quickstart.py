"""Quickstart: drive one tick with a fake AnthropicClient and fake ExecFn.

Demonstrates dependency injection — no ANTHROPIC_API_KEY, no GitHub, no network.
Run:  python examples/quickstart.py
"""

from __future__ import annotations

from datetime import datetime, timezone

from agent_fleet import ExecResult, FleetEntry, TickDeps, tick_one


class FakeMessages:
    """Scripted Anthropic messages.create — returns one block list per turn."""

    def __init__(self, scripts: list[list[dict]]) -> None:
        self._scripts = scripts
        self._i = 0

    def create(self, **_: object) -> dict:
        blocks = self._scripts[self._i] if self._i < len(self._scripts) else [
            {"type": "text", "text": "done"}
        ]
        self._i += 1
        stop = "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "end_turn"
        return {"content": blocks, "stop_reason": stop, "model": "claude-opus-4-7"}


class FakeAnthropic:
    def __init__(self, scripts: list[list[dict]]) -> None:
        self.messages = FakeMessages(scripts)


def fake_exec(cmd: str) -> ExecResult:
    """Stand-in for the real `gh` shell exec — returns canned output."""
    if cmd.startswith("gh pr list"):
        return ExecResult(stdout='[{"number":1,"title":"stale","url":"u"}]', stderr="", code=0)
    if cmd.startswith("gh issue create"):
        return ExecResult(
            stdout="https://github.com/yourname/agent-id/issues/123\n", stderr="", code=0
        )
    return ExecResult(stdout="[]", stderr="", code=0)


def main() -> None:
    entry = FleetEntry(
        name="agent-id",
        repo="yourname/agent-id",
        path="../agent-id",
        template="typescript-bun",
    )

    # Turn 1: model inspects PRs.  Turn 2: model creates the summary issue.
    scripts: list[list[dict]] = [
        [{"type": "tool_use", "id": "t1", "name": "bash",
          "input": {"command": "gh pr list --state open --json number,title,updatedAt,url"}}],
        [{"type": "tool_use", "id": "t2", "name": "bash",
          "input": {"command":
              'gh issue create --repo yourname/agent-id'
              ' --title "Weekly fleet review 2026-04-25" --body "- 1 stale PR"'}}],
        [{"type": "text", "text": "done"}],
    ]

    deps = TickDeps(
        anthropic=FakeAnthropic(scripts),
        exec=fake_exec,
        now=lambda: datetime(2026, 4, 25, 9, 0, 0, tzinfo=timezone.utc),
    )

    result = tick_one(entry, deps)
    print(f"tick {entry.name}: {result.outcome} {result.url}".rstrip())


if __name__ == "__main__":
    main()
