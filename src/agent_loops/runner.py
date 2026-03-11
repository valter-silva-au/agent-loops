"""Agent runner: Claude Agent SDK wrapper (FR-M2-006)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .models import IterationResult, Provider


@dataclass
class RunnerConfig:
    model: str = ""
    provider: Provider = Provider.BEDROCK
    max_turns: int = 50
    per_iteration_budget_usd: float = 5.0
    project_dir: Path = Path(".")


class AgentRunner:
    """Configure and invoke a single Claude Agent SDK session."""

    ALLOWED_TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
    SYSTEM_PROMPT = (
        "You are a software engineer. Complete the task described in the user prompt. "
        "Follow all rules exactly. Run tests after changes. Commit on success. "
        "Report failure clearly if you cannot complete the task."
    )

    def __init__(self, config: RunnerConfig, pre_hooks: list | None = None, post_hooks: list | None = None) -> None:
        self.config = config
        self.pre_hooks = pre_hooks or []
        self.post_hooks = post_hooks or []

    def _build_env(self) -> dict[str, str]:
        """Build environment variables for the Agent SDK session."""
        # Prevent nested session detection when running inside Claude Code
        env: dict[str, str] = {"CLAUDECODE": ""}

        if self.config.provider == Provider.BEDROCK:
            env["CLAUDE_CODE_USE_BEDROCK"] = "1"
            # Forward AWS credentials from current environment
            for key in (
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_SESSION_TOKEN",
                "AWS_REGION",
                "AWS_PROFILE",
                "AWS_BEARER_TOKEN_BEDROCK",
            ):
                val = os.environ.get(key)
                if val:
                    env[key] = val
        return env

    async def run_iteration(self, prompt: str) -> IterationResult:
        """Run a single agent iteration via the Claude Agent SDK."""
        try:
            from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, query, ResultMessage, AssistantMessage
        except ImportError:
            print("[ERROR] claude-agent-sdk not installed. Cannot run agent.", file=sys.stderr)
            return IterationResult(success=False, error="claude-agent-sdk not installed")

        hooks: dict[str, list] = {}
        if self.pre_hooks:
            hooks["PreToolUse"] = [HookMatcher(hooks=self.pre_hooks)]
        if self.post_hooks:
            hooks["PostToolUse"] = [HookMatcher(hooks=self.post_hooks)]

        options = ClaudeAgentOptions(
            allowed_tools=self.ALLOWED_TOOLS,
            system_prompt=self.SYSTEM_PROMPT,
            permission_mode="bypassPermissions",
            cwd=self.config.project_dir,
            model=self.config.model,
            max_turns=self.config.max_turns,
            max_budget_usd=self.config.per_iteration_budget_usd,
            hooks=hooks if hooks else None,
            env=self._build_env(),
        )

        total_cost = 0.0
        input_tokens = 0
        output_tokens = 0
        tool_calls = 0
        error: str | None = None
        got_result = False

        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, ResultMessage):
                    if hasattr(message, "total_cost_usd") and message.total_cost_usd:
                        total_cost = message.total_cost_usd
                    if hasattr(message, "total_input_tokens"):
                        input_tokens = message.total_input_tokens or 0
                    if hasattr(message, "total_output_tokens"):
                        output_tokens = message.total_output_tokens or 0
                    got_result = True
        except Exception as e:
            # The SDK may throw after yielding ResultMessage (process cleanup).
            # If we already got a result with cost, the agent DID run successfully.
            if not got_result:
                error = str(e)

        success = got_result

        return IterationResult(
            success=success,
            cost_usd=total_cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_calls=tool_calls,
            error=error,
        )
