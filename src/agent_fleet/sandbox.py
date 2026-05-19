"""gh-only sandbox (SPEC §6, S3+S4, C4)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# gh subcommand prefixes that are forbidden because they mutate code/PRs/existing issues.
FORBIDDEN_GH_PREFIXES: tuple[str, ...] = (
    "gh pr create",
    "gh pr close",
    "gh pr merge",
    "gh pr review",
    "gh pr edit",
    "gh issue close",
    "gh issue comment",
    "gh issue edit",
    "gh issue reopen",
    "gh issue delete",
    "gh release create",
    "gh release edit",
    "gh release delete",
    "gh release upload",
    "gh repo edit",
    "gh repo delete",
    "gh repo archive",
    "gh repo clone",
    "gh repo create",
    "gh repo fork",
    "gh repo rename",
    "gh repo sync",
    "gh workflow run",
    "gh workflow disable",
    "gh workflow enable",
    "gh secret set",
    "gh secret delete",
    "gh variable set",
    "gh variable delete",
    "gh label create",
    "gh label edit",
    "gh label delete",
)

# gh api -X POST allowed only against this path family (issue creation).
_ALLOWED_API_POST_PREFIXES: tuple[re.Pattern[str], ...] = (
    re.compile(r"^/?repos/[^/]+/[^/]+/issues(\?|$)"),
)
_MUTATING_API_FLAGS = re.compile(r"-X\s+(POST|PUT|PATCH|DELETE)\b")

# Shell metacharacters that could enable command injection beyond the gh prefix.
_SHELL_METACHARS = re.compile(r"[|&;`$<>(){}\\]")

_API_PATH_RE = re.compile(r"gh api(?:\s+-X\s+\w+)?\s+(\S+)")


@dataclass(frozen=True)
class AllowResult:
    allowed: bool
    reason: str = ""


def is_allowed_command(cmd: str) -> AllowResult:
    trimmed = cmd.strip()
    if len(trimmed) == 0:
        return AllowResult(False, "empty command")
    if _SHELL_METACHARS.search(trimmed):
        return AllowResult(False, "shell metacharacters not permitted")
    if not (trimmed.startswith("gh ") or trimmed == "gh"):
        return AllowResult(False, "non-gh command rejected")
    for prefix in FORBIDDEN_GH_PREFIXES:
        if trimmed == prefix or trimmed.startswith(prefix + " "):
            return AllowResult(False, f"forbidden gh subcommand: {prefix}")
    if trimmed.startswith("gh api") and _MUTATING_API_FLAGS.search(trimmed):
        m = _API_PATH_RE.search(trimmed)
        path = m.group(1) if m else ""
        if not any(p.search(path) for p in _ALLOWED_API_POST_PREFIXES):
            return AllowResult(False, f"forbidden mutating gh api path: {path}")
    return AllowResult(True)
