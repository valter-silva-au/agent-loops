"""Tests for state manager (S3.1, S3.2, S3.3)."""

import json
import pytest
from pathlib import Path

from agent_loops.state import StateManager
from agent_loops.models import ProgressEntry, BudgetEntry


class TestAtomicWrites:
    """S3.1: Atomic file writes."""

    def test_write_spec_creates_file(self, tmp_project):
        state = StateManager(tmp_project)
        spec = {"name": "test", "test_command": "pytest", "tasks": []}
        state.write_spec(spec)
        assert (tmp_project / "prd.json").exists()
        loaded = json.loads((tmp_project / "prd.json").read_text())
        assert loaded["name"] == "test"

    def test_write_spec_overwrites_atomically(self, tmp_project):
        state = StateManager(tmp_project)
        state.write_spec({"name": "v1", "test_command": "t", "tasks": []})
        state.write_spec({"name": "v2", "test_command": "t", "tasks": []})
        loaded = json.loads((tmp_project / "prd.json").read_text())
        assert loaded["name"] == "v2"

    def test_state_dir_created_automatically(self, tmp_path):
        project = tmp_path / "new-project"
        project.mkdir()
        state = StateManager(project)
        assert (project / ".agent-loops").is_dir()

    def test_read_spec_missing_raises(self, tmp_project):
        state = StateManager(tmp_project)
        with pytest.raises(FileNotFoundError):
            state.read_spec()


class TestProgressLog:
    """S3.2: Progress log read/write."""

    def test_read_empty(self, tmp_project):
        state = StateManager(tmp_project)
        assert state.read_progress() == []

    def test_append_and_read(self, tmp_project):
        state = StateManager(tmp_project)
        entry = ProgressEntry(iteration=1, task_id="T1", status="success")
        state.append_progress(entry)
        entries = state.read_progress()
        assert len(entries) == 1
        assert entries[0]["task_id"] == "T1"
        assert entries[0]["status"] == "success"

    def test_read_last_n(self, tmp_project):
        state = StateManager(tmp_project)
        for i in range(20):
            state.append_progress(
                ProgressEntry(iteration=i, task_id=f"T{i}", status="success")
            )
        entries = state.read_progress(last_n=5)
        assert len(entries) == 5
        assert entries[0]["iteration"] == 15

    def test_read_skips_partial_line(self, tmp_project):
        state = StateManager(tmp_project)
        state.append_progress(
            ProgressEntry(iteration=1, task_id="T1", status="success")
        )
        # Simulate crash: append partial JSON
        progress_path = tmp_project / ".agent-loops" / "progress.jsonl"
        with open(progress_path, "a") as f:
            f.write('{"iteration": 2, "task_id": "T2", "stat')  # truncated

        entries = state.read_progress()
        assert len(entries) == 1  # partial line skipped
        assert entries[0]["task_id"] == "T1"

    def test_timestamp_populated(self, tmp_project):
        state = StateManager(tmp_project)
        entry = ProgressEntry(iteration=1, task_id="T1", status="success")
        state.append_progress(entry)
        entries = state.read_progress()
        assert "timestamp" in entries[0]
        assert entries[0]["timestamp"]  # not empty


class TestBudgetLog:
    """S3.3: Budget log read/write."""

    def test_cumulative_cost_empty(self, tmp_project):
        state = StateManager(tmp_project)
        assert state.get_cumulative_cost() == 0.0

    def test_append_and_get_cumulative(self, tmp_project):
        state = StateManager(tmp_project)
        state.append_budget(BudgetEntry(
            iteration=1, cost_usd=0.42,
            input_tokens=15000, output_tokens=3200,
            cumulative_cost_usd=0.42,
        ))
        state.append_budget(BudgetEntry(
            iteration=2, cost_usd=0.38,
            input_tokens=14000, output_tokens=2800,
            cumulative_cost_usd=0.80,
        ))
        assert state.get_cumulative_cost() == 0.80

    def test_read_budget_entries(self, tmp_project):
        state = StateManager(tmp_project)
        state.append_budget(BudgetEntry(
            iteration=1, cost_usd=0.42,
            input_tokens=15000, output_tokens=3200,
            cumulative_cost_usd=0.42,
        ))
        entries = state.read_budget()
        assert len(entries) == 1
        assert entries[0]["cost_usd"] == 0.42
