"""Tests for loop engine (S5.3, S5.4, S6.2)."""

import json
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_loops.engine import LoopEngine
from agent_loops.models import IterationResult, LoopConfig
from agent_loops.runner import RunnerConfig


@pytest.fixture
def engine_project(tmp_path):
    """Create a project with git repo and prd.json."""
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "initial"],
        cwd=project, check=True, capture_output=True,
    )

    spec = {
        "name": "test-app",
        "test_command": "echo ok",
        "tasks": [
            {
                "id": "TASK-001",
                "title": "Create hello.py",
                "description": "Create a hello world file",
                "acceptance_criteria": ["hello.py exists"],
                "status": "pending",
                "dependencies": [],
            },
        ],
    }
    (project / "prd.json").write_text(json.dumps(spec))
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add prd.json"],
        cwd=project, check=True, capture_output=True,
    )
    return project


def make_mock_runner(return_result: IterationResult):
    """Create a mock AgentRunner class that returns the given result."""
    mock_class = MagicMock()
    instance = MagicMock()
    instance.run_iteration = AsyncMock(return_value=return_result)
    instance.config = RunnerConfig()
    mock_class.return_value = instance
    return mock_class


class TestGitValidation:
    """S5.4: Git state validation."""

    def test_rejects_non_git_dir(self, tmp_path):
        project = tmp_path / "not-git"
        project.mkdir()
        (project / "prd.json").write_text(json.dumps({
            "name": "t", "test_command": "t",
            "tasks": [{"id": "T1", "title": "t", "description": "d",
                       "acceptance_criteria": [], "status": "pending", "dependencies": []}],
        }))
        config = LoopConfig(prd_path=project / "prd.json", project_dir=project, max_iterations=1)
        engine = LoopEngine(config)
        with pytest.raises(RuntimeError, match="git repository"):
            import asyncio
            asyncio.run(engine.run())

    def test_rejects_dirty_working_tree(self, engine_project):
        (engine_project / "dirty.txt").write_text("uncommitted")
        config = LoopConfig(
            prd_path=engine_project / "prd.json",
            project_dir=engine_project, max_iterations=1,
        )
        engine = LoopEngine(config)
        with pytest.raises(RuntimeError, match="Clean working tree"):
            import asyncio
            asyncio.run(engine.run())


class TestLoopExecution:
    """S5.3: Loop engine core."""

    @pytest.mark.asyncio
    async def test_completes_when_all_tasks_done(self, engine_project):
        """Simulate an agent that commits successfully."""
        call_count = 0

        async def mock_run_iteration(prompt):
            nonlocal call_count
            call_count += 1
            # Simulate the agent creating and committing a file
            (engine_project / "hello.py").write_text("print('hello')")
            subprocess.run(["git", "add", "."], cwd=engine_project, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "feat: add hello.py [TASK-001]"],
                cwd=engine_project, capture_output=True,
            )
            return IterationResult(success=True, cost_usd=0.50, input_tokens=1000, output_tokens=500)

        mock_runner = make_mock_runner(IterationResult(success=True))
        mock_runner.return_value.run_iteration = AsyncMock(side_effect=mock_run_iteration)

        config = LoopConfig(
            prd_path=engine_project / "prd.json",
            project_dir=engine_project, max_iterations=10,
        )
        engine = LoopEngine(config)

        with patch("agent_loops.engine.AgentRunner", mock_runner):
            result = await engine.run()

        assert result.exit_reason == "all_tasks_complete"
        assert result.tasks_done == 1
        assert result.total_cost_usd > 0

    @pytest.mark.asyncio
    async def test_stops_at_max_iterations(self, tmp_path):
        """More tasks than max_iterations should hit iteration limit."""
        project = tmp_path / "many-tasks"
        project.mkdir()
        subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "initial"],
            cwd=project, check=True, capture_output=True,
        )
        # Create spec with 10 independent tasks
        spec = {
            "name": "test", "test_command": "echo ok",
            "tasks": [
                {"id": f"TASK-{i:03d}", "title": f"Task {i}", "description": "d",
                 "acceptance_criteria": [], "status": "pending", "dependencies": []}
                for i in range(1, 11)
            ],
        }
        (project / "prd.json").write_text(json.dumps(spec))
        subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "spec"], cwd=project, check=True, capture_output=True)

        mock_runner = make_mock_runner(IterationResult(success=True, cost_usd=0.10))

        config = LoopConfig(
            prd_path=project / "prd.json",
            project_dir=project, max_iterations=3,
        )
        engine = LoopEngine(config)

        with patch("agent_loops.engine.AgentRunner", mock_runner):
            result = await engine.run()

        assert result.exit_reason == "max_iterations_reached"
        assert result.iterations_completed == 3

    @pytest.mark.asyncio
    async def test_stops_on_budget_exceeded(self, engine_project):
        """Agent that exceeds budget should terminate."""
        mock_runner = make_mock_runner(IterationResult(success=True, cost_usd=2.0))

        config = LoopConfig(
            prd_path=engine_project / "prd.json",
            project_dir=engine_project, max_iterations=100, budget_usd=1.0,
        )
        engine = LoopEngine(config)

        with patch("agent_loops.engine.AgentRunner", mock_runner):
            result = await engine.run()

        assert result.exit_reason == "budget_exceeded"
