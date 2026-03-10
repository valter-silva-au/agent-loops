"""Spec parser for prd.json: validation, task selection, and status management."""

from __future__ import annotations

from .models import Task, TaskStatus


class SpecValidationError(Exception):
    """Raised when prd.json fails schema validation."""


class SpecParser:
    """Parse, validate, and manage a prd.json product spec."""

    REQUIRED_TOP_LEVEL = {"name", "test_command", "tasks"}
    REQUIRED_TASK_FIELDS = {"id", "title", "description", "acceptance_criteria", "status", "dependencies"}

    def __init__(self, spec: dict) -> None:
        self._raw = spec
        self._validate(spec)
        self.name: str = spec["name"]
        self.test_command: str = spec["test_command"]
        self.deploy_target: str | None = spec.get("deploy_target")
        self.tasks: list[Task] = [self._parse_task(t) for t in spec["tasks"]]

    def _validate(self, spec: dict) -> None:
        missing = self.REQUIRED_TOP_LEVEL - set(spec.keys())
        if missing:
            raise SpecValidationError(f"Missing required top-level fields: {missing}")

        if not isinstance(spec["tasks"], list):
            raise SpecValidationError("'tasks' must be a list")

        if len(spec["tasks"]) == 0:
            raise SpecValidationError("'tasks' must contain at least one task")

        task_ids = set()
        for i, task in enumerate(spec["tasks"]):
            task_missing = self.REQUIRED_TASK_FIELDS - set(task.keys())
            if task_missing:
                raise SpecValidationError(
                    f"Task at index {i} missing required fields: {task_missing}"
                )
            if task["id"] in task_ids:
                raise SpecValidationError(f"Duplicate task id: {task['id']}")
            task_ids.add(task["id"])

        # Validate dependency references
        for task in spec["tasks"]:
            for dep in task.get("dependencies", []):
                if dep not in task_ids:
                    raise SpecValidationError(
                        f"Task '{task['id']}' depends on unknown task '{dep}'"
                    )

    def _parse_task(self, raw: dict) -> Task:
        try:
            return Task(
                id=raw["id"],
                title=raw["title"],
                description=raw["description"],
                acceptance_criteria=raw["acceptance_criteria"],
                status=TaskStatus(raw["status"]),
                dependencies=raw.get("dependencies", []),
            )
        except ValueError as e:
            raise SpecValidationError(f"Invalid task '{raw.get('id', '?')}': {e}") from e

    def next_task(self) -> Task | None:
        """Return the next pending task with all dependencies met, or None."""
        done_ids = {t.id for t in self.tasks if t.status == TaskStatus.DONE}
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            if all(dep in done_ids for dep in task.dependencies):
                return task
        return None

    def mark_done(self, task_id: str) -> None:
        task = self._find_task(task_id)
        task.status = TaskStatus.DONE

    def mark_failed(self, task_id: str, reason: str) -> None:
        task = self._find_task(task_id)
        task.status = TaskStatus.FAILED

    def mark_blocked(self, task_id: str, reason: str) -> None:
        task = self._find_task(task_id)
        task.status = TaskStatus.BLOCKED

    def is_complete(self) -> bool:
        """True if all tasks are done or blocked (no pending/in_progress/failed)."""
        return all(
            t.status in (TaskStatus.DONE, TaskStatus.BLOCKED)
            for t in self.tasks
        )

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for task in self.tasks:
            counts[task.status.value] = counts.get(task.status.value, 0) + 1
        return counts

    def to_dict(self) -> dict:
        """Serialize back to a dict suitable for JSON output."""
        result = {
            "name": self.name,
            "test_command": self.test_command,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "acceptance_criteria": t.acceptance_criteria,
                    "status": t.status.value,
                    "dependencies": t.dependencies,
                }
                for t in self.tasks
            ],
        }
        if self.deploy_target:
            result["deploy_target"] = self.deploy_target
        return result

    def _find_task(self, task_id: str) -> Task:
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise ValueError(f"Task not found: {task_id}")
