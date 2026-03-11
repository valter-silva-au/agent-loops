# Agent Loops - Project Instructions

## What This Is

A Python framework that autonomously builds software using AI agent loops (the "Ralph Wiggum" pattern). It takes a `prd.json` spec, spawns Claude Agent SDK sessions in a loop, and each agent picks a task, implements it, runs tests, commits, and exits. Safety guardrails prevent runaway costs.

## Architecture

- `src/agent_loops/engine.py` — Main loop orchestrator
- `src/agent_loops/runner.py` — Claude Agent SDK wrapper (uses `query()` with hooks)
- `src/agent_loops/prompt.py` — Builds iteration prompts from state
- `src/agent_loops/spec.py` — prd.json parser with dependency-aware task selection
- `src/agent_loops/state.py` — Atomic read/write for state files (JSONL)
- `src/agent_loops/safety/` — Budget, gutter detection, kill switch, path guard, idempotency
- `src/agent_loops/cli.py` — Click CLI (run, status, init)
- `src/agent_loops/models.py` — Dataclasses for all shared types
- `src/agent_loops/markdown_parser.py` — Converts markdown PRDs to prd.json

## Development

```bash
pip install -e ".[dev]"
pytest -v
```

- Tests run without an API key (Agent SDK is mocked in integration tests)
- E2E tests requiring `ANTHROPIC_API_KEY` use `@pytest.mark.e2e`
- State files go in `.agent-loops/` (excluded from git status checks)

## Key Decisions

- Claude Agent SDK (not CLI subprocess) for programmatic hook control
- JSONL for progress/budget logs (append-only, crash-safe)
- Fresh `query()` per iteration (no persistent sessions)
- Safety enforced via PreToolUse/PostToolUse hooks
- Atomic file writes via `os.replace()`

## Planning Docs

All in `docs/`: RESEARCH.md → product-brief.md → prd.md → architecture-doc.md → epics.md
