"""Tick loop: run the Anthropic model with a gh-only sandbox (SPEC §3.2)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from agent_fleet.config import FleetEntry
from agent_fleet.prompts import render_tick_prompt
from agent_fleet.sandbox import is_allowed_command

MAX_TURNS = 10

TOOLS: list[dict[str, Any]] = [
    {
        "name": "bash",
        "description": "Run a shell command. Restricted to invocations of `gh`.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    }
]

_URL_RE = re.compile(r"https://github\.com/\S+")


@dataclass(frozen=True)
class ExecResult:
    stdout: str
    stderr: str
    code: int


ExecFn = Callable[[str], ExecResult]


class AnthropicMessages(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class AnthropicClient(Protocol):
    messages: AnthropicMessages


@dataclass(frozen=True)
class TickDeps:
    anthropic: Any
    exec: ExecFn
    now: Callable[[], datetime]


@dataclass(frozen=True)
class TickOutcome:
    outcome: str  # "no-findings" | "issue-created" | "error"
    url: str = ""
    message: str = ""


def _as_dict(obj: Any) -> dict[str, Any]:
    """Coerce SDK objects to plain dicts (handles real Anthropic SDK and fake clients)."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    # Fallback: assume already mapping-like
    return dict(obj)  # type: ignore[arg-type]


def _block_dict(block: Any) -> dict[str, Any]:
    if isinstance(block, dict):
        return block
    return _as_dict(block)


def tick_one(entry: FleetEntry, deps: TickDeps) -> TickOutcome:
    now = deps.now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    iso_date = now.astimezone(timezone.utc).date().isoformat()
    prompt = render_tick_prompt(repo=entry.repo, iso_date=iso_date)
    messages: list[Any] = [{"role": "user", "content": prompt}]
    issue_url: str | None = None

    for _ in range(MAX_TURNS):
        resp = deps.anthropic.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )
        # Awaitable response? (Anthropic sync client returns plain object;
        # but a caller might pass an async coroutine — we only support sync here.)
        if hasattr(resp, "__await__"):
            raise RuntimeError(
                "tick_one received an awaitable from anthropic; pass a sync client"
            )

        resp_d = _as_dict(resp)
        content = resp_d.get("content", [])
        blocks = [_block_dict(b) for b in content]

        # Append assistant message preserving original objects when possible.
        messages.append({"role": "assistant", "content": content})

        tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
        text_blocks = [b for b in blocks if b.get("type") == "text"]

        if len(tool_uses) == 0:
            if issue_url:
                return TickOutcome(outcome="issue-created", url=issue_url)
            text = " ".join(b.get("text", "") for b in text_blocks).strip()
            if "no-findings" in text:
                return TickOutcome(outcome="no-findings")
            return TickOutcome(outcome="no-findings")

        tool_results: list[dict[str, Any]] = []
        for tu in tool_uses:
            tu_id = tu.get("id", "")
            if tu.get("name") != "bash":
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "content": "unknown tool",
                        "is_error": True,
                    }
                )
                continue
            cmd_in = tu.get("input") or {}
            if not isinstance(cmd_in, dict):
                cmd_in = _as_dict(cmd_in)
            cmd = str(cmd_in.get("command", ""))

            allow = is_allowed_command(cmd)
            if not allow.allowed:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "content": f"error: {allow.reason}",
                        "is_error": True,
                    }
                )
                continue

            # C3 interlock: at most one issue created per tick run.
            if cmd.startswith("gh issue create"):
                if issue_url is not None:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tu_id,
                            "content": "error: only one issue allowed per tick run",
                            "is_error": True,
                        }
                    )
                    continue
                r = deps.exec(cmd)
                m = _URL_RE.search(r.stdout)
                if m:
                    issue_url = m.group(0)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu_id,
                        "content": r.stdout or r.stderr or "",
                        "is_error": r.code != 0,
                    }
                )
                continue

            r = deps.exec(cmd)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu_id,
                    "content": r.stdout or r.stderr or "",
                    "is_error": r.code != 0,
                }
            )
        messages.append({"role": "user", "content": tool_results})

    return TickOutcome(outcome="error", message=f"exceeded {MAX_TURNS} turns")
