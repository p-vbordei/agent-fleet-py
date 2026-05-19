# Contributing to agent-fleet (Python)

Thanks for your interest. This port mirrors the behaviour of the [TypeScript reference](https://github.com/p-vbordei/agent-fleet) — please file behavioural-deviation reports against [SPEC.md](./SPEC.md), not against subjective preference.

## Development setup

```bash
git clone https://github.com/p-vbordei/agent-fleet-py
cd agent-fleet-py
uv sync --extra dev
uv run pytest -v       # 78 tests, <1s
uv run ruff check .
uv run mypy src
```

## Pull requests

- One topic per PR. Reference the SPEC clause (e.g. "C4: extend sandbox to cover `gh extension install`").
- Tests are mandatory for any behaviour change.
- Public API additions must update both `__all__` in `src/agent_fleet/__init__.py` and the architecture doc.
- Match the existing style: type-annotated, `from __future__ import annotations`, dataclasses where appropriate.

## Testing policy (read this)

**Never let this port hit real GitHub or real Anthropic in unit tests.** Always inject mocks:

- For the Anthropic client, pass any object exposing `.messages.create(**kwargs)` into `TickDeps.anthropic`. See `tests/test_tick.py` for the `FakeClient` pattern.
- For `gh`, pass a `Callable[[str], ExecResult]` into `TickDeps.exec`. The real `subprocess.run` wrapper lives only in `cli.py` and is exercised exclusively via CLI integration tests with the subprocess patched.
- For sockets, `tests/test_security.py::test_s5_enroll_does_not_make_network_calls` monkeypatches `socket.create_connection` and asserts it is never called.

A test that requires network access will be rejected.

## Releases

Releases are tagged `vX.Y.Z` on `main`. The wheel is built by `hatch build` and published to PyPI. The template kit version is implicitly pinned to the agent-fleet release — bumping templates requires a new release.

## License

By contributing you agree your contributions are licensed under Apache-2.0 (see [LICENSE](./LICENSE)).
