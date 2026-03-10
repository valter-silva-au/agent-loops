"""Tests for idempotency guard (S4.6)."""

import subprocess

from agent_loops.safety.idempotency import IdempotencyGuard


class TestIdempotencyGuard:
    def test_empty_diff_on_clean_tree(self, tmp_project):
        guard = IdempotencyGuard(tmp_project)
        assert guard.is_empty_diff()

    def test_non_empty_diff_with_changes(self, tmp_project):
        (tmp_project / "new.py").write_text("hello")
        guard = IdempotencyGuard(tmp_project)
        # Untracked files don't show in git diff HEAD, need to stage
        subprocess.run(["git", "add", "."], cwd=tmp_project, capture_output=True)
        assert not guard.is_empty_diff()

    def test_file_content_unchanged(self, tmp_project):
        path = tmp_project / "test.txt"
        path.write_text("hello world")
        guard = IdempotencyGuard(tmp_project)
        assert guard.file_content_unchanged(path, "hello world")

    def test_file_content_changed(self, tmp_project):
        path = tmp_project / "test.txt"
        path.write_text("hello world")
        guard = IdempotencyGuard(tmp_project)
        assert not guard.file_content_unchanged(path, "hello world v2")

    def test_file_nonexistent(self, tmp_project):
        guard = IdempotencyGuard(tmp_project)
        assert not guard.file_content_unchanged(tmp_project / "nope.txt", "content")

    def test_no_uncommitted_changes_clean(self, tmp_project):
        guard = IdempotencyGuard(tmp_project)
        assert not guard.has_uncommitted_changes()

    def test_has_uncommitted_changes_staged(self, tmp_project):
        (tmp_project / "staged.py").write_text("code")
        subprocess.run(["git", "add", "."], cwd=tmp_project, capture_output=True)
        guard = IdempotencyGuard(tmp_project)
        assert guard.has_uncommitted_changes()
