# agent-fleet (Python)

[![CI](https://github.com/p-vbordei/agent-fleet-py/actions/workflows/ci.yml/badge.svg)](https://github.com/p-vbordei/agent-fleet-py/actions/workflows/ci.yml)
[![spec: v0.1](https://img.shields.io/badge/spec-v0.1-blue)](./SPEC.md)
[![license: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green)](./LICENSE)

> **Idiomatic Python port of [`@p-vbordei/agent-fleet`](https://github.com/p-vbordei/agent-fleet)** (on npm as `@p-vbordei/agent-fleet` v0.1.3). Autonomous OSS-repo health for solo maintainers — one config, one cron, N repos kept reviewed and dep-current. The CLI drives an Anthropic loop through a strict `gh`-only command allowlist (sandbox) gated by a C3 single-issue interlock. **78 tests** — the most of any port in the family — cover config validation, enroll, sandbox, the tick loop, and S1/S3/S5/S6 security invariants.

## What's in the box

- `agent-fleet enroll <name>` — bootstrap one repo with the five-file `typescript-bun` template kit plus a `.release-please-manifest.json` seeded from the target's `package.json`.
- `agent-fleet tick [<name>]` — single Anthropic-loop iteration against one or every fleet entry; opens at most one summary issue per repo.
- `agent-fleet` (no args) — usage hint; exits `64`.
- Strict `fleet.yaml` schema (Pydantic-grade validation in pure Python).
- Sandbox: `gh`-only allowlist with a forbidden-prefix table for mutating subcommands, enforced before every shell call.
- DI-friendly: `AnthropicClient` and `ExecFn` are injectable — no network or real `gh` in CI.

## Install

```bash
pip install agent-fleet
```

## Quickstart

```bash
# Configure one repo:
cat > fleet.yaml <<'EOF'
fleet:
  - name: agent-id
    repo: yourname/agent-id
    path: ../agent-id
    template: typescript-bun
EOF

# Bootstrap the five-file kit + release-please manifest:
agent-fleet enroll agent-id
# enrolled agent-id: 6 files written

# Run one tick (reads ANTHROPIC_API_KEY from env, calls real gh):
ANTHROPIC_API_KEY=sk-ant-... agent-fleet tick agent-id
# tick agent-id: issue-created https://github.com/yourname/agent-id/issues/42
```

Library use with no network — both Anthropic and `gh` are stubbed — see [`examples/quickstart.py`](./examples/quickstart.py):

```bash
python examples/quickstart.py
# tick agent-id: issue-created https://github.com/yourname/agent-id/issues/123
```

## How it relates

| Repo | Role |
|---|---|
| [`agent-fleet`](https://github.com/p-vbordei/agent-fleet) | TypeScript reference (npm `@p-vbordei/agent-fleet`) — source of truth. |
| [`agent-fleet-py`](https://github.com/p-vbordei/agent-fleet-py) | Python port (this repo). |
| [`agent-fleet-rs`](https://github.com/p-vbordei/agent-fleet-rs) | Rust port. |

## Conformance + Security

The 78-test suite covers every clause in [SPEC.md](./SPEC.md):

- **C1** — enroll idempotency: second run produces a byte-identical tree.
- **C2** — enroll bounded write set: only the five template files (+ release-please manifest) are touched.
- **C3** — tick at-most-one issue: the loop refuses a second `gh issue create` in the same run.
- **C4** — tick read-only on code: forbidden-prefix table rejects mutating `gh pr/issue/release/repo/workflow/secret/variable/label` subcommands.
- **C5** — `fleet.yaml` strict schema: missing fields, extras, empty list, bad name/template all fail fast.
- **S1/S6** — secrets never appear in rendered prompts or sandbox rejection reasons.
- **S3** — sandbox rejects shell metacharacters (`|&;\`$<>(){}\\`) before any allowlist check.
- **S5** — `enroll` makes zero network calls (templates are vendored).

```bash
uv sync --extra dev
uv run pytest -v
# 78 passed
```

See the TS reference's [conformance suite](https://github.com/p-vbordei/agent-fleet/tree/main/conformance) for the canonical fixtures.

## Architecture

See [docs/architecture.md](docs/architecture.md).

## Development

```bash
git clone https://github.com/p-vbordei/agent-fleet-py
cd agent-fleet-py
uv sync --extra dev
uv run pytest -v
```

## License

Apache-2.0 — see [LICENSE](./LICENSE).
