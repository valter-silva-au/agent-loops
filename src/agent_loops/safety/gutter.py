"""Gutter detection: identify when an agent is thrashing on the same task (FR-SL-003)."""

from __future__ import annotations

from ..models import GutterStatus


class GutterDetector:
    """Detect repeated failures on the same task across consecutive iterations."""

    def __init__(self, threshold: int = 3) -> None:
        self.threshold = threshold

    def check(self, progress: list[dict], task_id: str) -> GutterStatus:
        """Check if the given task has failed consecutively >= threshold times.

        Only looks at the most recent entries. The streak is broken by:
        - A success on the same task
        - A different task appearing between failures
        """
        consecutive_failures = 0
        for entry in reversed(progress):
            if entry.get("task_id") != task_id:
                break  # different task breaks the streak
            if entry.get("status") == "failed":
                consecutive_failures += 1
            else:
                break  # success or other status breaks the streak

        if consecutive_failures >= self.threshold:
            return GutterStatus.BLOCKED
        return GutterStatus.OK
