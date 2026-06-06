"""Register the lean-lsp MCP server in Claude config when Claude is selected."""

from __future__ import annotations

from pathlib import Path

from archon import log

from ..utils import data_path, find_global_mcp_lean_lsp, run
from .base import InitStep


class LeanLspMcpStep(InitStep):
    name = "Installing lean-lsp MCP server (project scope)"
    number = 5

    def run(self) -> None:
        ctx = self.ctx
        log.phase(self.number, self.name)

        if not _project_uses_claude(ctx.project_path):
            log.step(
                "Codex harness selected — skipping Claude MCP registration "
                "(Codex receives Lean LSP via per-invocation config)"
            )
            return

        lean_lsp_dir = data_path("tools/lean-lsp-mcp")

        existing = run(["claude", "mcp", "list"], cwd=ctx.project_path)
        already_registered = "archon-lean-lsp" in (existing.stdout or "")

        if already_registered:
            log.step("Found existing archon-lean-lsp. Removing to refresh paths...")
            run(
                ["claude", "mcp", "remove", "archon-lean-lsp", "-s", "project"],
                cwd=ctx.project_path,
            )

        for name in find_global_mcp_lean_lsp():
            log.warn(f"Found conflicting MCP server '{name}' in global config")
            run(
                ["claude", "mcp", "remove", name, "-s", "project"],
                cwd=ctx.project_path,
            )
            log.success(f"Disabled '{name}' for this project")

        r = run(
            ["claude", "mcp", "add", "archon-lean-lsp", "-s", "project", "--",
             "uv", "run", "--directory", str(lean_lsp_dir), "lean-lsp-mcp"],
            cwd=ctx.project_path,
        )
        output = r.stdout + r.stderr
        if "already exists" in output.lower():
            log.success("archon-lean-lsp already configured")
        elif r.returncode == 0:
            log.success("archon-lean-lsp added")
        else:
            log.error(f"Failed to add archon-lean-lsp: {output.strip()}")


def _project_uses_claude(project_path: Path) -> bool:
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
