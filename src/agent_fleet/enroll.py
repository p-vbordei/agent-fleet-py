"""enroll — write the typescript-bun kit into a target repo (SPEC §3.1)."""

from __future__ import annotations

import json
from pathlib import Path

from agent_fleet.config import FleetEntry


class EnrollError(Exception):
    """Raised when the target path is missing or template is unknown."""


def _walk(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def enroll(entry: FleetEntry, templates_root: str | Path) -> dict[str, list[str]]:
    target = Path(entry.path)
    if not target.exists() or not target.is_dir():
        raise EnrollError(
            f"target path does not exist or is not a directory: {entry.path}"
        )
    tpl_dir = Path(templates_root) / entry.template
    if not tpl_dir.exists():
        raise EnrollError(
            f"template not found: {entry.template} (looked in {tpl_dir})"
        )

    variables = {"name": entry.name, "repo": entry.repo}
    written: list[str] = []
    for src in _walk(tpl_dir):
        rel = src.relative_to(tpl_dir)
        dest = target / rel
        raw = src.read_text(encoding="utf-8")
        rendered = raw
        for key, val in variables.items():
            rendered = rendered.replace("{{" + key + "}}", val)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered, encoding="utf-8")
        written.append(str(rel).replace("\\", "/"))

    # Bootstrap release-please manifest from target's current package.json version.
    pkg_path = target / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
            version = pkg.get("version", "0.0.0")
            if not isinstance(version, str):
                version = "0.0.0"
            manifest_path = target / ".release-please-manifest.json"
            manifest_path.write_text(
                json.dumps({".": version}, indent=2) + "\n", encoding="utf-8"
            )
            written.append(".release-please-manifest.json")
        except Exception:
            pass

    return {"written": written}
