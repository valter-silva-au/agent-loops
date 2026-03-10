"""Tests for spec parser (S2.1, S2.2, S2.3, S2.4)."""

import pytest

from agent_loops.spec import SpecParser, SpecValidationError
from agent_loops.models import TaskStatus


class TestSpecValidation:
    """S2.1: prd.json schema validation."""

    def test_valid_spec(self, sample_spec):
        parser = SpecParser(sample_spec)
        assert parser.name == "test-app"
        assert parser.test_command == "pytest"
        assert len(parser.tasks) == 2

    def test_missing_name(self, sample_spec):
        del sample_spec["name"]
        with pytest.raises(SpecValidationError, match="Missing required"):
            SpecParser(sample_spec)

    def test_missing_test_command(self, sample_spec):
        del sample_spec["test_command"]
        with pytest.raises(SpecValidationError, match="Missing required"):
            SpecParser(sample_spec)

    def test_missing_tasks(self, sample_spec):
        del sample_spec["tasks"]
        with pytest.raises(SpecValidationError, match="Missing required"):
            SpecParser(sample_spec)

    def test_empty_tasks(self, sample_spec):
        sample_spec["tasks"] = []
        with pytest.raises(SpecValidationError, match="at least one task"):
            SpecParser(sample_spec)

    def test_task_missing_fields(self, sample_spec):
        del sample_spec["tasks"][0]["title"]
        with pytest.raises(SpecValidationError, match="missing required fields"):
            SpecParser(sample_spec)

    def test_duplicate_task_id(self, sample_spec):
        sample_spec["tasks"][1]["id"] = "TASK-001"
        with pytest.raises(SpecValidationError, match="Duplicate task id"):
            SpecParser(sample_spec)

    def test_invalid_dependency_reference(self, sample_spec):
        sample_spec["tasks"][0]["dependencies"] = ["NONEXISTENT"]
        with pytest.raises(SpecValidationError, match="unknown task"):
            SpecParser(sample_spec)

    def test_invalid_status(self, sample_spec):
        sample_spec["tasks"][0]["status"] = "invalid"
        with pytest.raises(SpecValidationError, match="Invalid task"):
            SpecParser(sample_spec)

    def test_valid_statuses(self, sample_spec):
        for status in ["pending", "in_progress", "done", "failed", "blocked"]:
            sample_spec["tasks"][0]["status"] = status
            parser = SpecParser(sample_spec)
            assert parser.tasks[0].status == TaskStatus(status)

    def test_deploy_target_optional(self, sample_spec):
        parser = SpecParser(sample_spec)
        assert parser.deploy_target is None

    def test_deploy_target_present(self, sample_spec):
        sample_spec["deploy_target"] = "docker"
        parser = SpecParser(sample_spec)
        assert parser.deploy_target == "docker"


class TestTaskSelection:
    """S2.2: Task selection with dependency resolution."""

    def test_next_task_returns_first_pending(self, sample_spec):
        parser = SpecParser(sample_spec)
        task = parser.next_task()
        assert task is not None
        assert task.id == "TASK-001"

    def test_next_task_skips_unmet_dependencies(self, sample_spec):
        parser = SpecParser(sample_spec)
        # TASK-002 depends on TASK-001 which is pending
        # next_task should return TASK-001, not TASK-002
        task = parser.next_task()
        assert task.id == "TASK-001"

    def test_next_task_after_dependency_done(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_done("TASK-001")
        task = parser.next_task()
        assert task is not None
        assert task.id == "TASK-002"

    def test_next_task_returns_none_when_all_done(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_done("TASK-001")
        parser.mark_done("TASK-002")
        assert parser.next_task() is None

    def test_next_task_returns_none_when_all_blocked(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_blocked("TASK-001", "stuck")
        parser.mark_blocked("TASK-002", "stuck")
        assert parser.next_task() is None

    def test_next_task_skips_blocked_tasks(self, sample_spec):
        # Add a third task with no deps
        sample_spec["tasks"].append({
            "id": "TASK-003",
            "title": "Extra task",
            "description": "No deps",
            "acceptance_criteria": [],
            "status": "pending",
            "dependencies": [],
        })
        parser = SpecParser(sample_spec)
        parser.mark_blocked("TASK-001", "stuck")
        task = parser.next_task()
        assert task is not None
        assert task.id == "TASK-003"


class TestTaskStatusUpdates:
    """S2.3: Task status updates."""

    def test_mark_done(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_done("TASK-001")
        assert parser.tasks[0].status == TaskStatus.DONE

    def test_mark_failed(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_failed("TASK-001", "test failure")
        assert parser.tasks[0].status == TaskStatus.FAILED

    def test_mark_blocked(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_blocked("TASK-001", "gutter detected")
        assert parser.tasks[0].status == TaskStatus.BLOCKED

    def test_mark_done_idempotent(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_done("TASK-001")
        parser.mark_done("TASK-001")
        assert parser.tasks[0].status == TaskStatus.DONE

    def test_mark_nonexistent_raises(self, sample_spec):
        parser = SpecParser(sample_spec)
        with pytest.raises(ValueError, match="Task not found"):
            parser.mark_done("NONEXISTENT")

    def test_summary(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_done("TASK-001")
        summary = parser.summary()
        assert summary == {"done": 1, "pending": 1}


class TestSpecCompletion:
    """S2.4: Spec completion check."""

    def test_not_complete_with_pending(self, sample_spec):
        parser = SpecParser(sample_spec)
        assert not parser.is_complete()

    def test_complete_all_done(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_done("TASK-001")
        parser.mark_done("TASK-002")
        assert parser.is_complete()

    def test_complete_mix_done_and_blocked(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_done("TASK-001")
        parser.mark_blocked("TASK-002", "stuck")
        assert parser.is_complete()

    def test_not_complete_with_failed(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_done("TASK-001")
        parser.mark_failed("TASK-002", "error")
        assert not parser.is_complete()


class TestSpecSerialization:
    def test_to_dict_roundtrip(self, sample_spec):
        parser = SpecParser(sample_spec)
        parser.mark_done("TASK-001")
        result = parser.to_dict()
        assert result["tasks"][0]["status"] == "done"
        # Can re-parse the output
        parser2 = SpecParser(result)
        assert parser2.tasks[0].status == TaskStatus.DONE
