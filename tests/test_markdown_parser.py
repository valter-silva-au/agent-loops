"""Tests for markdown PRD parser (S7.3)."""

from agent_loops.markdown_parser import parse_prd_markdown


SAMPLE_PRD = """# Product Requirements Document: My Cool App

## 4. Functional Requirements

#### FR-M2-001: Loop Harness

**Priority:** Must-Have
**Description:** The system shall implement a loop.
**Acceptance Criteria:**
- Given a spec, when run is invoked, then the loop starts
- Given the loop finishes, when checked, then results are saved

#### FR-M2-002: State Management

**Priority:** Must-Have
**Description:** The system shall manage state files.
**Acceptance Criteria:**
- Given state is written, when read back, then it matches

## 5. Non-Functional Requirements

Performance stuff here.
"""


class TestMarkdownParser:
    def test_extracts_tasks(self):
        result = parse_prd_markdown(SAMPLE_PRD)
        assert len(result["tasks"]) == 2

    def test_extracts_task_ids(self):
        result = parse_prd_markdown(SAMPLE_PRD)
        ids = [t["id"] for t in result["tasks"]]
        assert "TASK-M2-001" in ids
        assert "TASK-M2-002" in ids

    def test_extracts_titles(self):
        result = parse_prd_markdown(SAMPLE_PRD)
        assert result["tasks"][0]["title"] == "Loop Harness"

    def test_extracts_descriptions(self):
        result = parse_prd_markdown(SAMPLE_PRD)
        assert "loop" in result["tasks"][0]["description"].lower()

    def test_extracts_acceptance_criteria(self):
        result = parse_prd_markdown(SAMPLE_PRD)
        criteria = result["tasks"][0]["acceptance_criteria"]
        assert len(criteria) == 2
        assert "Given a spec" in criteria[0]

    def test_extracts_project_name(self):
        result = parse_prd_markdown(SAMPLE_PRD)
        assert result["name"] == "My Cool App"

    def test_default_test_command(self):
        result = parse_prd_markdown(SAMPLE_PRD)
        assert result["test_command"] == "pytest"

    def test_all_tasks_pending(self):
        result = parse_prd_markdown(SAMPLE_PRD)
        for task in result["tasks"]:
            assert task["status"] == "pending"
            assert task["dependencies"] == []

    def test_empty_content_returns_no_tasks(self):
        result = parse_prd_markdown("# Just a title\n\nNo requirements here.")
        assert result["tasks"] == []

    def test_parseable_by_spec_parser(self):
        """Ensure the output can be consumed by SpecParser."""
        result = parse_prd_markdown(SAMPLE_PRD)
        from agent_loops.spec import SpecParser
        parser = SpecParser(result)
        assert len(parser.tasks) == 2
