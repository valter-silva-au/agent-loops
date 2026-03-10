"""Tests for budget tracker (S4.1)."""

import pytest
from agent_loops.safety.budget import BudgetTracker
from agent_loops.models import BudgetStatus
from agent_loops.state import StateManager


class TestBudgetTracker:
    def test_initial_cost_zero(self, tmp_project):
        state = StateManager(tmp_project)
        tracker = BudgetTracker(budget_usd=50.0, state=state)
        assert tracker.cumulative_cost == 0.0
        assert tracker.remaining == 50.0

    def test_record_updates_cumulative(self, tmp_project):
        state = StateManager(tmp_project)
        tracker = BudgetTracker(budget_usd=50.0, state=state)
        tracker.record(iteration=1, cost_usd=5.0, input_tokens=10000, output_tokens=2000)
        assert tracker.cumulative_cost == 5.0
        assert tracker.remaining == 45.0

    def test_check_ok(self, tmp_project):
        state = StateManager(tmp_project)
        tracker = BudgetTracker(budget_usd=50.0, state=state)
        tracker.record(iteration=1, cost_usd=10.0, input_tokens=10000, output_tokens=2000)
        assert tracker.check() == BudgetStatus.OK

    def test_check_warning_at_80_percent(self, tmp_project):
        state = StateManager(tmp_project)
        tracker = BudgetTracker(budget_usd=50.0, state=state)
        tracker.record(iteration=1, cost_usd=41.0, input_tokens=100000, output_tokens=20000)
        assert tracker.check() == BudgetStatus.WARNING

    def test_check_exceeded_at_100_percent(self, tmp_project):
        state = StateManager(tmp_project)
        tracker = BudgetTracker(budget_usd=50.0, state=state)
        tracker.record(iteration=1, cost_usd=50.0, input_tokens=100000, output_tokens=20000)
        assert tracker.check() == BudgetStatus.EXCEEDED

    def test_check_exceeded_over_budget(self, tmp_project):
        state = StateManager(tmp_project)
        tracker = BudgetTracker(budget_usd=10.0, state=state)
        tracker.record(iteration=1, cost_usd=15.0, input_tokens=50000, output_tokens=10000)
        assert tracker.check() == BudgetStatus.EXCEEDED

    def test_persists_to_budget_jsonl(self, tmp_project):
        state = StateManager(tmp_project)
        tracker = BudgetTracker(budget_usd=50.0, state=state)
        tracker.record(iteration=1, cost_usd=5.0, input_tokens=10000, output_tokens=2000)
        tracker.record(iteration=2, cost_usd=3.0, input_tokens=8000, output_tokens=1500)
        entries = state.read_budget()
        assert len(entries) == 2
        assert entries[1]["cumulative_cost_usd"] == 8.0

    def test_resumes_from_existing_budget(self, tmp_project):
        state = StateManager(tmp_project)
        # First session
        tracker1 = BudgetTracker(budget_usd=50.0, state=state)
        tracker1.record(iteration=1, cost_usd=20.0, input_tokens=50000, output_tokens=10000)
        # Second session resumes
        tracker2 = BudgetTracker(budget_usd=50.0, state=state)
        assert tracker2.cumulative_cost == 20.0
        assert tracker2.remaining == 30.0
