"""Iteration prompt construction (FR-M2-003)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .models import Task
from .state import StateManager


class PromptBuilder:
    """Construct context-rich prompts for each agent iteration."""

    def __init__(self, project_dir: Path, state: StateManager) -> None:
        self.project_dir = Path(project_dir)
        self.state = state

    def build(self, task: Task, iteration: int, test_command: str) -> str:
        sections = [
            self._role_section(),
            self._task_section(task),
            self._test_section(test_command),
            self._progress_section(),
            self._git_section(),
            self._iteration_section(iteration),
        ]
        return "\n\n".join(sections)

    def _role_section(self) -> str:
        return """## Role and Rules

You are a software engineer working on a project. Your job is to complete exactly ONE task per session.

**Rules:**
1. Read the task description and acceptance criteria carefully.
2. Implement the changes needed to satisfy the acceptance criteria.
3. After making changes, run the test command to verify your work.
4. If tests pass, commit your changes with a message referencing the task ID.
5. If tests fail, read the error output and fix the issue. You may retry up to 3 times.
6. If you cannot fix after 3 attempts, discard all changes (git checkout .) and report the failure.
7. Before exiting, update prd.json to mark your task status.
8. Do NOT modify files outside the project directory.
9. Do NOT use git push, git rebase, or git reset --hard.
10. Write clean, secure code. Avoid common vulnerabilities (SQL injection, XSS, etc.)."""

    def _task_section(self, task: Task) -> str:
        criteria = "\n".join(f"- [ ] {c}" for c in task.acceptance_criteria)
        return f"""## Current Task

**ID:** {task.id}
**Title:** {task.title}
**Description:** {task.description}

**Acceptance Criteria:**
{criteria}"""

    def _test_section(self, test_command: str) -> str:
        return f"""## Testing

Run this command after making changes:
```
{test_command}
```
Only commit if tests pass."""

    def _progress_section(self) -> str:
        entries = self.state.read_progress(last_n=5)
        if not entries:
            return "## Recent Progress\n\nNo previous iterations."

        lines = []
        for e in entries:
            status = e.get("status", "?")
            task_id = e.get("task_id", "?")
            error = e.get("error", "")
            learnings = e.get("learnings", "")
            detail = error if status == "failed" else learnings
            lines.append(f"- Iteration {e.get('iteration', '?')}: {task_id} — {status}" +
                        (f" ({detail})" if detail else ""))

        return "## Recent Progress\n\n" + "\n".join(lines)

    def _git_section(self) -> str:
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                cwd=self.project_dir,
                capture_output=True, text=True, timeout=5,
            )
            log = result.stdout.strip() if result.returncode == 0 else "No git history"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            log = "Git unavailable"

        return f"## Recent Git History\n\n```\n{log}\n```"

    def _iteration_section(self, iteration: int) -> str:
        return f"## Iteration\n\nThis is iteration #{iteration}."
