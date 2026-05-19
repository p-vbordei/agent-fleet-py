"""Tests for tick prompt rendering (mirrors TS tests/prompts.test.ts)."""

from __future__ import annotations

from agent_fleet.prompts import render_tick_prompt


def test_substitutes_repo_and_iso_date():
    out = render_tick_prompt(repo="p-vbordei/agent-id", iso_date="2026-04-25")
    assert "p-vbordei/agent-id" in out
    assert "2026-04-25" in out
    assert "{{repo}}" not in out
    assert "{{ISO_DATE}}" not in out


def test_mentions_all_four_inspection_categories():
    out = render_tick_prompt(repo="o/r", iso_date="2026-04-25")
    assert "Open PRs" in out
    assert "Issues open 30+" in out
    assert "CI run" in out
    assert "Dependabot" in out


def test_forbids_non_gh_commands_and_mutating_subcommands():
    out = render_tick_prompt(repo="o/r", iso_date="2026-04-25")
    assert "Do NOT modify" in out
    assert "AT MOST ONE issue" in out
