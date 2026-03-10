# Epics and Stories: Agent Loop Framework

**Date:** 2026-03-11
**Author:** product-owner
**Source:** [PRD](prd.md) | [Architecture](architecture-doc.md) | [Product Brief](product-brief.md)

---

## Epic Overview

| Epic | Name | PRD Requirements | Architecture Components | Priority | Stories |
|------|------|-----------------|------------------------|----------|---------|
| E1 | Project Foundation | -- | All | Must-Have | 3 |
| E2 | Spec & Task Management | FR-M2-005 | Spec Parser, models.py | Must-Have | 4 |
| E3 | State Management | FR-M2-002 | State Manager | Must-Have | 3 |
| E4 | Safety Guardrails | FR-SL-001 to FR-SL-005 | safety/* | Must-Have | 6 |
| E5 | Core Loop Engine | FR-M2-001, FR-M2-003, FR-M2-006 | Loop Engine, Prompt Builder, Agent Runner | Must-Have | 5 |
| E6 | Test-Driven Build Cycle | FR-M2-004 | Prompt Builder (rules) | Must-Have | 2 |
| E7 | CLI Interface | FR-CLI-001 to FR-CLI-003 | CLI | Must-Have/Should-Have | 4 |
| E8 | Infrastructure Generation | FR-M3-001, FR-M3-002 | Prompt Builder | Should-Have/Nice-to-Have | 2 |

**Total: 8 epics, 29 stories**

---

## E1: Project Foundation

_Set up the Python project structure, dependencies, and development tooling._

No direct PRD requirement -- this is prerequisite infrastructure for all other epics.

### S1.1: Initialize Python Project

**Size:** S
**As a** developer, **I want** a properly structured Python project with `pyproject.toml`, src layout, and dev dependencies, **so that** all subsequent code has a consistent home.

**Acceptance Criteria:**
- Given the repo is cloned, when `pip install -e ".[dev]"` is run, then the package installs successfully
- Given the project structure, when I look at `src/agent_loops/`, then it contains `__init__.py` with version info
- Given `pyproject.toml`, when inspected, then it declares: Python >=3.11, click, claude-agent-sdk as dependencies, and pytest + pytest-asyncio as dev dependencies

**Architecture:** `src/agent_loops/` layout per Section 7.1
**Dependencies:** None

### S1.2: Define Core Data Models

**Size:** S
**As a** developer, **I want** dataclass definitions for all shared data structures, **so that** components have a consistent type contract.

**Acceptance Criteria:**
- Given `models.py`, when imported, then it exports: `LoopConfig`, `LoopResult`, `Task`, `ProgressEntry`, `BudgetEntry`, `IterationResult`, `BudgetStatus`, `GutterStatus`
- Given `LoopConfig`, when instantiated, then it requires: `prd_path`, `project_dir`, `max_iterations`, `budget_usd`, `model`
- Given `Task`, when instantiated, then it has: `id`, `title`, `description`, `acceptance_criteria`, `status`, `dependencies`
- Given each dataclass, when invalid data is provided, then a `ValueError` is raised with a descriptive message

**Architecture:** `agent_loops/models.py` per Section 4.1
**Dependencies:** S1.1

### S1.3: Set Up Test Infrastructure

**Size:** S
**As a** developer, **I want** pytest configured with asyncio support, fixtures, and markers, **so that** all subsequent stories can include tests from the start.

**Acceptance Criteria:**
- Given `pytest` is run, when there are no test files, then it exits with 0 errors
- Given `conftest.py`, when inspected, then it provides: `tmp_project` fixture (temp dir with git init), `sample_spec` fixture (minimal prd.json)
- Given `pyproject.toml`, when inspected, then it configures pytest with `asyncio_mode = "auto"` and marker `e2e` for slow tests

**Architecture:** `tests/conftest.py` per Section 8
**Dependencies:** S1.1

---

## E2: Spec & Task Management

_Parse, validate, and manage the `prd.json` product spec and task lifecycle._

**PRD Requirements:** FR-M2-005

### S2.1: Define prd.json Schema

**Size:** S
**As a** founder, **I want** a well-defined JSON schema for `prd.json`, **so that** I know exactly how to structure my product spec.

**Acceptance Criteria:**
- Given a valid `prd.json`, when parsed by `SpecParser`, then all required fields are present: `name`, `test_command`, `tasks[]`
- Given a task in `prd.json`, when parsed, then it has: `id`, `title`, `description`, `acceptance_criteria[]`, `status`, `dependencies[]`
- Given `status`, when read, then it is one of: `pending`, `in_progress`, `done`, `failed`, `blocked`
- Given an invalid `prd.json` (missing required fields), when parsed, then a `SpecValidationError` is raised with details about what's wrong

**Architecture:** `agent_loops/spec.py`, `agent_loops/models.py` per Section 4.2
**Dependencies:** S1.2

### S2.2: Implement Task Selection with Dependency Resolution

**Size:** M
**As an** agent actor, **I want** the framework to select the next available task respecting dependency order, **so that** I always work on a task whose prerequisites are complete.

**Acceptance Criteria:**
- Given tasks A (no deps) and B (depends on A), when `next_task()` is called and A is pending, then A is returned
- Given task A is done and B depends on A, when `next_task()` is called, then B is returned
- Given task B depends on A and A is pending, when `next_task()` is called, then B is skipped
- Given all tasks are done or blocked, when `next_task()` is called, then `None` is returned
- Given multiple tasks have no unmet dependencies, when `next_task()` is called, then the first pending task by list order is returned

**Architecture:** `SpecParser.next_task()` per Section 3.3
**Dependencies:** S2.1

### S2.3: Implement Task Status Updates

**Size:** S
**As a** loop engine, **I want** to mark tasks as done, failed, or blocked, **so that** subsequent iterations see the updated state.

**Acceptance Criteria:**
- Given a pending task, when `mark_done(task_id)` is called, then its status changes to `done`
- Given a pending task, when `mark_failed(task_id, reason)` is called, then its status changes to `failed`
- Given a pending task, when `mark_blocked(task_id, reason)` is called, then its status changes to `blocked`
- Given an already-done task, when `mark_done()` is called again, then it remains `done` (idempotent)
- Given the spec, when `summary()` is called, then it returns counts: `{"pending": N, "done": N, "failed": N, "blocked": N}`

**Architecture:** `SpecParser.mark_done()`, `mark_failed()`, `mark_blocked()`, `summary()` per Section 3.3
**Dependencies:** S2.1

### S2.4: Implement Spec Completion Check

**Size:** S
**As a** loop engine, **I want** to know when all tasks are done or blocked, **so that** the loop can terminate.

**Acceptance Criteria:**
- Given all tasks are `done`, when `is_complete()` is called, then it returns `True`
- Given all tasks are `done` or `blocked`, when `is_complete()` is called, then it returns `True`
- Given at least one task is `pending`, when `is_complete()` is called, then it returns `False`

**Architecture:** `SpecParser.is_complete()` per Section 3.3
**Dependencies:** S2.3

---

## E3: State Management

_Read and write all persistent state files with atomic guarantees._

**PRD Requirements:** FR-M2-002

### S3.1: Implement Atomic File Writes

**Size:** S
**As a** framework, **I want** all state file writes to be atomic, **so that** a crash mid-write never corrupts state.

**Acceptance Criteria:**
- Given `write_spec(spec)` is called, when the write completes, then the file is written via temp file + `os.replace()`
- Given a crash occurs during `write_spec()`, when the system recovers, then the previous valid `prd.json` is intact
- Given `append_progress(entry)` is called, when the write completes, then a single JSONL line is appended with a trailing newline
- Given `.agent-loops/` directory does not exist, when any state write is attempted, then the directory is created automatically

**Architecture:** `StateManager` per Section 3.3, ADR-006
**Dependencies:** S1.2

### S3.2: Implement Progress Log Read/Write

**Size:** S
**As a** prompt builder, **I want** to read the last N progress entries, **so that** the agent receives context from prior iterations.

**Acceptance Criteria:**
- Given `progress.jsonl` has 20 entries, when `read_progress(last_n=5)` is called, then the last 5 entries are returned as dicts
- Given `progress.jsonl` does not exist, when `read_progress()` is called, then an empty list is returned
- Given a `ProgressEntry`, when `append_progress(entry)` is called, then a valid JSONL line is appended with ISO 8601 timestamp
- Given `progress.jsonl` has a partial last line (crash artifact), when `read_progress()` is called, then the partial line is skipped without error

**Architecture:** `StateManager.read_progress()`, `append_progress()` per Section 3.3
**Dependencies:** S3.1

### S3.3: Implement Budget Log Read/Write

**Size:** S
**As a** budget tracker, **I want** to read cumulative cost from the budget log, **so that** I can enforce spending caps.

**Acceptance Criteria:**
- Given `budget.jsonl` has entries, when `get_cumulative_cost()` is called, then it returns the `cumulative_cost_usd` from the last entry
- Given `budget.jsonl` does not exist, when `get_cumulative_cost()` is called, then `0.0` is returned
- Given a `BudgetEntry`, when `append_budget(entry)` is called, then a valid JSONL line is appended

**Architecture:** `StateManager.read_budget()`, `append_budget()`, `get_cumulative_cost()` per Section 3.3
**Dependencies:** S3.1

---

## E4: Safety Guardrails

_Implement all safety mechanisms to enable safe unattended operation._

**PRD Requirements:** FR-SL-001, FR-SL-002, FR-SL-003, FR-SL-004, FR-SL-005

### S4.1: Implement Token Budget Tracker

**Size:** M
**As a** founder, **I want** cumulative token usage tracked with hard spending caps, **so that** I don't wake up to a $500 API bill.

**Acceptance Criteria:**
- Given `--budget 50.0` is set, when cumulative cost reaches $40 (80%), then a warning is logged to stderr
- Given cumulative cost reaches $50 (100%), when the threshold is hit, then the PreToolUse hook returns `permissionDecision: "deny"` and the engine terminates
- Given each iteration completes, when `record(cost_usd, tokens)` is called, then a `BudgetEntry` is appended to `budget.jsonl` with cumulative totals
- Given the Agent SDK returns `ResultMessage.total_cost_usd`, when the iteration ends, then that value is used for budget tracking

**Architecture:** `safety/budget.py` with PreToolUse/PostToolUse hooks per Section 3.3, ADR-004
**Dependencies:** S3.3, S1.2

### S4.2: Implement Iteration Limits

**Size:** S
**As a** founder, **I want** a maximum iteration count, **so that** the loop always terminates even if tasks never complete.

**Acceptance Criteria:**
- Given `--max-iterations 50`, when 50 iterations have completed, then the loop exits with `exit_reason: "max_iterations_reached"`
- Given no `--max-iterations` flag, when the loop starts, then the default is 100 iterations
- Given max iterations reached, when the loop exits, then all state files are properly finalized

**Architecture:** Counter in `LoopEngine.run()` per Section 3.3
**Dependencies:** S1.2

### S4.3: Implement Gutter Detection

**Size:** M
**As a** founder, **I want** the framework to detect when an agent keeps failing on the same task, **so that** it moves on instead of burning budget on an impossible task.

**Acceptance Criteria:**
- Given the last 3 progress entries all show `status: "failed"` for task TASK-005 with similar error strings, when a new iteration starts, then TASK-005 is marked `blocked` with the error history
- Given a task is marked `blocked`, when `next_task()` is called, then it selects the next non-blocked pending task
- Given the last 3 entries are: fail TASK-005, fail TASK-005, success TASK-005, when checked, then TASK-005 is NOT blocked (the success broke the streak)
- Given the last 3 entries are: fail TASK-005, fail TASK-006, fail TASK-005, when checked, then neither task is blocked (failures are not consecutive for the same task)

**Architecture:** `safety/gutter.py` per Section 3.3
**Dependencies:** S3.2, S2.3

### S4.4: Implement Kill Switch

**Size:** S
**As a** founder, **I want** to stop the loop cleanly at any time via Ctrl+C or a kill file, **so that** I maintain control and state is never corrupted.

**Acceptance Criteria:**
- Given the loop is running, when SIGINT is received, then the framework sets a termination flag and waits up to 30 seconds for the current agent to finish
- Given SIGINT was received and 30 seconds elapsed, when the timeout expires, then the agent process is forcefully terminated and state is saved
- Given a file `.agent-loops/kill` exists in the project directory, when the engine checks at iteration boundaries, then the loop terminates gracefully
- Given the kill file triggered shutdown, when the loop exits, then the kill file is deleted and `exit_reason: "kill_switch"` is reported

**Architecture:** `safety/kill.py` per Section 3.3
**Dependencies:** S1.2

### S4.5: Implement Path Guard

**Size:** S
**As a** founder, **I want** the agent restricted to the target project directory, **so that** it cannot read or modify files outside the project.

**Acceptance Criteria:**
- Given `project_dir` is `/home/user/my-project`, when the agent attempts to Read `/etc/passwd`, then the PreToolUse hook returns `permissionDecision: "deny"` with reason "Path outside project directory"
- Given the agent writes to `/home/user/my-project/src/main.py`, when the hook checks, then the write is allowed
- Given the agent runs `cat /etc/shadow` via Bash, when the hook inspects the command, then it denies commands referencing paths outside project_dir
- Given a path with `../` traversal, when resolved, then it is checked against the canonical project_dir

**Architecture:** `safety/pathguard.py` per Section 3.3
**Dependencies:** S1.2

### S4.6: Implement Idempotency Guard

**Size:** S
**As a** framework, **I want** duplicate side-effects prevented, **so that** agents don't create duplicate commits or overwrite files with identical content.

**Acceptance Criteria:**
- Given an agent attempts to commit, when the git diff is empty (no changes), then the commit is skipped and a warning is logged
- Given an agent writes file content identical to what's already on disk, when the write hook checks, then the write is skipped
- Given duplicate detection fires, when logged, then the progress entry notes `"duplicate_detected": true`

**Architecture:** State Manager + PostToolUse hook per FR-SL-004
**Dependencies:** S3.1

---

## E5: Core Loop Engine

_Implement the main orchestration loop, prompt construction, and Agent SDK integration._

**PRD Requirements:** FR-M2-001, FR-M2-003, FR-M2-006

### S5.1: Implement Agent Runner (SDK Wrapper)

**Size:** M
**As a** loop engine, **I want** to invoke a single Claude Agent SDK session with configured tools and hooks, **so that** each iteration is a controlled, observable agent execution.

**Acceptance Criteria:**
- Given a prompt and config, when `run_iteration(prompt)` is called, then a `query()` call is made with `ClaudeAgentOptions` configured for: allowed_tools, system_prompt, cwd, model, max_turns, max_budget_usd, and all hooks
- Given the agent session completes, when `ResultMessage` is received, then `IterationResult` is returned with: success flag, cost_usd, tokens_used, error (if any)
- Given the agent session raises an API error, when caught, then `IterationResult` is returned with `success=False` and the error details
- Given hooks are provided, when the agent calls tools, then PreToolUse and PostToolUse hooks fire correctly

**Architecture:** `agent_loops/runner.py` per Section 3.3, uses `query()`, `ClaudeAgentOptions`, `HookMatcher`
**Dependencies:** S4.1, S4.5, S1.2

### S5.2: Implement Prompt Builder

**Size:** M
**As an** agent actor, **I want** a clear, structured prompt that tells me exactly what to do, **so that** I can complete my task efficiently without prior context.

**Acceptance Criteria:**
- Given a task and current state, when `build(task, iteration)` is called, then the prompt includes: role/rules section, current task details, acceptance criteria, project file tree (truncated to 50 lines), last 5 progress entries, last 5 git log messages, test command to run
- Given the task has acceptance criteria, when the prompt is built, then each criterion is listed as a checklist item the agent must verify
- Given `progress.jsonl` has prior failures for related tasks, when the prompt is built, then relevant learnings are included
- Given the prompt, when measured, then it is constructed in under 2 seconds

**Architecture:** `agent_loops/prompt.py` per Section 3.3
**Dependencies:** S3.2, S2.1

### S5.3: Implement Loop Engine Core

**Size:** L
**As a** founder, **I want** the main loop that orchestrates read-state, select-task, build-prompt, run-agent, write-results, check-termination, **so that** the entire autonomous build cycle works end-to-end.

**Acceptance Criteria:**
- Given a valid `prd.json` and project dir, when `LoopEngine.run()` is called, then it executes iterations: read spec -> select task -> check gutter -> build prompt -> run agent -> update spec -> write progress -> write budget -> check termination
- Given an iteration succeeds (agent completes task, tests pass), when the iteration ends, then: task is marked `done` in prd.json, progress entry with `status: "success"` is written, git commit exists
- Given an iteration fails, when the iteration ends, then: task remains `pending`, progress entry with `status: "failed"` is written, uncommitted changes are discarded
- Given max iterations or budget exceeded or kill switch or all tasks done, when the termination condition is met, then the loop exits and returns `LoopResult` with summary
- Given the loop completes, when `LoopResult` is returned, then it contains: `iterations_completed`, `tasks_done`, `total_cost_usd`, `exit_reason`
- Given 5 consecutive API errors, when the retry threshold is exceeded, then the loop pauses with `exit_reason: "api_errors"`

**Architecture:** `agent_loops/engine.py` per Section 3.2, integrates all other components
**Dependencies:** S5.1, S5.2, S2.2, S3.1, S3.2, S3.3, S4.1, S4.2, S4.3, S4.4

### S5.4: Implement Git Operations

**Size:** S
**As a** loop engine, **I want** to validate git state at startup and discard uncommitted changes on failure, **so that** the git repo stays clean between iterations.

**Acceptance Criteria:**
- Given the project dir is not a git repo, when the loop starts, then it exits with an error: "Target directory must be a git repository"
- Given the working tree has uncommitted changes, when the loop starts, then it exits with an error: "Clean working tree required. Commit or stash changes first."
- Given an iteration fails, when cleanup runs, then `git checkout .` and `git clean -fd` restore the working tree to the last commit
- Given the loop finishes, when inspected, then no force-pushes or rebases were executed

**Architecture:** Loop Engine git safety per NFR 5.3
**Dependencies:** S1.2

### S5.5: Implement API Error Retry with Backoff

**Size:** S
**As a** loop engine, **I want** transient API errors to trigger exponential backoff, **so that** temporary outages don't permanently halt the loop.

**Acceptance Criteria:**
- Given an API error (rate limit, 500, timeout), when caught, then the engine waits with exponential backoff: 1s, 2s, 4s, 8s, capped at 60s, with random jitter (0-1s)
- Given 5 consecutive API errors, when the threshold is reached, then the loop terminates with `exit_reason: "api_errors"` instead of retrying indefinitely
- Given a successful iteration after an API error, when the counter resets, then the consecutive error count returns to 0

**Architecture:** Loop Engine error handling per Section 7.3
**Dependencies:** S5.1

---

## E6: Test-Driven Build Cycle

_Ensure the agent runs tests after changes and only commits passing code._

**PRD Requirements:** FR-M2-004

### S6.1: Embed Test-Driven Rules in Prompt

**Size:** S
**As an** agent actor, **I want** clear instructions to run tests after changes and only commit on pass, **so that** I follow the test-driven build cycle consistently.

**Acceptance Criteria:**
- Given the prompt template, when built, then it includes explicit rules: "After making changes, run the test command. If tests pass, commit with a message referencing the task ID. If tests fail, read the error output and attempt to fix. If you cannot fix after 3 attempts within this session, discard all changes and report the failure."
- Given `prd.json` has a `test_command` field, when the prompt is built, then the exact test command (e.g., `pytest`) is included in the instructions
- Given the test command is missing from `prd.json`, when the prompt is built, then the agent is instructed to detect the appropriate test runner from project files

**Architecture:** `prompt.py` behavioral rules per Section 3.3
**Dependencies:** S5.2

### S6.2: Validate Iteration Outcome via Git State

**Size:** S
**As a** loop engine, **I want** to detect whether the agent committed (success) or left dirty state (failure), **so that** I can correctly record the iteration outcome.

**Acceptance Criteria:**
- Given the agent exits and `git status` shows a clean working tree with a new commit since iteration start, when outcome is checked, then `status: "success"` is recorded
- Given the agent exits and `git status` shows uncommitted changes, when outcome is checked, then `status: "failed"` is recorded and changes are discarded
- Given the agent exits and no new commit exists, when outcome is checked, then `status: "failed"` is recorded (agent didn't complete the task)

**Architecture:** Loop Engine post-iteration validation per FR-M2-004
**Dependencies:** S5.3, S5.4

---

## E7: CLI Interface

_Provide user-facing commands for running, monitoring, and initializing agent loops._

**PRD Requirements:** FR-CLI-001, FR-CLI-002, FR-CLI-003

### S7.1: Implement `run` Command

**Size:** M
**As a** founder, **I want** to run `agent-loops run --prd spec.json` and walk away, **so that** my app is built overnight.

**Acceptance Criteria:**
- Given `agent-loops run --prd spec.json --dir ./project --max-iterations 50 --budget 30.0 --model claude-sonnet-4-6`, when invoked, then the loop starts with the specified parameters
- Given `--prd` is missing, when invoked, then usage help is printed and exit code is 1
- Given `--dir` is not provided, when invoked, then the current directory is used as default
- Given `--budget` is not provided, when invoked, then the default of 50.0 USD is used
- Given the loop finishes, when the CLI exits, then a summary is printed: iterations, tasks completed, cost, exit reason

**Architecture:** `cli.py` with Click per ADR-005, Section 5.1
**Dependencies:** S5.3

### S7.2: Implement `status` Command

**Size:** S
**As a** founder, **I want** to check the progress of a running or completed loop, **so that** I can see how things are going without reading raw log files.

**Acceptance Criteria:**
- Given `agent-loops status --dir ./project`, when invoked, then it displays: iterations completed, tasks by status (done/pending/failed/blocked), tokens consumed, estimated cost, elapsed time
- Given no `.agent-loops/` directory exists, when invoked, then it prints "No agent-loops session found in this directory" and exits with code 1
- Given a loop is currently running, when status is invoked from another terminal, then it reads the latest state without interfering

**Architecture:** `cli.py` reads state via `StateManager` per FR-CLI-002
**Dependencies:** S3.2, S3.3, S2.1

### S7.3: Implement `init` Command (from markdown)

**Size:** M
**As a** founder, **I want** to convert my markdown PRD into a `prd.json`, **so that** I don't have to write JSON by hand.

**Acceptance Criteria:**
- Given `agent-loops init --from docs/prd.md`, when invoked, then it parses the markdown for functional requirements and generates a `prd.json` with tasks extracted from FR-XXX entries
- Given the markdown has requirements with acceptance criteria, when parsed, then each FR becomes a task with the acceptance criteria list populated
- Given the generated `prd.json`, when validated by `SpecParser`, then it passes schema validation
- Given `--from` points to a non-existent file, when invoked, then an error is printed and exit code is 1

**Architecture:** `cli.py` + `spec.py` per FR-CLI-003
**Dependencies:** S2.1

### S7.4: Implement `init` Command (interactive)

**Size:** S
**As a** founder, **I want** to create a `prd.json` interactively when I don't have a markdown PRD, **so that** I can quickly define tasks from scratch.

**Acceptance Criteria:**
- Given `agent-loops init`, when invoked without `--from`, then it prompts for: project name, test command, and walks through adding tasks (id, title, description)
- Given the user finishes adding tasks, when confirmed, then a valid `prd.json` is written to the current directory
- Given the user presses Ctrl+C during prompts, when interrupted, then no file is written and exit is clean

**Architecture:** `cli.py` interactive prompts via Click per FR-CLI-003
**Dependencies:** S2.1

---

## E8: Infrastructure Generation

_Generate CI and deployment configuration for completed projects._

**PRD Requirements:** FR-M3-001, FR-M3-002

### S8.1: Generate CI Pipeline on Completion

**Size:** S
**As a** founder, **I want** a GitHub Actions CI config auto-generated when all tasks are done, **so that** the built project has automated tests from day one.

**Acceptance Criteria:**
- Given all `prd.json` tasks are `done`, when the loop's final iteration completes, then the prompt instructs the agent to generate `.github/workflows/ci.yml`
- Given the CI config is generated, when inspected, then it runs the project's `test_command` on push to main
- Given some tasks are still pending or blocked, when the loop exits, then no CI config is generated

**Architecture:** Prompt Builder conditional instruction per FR-M3-001
**Dependencies:** S5.3, S6.1

### S8.2: Generate Deploy Configuration on Completion

**Size:** S
**As a** founder, **I want** a deployment config auto-generated based on `deploy_target`, **so that** I can deploy the built project immediately.

**Acceptance Criteria:**
- Given `deploy_target: "docker"` in `prd.json`, when all tasks are done, then the agent is prompted to generate a `Dockerfile`
- Given `deploy_target: "vercel"` in `prd.json`, when all tasks are done, then the agent is prompted to generate a `vercel.json`
- Given no `deploy_target` field, when all tasks are done, then no deploy config is generated

**Architecture:** Prompt Builder conditional instruction per FR-M3-002
**Dependencies:** S5.3, S6.1

---

## Dependency Map

```
S1.1 ─────────────────────────────────────────────┐
  │                                                │
  ├── S1.2 (models) ──┬── S2.1 (schema) ──────┐   │
  │                    │      │                │   │
  │                    │      ├── S2.2 (task   │   │
  │                    │      │    selection)   │   │
  │                    │      │                │   │
  │                    │      ├── S2.3 (status  │   │
  │                    │      │    updates)     │   │
  │                    │      │    │            │   │
  │                    │      │    └── S2.4     │   │
  │                    │      │      (complete) │   │
  │                    │      │                │   │
  │                    ├── S3.1 (atomic writes)│   │
  │                    │      │                │   │
  │                    │      ├── S3.2 (progress│   │
  │                    │      │    log)         │   │
  │                    │      │                │   │
  │                    │      └── S3.3 (budget  │   │
  │                    │           log)         │   │
  │                    │                       │   │
  │                    ├── S4.1 (budget tracker)│   │
  │                    ├── S4.2 (iter limits)   │   │
  │                    ├── S4.4 (kill switch)   │   │
  │                    └── S4.5 (path guard)    │   │
  │                                            │   │
  └── S1.3 (test infra) ──────────────────────┘   │
                                                    │
  S4.3 (gutter) ◄── S3.2, S2.3                     │
  S4.6 (idempotency) ◄── S3.1                      │
                                                    │
  S5.1 (agent runner) ◄── S4.1, S4.5, S1.2         │
  S5.2 (prompt builder) ◄── S3.2, S2.1             │
  S5.4 (git ops) ◄── S1.2                          │
  S5.5 (backoff) ◄── S5.1                          │
                                                    │
  S5.3 (loop engine) ◄── S5.1, S5.2, S5.4,         │
       S2.2, S3.1, S3.2, S3.3, S4.1-S4.4           │
                                                    │
  S6.1 (test rules) ◄── S5.2                       │
  S6.2 (outcome validation) ◄── S5.3, S5.4         │
                                                    │
  S7.1 (run cmd) ◄── S5.3                          │
  S7.2 (status cmd) ◄── S3.2, S3.3, S2.1           │
  S7.3 (init from md) ◄── S2.1                     │
  S7.4 (init interactive) ◄── S2.1                  │
                                                    │
  S8.1 (CI gen) ◄── S5.3, S6.1                     │
  S8.2 (deploy gen) ◄── S5.3, S6.1                 │
```

### Suggested Implementation Order

**Wave 1 — Foundation (no SDK needed):**
S1.1 → S1.2 → S1.3 → S2.1 → S3.1

**Wave 2 — State & Safety (still no SDK):**
S2.2, S2.3, S2.4, S3.2, S3.3, S4.2, S4.4, S4.5, S4.6 (parallel)

**Wave 3 — Safety Analysis:**
S4.1 (budget tracker), S4.3 (gutter detection)

**Wave 4 — Agent Integration:**
S5.1 (agent runner) → S5.2 (prompt builder) → S5.4 (git ops) → S5.5 (backoff)

**Wave 5 — Loop Assembly:**
S5.3 (loop engine) → S6.1 (test rules) → S6.2 (outcome validation)

**Wave 6 — CLI:**
S7.1 (run) → S7.2 (status), S7.3 (init from md), S7.4 (init interactive)

**Wave 7 — Polish:**
S8.1 (CI), S8.2 (deploy)

---

## Traceability Matrix

| PRD Requirement | Stories | Coverage |
|----------------|---------|----------|
| FR-M2-001: Loop Harness | S5.1, S5.3, S5.4, S5.5 | Full |
| FR-M2-002: Externalized State | S3.1, S3.2, S3.3 | Full |
| FR-M2-003: Prompt Construction | S5.2 | Full |
| FR-M2-004: Test-Driven Build | S6.1, S6.2 | Full |
| FR-M2-005: Spec Format | S2.1, S2.2, S2.3, S2.4 | Full |
| FR-M2-006: Agent SDK Integration | S5.1 | Full |
| FR-SL-001: Budget Enforcement | S4.1 | Full |
| FR-SL-002: Iteration Limits | S4.2 | Full |
| FR-SL-003: Gutter Detection | S4.3 | Full |
| FR-SL-004: Idempotency Guard | S4.6 | Full |
| FR-SL-005: Kill Switch | S4.4 | Full |
| FR-M3-001: CI Pipeline | S8.1 | Full |
| FR-M3-002: Deploy Config | S8.2 | Full |
| FR-CLI-001: Run Command | S7.1 | Full |
| FR-CLI-002: Status Command | S7.2 | Full |
| FR-CLI-003: Init Command | S7.3, S7.4 | Full |

**All 16 PRD requirements are covered.** No orphan stories (every story traces to a requirement or is explicit foundation work in E1).

---

_These epics and stories were generated during the Stories phase. Next step: run `/check-readiness` to validate cross-artifact alignment before implementation._
