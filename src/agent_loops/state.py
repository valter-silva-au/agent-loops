"""State management for agent-loops: atomic reads/writes for prd.json, progress.jsonl, budget.jsonl."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from .models import BudgetEntry, ProgressEntry


class StateManager:
    """Centralized read/write for all state files with atomic write guarantees."""

    STATE_DIR = ".agent-loops"

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir)
        self.state_dir = self.project_dir / self.STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)

    # -- prd.json --

    def read_spec(self) -> dict:
        spec_path = self.project_dir / "prd.json"
        if not spec_path.exists():
            raise FileNotFoundError(f"prd.json not found in {self.project_dir}")
        return json.loads(spec_path.read_text())

    def write_spec(self, spec: dict) -> None:
        self._atomic_write_json(self.project_dir / "prd.json", spec)

    # -- progress.jsonl --

    @property
    def _progress_path(self) -> Path:
        return self.state_dir / "progress.jsonl"

    def read_progress(self, last_n: int = 10) -> list[dict]:
        if not self._progress_path.exists():
            return []
        lines = self._read_jsonl_safe(self._progress_path)
        return lines[-last_n:] if last_n else lines

    def append_progress(self, entry: ProgressEntry) -> None:
        self._append_jsonl(self._progress_path, asdict(entry))

    # -- budget.jsonl --

    @property
    def _budget_path(self) -> Path:
        return self.state_dir / "budget.jsonl"

    def read_budget(self) -> list[dict]:
        if not self._budget_path.exists():
            return []
        return self._read_jsonl_safe(self._budget_path)

    def append_budget(self, entry: BudgetEntry) -> None:
        self._append_jsonl(self._budget_path, asdict(entry))

    def get_cumulative_cost(self) -> float:
        entries = self.read_budget()
        if not entries:
            return 0.0
        return entries[-1].get("cumulative_cost_usd", 0.0)

    # -- Atomic write helpers --

    def _atomic_write_json(self, path: Path, data: dict) -> None:
        """Write JSON atomically via temp file + os.replace()."""
        content = json.dumps(data, indent=2) + "\n"
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, suffix=".tmp", prefix=path.stem
        )
        try:
            os.write(fd, content.encode())
            os.close(fd)
            os.replace(tmp_path, path)
        except Exception:
            os.close(fd) if not os.get_inheritable(fd) else None
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _append_jsonl(self, path: Path, data: dict) -> None:
        """Append a single JSON line. Append-only is crash-safe (partial last line is skipped on read)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(data) + "\n"
        with open(path, "a") as f:
            f.write(line)

    def _read_jsonl_safe(self, path: Path) -> list[dict]:
        """Read JSONL, skipping partial/corrupt lines (crash artifacts)."""
        entries = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # skip partial line from crash
        return entries
