"""Tests for the gh-only sandbox (mirrors TS tests/sandbox.test.ts)."""

from __future__ import annotations

from agent_fleet.sandbox import is_allowed_command


def test_allows_gh_pr_list():
    r = is_allowed_command("gh pr list --state open --json number,title")
    assert r.allowed


def test_allows_gh_issue_create_the_one_permitted_mutation():
    r = is_allowed_command("gh issue create --repo o/r --title T --body B")
    assert r.allowed


def test_rejects_non_gh_command():
    r = is_allowed_command("rm -rf /")
    assert not r.allowed
    assert "non-gh" in r.reason.lower()


def test_rejects_gh_pr_create_mutation():
    r = is_allowed_command("gh pr create --title X")
    assert not r.allowed
    assert "forbidden" in r.reason.lower()


def test_rejects_gh_issue_close():
    assert not is_allowed_command("gh issue close 42").allowed


def test_rejects_gh_issue_comment():
    assert not is_allowed_command("gh issue comment 42 --body x").allowed


def test_rejects_gh_release_create():
    assert not is_allowed_command("gh release create v1.0").allowed


def test_rejects_gh_api_post_against_pulls():
    assert not is_allowed_command("gh api -X POST /repos/o/r/pulls -f title=x").allowed


def test_rejects_gh_api_patch_against_issues_close():
    assert not is_allowed_command(
        "gh api -X PATCH /repos/o/r/issues/1 -f state=closed"
    ).allowed


def test_rejects_gh_api_delete():
    assert not is_allowed_command(
        "gh api -X DELETE /repos/o/r/issues/1/comments/2"
    ).allowed


def test_allows_gh_api_get_any_path():
    assert is_allowed_command("gh api repos/o/r/dependabot/alerts").allowed


def test_allows_gh_api_post_issues():
    assert is_allowed_command("gh api -X POST /repos/o/r/issues -f title=x").allowed


def test_rejects_empty_command():
    assert not is_allowed_command("").allowed


def test_rejects_shell_pipe():
    assert not is_allowed_command("gh pr list | rm -rf /").allowed


def test_rejects_shell_substitution():
    assert not is_allowed_command("gh pr list $(rm -rf /)").allowed
