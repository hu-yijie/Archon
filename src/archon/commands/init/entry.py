"""Typer-decorated `init` entry point."""

from __future__ import annotations

import typer

from .command import InitCommand


def init(
    project_path: str = typer.Argument(
        None,
        help="Path to Lean project (directory containing lakefile.lean/toml). "
        "If omitted, prompts for a name and creates the project.",
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Skip the re-init prompt and overwrite existing Archon files.",
    ),
    model: str | None = typer.Option(
        None, "--model", "-M",
        help="Model override for Claude Code harnesses. The default Codex "
             "harness uses the codex-gpt descriptor model.",
    ),
    harness: str = typer.Option(
        None, "--harness",
        help="Engine for the loop's roles (plan/prover/review): "
             "'codex-gpt' (default, native ~/.codex login), 'claude-code', "
             "or 'mixed' (pick per role, interactive). Omit to be asked at "
             "init time.",
    ),
) -> None:
    """Initialize a new Archon project.

    Runs the deterministic bootstrap (lake init, Mathlib, blueprint, workspace
    skeletons) in Python, then hands off to the configured agent driver for
    the semantic pass only: reorganizing reference files, writing
    README/summary.md prose, and proposing initial objectives.

    [bold]Examples:[/bold]
      [cyan]archon init .[/cyan]
      [cyan]archon init /path/to/lean-project[/cyan]
    """
    InitCommand(project_path, force=force, model=model, harness=harness).run()
