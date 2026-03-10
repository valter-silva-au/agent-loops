# Architecture Document: Agent Loop Framework

**Date:** 2026-03-11
**Author:** design-reviewer
**Status:** Draft
**Source:** [PRD](prd.md) | [Product Brief](product-brief.md) | [Research](RESEARCH.md)

---

## 1. Overview

### 1.1 Purpose

This document defines the technical architecture for **agent-loops**, a Python framework that autonomously builds software by running Claude AI agents in a continuous loop (the "Ralph Wiggum" pattern). It covers the MVP components: the loop engine, state management, Agent SDK integration, safety guardrails, and CLI interface.

### 1.2 System Context

```
                         ┌─────────────────────────────────┐
                         │         agent-loops CLI          │
                         │   (agent-loops run --prd ...)    │
                         └──────────────┬──────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │            Loop Engine                 │
                    │   (spawns fresh agent per iteration)   │
                    └───┬───────────┬───────────────┬───────┘
                        │           │               │
              ┌─────────▼──┐  ┌────▼─────┐  ┌──────▼──────┐
              │   State    │  │  Agent   │  │   Safety    │
              │  Manager   │  │  Runner  │  │   Layer     │
              │            │  │          │  │             │
              │ prd.json   │  │  Claude  │  │ budget.jsonl│
              │ progress.  │  │  Agent   │  │ gutter det. │
              │  jsonl     │  │  SDK     │  │ kill switch │
              └─────┬──────┘  └────┬─────┘  └──────┬──────┘
                    │              │                │
                    │     ┌────────▼────────┐       │
                    │     │  Anthropic API  │       │
                    │     └────────────────┘       │
                    │                               │
              ┌─────▼───────────────────────────────▼──┐
              │         Target Project Directory        │
              │   (git repo being built by agents)      │
              └────────────────────────────────────────┘
```

**External actors:**
- **Founder/Operator**: Invokes CLI, authors `prd.json`, reviews output
- **Anthropic API**: Provides Claude model inference for Agent SDK sessions
- **Target project git repo**: The codebase being autonomously built

---

## 2. Key Decisions

### ADR-001: Claude Agent SDK as the Agent Interface

**Status:** Accepted
**Context:** The framework needs to spawn AI agent sessions that can read files, write code, run tests, and commit to git. Two options: shell out to Claude Code CLI or use the Agent SDK as a Python library.
**Decision:** Use the Claude Agent SDK Python library (`claude_agent_sdk`).
**Alternatives Considered:**
1. _Claude Code CLI subprocess_ -- Pros: simpler, no SDK dependency / Cons: no programmatic hook control, harder to enforce guardrails, subprocess overhead
2. _Raw Anthropic API + custom tool loop_ -- Pros: full control / Cons: massive implementation effort to replicate agent loop, tool routing, context management

**Rationale:** The Agent SDK provides `PreToolUse`/`PostToolUse` hooks via `HookMatcher`, `max_budget_usd` per session, `allowed_tools` scoping, and `ResultMessage.total_cost_usd` for cost tracking -- all critical for safety guardrails. The `query()` async generator provides a clean one-shot session model that aligns with the Ralph Wiggum pattern.
**Consequences:** Tied to Anthropic's SDK release cycle. Must handle SDK API changes across versions.

### ADR-002: Structured JSONL for All State Files

**Status:** Accepted
**Context:** The framework needs to persist progress, budget, and learnings across agent iterations.
**Decision:** Use append-only JSONL (one JSON object per line) for `progress.jsonl` and `budget.jsonl`. Use standard JSON for `prd.json`.
**Alternatives Considered:**
1. _SQLite database_ -- Pros: queryable, transactional / Cons: overkill for MVP, harder for agents to read directly
2. _Freeform markdown_ -- Pros: agent-friendly / Cons: unparseable for gutter detection, metrics

**Rationale:** JSONL is append-only (no read-modify-write races), machine-parseable for safety analysis, human-readable, and trivially readable by agents as prompt context.
**Consequences:** No complex queries; filtering is done in Python. Sufficient for MVP scale.

### ADR-003: One Session Per Iteration (Ralph Wiggum Pattern)

**Status:** Accepted
**Context:** Long-running agent sessions degrade in quality due to context window limits and compounding errors.
**Decision:** Each loop iteration spawns a completely fresh `query()` call with a clean context. State continuity comes entirely from filesystem artifacts.
**Alternatives Considered:**
1. _Persistent `ClaudeSDKClient` session_ -- Pros: maintains conversation context / Cons: context degradation, harder to enforce clean boundaries
2. _Multi-turn within iteration_ -- Pros: agent can self-correct / Cons: addressed by SDK's own agent loop within `query()`

**Rationale:** The SDK's `query()` function already runs its own internal agent loop (tool calls, retries) within a single invocation. Each `query()` call is a self-contained "iteration" that can make multiple tool calls. The outer Ralph Wiggum loop only needs to handle iteration-to-iteration state transfer.
**Consequences:** Each iteration starts with prompt construction overhead. Mitigated by the <2s prompt construction target.

### ADR-004: Safety via SDK Hooks (Not External Wrappers)

**Status:** Accepted
**Context:** Safety guardrails (budget enforcement, path scoping, dangerous command blocking) must intercept agent actions in real-time.
**Decision:** Implement all safety checks as `PreToolUse` and `PostToolUse` hooks registered via `ClaudeAgentOptions.hooks`.
**Alternatives Considered:**
1. _Wrapper scripts around tool binaries_ -- Pros: language-agnostic / Cons: fragile, bypassable, no structured deny/allow protocol
2. _Post-iteration validation only_ -- Pros: simpler / Cons: damage already done by the time we check

**Rationale:** SDK hooks provide a structured deny/allow protocol (`permissionDecision: "deny"`), fire synchronously before tool execution, and receive full tool input for inspection. This is the architecturally correct interception point.
**Consequences:** Safety logic runs in the same process as the agent. A crash in hook code could affect the agent session.

### ADR-005: Click for CLI Framework

**Status:** Accepted
**Context:** Need a CLI framework for `agent-loops run/status/init` commands.
**Decision:** Use Click (standard Python CLI library).
**Alternatives Considered:**
1. _Typer_ -- Pros: type-hint-based / Cons: extra dependency, Click is more established
2. _argparse_ -- Pros: stdlib / Cons: verbose, poor subcommand support

**Rationale:** Click is battle-tested, supports subcommands naturally, and is the most common choice in the Python ecosystem. Minimal dependency.
**Consequences:** None significant.

### ADR-006: Atomic File Writes for State Integrity

**Status:** Accepted
**Context:** `prd.json` is read-modify-written by the agent within `query()`. A crash mid-write could corrupt state.
**Decision:** All state file writes use atomic replacement: write to a temporary file, then `os.replace()` to the target path.
**Alternatives Considered:**
1. _Direct file writes_ -- Pros: simpler / Cons: corruption on crash
2. _File locking (fcntl)_ -- Pros: prevents concurrent access / Cons: overkill for single-agent MVP

**Rationale:** `os.replace()` is atomic on POSIX systems. Combined with JSONL append-only for progress/budget files, this ensures state integrity even on unexpected termination.
**Consequences:** Slightly more complex write path. Trivial implementation cost.

---

## 3. Component Design

### 3.1 Component Overview

| Component | Responsibility | Package/Module |
|-----------|---------------|----------------|
| **CLI** | Parse commands, validate args, invoke engine | `agent_loops/cli.py` |
| **Loop Engine** | Orchestrate iteration cycle: read state, run agent, write results, check termination | `agent_loops/engine.py` |
| **State Manager** | Read/write `prd.json`, `progress.jsonl`, `budget.jsonl`; atomic writes | `agent_loops/state.py` |
| **Prompt Builder** | Construct iteration prompt from current state | `agent_loops/prompt.py` |
| **Agent Runner** | Configure and invoke Claude Agent SDK `query()` with hooks | `agent_loops/runner.py` |
| **Safety: Budget Tracker** | Track cumulative tokens/cost, enforce caps | `agent_loops/safety/budget.py` |
| **Safety: Gutter Detector** | Detect thrashing patterns in progress history | `agent_loops/safety/gutter.py` |
| **Safety: Kill Switch** | Handle SIGINT and kill-file termination | `agent_loops/safety/kill.py` |
| **Safety: Path Guard** | Restrict file operations to target directory | `agent_loops/safety/pathguard.py` |
| **Spec Parser** | Validate `prd.json` schema, select next task, manage dependencies | `agent_loops/spec.py` |

### 3.2 Component Interactions

```
CLI
 │
 ▼
Loop Engine ──────────────────────────────────────────────┐
 │                                                         │
 │  ┌──► State Manager ──► read prd.json, progress.jsonl   │
 │  │                                                      │
 │  ├──► Spec Parser ──► select next task (dependency-aware)│
 │  │                                                      │
 │  ├──► Gutter Detector ──► check if task is blocked      │
 │  │                                                      │
 │  ├──► Prompt Builder ──► assemble iteration prompt      │
 │  │                                                      │
 │  ├──► Agent Runner ──► query() with hooks ──────────┐   │
 │  │         │                                        │   │
 │  │         ├── PreToolUse: Budget Tracker (check)    │   │
 │  │         ├── PreToolUse: Path Guard (scope check)  │   │
 │  │         ├── PostToolUse: Budget Tracker (tally)   │   │
 │  │         └── PostToolUse: Progress Logger          │   │
 │  │                                                   │   │
 │  ├──► State Manager ──► write progress, budget, prd  │   │
 │  │                                                   │   │
 │  ├──► Kill Switch ──► check SIGINT / kill file       │   │
 │  │                                                   │   │
 │  └──► Budget Tracker ──► check cumulative threshold  │   │
 │                                                      │   │
 └──── loop continues or terminates ◄──────────────────┘   │
                                                            │
 ◄──────────────────────────────────────────────────────────┘
```

### 3.3 Component Details

#### CLI (`agent_loops/cli.py`)

**Responsibility:** Parse user commands, validate arguments, invoke the loop engine.
**Interface:**
```python
# Commands:
# agent-loops run --prd <path> --dir <path> --max-iterations <N> --budget <USD> --model <name>
# agent-loops status --dir <path>
# agent-loops init [--from <prd.md>]
```
**Dependencies:** Click, Loop Engine, State Manager

#### Loop Engine (`agent_loops/engine.py`)

**Responsibility:** Orchestrate the Ralph Wiggum loop. For each iteration: read state, select task, build prompt, run agent, persist results, check termination conditions.
**Interface:**
```python
class LoopEngine:
    def __init__(self, config: LoopConfig) -> None: ...
    async def run(self) -> LoopResult: ...
    # LoopConfig holds: prd_path, project_dir, max_iterations, budget_usd, model
    # LoopResult holds: iterations_completed, tasks_done, total_cost_usd, exit_reason
```
**Dependencies:** State Manager, Spec Parser, Prompt Builder, Agent Runner, Safety components

#### State Manager (`agent_loops/state.py`)

**Responsibility:** Centralized read/write for all state files with atomic write guarantees.
**Interface:**
```python
class StateManager:
    def __init__(self, project_dir: Path) -> None: ...

    # prd.json
    def read_spec(self) -> dict: ...
    def write_spec(self, spec: dict) -> None: ...  # atomic

    # progress.jsonl
    def read_progress(self, last_n: int = 10) -> list[dict]: ...
    def append_progress(self, entry: ProgressEntry) -> None: ...

    # budget.jsonl
    def read_budget(self) -> list[dict]: ...
    def append_budget(self, entry: BudgetEntry) -> None: ...
    def get_cumulative_cost(self) -> float: ...
```
**Dependencies:** None (filesystem only)

#### Prompt Builder (`agent_loops/prompt.py`)

**Responsibility:** Construct the iteration prompt by assembling spec state, recent progress, git context, and behavioral rules.
**Interface:**
```python
class PromptBuilder:
    def __init__(self, project_dir: Path, state: StateManager) -> None: ...
    def build(self, task: Task, iteration: int) -> str: ...
```
**Dependencies:** State Manager, git CLI (for diff/log)

The prompt template includes:
1. **Role and rules**: "You are a software engineer. Complete exactly one task. Run tests. Commit on success. Write progress on exit."
2. **Current task**: Task ID, title, description, acceptance criteria from `prd.json`
3. **Project context**: File tree summary, recent git log (last 5 commits)
4. **Learnings**: Last 5 entries from `progress.jsonl` (successes and failures)
5. **Constraints**: Test command to run, files to avoid modifying, iteration number

#### Agent Runner (`agent_loops/runner.py`)

**Responsibility:** Configure and invoke a single Claude Agent SDK `query()` session with all hooks registered.
**Interface:**
```python
class AgentRunner:
    def __init__(self, config: RunnerConfig, hooks: list[HookMatcher]) -> None: ...
    async def run_iteration(self, prompt: str) -> IterationResult: ...
    # IterationResult holds: success, cost_usd, tokens_used, tool_calls, error
```
**Dependencies:** `claude_agent_sdk` (ClaudeAgentOptions, query, HookMatcher, ResultMessage)

Implementation maps directly to the SDK:
```python
options = ClaudeAgentOptions(
    allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
    system_prompt=self.system_prompt,
    permission_mode="bypassPermissions",
    cwd=self.project_dir,
    model=self.config.model,  # e.g., "claude-sonnet-4-6"
    max_turns=self.config.max_turns,  # limit tool calls per iteration
    max_budget_usd=self.config.per_iteration_budget,
    hooks={
        "PreToolUse": self.pre_hooks,
        "PostToolUse": self.post_hooks,
    },
)
async for message in query(prompt=prompt, options=options):
    # collect results, extract cost from ResultMessage
```

#### Safety: Budget Tracker (`agent_loops/safety/budget.py`)

**Responsibility:** Track cumulative token usage and cost across all iterations. Enforce warning at 80% and hard kill at 100%.
**Interface:**
```python
class BudgetTracker:
    def __init__(self, budget_usd: float, state: StateManager) -> None: ...
    def record(self, cost_usd: float, tokens: int) -> None: ...
    def check(self) -> BudgetStatus: ...  # returns OK | WARNING | EXCEEDED
    def get_pre_hook(self) -> Callable: ...  # returns PreToolUse hook function
    def get_post_hook(self) -> Callable: ...  # returns PostToolUse hook function
```
**Dependencies:** State Manager

The `PreToolUse` hook checks cumulative cost before each tool call. If budget is exceeded, it returns `permissionDecision: "deny"` to block the tool and signals the engine to terminate.

#### Safety: Gutter Detector (`agent_loops/safety/gutter.py`)

**Responsibility:** Analyze recent `progress.jsonl` entries to detect thrashing (same task failing N times consecutively with similar errors).
**Interface:**
```python
class GutterDetector:
    def __init__(self, threshold: int = 3) -> None: ...
    def check(self, progress: list[dict], task_id: str) -> GutterStatus: ...
    # GutterStatus: OK | BLOCKED (with reason)
```
**Dependencies:** None (pure function over progress data)

#### Safety: Kill Switch (`agent_loops/safety/kill.py`)

**Responsibility:** Handle graceful termination via SIGINT or kill-file detection.
**Interface:**
```python
class KillSwitch:
    def __init__(self, project_dir: Path) -> None: ...
    def install_signal_handler(self) -> None: ...  # registers SIGINT handler
    def check(self) -> bool: ...  # checks for kill file
    @property
    def triggered(self) -> bool: ...
```
**Dependencies:** None (signals + filesystem)

#### Safety: Path Guard (`agent_loops/safety/pathguard.py`)

**Responsibility:** PreToolUse hook that blocks file operations outside the target project directory.
**Interface:**
```python
class PathGuard:
    def __init__(self, project_dir: Path) -> None: ...
    def get_pre_hook(self) -> Callable: ...  # returns PreToolUse hook function
```
**Dependencies:** None

Inspects `tool_input` for Read, Write, Edit, Bash tools. Denies any path that resolves outside `project_dir`.

#### Spec Parser (`agent_loops/spec.py`)

**Responsibility:** Validate `prd.json` schema, select the next task based on status and dependency ordering, update task status.
**Interface:**
```python
class SpecParser:
    def __init__(self, spec: dict) -> None: ...
    def next_task(self) -> Task | None: ...  # returns next pending task with all deps met
    def mark_done(self, task_id: str) -> None: ...
    def mark_failed(self, task_id: str, reason: str) -> None: ...
    def mark_blocked(self, task_id: str, reason: str) -> None: ...
    def is_complete(self) -> bool: ...  # all tasks done or blocked
    def summary(self) -> dict: ...  # counts by status
```
**Dependencies:** None (pure data operations)

---

## 4. Data Model

### 4.1 Entities

| Entity | Description | Key Fields |
|--------|-------------|------------|
| **Spec** | Top-level product spec | `name`, `test_command`, `deploy_target`, `tasks[]` |
| **Task** | A unit of work in the spec | `id`, `title`, `description`, `acceptance_criteria`, `status`, `dependencies[]` |
| **ProgressEntry** | Record of one iteration | `iteration`, `task_id`, `status`, `changes[]`, `learnings`, `error`, `timestamp` |
| **BudgetEntry** | Cost record for one iteration | `iteration`, `cost_usd`, `input_tokens`, `output_tokens`, `cumulative_cost_usd`, `timestamp` |

### 4.2 Schemas

**`prd.json`:**
```json
{
  "name": "my-saas-app",
  "description": "A simple SaaS API with user auth",
  "test_command": "pytest",
  "deploy_target": "docker",
  "tasks": [
    {
      "id": "TASK-001",
      "title": "Initialize project structure",
      "description": "Create Python project with pyproject.toml, src/ layout, and pytest config",
      "acceptance_criteria": [
        "pyproject.toml exists with project metadata",
        "src/ directory with __init__.py exists",
        "pytest runs with 0 errors (even if 0 tests)"
      ],
      "status": "pending",
      "dependencies": []
    },
    {
      "id": "TASK-002",
      "title": "Add user model",
      "description": "Create SQLAlchemy User model with id, email, hashed_password",
      "acceptance_criteria": [
        "User model class exists",
        "Unit test for model creation passes"
      ],
      "status": "pending",
      "dependencies": ["TASK-001"]
    }
  ]
}
```

**`progress.jsonl`** (one line per entry):
```json
{"iteration": 1, "task_id": "TASK-001", "status": "success", "changes": ["pyproject.toml", "src/__init__.py"], "learnings": "Used src layout with pytest auto-discovery", "error": null, "timestamp": "2026-03-11T22:15:00Z"}
{"iteration": 2, "task_id": "TASK-002", "status": "failed", "changes": [], "learnings": null, "error": "ImportError: sqlalchemy not in requirements", "timestamp": "2026-03-11T22:22:00Z"}
```

**`budget.jsonl`** (one line per entry):
```json
{"iteration": 1, "cost_usd": 0.42, "input_tokens": 15000, "output_tokens": 3200, "cumulative_cost_usd": 0.42, "timestamp": "2026-03-11T22:15:00Z"}
{"iteration": 2, "cost_usd": 0.38, "input_tokens": 14000, "output_tokens": 2800, "cumulative_cost_usd": 0.80, "timestamp": "2026-03-11T22:22:00Z"}
```

### 4.3 Storage

| Data | Store | Rationale |
|------|-------|-----------|
| Product spec (`prd.json`) | JSON file in project root | Agents read/update directly; human-editable; atomic writes |
| Progress log (`progress.jsonl`) | JSONL file in `.agent-loops/` | Append-only; machine-parseable for gutter detection |
| Budget log (`budget.jsonl`) | JSONL file in `.agent-loops/` | Append-only; cumulative cost tracking |
| Code changes | Git commits in target repo | Externalized memory; rollback via `git revert` |
| Framework config | CLI flags + optional `.agent-loops/config.json` | Overridable defaults |

State files live in `.agent-loops/` within the target project directory to keep framework artifacts separate from generated code.

---

## 5. API Design

This is a CLI tool, not a web service. The "API" is the CLI interface and the `prd.json` spec format.

### 5.1 CLI Commands

| Command | Arguments | Description |
|---------|-----------|-------------|
| `agent-loops run` | `--prd PATH` (required), `--dir PATH` (default: `.`), `--max-iterations N` (default: 100), `--budget FLOAT` (USD, default: 50.0), `--model STR` (default: `claude-sonnet-4-6`) | Start the autonomous build loop |
| `agent-loops status` | `--dir PATH` (default: `.`) | Display current loop state: iterations, tasks, cost |
| `agent-loops init` | `--from PATH` (optional markdown PRD) | Generate a template `prd.json` |

### 5.2 Programmatic API (Future)

The `LoopEngine` class is designed to be importable for programmatic use:
```python
from agent_loops.engine import LoopEngine, LoopConfig

config = LoopConfig(
    prd_path=Path("prd.json"),
    project_dir=Path("./my-project"),
    max_iterations=50,
    budget_usd=30.0,
    model="claude-sonnet-4-6",
)
engine = LoopEngine(config)
result = await engine.run()
print(f"Completed {result.tasks_done} tasks in {result.iterations_completed} iterations (${result.total_cost_usd:.2f})")
```

---

## 6. Security

### 6.1 Authentication

- The framework authenticates to the Anthropic API via the `ANTHROPIC_API_KEY` environment variable.
- No user authentication is needed (single-user CLI tool).

### 6.2 Authorization

- **Tool scoping**: `ClaudeAgentOptions.allowed_tools` restricts agent to: Bash, Read, Write, Edit, Glob, Grep. No WebFetch, no Agent spawning.
- **Path scoping**: PathGuard `PreToolUse` hook denies file operations outside the target project directory.
- **Command blocking**: PreToolUse hook denies dangerous bash patterns: `rm -rf /`, `git push --force`, `git reset --hard`, `curl | sh`, etc.
- **Permission mode**: `bypassPermissions` within the scoped tool set (agent runs unattended; safety is enforced by hooks, not interactive prompts).

### 6.3 Data Protection

- **No PII in state files**: Progress and budget logs contain only task IDs, file paths, error messages, and metrics. No user data.
- **API keys never persisted**: `ANTHROPIC_API_KEY` read from env, never written to any file.
- **`.agent-loops/` in `.gitignore`**: Framework state files are not committed to the generated project's git history (only code changes are committed).

---

## 7. Deployment & Operations

### 7.1 Deployment Strategy

**Package distribution:** Published to PyPI as `agent-loops`. Install via `pip install agent-loops`.

**Project structure:**
```
agent-loops/
├── pyproject.toml
├── src/
│   └── agent_loops/
│       ├── __init__.py
│       ├── cli.py           # Click CLI commands
│       ├── engine.py         # Loop engine orchestration
│       ├── state.py          # State file read/write
│       ├── prompt.py         # Iteration prompt construction
│       ├── runner.py         # Agent SDK wrapper
│       ├── spec.py           # prd.json parser and task selector
│       ├── models.py         # Dataclasses: LoopConfig, Task, ProgressEntry, etc.
│       └── safety/
│           ├── __init__.py
│           ├── budget.py     # Token/cost budget enforcement
│           ├── gutter.py     # Thrashing detection
│           ├── kill.py       # SIGINT + kill file handler
│           └── pathguard.py  # File path scoping
├── tests/
│   ├── test_engine.py
│   ├── test_state.py
│   ├── test_prompt.py
│   ├── test_spec.py
│   ├── test_safety/
│   │   ├── test_budget.py
│   │   ├── test_gutter.py
│   │   ├── test_kill.py
│   │   └── test_pathguard.py
│   └── conftest.py
└── docs/
    ├── RESEARCH.md
    ├── product-brief.md
    ├── prd.md
    └── architecture-doc.md
```

### 7.2 Monitoring

| What | How | Alert Threshold |
|------|-----|-----------------|
| Cumulative API cost | `budget.jsonl` cumulative total | Warning at 80%, kill at 100% of `--budget` |
| Iteration success rate | `progress.jsonl` success/total ratio | Log warning if < 40% over last 10 iterations |
| Gutter detection | Consecutive same-task failures in `progress.jsonl` | Block task after 3 consecutive failures |
| Kill file presence | Check `.agent-loops/kill` at iteration boundaries | Immediate graceful shutdown |
| Loop wall-clock time | Tracked in engine | Log total elapsed on termination |

### 7.3 Failure Modes

| Failure | Impact | Recovery |
|---------|--------|----------|
| Anthropic API outage | Agent iteration fails | Exponential backoff (1s, 2s, 4s, 8s, max 60s) with jitter. After 5 consecutive API failures, pause loop and log. |
| Agent produces broken code | Test failure, no commit | Changes discarded (`git checkout .`), failure logged, next iteration retries or moves on |
| Crash mid-state-write | Potentially corrupted state file | Atomic writes (`os.replace`) prevent partial writes. JSONL append is crash-safe (partial last line discarded on read). |
| Budget exceeded mid-iteration | Current iteration's tools blocked | PreToolUse hook denies all further tools. Agent receives deny reason, exits. Loop terminates. |
| SIGINT during agent execution | Need clean shutdown | Signal handler sets flag. Engine waits up to 30s for current tool call, then saves state and exits. |
| Disk full | Cannot write state files | Caught as IOError. Loop terminates with error logged to stderr. |

---

## 8. Testing Strategy

| Layer | Scope | Tools | Key Tests |
|-------|-------|-------|-----------|
| **Unit** | Individual functions/methods | pytest, pytest-asyncio | Spec parser task selection logic; gutter detection algorithm; budget threshold math; prompt template construction; atomic file writes |
| **Integration** | Component interactions | pytest, tmp_path fixture | State Manager round-trip (write then read); Loop Engine with mocked Agent Runner (verify iteration flow); Safety hooks with simulated tool calls |
| **E2E** | Full loop with real Agent SDK | pytest (slow suite), real API key | Run `agent-loops run` against a trivial `prd.json` (e.g., "create a hello.py that prints hello world"). Verify: task marked done, git commit exists, progress.jsonl populated, budget tracked. |

**Testing principles:**
- Unit and integration tests run without API keys (Agent Runner mocked).
- E2E tests are opt-in (`pytest -m e2e`) and require `ANTHROPIC_API_KEY`.
- Safety tests include adversarial cases: path traversal attempts, budget overflow, concurrent SIGINT.

---

## 9. PRD Requirement Traceability

| Requirement | Component(s) | How Addressed |
|-------------|-------------|---------------|
| FR-M2-001: Loop Harness | Loop Engine, Agent Runner | `LoopEngine.run()` iterates, `AgentRunner.run_iteration()` calls `query()` per iteration |
| FR-M2-002: Externalized State | State Manager | `read_spec()`, `append_progress()`, `write_spec()` with atomic writes |
| FR-M2-003: Prompt Construction | Prompt Builder | `build()` assembles task + progress + git context + rules |
| FR-M2-004: Test-Driven Cycle | Prompt Builder (rules), Agent Runner | Prompt instructs agent to run test command; PostToolUse logs results |
| FR-M2-005: Spec Format | Spec Parser, models.py | `prd.json` schema with Task dataclass; `next_task()` respects dependencies |
| FR-M2-006: Agent SDK Integration | Agent Runner | Direct use of `query()`, `ClaudeAgentOptions`, `HookMatcher` |
| FR-SL-001: Budget Enforcement | Budget Tracker | PreToolUse hook denies at cap; PostToolUse tallies cost |
| FR-SL-002: Iteration Limits | Loop Engine | Counter in `run()` loop, terminates at max |
| FR-SL-003: Gutter Detection | Gutter Detector | `check()` called before each iteration; blocks thrashing tasks |
| FR-SL-004: Idempotency Guard | State Manager | Duplicate commit detection via git diff check before commit |
| FR-SL-005: Kill Switch | Kill Switch | SIGINT handler + kill file check at iteration boundary |
| FR-M3-001: CI Pipeline | Prompt Builder | Final iteration prompt includes CI generation instruction if all tasks done |
| FR-M3-002: Deploy Config | Prompt Builder | Conditional instruction based on `deploy_target` in spec |
| FR-CLI-001: Run Command | CLI | `agent-loops run` with Click |
| FR-CLI-002: Status Command | CLI, State Manager | Reads state files, formats summary |
| FR-CLI-003: Init Command | CLI, Spec Parser | Template generation or markdown parsing |

All 16 functional requirements have architectural implementation paths. No components exist without corresponding requirements.

---

## 10. Open Questions

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | What is the optimal `max_turns` per Agent SDK session? Too low = agent can't complete complex tasks. Too high = cost bloat. | Performance / cost | Valter |
| 2 | Should the framework auto-install project dependencies (e.g., `pip install -r requirements.txt`) at the start of each iteration? | Agent success rate | Valter |
| 3 | How should the prompt handle large codebases that exceed context limits? (e.g., file tree truncation, selective inclusion) | Scalability | Valter |
| 4 | Should `.agent-loops/` state survive across multiple `agent-loops run` invocations (resume) or start fresh? | UX | Valter |

---

_This architecture document was generated during the Architecture phase. Next step: run `/create-stories` to decompose into implementable epics and stories._
