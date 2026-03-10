"""Loop engine: orchestrates the Ralph Wiggum build loop (FR-M2-001)."""

from __future__ import annotations

import asyncio
import random
import subprocess
import sys
import time
from pathlib import Path

from .models import (
    BudgetStatus,
    GutterStatus,
    LoopConfig,
    LoopResult,
    ProgressEntry,
    TaskStatus,
)
from .prompt import PromptBuilder
from .runner import AgentRunner, RunnerConfig
from .safety.budget import BudgetTracker
from .safety.gutter import GutterDetector
from .safety.kill import KillSwitch
from .spec import SpecParser
from .state import StateManager


class LoopEngine:
    """Orchestrate the autonomous build loop."""

    MAX_CONSECUTIVE_API_ERRORS = 5
    BACKOFF_BASE = 1.0
    BACKOFF_MAX = 60.0
    LOW_SUCCESS_RATE_THRESHOLD = 0.40
    LOW_SUCCESS_RATE_WINDOW = 10

    def __init__(self, config: LoopConfig) -> None:
        self.config = config
        self.state = StateManager(config.project_dir)
        self.budget_tracker = BudgetTracker(config.budget_usd, self.state)
        self.gutter_detector = GutterDetector(threshold=3)
        self.kill_switch = KillSwitch(config.project_dir)
        self.prompt_builder = PromptBuilder(config.project_dir, self.state)

    async def run(self) -> LoopResult:
        """Run the main loop. Returns when a termination condition is met."""
        self._validate_git_state()
        self.kill_switch.install_signal_handler()

        spec_data = self.state.read_spec()
        spec = SpecParser(spec_data)

        runner_config = RunnerConfig(
            model=self.config.model,
            max_turns=self.config.max_turns_per_iteration,
            per_iteration_budget_usd=min(5.0, self.budget_tracker.remaining),
            project_dir=self.config.project_dir,
        )
        runner = AgentRunner(config=runner_config)

        consecutive_api_errors = 0
        exit_reason = "unknown"

        try:
            for iteration in range(1, self.config.max_iterations + 1):
                # Check termination conditions
                if self.kill_switch.check():
                    exit_reason = "kill_switch"
                    break

                if self.budget_tracker.check() == BudgetStatus.EXCEEDED:
                    exit_reason = "budget_exceeded"
                    break

                if spec.is_complete():
                    exit_reason = "all_tasks_complete"
                    break

                # Select next task
                task = spec.next_task()
                if task is None:
                    exit_reason = "no_available_tasks"
                    break

                # Check gutter detection
                progress = self.state.read_progress(last_n=10)
                gutter_status = self.gutter_detector.check(progress, task.id)
                if gutter_status == GutterStatus.BLOCKED:
                    spec.mark_blocked(task.id, "Gutter detection: consecutive failures")
                    self.state.write_spec(spec.to_dict())
                    self.state.append_progress(ProgressEntry(
                        iteration=iteration,
                        task_id=task.id,
                        status="blocked",
                        learnings="Blocked by gutter detection after consecutive failures",
                    ))
                    continue

                # Check success rate
                self._check_success_rate(progress)

                # Build prompt and run agent
                # Check if this is the last pending task (trigger finalization)
                pending_count = sum(1 for t in spec.tasks if t.status == TaskStatus.PENDING)
                is_final = pending_count == 1
                prompt = self.prompt_builder.build(
                    task, iteration, spec.test_command,
                    is_final=is_final, deploy_target=spec.deploy_target,
                )

                print(f"[Iteration {iteration}] Working on {task.id}: {task.title}", file=sys.stderr)

                # Update per-iteration budget cap
                runner.config.per_iteration_budget_usd = min(5.0, self.budget_tracker.remaining)

                result = await runner.run_iteration(prompt)

                # Handle API errors with backoff
                if result.error and not result.success:
                    consecutive_api_errors += 1
                    if consecutive_api_errors >= self.MAX_CONSECUTIVE_API_ERRORS:
                        exit_reason = "api_errors"
                        self.state.append_progress(ProgressEntry(
                            iteration=iteration,
                            task_id=task.id,
                            status="failed",
                            error=result.error,
                        ))
                        break

                    backoff = min(
                        self.BACKOFF_BASE * (2 ** (consecutive_api_errors - 1)),
                        self.BACKOFF_MAX,
                    ) + random.uniform(0, 1)
                    print(f"[Iteration {iteration}] API error, retrying in {backoff:.1f}s: {result.error}", file=sys.stderr)
                    await asyncio.sleep(backoff)

                    self.state.append_progress(ProgressEntry(
                        iteration=iteration,
                        task_id=task.id,
                        status="failed",
                        error=result.error,
                    ))
                    continue
                else:
                    consecutive_api_errors = 0

                # Record budget
                self.budget_tracker.record(
                    iteration=iteration,
                    cost_usd=result.cost_usd,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                )

                # Check outcome via git state
                iteration_success = self._check_git_outcome()

                if iteration_success:
                    spec.mark_done(task.id)
                    self.state.write_spec(spec.to_dict())
                    self.state.append_progress(ProgressEntry(
                        iteration=iteration,
                        task_id=task.id,
                        status="success",
                        changes=self._get_changed_files(),
                    ))
                else:
                    self._discard_uncommitted_changes()
                    self.state.append_progress(ProgressEntry(
                        iteration=iteration,
                        task_id=task.id,
                        status="failed",
                        error=result.error or "No commit produced",
                    ))
            else:
                exit_reason = "max_iterations_reached"
        finally:
            self.kill_switch.uninstall_signal_handler()

        summary = spec.summary()
        return LoopResult(
            iterations_completed=sum(1 for _ in self.state.read_progress(last_n=0) or []) if False else iteration,
            tasks_done=summary.get("done", 0),
            tasks_pending=summary.get("pending", 0),
            tasks_failed=summary.get("failed", 0),
            tasks_blocked=summary.get("blocked", 0),
            total_cost_usd=self.budget_tracker.cumulative_cost,
            exit_reason=exit_reason,
        )

    def _validate_git_state(self) -> None:
        """Ensure the project dir is a git repo with a clean working tree."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.config.project_dir,
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                raise RuntimeError("Target directory must be a git repository")
        except FileNotFoundError:
            raise RuntimeError("git is not installed")

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.config.project_dir,
            capture_output=True, text=True, timeout=5,
        )
        # Filter out .agent-loops/ (framework state directory)
        dirty_lines = [
            line for line in result.stdout.strip().splitlines()
            if not line.lstrip(" ?MA").startswith(".agent-loops/")
        ]
        if dirty_lines:
            raise RuntimeError(
                "Clean working tree required. Commit or stash changes first."
            )

    def _check_git_outcome(self) -> bool:
        """Check if the agent produced a new commit (success) or left dirty state (failure).

        Ignores .agent-loops/ directory which contains framework state files.
        """
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.config.project_dir,
            capture_output=True, text=True, timeout=5,
        )
        # Filter out .agent-loops/ entries (framework state, not project code)
        lines = [
            line for line in result.stdout.strip().splitlines()
            if not line.lstrip(" ?MA").startswith(".agent-loops/")
        ]
        return len(lines) == 0

    def _discard_uncommitted_changes(self) -> None:
        """Discard all uncommitted changes to restore clean state."""
        subprocess.run(
            ["git", "checkout", "."],
            cwd=self.config.project_dir,
            capture_output=True, timeout=5,
        )
        subprocess.run(
            ["git", "clean", "-fd"],
            cwd=self.config.project_dir,
            capture_output=True, timeout=5,
        )

    def _get_changed_files(self) -> list[str]:
        """Get list of files changed in the most recent commit."""
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            cwd=self.config.project_dir,
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split("\n") if f]
        return []

    def _check_success_rate(self, progress: list[dict]) -> None:
        """Log warning if success rate drops below threshold."""
        if len(progress) < self.LOW_SUCCESS_RATE_WINDOW:
            return
        recent = progress[-self.LOW_SUCCESS_RATE_WINDOW:]
        successes = sum(1 for e in recent if e.get("status") == "success")
        rate = successes / len(recent)
        if rate < self.LOW_SUCCESS_RATE_THRESHOLD:
            print(
                f"[WARNING] Success rate is {rate:.0%} over last {len(recent)} iterations "
                f"(threshold: {self.LOW_SUCCESS_RATE_THRESHOLD:.0%})",
                file=sys.stderr,
            )
