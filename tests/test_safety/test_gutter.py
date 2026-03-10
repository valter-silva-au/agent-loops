"""Tests for gutter detection (S4.3)."""

from agent_loops.safety.gutter import GutterDetector
from agent_loops.models import GutterStatus


class TestGutterDetector:
    def test_no_failures_ok(self):
        detector = GutterDetector(threshold=3)
        progress = [
            {"task_id": "T1", "status": "success"},
            {"task_id": "T2", "status": "success"},
        ]
        assert detector.check(progress, "T1") == GutterStatus.OK

    def test_consecutive_failures_blocked(self):
        detector = GutterDetector(threshold=3)
        progress = [
            {"task_id": "T1", "status": "failed"},
            {"task_id": "T1", "status": "failed"},
            {"task_id": "T1", "status": "failed"},
        ]
        assert detector.check(progress, "T1") == GutterStatus.BLOCKED

    def test_success_breaks_streak(self):
        detector = GutterDetector(threshold=3)
        progress = [
            {"task_id": "T1", "status": "failed"},
            {"task_id": "T1", "status": "failed"},
            {"task_id": "T1", "status": "success"},
        ]
        assert detector.check(progress, "T1") == GutterStatus.OK

    def test_different_task_breaks_streak(self):
        detector = GutterDetector(threshold=3)
        progress = [
            {"task_id": "T1", "status": "failed"},
            {"task_id": "T2", "status": "failed"},
            {"task_id": "T1", "status": "failed"},
        ]
        assert detector.check(progress, "T1") == GutterStatus.OK

    def test_below_threshold_ok(self):
        detector = GutterDetector(threshold=3)
        progress = [
            {"task_id": "T1", "status": "failed"},
            {"task_id": "T1", "status": "failed"},
        ]
        assert detector.check(progress, "T1") == GutterStatus.OK

    def test_empty_progress_ok(self):
        detector = GutterDetector(threshold=3)
        assert detector.check([], "T1") == GutterStatus.OK

    def test_custom_threshold(self):
        detector = GutterDetector(threshold=2)
        progress = [
            {"task_id": "T1", "status": "failed"},
            {"task_id": "T1", "status": "failed"},
        ]
        assert detector.check(progress, "T1") == GutterStatus.BLOCKED

    def test_only_checks_tail(self):
        """Gutter detection only looks at the consecutive tail, not scattered failures."""
        detector = GutterDetector(threshold=3)
        progress = [
            {"task_id": "T1", "status": "failed"},
            {"task_id": "T1", "status": "success"},  # breaks streak
            {"task_id": "T1", "status": "failed"},
            {"task_id": "T1", "status": "failed"},
        ]
        assert detector.check(progress, "T1") == GutterStatus.OK
