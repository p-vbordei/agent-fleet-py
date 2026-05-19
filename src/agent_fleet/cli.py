"""CLI dispatch (SPEC §3)."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from agent_fleet.config import FleetConfigError, load_fleet_config
from agent_fleet.enroll import EnrollError, enroll
from agent_fleet.tick import ExecResult, TickDeps, tick_one

app = typer.Typer(
    add_completion=False,
    help="Autonomous OSS-repo health for solo maintainers.",
    no_args_is_help=False,
    invoke_without_command=True,
)


def _templates_root() -> Path:
    """Locate the templates directory.

    1. Wheel install: <package>/_data/templates
    2. Source checkout: <repo-root>/templates
    """
    pkg_data = Path(__file__).resolve().parent / "_data" / "templates"
    if pkg_data.exists():
        return pkg_data
    src_root = Path(__file__).resolve().parent.parent.parent / "templates"
    return src_root


def _load_or_exit():
    cfg_path = Path.cwd() / "fleet.yaml"
    try:
        cfg = load_fleet_config(cfg_path)
    except FileNotFoundError:
        typer.echo(f"fleet.yaml not found at {cfg_path}", err=True)
        raise typer.Exit(1)
    except FleetConfigError as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(1)
    return cfg, cfg_path


@app.callback()
def _main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo("Usage: agent-fleet <enroll|tick> [args]", err=True)
        raise typer.Exit(64)


@app.command("enroll")
def enroll_cmd(name: str = typer.Argument(..., metavar="<name>")) -> None:
    """Install the template kit into a fleet entry's target path."""
    cfg, _ = _load_or_exit()
    entry = next((e for e in cfg.fleet if e.name == name), None)
    if entry is None:
        typer.echo(f"fleet entry not found: {name}", err=True)
        raise typer.Exit(1)
    try:
        result = enroll(entry, _templates_root())
    except EnrollError as err:
        typer.echo(str(err), err=True)
        raise typer.Exit(2)
    except Exception as err:  # noqa: BLE001
        typer.echo(str(err), err=True)
        raise typer.Exit(3)
    typer.echo(f"enrolled {name}: {len(result['written'])} files written")


def _gh_exec(cmd: str) -> ExecResult:
    # NB: sandbox.is_allowed_command rejects shell metacharacters before we get here,
    # so shell=True is safe; matches the TS reference's spawnSync behaviour.
    r = subprocess.run(  # noqa: S602
        cmd, shell=True, capture_output=True, text=True
    )
    return ExecResult(
        stdout=r.stdout or "", stderr=r.stderr or "", code=r.returncode
    )


@app.command("tick")
def tick_cmd(
    name: Optional[str] = typer.Argument(None, metavar="[<name>]"),
) -> None:
    """Run the weekly health check, optionally scoped to one fleet entry."""
    cfg, _ = _load_or_exit()
    entries = [e for e in cfg.fleet if e.name == name] if name else list(cfg.fleet)
    if len(entries) == 0:
        typer.echo(f"no fleet entries match: {name}", err=True)
        raise typer.Exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        typer.echo("ANTHROPIC_API_KEY not set", err=True)
        raise typer.Exit(4)

    try:
        from anthropic import Anthropic
    except ImportError as err:
        typer.echo(f"anthropic SDK not installed: {err}", err=True)
        raise typer.Exit(4)

    client = Anthropic(api_key=api_key)
    deps = TickDeps(
        anthropic=client,
        exec=_gh_exec,
        now=lambda: datetime.now(timezone.utc),
    )

    any_error = False
    for entry in entries:
        try:
            result = tick_one(entry, deps)
            if result.outcome == "issue-created":
                typer.echo(f"tick {entry.name}: issue-created {result.url}")
            elif result.outcome == "no-findings":
                typer.echo(f"tick {entry.name}: no-findings")
            else:
                any_error = True
                typer.echo(f"tick {entry.name}: error {result.message}")
        except Exception as err:  # noqa: BLE001
            any_error = True
            typer.echo(f"tick {entry.name}: error {err}")

    raise typer.Exit(1 if any_error else 0)


# Silence unused-import warnings.
_ = sys


if __name__ == "__main__":
    app()
