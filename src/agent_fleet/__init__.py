"""agent-fleet — Autonomous OSS-repo health for solo maintainers.

Python port of @p-vbordei/agent-fleet.
"""

from agent_fleet.config import FleetConfig, FleetConfigError, FleetEntry, load_fleet_config
from agent_fleet.enroll import EnrollError, enroll
from agent_fleet.prompts import TICK_PROMPT, render_tick_prompt
from agent_fleet.sandbox import AllowResult, is_allowed_command
from agent_fleet.tick import ExecResult, TickDeps, TickOutcome, tick_one

__version__ = "0.1.0"

__all__ = [
    "FleetConfig",
    "FleetConfigError",
    "FleetEntry",
    "load_fleet_config",
    "enroll",
    "EnrollError",
    "TICK_PROMPT",
    "render_tick_prompt",
    "AllowResult",
    "is_allowed_command",
    "ExecResult",
    "TickDeps",
    "TickOutcome",
    "tick_one",
    "__version__",
]
