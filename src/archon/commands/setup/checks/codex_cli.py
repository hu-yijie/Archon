"""Check OpenAI Codex CLI availability."""

from __future__ import annotations

from archon import log

from ..shell import has, version
from .base import DependencyCheck


class CodexCliCheck(DependencyCheck):
    name = "Codex CLI"

    def run(self) -> bool:
        if has("codex"):
            log.success(f"Codex CLI: {version(['codex', '--version'])}")
            return True

        log.error("Codex CLI is not installed")
        log.step("Install it with your preferred OpenAI Codex CLI installation method, then run: codex login")
        return False
