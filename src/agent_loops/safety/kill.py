"""Kill switch: graceful termination via SIGINT or kill file (FR-SL-005)."""

from __future__ import annotations

import signal
from pathlib import Path


class KillSwitch:
    """Handle graceful termination via SIGINT signal or kill file."""

    KILL_FILENAME = "kill"

    def __init__(self, project_dir: Path) -> None:
        self.project_dir = Path(project_dir)
        self._triggered = False
        self._original_handler = None

    def install_signal_handler(self) -> None:
        self._original_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handle_signal)

    def uninstall_signal_handler(self) -> None:
        if self._original_handler is not None:
            signal.signal(signal.SIGINT, self._original_handler)
            self._original_handler = None

    def check(self) -> bool:
        """Check for kill file. Returns True if termination requested."""
        kill_path = self.project_dir / ".agent-loops" / self.KILL_FILENAME
        if kill_path.exists():
            self._triggered = True
            kill_path.unlink()  # clean up
            return True
        return self._triggered

    @property
    def triggered(self) -> bool:
        return self._triggered

    def _handle_signal(self, signum: int, frame) -> None:
        self._triggered = True
