# SPEC — agent-fleet v0.1 (DRAFT)

**Status:** DRAFT 0.1 — flips to 1.0 at release per project scaffold.
**Last updated:** 2026-04-25

## 1. Overview

agent-fleet is a single Bun-compiled binary that maintains a list of TS+Bun OSS repos described in `fleet.yaml`. It exposes two operations:

1. **enroll** — install a fixed kit of automation files into a target repo, given a fleet entry.
2. **tick** — produce a weekly health-summary issue in each enrolled repo via GitHub.

It is invoked manually (`agent-fleet enroll`, `agent-fleet tick`) and on a weekly cron in its own GitHub Actions workflow (`tick`).

## 2. Data model

### 2.1 `fleet.yaml`

```yaml
fleet:
  - name: <string>          # repo nickname, used in CLI args; must match `^[a-z0-9][a-z0-9-]*$`
    repo: <string>          # GitHub coordinate "owner/name"
    path: <string>          # path relative to agent-fleet repo root
    template: <string>      # template id; v0.1 only "typescript-bun" is valid
```

**Validation (Zod, strict):**
- `fleet`: required; non-empty array
- Each entry: all four fields required, no optionals
- Strict mode: any unknown key rejects the whole config
- Empty `fleet:` array rejects

### 2.2 Template kit `typescript-bun` (v0.1)

The kit installed by enroll consists of EXACTLY five files in the target repo:

```
.github/workflows/ci.yml
.github/workflows/claude-review.yml
.github/workflows/release-please.yml
renovate.json
release-please-config.json
```

Each file is a Mustache-rendered template living in `templates/typescript-bun/` of the agent-fleet repo. The only template variables are `{{name}}` and `{{repo}}`. No other variables are introduced.

Template contents are **pinned per agent-fleet release**. Users adopt newer kit by upgrading agent-fleet and re-running `enroll`.

## 3. CLI

```
agent-fleet enroll <name>
agent-fleet tick [<name>]
```

### 3.1 `enroll`

**Inputs:** `<name>` matching a fleet.yaml entry's `name` field.

**Behavior:**
1. Load `fleet.yaml` (per §2.1). On validation failure, exit non-zero.
2. Find the entry with matching `name`. If none, exit 1.
3. Resolve target = `path`. Must exist and be a directory. MAY be a dirty git tree.
4. For each file in `templates/<entry.template>/`:
   a. Render with `{{name}}` and `{{repo}}` from the fleet entry.
   b. Compute target path: `<target>/<rel-path>`.
   c. Create parent directories as needed.
   d. Write the file. **Overwrite existing files unconditionally.**
5. Print: `enrolled <name>: 5 files written` to stdout.

**Exit codes:**
- 0 success
- 1 fleet entry not found, or fleet.yaml invalid
- 2 target path missing or not a directory
- 3 write error

### 3.2 `tick`

**Inputs:** optional `<name>`. If omitted, runs against every entry in `fleet.yaml`.

**Per-entry behavior:**
1. Construct the tick prompt (§4) with `{{repo}}` and today's UTC ISO date.
2. Issue an Anthropic API call to model `claude-opus-4-7`:
   - System prompt: §4
   - Tools: ONE tool, named `bash`, restricted at the SDK boundary to commands whose first token is exactly `gh`. Other invocations return an error to the model and do NOT execute.
   - Max tool turns: 10.
3. Allow the model to call `bash` repeatedly to gather data, then either:
   - Call `bash` once to run `gh issue create ...` — the issue creation, OR
   - Output a final assistant message containing the literal string `no-findings` and stop.
4. Print: `tick <name>: <outcome>` where `<outcome>` is one of:
   - `issue-created <url>` (extracted from `gh issue create` stdout)
   - `no-findings`
   - `error <message>` (any unhandled exception or budget exhaustion)

**Exit codes:**
- 0 if all entries completed (regardless of per-entry outcome)
- 1 if any entry produced `error <message>`

**Concurrency:** sequential per entry. No parallelism in v0.1.

## 4. Tick prompt (normative)

Variables `{{repo}}` and `{{ISO_DATE}}` are substituted at runtime.

```
You are auditing GitHub repository {{repo}} on {{ISO_DATE}}.

You have ONE tool: bash, restricted to invocations of `gh`.

Inspect the repository for:
  1. Open PRs with no activity in the last 7 days
     (gh pr list --state open --json number,title,updatedAt,url)
  2. Issues open for 30+ days
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
```

## 5. Conformance clauses

- **C1 — enroll idempotency.** Running `enroll <name>` twice in succession on a fleet entry yields a working tree byte-identical after the second run as after the first.
- **C2 — enroll bounded write set.** `enroll` writes only the five files listed in §2.2. No other path under the target is touched.
- **C3 — tick at-most-one issue.** Per `tick` invocation per fleet entry, at most one issue is created in the target repo.
- **C4 — tick read-only on code.** `tick` MUST NOT execute any `gh` command that mutates code, PRs, or existing issues. Specifically forbidden: `gh pr create`, `gh pr close`, `gh pr merge`, `gh pr review`, `gh issue close`, `gh issue comment`, `gh issue edit`, `gh release create`, `gh repo edit`, `gh api -X POST/PUT/PATCH/DELETE` against any path other than `/repos/<repo>/issues`.
- **C5 — fleet.yaml strict schema.** Loading a `fleet.yaml` with missing required fields, extra unknown fields, an empty `fleet:` array, or an invalid `name`/`template` value fails fast with a non-zero exit and a clear error message.

A test in `conformance/` validates each clause with a fixture. Full conformance run completes in < 30 seconds on a clean checkout.

## 6. Security considerations

- **S1 — Secret handling.** `ANTHROPIC_API_KEY` and `GH_TOKEN` are read from environment only. Never logged. Never written to disk. Never echoed in tool-call logs.
- **S2 — PAT scope.** `GH_TOKEN` MUST be a fine-grained PAT scoped only to repos in `fleet.yaml`. Required permissions: PRs (read), Issues (read+write), Actions (read), Dependabot alerts (read). All other permissions explicitly NOT granted.
- **S3 — Tool sandbox.** The `bash` tool exposed to Claude during tick MUST allow only commands whose first whitespace-delimited token equals `gh`. Other commands MUST be rejected at the SDK boundary, before exec, and report an error to the model.
- **S4 — Mutation allowlist.** Within the `gh` allowlist, the SDK MUST further reject any invocation matching the patterns enumerated in C4 (forbidden mutations). Implemented as a regex pre-filter on the rendered command string.
- **S5 — Template integrity.** Template files are vendored at agent-fleet's HEAD in `templates/`. `enroll` never fetches templates from the network.
- **S6 — Secret echo.** Tick's prompt and outputs MUST NOT contain raw token values. Claude's tool calls run in a child process; tokens injected via env vars (`GH_TOKEN`), never via argv.

A test in `conformance/` (S-suite) or `tests/security/` validates each defense.

## 7. Versioning

- agent-fleet itself follows semver.
- Template-kit content is pinned per agent-fleet release. There is no separate template version. To adopt a new kit, the user upgrades agent-fleet and re-runs `enroll`.
- `fleet.yaml` schema version is implicit in the agent-fleet binary version. Schema breaks require a major bump.

## 8. Deliverables checklist (Stage 6)

- [ ] `bun install && bun test` green on a clean checkout
- [ ] `bun build --compile --outfile agent-fleet src/index.ts` produces a single binary
- [ ] `examples/demo.ts` runs end-to-end against agent-id with real `ANTHROPIC_API_KEY` + `GH_TOKEN`
- [ ] All conformance clauses pass
- [ ] CHANGELOG.md v0.1.0 entry
- [ ] SPEC.md banner flipped DRAFT → 1.0
- [ ] Git tag v0.1.0 created locally; push deferred to user confirmation
