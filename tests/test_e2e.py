"""E2E tests for agent-loops (require ANTHROPIC_API_KEY or AWS Bedrock credentials).

Run from a regular terminal (NOT inside Claude Code):
    pytest tests/test_e2e.py -v -m e2e
"""

import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def e2e_project(tmp_path):
    """Create a minimal project for E2E testing."""
    project = tmp_path / "e2e-project"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "initial"],
        cwd=project, check=True, capture_output=True,
    )

    spec = {
        "name": "hello-e2e",
        "test_command": "python -c \"import hello; assert hello.greet('World') == 'Hello, World!'\"",
        "tasks": [
            {
                "id": "TASK-001",
                "title": "Create hello module",
                "description": "Create a file called hello.py with a function greet(name: str) -> str that returns 'Hello, {name}!'",
                "acceptance_criteria": [
                    "hello.py exists",
                    "greet('World') returns 'Hello, World!'"
                ],
                "status": "pending",
                "dependencies": [],
            },
        ],
    }
    (project / "prd.json").write_text(json.dumps(spec, indent=2))
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add spec"], cwd=project, check=True, capture_output=True)
    return project


@pytest.mark.e2e
def test_single_task_build(e2e_project):
    """Run agent-loops on a single-task spec and verify it completes."""
    result = subprocess.run(
        [
            "agent-loops", "run",
            "--prd", str(e2e_project / "prd.json"),
            "--dir", str(e2e_project),
            "--max-iterations", "5",
            "--budget", "5.0",
        ],
        capture_output=True, text=True, timeout=300,
    )

    # Check the loop ran
    assert "Loop finished" in result.stdout

    # Check hello.py was created
    hello_py = e2e_project / "hello.py"
    assert hello_py.exists(), "hello.py should have been created by the agent"

    # Check the spec was updated
    spec = json.loads((e2e_project / "prd.json").read_text())
    task = spec["tasks"][0]
    assert task["status"] == "done", f"Task should be done, got: {task['status']}"

    # Check progress was logged
    progress_path = e2e_project / ".agent-loops" / "progress.jsonl"
    assert progress_path.exists(), "progress.jsonl should exist"

    # Check budget was tracked
    budget_path = e2e_project / ".agent-loops" / "budget.jsonl"
    assert budget_path.exists(), "budget.jsonl should exist"

    # Check a git commit was made
    log = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=e2e_project, capture_output=True, text=True,
    )
    assert len(log.stdout.strip().splitlines()) > 2, "Agent should have committed at least once"
