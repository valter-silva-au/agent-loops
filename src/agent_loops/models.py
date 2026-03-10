"""Core data models for agent-loops."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"


class BudgetStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    EXCEEDED = "exceeded"


class GutterStatus(str, Enum):
    OK = "ok"
    BLOCKED = "blocked"


@dataclass
class Task:
    id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Task id must not be empty")
        if not self.title:
            raise ValueError("Task title must not be empty")
        if isinstance(self.status, str):
            self.status = TaskStatus(self.status)


@dataclass
class LoopConfig:
    prd_path: Path
    project_dir: Path
    max_iterations: int = 100
    budget_usd: float = 50.0
    model: str = "claude-sonnet-4-6"
    max_turns_per_iteration: int = 50

    def __post_init__(self) -> None:
        self.prd_path = Path(self.prd_path)
        self.project_dir = Path(self.project_dir)
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if self.budget_usd <= 0:
            raise ValueError("budget_usd must be > 0")


@dataclass
class ProgressEntry:
    iteration: int
    task_id: str
    status: str
    changes: list[str] = field(default_factory=list)
    learnings: str | None = None
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class BudgetEntry:
    iteration: int
    cost_usd: float
    input_tokens: int
    output_tokens: int
    cumulative_cost_usd: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class IterationResult:
    success: bool
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    error: str | None = None


@dataclass
class LoopResult:
    iterations_completed: int
    tasks_done: int
    tasks_pending: int
    tasks_failed: int
    tasks_blocked: int
    total_cost_usd: float
    exit_reason: str
