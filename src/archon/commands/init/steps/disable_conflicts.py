"""Disable globally-installed lean4-skills plugins for this project."""

from __future__ import annotations

from archon import log

from ..utils import find_global_lean4_plugins, run
from .base import InitStep


class DisableConflictingPluginsStep(InitStep):
    name = "Checking for conflicting global lean4-skills"
    number = 7

    def run(self) -> None:
        ctx = self.ctx
        log.phase(self.number, self.name)
        if not _project_uses_claude(ctx.project_path):
            log.step("Codex harness selected — no Claude plugin conflicts to disable")
            return
        conflicting = find_global_lean4_plugins()
        if not conflicting:
            log.success("No conflicting global lean4-skills detected")
            return
        log.warn(f"Found {len(conflicting)} conflicting plugin(s) in global config")
        for name in conflicting:
            r = run(
                ["claude", "plugin", "disable", name, "--scope", "project"],
                cwd=ctx.project_path,
            )
            if r.returncode == 0:
                log.success(f"Disabled '{name}' for this project")
            else:
                log.warn(f"Could not auto-disable '{name}'")


def _project_uses_claude(project_path) -> bool:
    from archon.agent import CLAUDE_HARNESS
    from archon.commands.tooling.project_config import (
        load_harness_descriptor,
        load_project_config,
        resolve_role_harness,
    )

    cfg = load_project_config(project_path)
    for role in ("plan", "prover", "review"):
        name = resolve_role_harness(cfg, role)
        if load_harness_descriptor(cfg, name).runner == CLAUDE_HARNESS:
            return True
    return False
