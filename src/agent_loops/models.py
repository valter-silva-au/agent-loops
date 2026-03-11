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


class Provider(str, Enum):
    BEDROCK = "bedrock"
    ANTHROPIC = "anthropic"


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


BEDROCK_MODELS = {
    "sonnet": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "opus": "us.anthropic.claude-opus-4-6-v1",
    "haiku": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
}

ANTHROPIC_MODELS = {
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-6",
    "haiku": "claude-haiku-4-5-20251001",
}

DEFAULT_MODEL = BEDROCK_MODELS["sonnet"]
DEFAULT_PROVIDER = Provider.BEDROCK


@dataclass
class LoopConfig:
    prd_path: Path
    project_dir: Path
    max_iterations: int = 100
    budget_usd: float = 50.0
    model: str = ""
    provider: Provider = DEFAULT_PROVIDER
    max_turns_per_iteration: int = 50

    def __post_init__(self) -> None:
        self.prd_path = Path(self.prd_path)
        self.project_dir = Path(self.project_dir)
        if isinstance(self.provider, str):
            self.provider = Provider(self.provider)
        if not self.model:
            models = BEDROCK_MODELS if self.provider == Provider.BEDROCK else ANTHROPIC_MODELS
            self.model = models["sonnet"]
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
