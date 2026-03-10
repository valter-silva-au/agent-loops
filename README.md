# agent-loops

A Python framework that autonomously builds software from a structured spec using AI agent loops.

## How It Works

1. You write a product spec (`prd.json`) describing what to build
2. Run `agent-loops run --prd spec.json`
3. The framework spawns Claude AI agents in a continuous loop (the "Ralph Wiggum" pattern)
4. Each agent reads the current state, picks a task, implements it, runs tests, commits, and exits
5. A fresh agent spawns with a clean context and continues from where the last one left off
6. Safety guardrails (token budgets, iteration caps, gutter detection) prevent runaway costs
7. By morning, you have a tested, committed codebase

## Quick Start

```bash
# Install
pip install agent-loops

# Or from source
git clone https://github.com/valter-silva-au/agent-loops.git
cd agent-loops
pip install -e ".[dev]"

# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Create a project directory
mkdir my-app && cd my-app && git init && git commit --allow-empty -m "init"

# Copy a spec (or create your own)
cp ../examples/hello-world.json prd.json
git add . && git commit -m "add spec"

# Run the loop
agent-loops run --prd prd.json --max-iterations 20 --budget 10.0
```

## CLI Commands

```bash
# Start the autonomous build loop
agent-loops run --prd spec.json --dir ./project --max-iterations 50 --budget 30.0 --model claude-sonnet-4-6

# Check progress of a running or completed loop
agent-loops status --dir ./project

# Generate prd.json from a markdown PRD
agent-loops init --from docs/prd.md

# Generate prd.json interactively
agent-loops init
```

## Spec Format (`prd.json`)

```json
{
  "name": "my-app",
  "test_command": "pytest",
  "deploy_target": "docker",
  "tasks": [
    {
      "id": "TASK-001",
      "title": "Create main module",
      "description": "Create src/main.py with a hello world function",
      "acceptance_criteria": ["main.py exists", "function returns 'hello'"],
      "status": "pending",
      "dependencies": []
    },
    {
      "id": "TASK-002",
      "title": "Add tests",
      "description": "Create tests for the main module",
      "acceptance_criteria": ["test file exists", "tests pass"],
      "status": "pending",
      "dependencies": ["TASK-001"]
    }
  ]
}
```

## Safety Guardrails

| Guardrail | What It Does |
|-----------|-------------|
| **Budget Cap** | Hard USD limit (`--budget`). Warning at 80%, kill at 100%. |
| **Iteration Limit** | Maximum loop iterations (`--max-iterations`, default: 100). |
| **Gutter Detection** | Blocks tasks that fail 3 times consecutively. |
| **Kill Switch** | `Ctrl+C` or create `.agent-loops/kill` file for graceful shutdown. |
| **Path Guard** | Blocks file operations outside the project directory. |
| **Command Blocking** | Denies `rm -rf /`, `git push --force`, pipe-to-shell, etc. |

## State Files

The framework stores state in `.agent-loops/` within the project directory:

- `progress.jsonl` — one JSONL entry per iteration (task, status, learnings)
- `budget.jsonl` — token usage and cost per iteration with cumulative totals

The `prd.json` spec is updated in-place as tasks complete.

## Documentation

| Document | Description |
|----------|-------------|
| [Product Brief](docs/product-brief.md) | Vision, problem statement, key features |
| [PRD](docs/prd.md) | 16 functional requirements with acceptance criteria |
| [Architecture](docs/architecture-doc.md) | 10 components, 6 ADRs, data model, security |
| [Epics & Stories](docs/epics.md) | 29 stories across 8 epics with dependency map |
| [Research](docs/RESEARCH.md) | Background on autonomous agent loops and SaaS automation |

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Run only fast tests (no API key needed)
pytest -v -m "not e2e"
```

## License

MIT
