"""Tests for core data models (S1.2)."""

import pytest

from agent_loops.models import (
    ANTHROPIC_MODELS,
    BEDROCK_MODELS,
    BudgetEntry,
    BudgetStatus,
    GutterStatus,
    IterationResult,
    LoopConfig,
    LoopResult,
    ProgressEntry,
    Provider,
    Task,
    TaskStatus,
)
from pathlib import Path


class TestTask:
    def test_create_valid_task(self):
        task = Task(
            id="TASK-001",
            title="Create main",
            description="Create main.py",
            acceptance_criteria=["main.py exists"],
        )
        assert task.status == TaskStatus.PENDING
        assert task.dependencies == []

    def test_status_string_coercion(self):
        task = Task(
            id="T1", title="t", description="d",
            acceptance_criteria=[], status="done",
        )
        assert task.status == TaskStatus.DONE

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            Task(
                id="T1", title="t", description="d",
                acceptance_criteria=[], status="invalid",
            )

    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="id must not be empty"):
            Task(id="", title="t", description="d", acceptance_criteria=[])

    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="title must not be empty"):
            Task(id="T1", title="", description="d", acceptance_criteria=[])


class TestLoopConfig:
    def test_valid_config(self):
        config = LoopConfig(prd_path="prd.json", project_dir="/tmp/project")
        assert config.max_iterations == 100
        assert config.budget_usd == 50.0
        assert isinstance(config.prd_path, Path)

    def test_default_provider_is_bedrock(self):
        config = LoopConfig(prd_path="prd.json", project_dir="/tmp/project")
        assert config.provider == Provider.BEDROCK

    def test_default_model_bedrock(self):
        config = LoopConfig(prd_path="prd.json", project_dir="/tmp/project")
        assert config.model == BEDROCK_MODELS["sonnet"]
        assert "us.anthropic" in config.model

    def test_default_model_anthropic(self):
        config = LoopConfig(prd_path="prd.json", project_dir="/tmp/project", provider="anthropic")
        assert config.model == ANTHROPIC_MODELS["sonnet"]
        assert "us.anthropic" not in config.model

    def test_explicit_model_preserved(self):
        config = LoopConfig(prd_path="prd.json", project_dir="/tmp/project", model="us.anthropic.claude-opus-4-6-v1")
        assert config.model == "us.anthropic.claude-opus-4-6-v1"

    def test_provider_string_coercion(self):
        config = LoopConfig(prd_path="prd.json", project_dir="/tmp/project", provider="anthropic")
        assert config.provider == Provider.ANTHROPIC

    def test_invalid_max_iterations(self):
        with pytest.raises(ValueError, match="max_iterations"):
            LoopConfig(prd_path="prd.json", project_dir="/tmp", max_iterations=0)

    def test_invalid_budget(self):
        with pytest.raises(ValueError, match="budget_usd"):
            LoopConfig(prd_path="prd.json", project_dir="/tmp", budget_usd=-1)


class TestProgressEntry:
    def test_defaults(self):
        entry = ProgressEntry(iteration=1, task_id="T1", status="success")
        assert entry.changes == []
        assert entry.learnings is None
        assert entry.error is None
        assert entry.timestamp  # auto-populated


class TestBudgetEntry:
    def test_create(self):
        entry = BudgetEntry(
            iteration=1, cost_usd=0.42,
            input_tokens=15000, output_tokens=3200,
            cumulative_cost_usd=0.42,
        )
        assert entry.cost_usd == 0.42
        assert entry.timestamp  # auto-populated


class TestEnums:
    def test_task_status_values(self):
        assert set(TaskStatus) == {
            TaskStatus.PENDING, TaskStatus.IN_PROGRESS,
            TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.BLOCKED,
        }

    def test_budget_status_values(self):
        assert set(BudgetStatus) == {
            BudgetStatus.OK, BudgetStatus.WARNING, BudgetStatus.EXCEEDED,
        }

    def test_gutter_status_values(self):
        assert set(GutterStatus) == {GutterStatus.OK, GutterStatus.BLOCKED}


class TestLoopResult:
    def test_create(self):
        result = LoopResult(
            iterations_completed=10, tasks_done=5, tasks_pending=2,
            tasks_failed=1, tasks_blocked=0, total_cost_usd=4.50,
            exit_reason="max_iterations_reached",
        )
        assert result.exit_reason == "max_iterations_reached"


class TestIterationResult:
    def test_defaults(self):
        result = IterationResult(success=True)
        assert result.cost_usd == 0.0
        assert result.error is None
