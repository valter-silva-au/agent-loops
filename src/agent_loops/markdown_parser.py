"""Parse markdown PRD into prd.json tasks (S7.3)."""

from __future__ import annotations

import re


def parse_prd_markdown(content: str) -> dict:
    """Extract functional requirements from a markdown PRD and generate a prd.json structure.

    Looks for sections matching the pattern:
    #### FR-XXX: Title
    **Description:** ...
    **Acceptance Criteria:**
    - Given ... when ... then ...
    """
    tasks = []
    # Match FR requirement blocks
    fr_pattern = re.compile(
        r"####\s+(FR-[\w-]+):\s*(.+?)$",
        re.MULTILINE,
    )

    matches = list(fr_pattern.finditer(content))
    for i, match in enumerate(matches):
        fr_id = match.group(1).strip()
        title = match.group(2).strip()

        # Extract text until next FR or next ## heading
        start = match.end()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            # Find next ## heading or end of content
            next_section = re.search(r"^##\s", content[start:], re.MULTILINE)
            end = start + next_section.start() if next_section else len(content)

        block = content[start:end]

        # Extract description
        desc_match = re.search(r"\*\*Description:\*\*\s*(.+?)(?:\n\*\*|\Z)", block, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else title

        # Extract acceptance criteria (lines starting with - Given or - )
        criteria = []
        criteria_section = re.search(r"\*\*Acceptance Criteria:\*\*(.+?)(?:\n\*\*|\n####|\Z)", block, re.DOTALL)
        if criteria_section:
            for line in criteria_section.group(1).strip().splitlines():
                line = line.strip().lstrip("- ")
                if line:
                    criteria.append(line)

        # Generate a task ID from the FR ID
        task_id = fr_id.replace("FR-", "TASK-").replace("-", "-", 1)

        tasks.append({
            "id": task_id,
            "title": title,
            "description": description,
            "acceptance_criteria": criteria,
            "status": "pending",
            "dependencies": [],
        })

    # Try to extract project name from title
    title_match = re.search(r"^#\s+.*?:\s*(.+?)$", content, re.MULTILINE)
    name = title_match.group(1).strip() if title_match else "unnamed-project"

    return {
        "name": name,
        "test_command": "pytest",
        "tasks": tasks,
    }
