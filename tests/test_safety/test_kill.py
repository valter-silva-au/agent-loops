"""Tests for kill switch (S4.4)."""

import signal
from pathlib import Path

from agent_loops.safety.kill import KillSwitch


class TestKillSwitch:
    def test_not_triggered_initially(self, tmp_project):
        ks = KillSwitch(tmp_project)
        assert not ks.triggered
        assert not ks.check()

    def test_kill_file_triggers(self, tmp_project):
        ks = KillSwitch(tmp_project)
        kill_path = tmp_project / ".agent-loops" / "kill"
        kill_path.parent.mkdir(parents=True, exist_ok=True)
        kill_path.touch()
        assert ks.check() is True
        assert ks.triggered is True
        # Kill file is cleaned up
        assert not kill_path.exists()

    def test_signal_triggers(self, tmp_project):
        ks = KillSwitch(tmp_project)
        ks.install_signal_handler()
        try:
            # Simulate SIGINT
            ks._handle_signal(signal.SIGINT, None)
            assert ks.triggered is True
        finally:
            ks.uninstall_signal_handler()

    def test_check_remains_triggered(self, tmp_project):
        ks = KillSwitch(tmp_project)
        ks._triggered = True
        assert ks.check() is True
        assert ks.check() is True  # stays triggered
