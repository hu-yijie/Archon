"""Pre-loop sanity checks: driver availability, project state, env keys."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import typer

from archon import log
from archon.agent import CLAUDE_HARNESS
from archon.commands.tooling.inner_git import InnerGit
from archon.commands.tooling.project_config import (
    load_harness_descriptor,
    load_project_config,
    resolve_role_harness,
)
from archon.state import read_stage


def preflight(project_path: Path, state_dir: Path, dry_run: bool) -> None:
    """Verify the selected driver is installed/auth'd and the project is init'd."""
    progress = state_dir / "PROGRESS.md"

    if not dry_run:
        _check_selected_drivers(project_path)

    if not progress.exists():
        log.error(f"No project state found. Run: archon init {project_path}")
        raise typer.Exit(1)
    stage = read_stage(progress)
    if stage == "init":
        log.error(f"Project is still in init stage. Run: archon init {project_path}")
        raise typer.Exit(1)


def _check_selected_drivers(project_path: Path) -> None:
    cfg = load_project_config(project_path)
    roles = ("plan", "prover", "review")
    runners = {
        load_harness_descriptor(
            cfg, resolve_role_harness(cfg, role),
        ).runner
        for role in roles
    }
    if "codex" in runners:
        _check_codex()
    if CLAUDE_HARNESS in runners:
        _check_claude()


def _check_codex() -> None:
    try:
        r = subprocess.run(
            ["codex", "login", "status"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        log.error("Codex CLI is not installed. Run: archon setup")
        raise typer.Exit(1) from None
    if r.returncode == 127 or "No such file" in (r.stderr or ""):
        log.error("Codex CLI is not installed. Run: archon setup")
        raise typer.Exit(1)
    if r.returncode != 0:
        log.error("Codex CLI is not authenticated. Run: codex login")
        raise typer.Exit(1)
    log.success("Codex CLI is authenticated and ready")


def _check_claude() -> None:
    try:
        r = subprocess.run(
            ["claude", "-p", "reply with OK", "--no-session-persistence"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        log.error("Claude Code is not installed. Run: archon setup")
        raise typer.Exit(1) from None
    if r.returncode == 127 or "No such file" in (r.stderr or ""):
        log.error("Claude Code is not installed. Run: archon setup")
        raise typer.Exit(1)
    if r.returncode != 0:
        log.error("Claude Code cannot run. Check: claude auth, ANTHROPIC_API_KEY, network.")
        raise typer.Exit(1)
    log.success("Claude Code is authenticated and ready")


def warn_if_lake_unbuilt(project_path: Path) -> None:
    """Warn (don't fail) when the project looks unbuilt.

    A cold ``.lake/build`` is the most common cause of the LSP MCP
    server returning ``success: false`` on the prover's first query —
    which the model historically misread as "the tool doesn't exist"
    and fell back to running ``lean_goal`` as a shell command (which
    obviously fails). Surfacing this up front gives the user a chance
    to ``lake build`` before burning a prover round on a cold cache.

    Skipped silently when there's no ``lakefile.lean`` / ``lakefile.toml``
    (not a Lake project, nothing to warn about).
    """
    has_lake = (
        (project_path / "lakefile.lean").exists()
        or (project_path / "lakefile.toml").exists()
    )
    if not has_lake:
        return
    build_dir = project_path / ".lake" / "build"
    if build_dir.is_dir() and any(build_dir.iterdir()):
        return

    log.warn(
        "No .lake/build artifacts found. The Lean LSP MCP server "
        "may return success: false on its first call and the prover "
        "could waste effort interpreting that as a missing tool. "
        "Consider running `lake build` once before starting the loop."
    )


def warn_if_inner_dirty(project_path: Path) -> None:
    """If the inner git has leftover state, tell the user; do not block."""
    inner = InnerGit(project_path)
    if not inner.is_initialized() or not inner.is_dirty():
        return

    log.warn(
        "Inner git has uncommitted agent work — leftover from a previous "
        "run or manual edits. This is fine: the loop will pick up whatever "
        "is on disk, and the next phase commit will capture it."
    )


def check_informal_agent_keys() -> None:
    """Warn (don't fail) if no external-LLM key is set for the informal agent."""
    keys = ("OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY")
    if not any(os.environ.get(k) for k in keys):
        log.warn(
            "No API keys for informal agent "
            "(OPENAI_API_KEY / GEMINI_API_KEY / OPENROUTER_API_KEY)"
        )
        log.step(
            "Provers will work without it, but may struggle on hard sorries "
            "where external LLM help would be useful."
        )
