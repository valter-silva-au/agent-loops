"""Tests for prompt builder (S5.2)."""

import time
from agent_loops.prompt import PromptBuilder
from agent_loops.models import Task, TaskStatus, ProgressEntry
from agent_loops.state import StateManager


class TestPromptBuilder:
    def test_build_includes_task(self, tmp_project):
        state = StateManager(tmp_project)
        builder = PromptBuilder(tmp_project, state)
        task = Task(
            id="TASK-001", title="Create main module",
            description="Create src/main.py",
            acceptance_criteria=["main.py exists", "prints hello"],
        )
        prompt = builder.build(task, iteration=1, test_command="pytest")
        assert "TASK-001" in prompt
        assert "Create main module" in prompt
        assert "main.py exists" in prompt
        assert "prints hello" in prompt

    def test_build_includes_test_command(self, tmp_project):
        state = StateManager(tmp_project)
        builder = PromptBuilder(tmp_project, state)
        task = Task(id="T1", title="t", description="d", acceptance_criteria=[])
        prompt = builder.build(task, iteration=1, test_command="npm test")
        assert "npm test" in prompt

    def test_build_includes_role_rules(self, tmp_project):
        state = StateManager(tmp_project)
        builder = PromptBuilder(tmp_project, state)
        task = Task(id="T1", title="t", description="d", acceptance_criteria=[])
        prompt = builder.build(task, iteration=1, test_command="pytest")
        assert "Role and Rules" in prompt
        assert "commit" in prompt.lower()
        assert "test" in prompt.lower()

    def test_build_includes_progress(self, tmp_project):
        state = StateManager(tmp_project)
        state.append_progress(ProgressEntry(
            iteration=1, task_id="T0", status="success",
            learnings="Used FastAPI",
        ))
        builder = PromptBuilder(tmp_project, state)
        task = Task(id="T1", title="t", description="d", acceptance_criteria=[])
        prompt = builder.build(task, iteration=2, test_command="pytest")
        assert "Used FastAPI" in prompt

    def test_build_includes_iteration_number(self, tmp_project):
        state = StateManager(tmp_project)
        builder = PromptBuilder(tmp_project, state)
        task = Task(id="T1", title="t", description="d", acceptance_criteria=[])
        prompt = builder.build(task, iteration=42, test_command="pytest")
        assert "#42" in prompt

    def test_build_speed(self, tmp_project):
        state = StateManager(tmp_project)
        builder = PromptBuilder(tmp_project, state)
        task = Task(id="T1", title="t", description="d", acceptance_criteria=["a", "b", "c"])
        start = time.monotonic()
        builder.build(task, iteration=1, test_command="pytest")
        elapsed = time.monotonic() - start
        assert elapsed < 2.0  # Must be under 2 seconds
