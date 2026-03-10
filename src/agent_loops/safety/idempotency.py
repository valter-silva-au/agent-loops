"""Idempotency guard: prevent duplicate side-effects (FR-SL-004)."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


class IdempotencyGuard:
    """Detect and prevent duplicate commits and file overwrites."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir)

    def has_uncommitted_changes(self) -> bool:
        """Check if there are actual changes to commit."""
        result = subprocess.run(
            ["git", "diff", "--cached", "--stat"],
            cwd=self.project_dir,
            capture_output=True, text=True, timeout=5,
        )
        return bool(result.stdout.strip())

    def is_empty_diff(self) -> bool:
        """Check if the working tree has no meaningful changes from HEAD."""
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=self.project_dir,
            capture_output=True, text=True, timeout=5,
        )
        return not result.stdout.strip()

    def file_content_unchanged(self, path: Path, new_content: str) -> bool:
        """Check if writing new_content to path would be a no-op."""
        abs_path = (self.project_dir / path) if not path.is_absolute() else path
        if not abs_path.exists():
            return False
        try:
            existing = abs_path.read_text()
            return existing == new_content
        except (OSError, UnicodeDecodeError):
            return False
