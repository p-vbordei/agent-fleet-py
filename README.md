# agent-fleet (Python)

> Autonomous OSS-repo health for solo maintainers. Python port of [@p-vbordei/agent-fleet](https://github.com/p-vbordei/agent-fleet).

[![CI](https://github.com/p-vbordei/agent-fleet-py/actions/workflows/ci.yml/badge.svg)](https://github.com/p-vbordei/agent-fleet-py/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](./LICENSE)

One config, one cron, N repos kept reviewed and dep-current. Single binary, no daemon, no DB.

## Install

```bash
pip install agent-fleet
```

## Two commands

```bash
agent-fleet enroll <name>     # install renovate + release-please + claude-review into a repo
agent-fleet tick [<name>]     # weekly cron-driven health check, opens one summary issue
```

## Example

```yaml
# fleet.yaml
fleet:
  - name: agent-id
    repo: p-vbordei/agent-id
    path: ../agent-id
    template: typescript-bun
```

```bash
agent-fleet enroll agent-id
# enrolled agent-id: 5 files written

ANTHROPIC_API_KEY=... GH_TOKEN=... agent-fleet tick
# tick agent-id: issue-created https://github.com/p-vbordei/agent-id/issues/42
```

## What it is NOT

- Not a release publisher — that's [`agent-publish`](https://github.com/p-vbordei/agent-publish).
- Not a launch-day agent — that's [`agent-launch`](https://github.com/p-vbordei/agent-launch).
- Not a code reviewer — delegated to `anthropics/claude-code-action` running per-repo (installed by `enroll`).
- Not a monorepo tool. Each enrolled repo stays standalone.
- v0.1 supports `typescript-bun` repos only.

## Conformance

This port passes the same five conformance clauses as the TS reference:

- **C1** — enroll idempotency
- **C2** — enroll bounded write set (5 files)
- **C3** — tick at-most-one issue per run
- **C4** — tick read-only on code (gh sandbox)
- **C5** — fleet.yaml strict schema

Run `pytest -v` from a checkout to verify.

## Reference

- TypeScript reference: <https://github.com/p-vbordei/agent-fleet>
- Rust sibling port: <https://github.com/p-vbordei/agent-fleet-rs>
- Spec: [SPEC.md](./SPEC.md)

## License

Apache 2.0 — see [LICENSE](./LICENSE).
