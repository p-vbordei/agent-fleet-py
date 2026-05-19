"""fleet.yaml parser + strict validator (SPEC §2.1, C5)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
REPO_RE = re.compile(r"^[^/]+/[^/]+$")
VALID_TEMPLATES = frozenset({"typescript-bun"})
ENTRY_KEYS = frozenset({"name", "repo", "path", "template"})
ROOT_KEYS = frozenset({"fleet"})


class FleetConfigError(Exception):
    """Raised on any fleet.yaml load or validation failure."""


@dataclass(frozen=True)
class FleetEntry:
    name: str
    repo: str
    path: str
    template: str


@dataclass(frozen=True)
class FleetConfig:
    fleet: tuple[FleetEntry, ...]


def _validate_entry(raw: Any, index: int) -> FleetEntry:
    if not isinstance(raw, dict):
        raise FleetConfigError(f"fleet.{index}: entry must be a mapping")
    keys = set(raw.keys())
    missing = ENTRY_KEYS - keys
    extra = keys - ENTRY_KEYS
    if missing:
        raise FleetConfigError(
            f"fleet.{index}: missing required field(s): {', '.join(sorted(missing))}"
        )
    if extra:
        raise FleetConfigError(
            f"fleet.{index}: unrecognized extra field(s): {', '.join(sorted(extra))}"
        )
    name = raw["name"]
    repo = raw["repo"]
    path = raw["path"]
    template = raw["template"]
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise FleetConfigError(
            f"fleet.{index}.name: name must match ^[a-z0-9][a-z0-9-]*$"
        )
    if not isinstance(repo, str) or not REPO_RE.match(repo):
        raise FleetConfigError(f'fleet.{index}.repo: repo must be "owner/name"')
    if not isinstance(path, str) or len(path) == 0:
        raise FleetConfigError(f"fleet.{index}.path: path must be a non-empty string")
    if not isinstance(template, str) or template not in VALID_TEMPLATES:
        raise FleetConfigError(
            f"fleet.{index}.template: template must be one of {sorted(VALID_TEMPLATES)}"
        )
    return FleetEntry(name=name, repo=repo, path=path, template=template)


def load_fleet_config(path: str | Path) -> FleetConfig:
    p = Path(path)
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except Exception as err:
        raise FleetConfigError(f"failed to read or parse {p}: {err}") from err

    if not isinstance(raw, dict):
        raise FleetConfigError("invalid fleet.yaml: root must be a mapping")
    keys = set(raw.keys())
    extra = keys - ROOT_KEYS
    if extra:
        raise FleetConfigError(
            f"invalid fleet.yaml: unrecognized extra key(s): {', '.join(sorted(extra))}"
        )
    if "fleet" not in raw:
        raise FleetConfigError("invalid fleet.yaml: missing required key 'fleet'")
    fleet = raw["fleet"]
    if not isinstance(fleet, list):
        raise FleetConfigError("invalid fleet.yaml: 'fleet' must be a list")
    if len(fleet) == 0:
        raise FleetConfigError("invalid fleet.yaml: fleet must contain at least one entry")
    entries = tuple(_validate_entry(item, i) for i, item in enumerate(fleet))
    return FleetConfig(fleet=entries)
