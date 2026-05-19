"""Tick prompt template (SPEC §4)."""

from __future__ import annotations

TICK_PROMPT = """You are auditing GitHub repository {{repo}} on {{ISO_DATE}}.

You have ONE tool: bash, restricted to invocations of `gh`.

Inspect the repository for:
  1. Open PRs with no activity in the last 7 days
     (gh pr list --state open --json number,title,updatedAt,url)
  2. Issues open 30+ days
     (gh issue list --state open --json number,title,createdAt,url)
  3. Most recent CI run failed within the last 7 days
     (gh run list --limit 1 --json conclusion,createdAt,url)
  4. Open Dependabot alerts
     (gh api repos/{{repo}}/dependabot/alerts --jq '.[] | select(.state=="open")')

If at least one of (1)-(4) yields findings:
  Create EXACTLY ONE issue in {{repo}}:
    gh issue create --repo {{repo}} \\
      --title "Weekly fleet review {{ISO_DATE}}" \\
      --body "<one bullet per finding category, item details inline>"
  Then stop.

If none yield findings:
  Output the literal text "no-findings" and stop. Do NOT create an issue.

Constraints (violations cause failure):
- Do NOT modify the repository's code.
- Do NOT open or close PRs.
- Do NOT comment on, close, assign, or label existing issues.
- Create AT MOST ONE issue per run.
- Do not invoke any command other than `gh`.
"""


def render_tick_prompt(*, repo: str, iso_date: str) -> str:
    return TICK_PROMPT.replace("{{repo}}", repo).replace("{{ISO_DATE}}", iso_date)
