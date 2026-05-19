"""Security tests (mirrors TS tests/security/)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from agent_fleet.config import FleetEntry
from agent_fleet.enroll import enroll
from agent_fleet.prompts import render_tick_prompt
from agent_fleet.sandbox import is_allowed_command
from tests.conftest import TEMPLATES_ROOT


def test_s1_s6_rendered_tick_prompt_contains_no_secret_patterns_from_env():
    os.environ["GH_TOKEN"] = "ghp_FAKE_FOR_TEST_DO_NOT_USE"
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-FAKE"
    try:
        out = render_tick_prompt(repo="o/r", iso_date="2026-04-25")
        assert "ghp_" not in out
        assert "sk-ant-" not in out
    finally:
        del os.environ["GH_TOKEN"]
        del os.environ["ANTHROPIC_API_KEY"]


def test_s1_s6_sandbox_does_not_echo_secret_in_rejection_reasons():
    r = is_allowed_command(
        'gh api repos/o/r --header "Authorization: token ghp_LEAK_TEST"'
    )
    if not r.allowed:
        assert "ghp_LEAK_TEST" not in r.reason


def test_s3_sandbox_rejects_pasted_auth_header_with_dollar_var():
    # Shell metacharacter $ must already be rejected.
    assert not is_allowed_command(
        'gh api /repos/o/r --header "Auth: ${TOKEN}"'
    ).allowed


def test_s5_enroll_does_not_make_network_calls(monkeypatch):
    """No HTTP/socket call should be made from enroll — templates are vendored."""
    import socket

    called = {"flag": False}

    def boom(*a, **kw):
        called["flag"] = True
        raise RuntimeError("S5 violation: enroll attempted network call")

    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(socket.socket, "connect", boom)

    with tempfile.TemporaryDirectory(prefix="s5-") as d:
        enroll(
            FleetEntry(
                name="agent-id",
                repo="p-vbordei/agent-id",
                path=d,
                template="typescript-bun",
            ),
            TEMPLATES_ROOT,
        )
    assert called["flag"] is False
