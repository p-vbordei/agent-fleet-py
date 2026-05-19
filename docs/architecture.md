# Architecture — agent-fleet (Python)

## Goal

Port [`@p-vbordei/agent-fleet`](https://github.com/p-vbordei/agent-fleet) (TypeScript / Bun) to idiomatic Python. Preserve the SPEC v0.1 behaviour byte-for-byte where observable: same CLI surface, same exit codes, same `fleet.yaml` schema, same template kit, same forbidden-`gh`-prefix table, same prompt text, same C1–C5 + S1/S3/S5/S6 invariants.

## Module map

```
src/agent_fleet/
  __init__.py     — public surface (re-exports + __version__)
  config.py       — fleet.yaml loader + strict validator (C5)
  enroll.py       — render templates into a target repo + seed release-please manifest (C1, C2, S5)
  prompts.py      — single tick prompt template + render helper (S1, S6)
  sandbox.py      — gh-only allowlist with forbidden-prefix table + shell-metachar gate (S3, S4, C4)
  tick.py         — Anthropic loop: AnthropicClient + ExecFn + C3 single-issue interlock
  cli.py          — typer dispatch + ANTHROPIC_API_KEY env read + real gh exec
tests/
  conftest.py     — pushes src/ onto sys.path; exports TEMPLATES_ROOT pointing at <repo>/templates
  test_*.py       — eight files, 78 tests total
templates/
  typescript-bun/ — five files installed by enroll (vendored, not fetched)
```

## Dependency choices

| Concern | Choice | Why |
|---|---|---|
| CLI | `typer` | Mirrors the TS reference's two-command surface with first-class subcommands and exit-code hygiene. |
| YAML | `pyyaml` | Stdlib-grade ubiquity; strict validation lives in `config.py`, not the parser. |
| Validation | hand-rolled in `config.py` | One file, no Pydantic dep needed for the v0.1 schema. Keeps wheel slim. |
| Anthropic client | `anthropic` SDK, injected via `TickDeps.anthropic` | Tests pass a `FakeClient` exposing `messages.create(**kwargs)`. CLI constructs the real `Anthropic(api_key=…)`. |
| `gh` exec | `subprocess.run(shell=True)` via `_gh_exec`, injected as `TickDeps.exec` | Tests inject a pure callable. `shell=True` is safe because the sandbox has already rejected shell metacharacters. |
| Templates packaging | `hatch.build.targets.wheel.force-include = { "templates" = "agent_fleet/_data/templates" }` | Wheel installs lookup `<package>/_data/templates`; source checkout falls back to `<repo>/templates`. |

## Sandbox design

`is_allowed_command(cmd)` returns `AllowResult(allowed, reason)`. Order of checks:

1. **Empty / whitespace** → reject.
2. **Shell metacharacters** matched by `[|&;\`$<>(){}\\]` → reject. This stops `gh foo; rm -rf /`, `$(…)`, backticks, and `${TOKEN}` injection from leaking secrets.
3. **First token must be `gh`** (no `bash`, no `sh`, no env-var prefix). Anything else → reject.
4. **Forbidden prefix table** — 30+ entries covering every code/PR/release/repo/workflow/secret/variable/label mutation, e.g. `gh pr create`, `gh issue close`, `gh release upload`, `gh workflow run`, `gh secret set`. Match is exact or `prefix + " "`.
5. **`gh api` mutating verbs** — `-X POST|PUT|PATCH|DELETE` against any path not matching `^/?repos/<owner>/<repo>/issues(\?|$)` → reject. This is the C4 escape-hatch closer: the model can still create issues via the REST API, but cannot e.g. PATCH a release.

Why `gh`-only? It collapses auth (gh handles the PAT), pagination, and JSON shaping to one tool — and gives us exactly one binary to enumerate forbidden subcommands against.

## C3 interlock

Inside `tick_one`, the loop tracks `issue_url: str | None`. The first `gh issue create` is executed and its stdout URL captured. Any subsequent `gh issue create` in the same `tick_one` call returns `tool_result { is_error: true, content: "error: only one issue allowed per tick run" }` to the model **without** running it. This guards against a model that, given partial output, decides to "try again with a better title" — the test suite covers this path explicitly.

## Testing strategy

78 tests, eight files:

- `test_config.py` — schema validity, missing/extra keys, bad name/repo/template patterns (C5).
- `test_enroll.py` — write set, byte-identical second run (C1, C2), release-please manifest seeding.
- `test_prompts.py` — variable substitution, no leakage.
- `test_sandbox.py` — every forbidden prefix, every metacharacter, the `gh api` POST allow/deny boundary.
- `test_tick.py` — five end-to-end loop scenarios with `FakeClient`: no-findings, issue-created, forbidden-command surfaced as `tool_result`, non-gh command rejected, budget exhaustion.
- `test_security.py` — S1/S5/S6 invariants (no secrets in prompts or rejection reasons, enroll makes zero socket calls).
- `test_conformance.py` — explicit C1–C5 checks.
- `test_cli.py` — typer integration with `CliRunner` + mocked subprocess.

Every GitHub call and every Anthropic call is mocked. Tests run in <100ms.
