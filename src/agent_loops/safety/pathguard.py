"""Path guard: restrict file operations to the target project directory (security)."""

from __future__ import annotations

from pathlib import Path


class PathGuard:
    """Validate that file paths resolve within the target project directory."""

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir).resolve()

    def is_allowed(self, path: str | Path) -> bool:
        """Check if a path resolves within the project directory."""
        try:
            resolved = Path(path).resolve()
            return resolved == self.project_dir or self.project_dir in resolved.parents
        except (OSError, ValueError):
            return False

    def check_bash_command(self, command: str) -> str | None:
        """Check a bash command for dangerous patterns.

        Returns a denial reason string if blocked, None if allowed.
        """
        dangerous_patterns = [
            "rm -rf /",
            "rm -rf ~",
            "git push --force",
            "git push -f",
            "git reset --hard",
        ]
        # Check for pipe-to-shell patterns (with flexible whitespace around pipe)
        import re
        pipe_to_shell = re.search(r"(curl|wget)\s.*\|\s*(sh|bash)", command)
        if pipe_to_shell:
            return f"Dangerous command blocked: pipe to shell detected"
        for pattern in dangerous_patterns:
            if pattern in command:
                return f"Dangerous command blocked: contains '{pattern}'"
        return None
