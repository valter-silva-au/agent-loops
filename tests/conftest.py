"""Shared test fixtures for agent-loops."""

import json
import subprocess

import pytest
from pathlib import Path


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory with git initialized."""
    project = tmp_path / "test-project"
    project.mkdir()
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    # Configure git identity for CI environments where no global config exists
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "initial"],
        cwd=project,
        check=True,
        capture_output=True,
    )
    return project


@pytest.fixture
def sample_spec() -> dict:
    """Return a minimal valid prd.json spec."""
    return {
        "name": "test-app",
        "test_command": "pytest",
        "tasks": [
            {
                "id": "TASK-001",
                "title": "Create main module",
                "description": "Create src/main.py with hello world",
                "acceptance_criteria": ["main.py exists", "prints hello world"],
                "status": "pending",
                "dependencies": [],
            },
            {
                "id": "TASK-002",
                "title": "Add tests",
                "description": "Create tests for main module",
                "acceptance_criteria": ["test_main.py exists", "tests pass"],
                "status": "pending",
                "dependencies": ["TASK-001"],
            },
        ],
    }


@pytest.fixture
def sample_spec_file(tmp_project: Path, sample_spec: dict) -> Path:
    """Write sample spec to a file and return the path."""
    spec_path = tmp_project / "prd.json"
    spec_path.write_text(json.dumps(sample_spec, indent=2))
    return spec_path
