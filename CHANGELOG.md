# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-04-25

### Added

- Initial Python port of [`@p-vbordei/agent-fleet`](https://github.com/p-vbordei/agent-fleet) v0.1.3.
- `agent-fleet` CLI with two subcommands:
  - `enroll <name>` — install the five-file `typescript-bun` template kit into a target repo and seed `.release-please-manifest.json` from the target's `package.json`.
  - `tick [<name>]` — single Anthropic-loop iteration that may open at most one summary issue per fleet entry.
- `fleet.yaml` strict schema (C5): required `name`/`repo`/`path`/`template`, no extras, non-empty list, name pattern `^[a-z0-9][a-z0-9-]*$`, template restricted to `typescript-bun`.
- `gh`-only command allowlist (S3, S4, C4): shell-metacharacter gate + 30+ forbidden-prefix table + `gh api` mutating-verb path restriction.
- C3 single-issue interlock inside `tick_one`: a second `gh issue create` in the same run returns a `tool_result` error to the model without executing.
- Dependency injection: `AnthropicClient` (any object exposing `.messages.create(**kwargs)`) and `ExecFn` (`Callable[[str], ExecResult]`) are injectable via `TickDeps`. Real CLI wires the `anthropic` SDK and `subprocess.run`; tests pass pure callables.
- 78 tests across `test_config`, `test_enroll`, `test_prompts`, `test_sandbox`, `test_tick`, `test_security`, `test_conformance`, `test_cli` — every GitHub and Anthropic call is mocked; no network in CI.
- Vendored template kit at `templates/typescript-bun/`, packaged into the wheel as `agent_fleet/_data/templates/`.
- Apache-2.0 license.

[0.1.0]: https://github.com/p-vbordei/agent-fleet-py/releases/tag/v0.1.0
