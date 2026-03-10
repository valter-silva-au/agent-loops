# Product Requirements Document: Agent Loop Framework

**Date:** 2026-03-11
**Author:** product-owner
**Status:** Draft
**Source:** [Product Brief](product-brief.md) | [Research](RESEARCH.md)

---

## 1. Overview

### 1.1 Purpose

This document defines the requirements for **agent-loops**, a Python framework that autonomously builds, tests, and commits software from a structured product spec (`prd.json`) using continuous AI agent loops. It covers the MVP (Agent Loop Framework) and the long-term roadmap (Full Autonomous SaaS Factory).

### 1.2 Background

Andrej Karpathy's autoresearch project demonstrated that AI agents can run continuous experiment loops -- modifying code, testing results, and iterating -- without human intervention. The "Ralph Wiggum" pattern (named for its naive persistence) externalizes agent memory to the filesystem, spawning fresh agents per iteration to avoid context degradation. This PRD adapts these patterns from ML research to general software engineering, creating a framework that builds entire applications overnight.

See [RESEARCH.md](RESEARCH.md) for the full research analysis covering autonomous ideation, software engineering, infrastructure, commerce, security, and compliance.

### 1.3 Goals

1. **Overnight autonomous builds**: Given a `prd.json` spec, the framework produces a tested, committed codebase within 8-12 hours of unattended operation, completing 80%+ of specified tasks.
2. **Safe unattended operation**: The framework runs autonomously with hard safety guardrails -- token budget caps, iteration limits, gutter detection -- ensuring zero runaway cost events or data loss.
3. **Observable progress**: Every iteration is logged as structured JSONL, providing a clear audit trail of what was attempted, what succeeded, and what the agent learned.
4. **Foundation for expansion**: The architecture supports future modules (market intelligence, infrastructure autopilot, revenue engine, compliance engine) without requiring a rewrite.

### 1.4 Non-Goals (Out of Scope)

- **Autonomous market discovery (M1)**: PRD specs are human-authored for MVP. AI-driven ideation comes in Phase Beta.
- **Multi-agent swarms**: MVP uses a single agent per iteration. Parallel worker agents are deferred.
- **Stripe ACP / autonomous commerce (M4)**: No payment integration. Monetization of generated products is manual.
- **Full compliance engine (M5)**: Framework embeds privacy-by-design principles but does not include automated PRIS Act breach reporting.
- **Model-agnostic support**: MVP targets Claude (Anthropic) only. Multi-model support is future work.
- **GUI / web dashboard**: CLI only for MVP.

---

## 2. System Modules

The research identifies 6 phases mapped to 5 product modules and 1 cross-cutting concern. The MVP implements M2 + Safety Layer + minimal M3.

| Module | Name | Research Phase | MVP? | Description |
|--------|------|---------------|------|-------------|
| **M2** | Autonomous Builder | Phase 2 | Yes | Core loop harness, Agent SDK integration, externalized state, test-driven build |
| **Safety** | Safety Layer | Phase 5 | Yes | Token budgets, iteration caps, gutter detection, idempotency (cross-cutting) |
| **M3** | Infrastructure Autopilot | Phase 3 | Minimal | Single-target deploy, CI pipeline |
| **M1** | Market Intelligence Engine | Phase 1 | No | Autoresearch adaptation for business ideation |
| **M4** | Revenue Engine | Phase 4 | No | Stripe ACP, autonomous GTM |
| **M5** | Compliance Engine | Phase 6 | No | PRIS Act automation, breach reporting |

### Post-MVP Roadmap

- **Phase Beta**: M1 -- Market Intelligence with autoresearch adaptation
- **Phase Gamma**: M3 full -- Self-healing SRE agents, MCP hub
- **Phase Delta**: M4 -- Stripe ACP, autonomous GTM agents
- **Phase Omega**: M5 -- Compliance Engine (must ship before July 2026 PRIS Act deadline)

---

## 3. User Personas

### Persona 1: Founder/Operator (Valter)

| Attribute | Description |
|-----------|-------------|
| Role | Solo technical founder building SaaS products in Perth, WA |
| Goals | Multiply personal output by delegating coding to overnight agent loops; review and deploy results in the morning |
| Pain Points | Limited hours in the day; AI coding tools require constant babysitting; no structured way to run autonomous loops safely |
| Technical Level | Advanced -- comfortable with Python, CLI tools, Claude API, git workflows |

### Persona 2: Agent Actor

| Attribute | Description |
|-----------|-------------|
| Role | The Claude AI agent operating within the loop framework |
| Goals | Receive clear context (spec + state), complete one bounded task per iteration, persist learnings for the next agent |
| Pain Points | Context degradation over long sessions; unclear task boundaries; no memory of previous iterations without externalized state |
| Technical Level | N/A -- operates within the framework's tool permissions and guardrails |

### Persona 3: End User (of generated products)

| Attribute | Description |
|-----------|-------------|
| Role | Users of the SaaS products built by agent-loops. Not direct users of the framework. |
| Goals | Functional, reliable, privacy-compliant software |
| Pain Points | N/A -- indirect persona. Quality is ensured by the framework's test-driven build cycle. |
| Technical Level | Varies |

---

## 4. Functional Requirements

### M2: Autonomous Builder (Core Loop)

#### FR-M2-001: Loop Harness

**Priority:** Must-Have
**Description:** The system shall implement an infinite loop that spawns a fresh Claude Agent SDK session per iteration, feeds it the current project state, waits for completion or failure, and restarts.
**Acceptance Criteria:**
- Given a `prd.json` file and a target project directory, when `agent-loops run` is invoked, then the framework spawns a new Agent SDK session for each iteration
- Given an agent session completes (success or failure), when the session exits, then the framework spawns a fresh session within 5 seconds
- Given the `--max-iterations N` flag is set, when N iterations have completed, then the loop terminates gracefully

#### FR-M2-002: Externalized State Management

**Priority:** Must-Have
**Description:** The system shall maintain all loop state in the filesystem so each fresh agent can resume from where the previous one stopped.
**Acceptance Criteria:**
- Given an agent completes a task, when it exits, then `prd.json` is updated to mark the task as complete
- Given a new agent spawns, when it reads `prd.json`, then it identifies the next incomplete task to work on
- Given an agent makes code changes, when tests pass, then it creates a git commit with a descriptive message
- Given an agent learns something useful, when it exits, then it appends a JSONL entry to `progress.jsonl`

#### FR-M2-003: Iteration Prompt Construction

**Priority:** Must-Have
**Description:** The system shall construct a context-rich prompt for each agent iteration by assembling the PRD spec, recent progress entries, current git status, and iteration-specific instructions.
**Acceptance Criteria:**
- Given a new iteration starts, when the prompt is constructed, then it includes: the current `prd.json` state, the last N entries from `progress.jsonl`, the git diff since last commit, and the framework's behavioral rules
- Given `progress.jsonl` contains prior learnings, when the prompt is constructed, then the agent receives relevant context from previous iterations

#### FR-M2-004: Test-Driven Build Cycle

**Priority:** Must-Have
**Description:** The system shall require each agent to run the project's test suite after making changes. Only passing changes are committed.
**Acceptance Criteria:**
- Given an agent modifies code, when the modification is complete, then the agent runs the configured test command
- Given tests pass, when the agent commits, then the commit message references the task ID and test results
- Given tests fail, when the agent has remaining turns, then it reads stderr and attempts to fix the failure
- Given tests fail after max retries within the iteration, when the iteration ends, then all uncommitted changes are discarded and the failure is logged to `progress.jsonl`

#### FR-M2-005: Spec Format (`prd.json`)

**Priority:** Must-Have
**Description:** The system shall define a structured JSON format for product specs that agents can read and update.
**Acceptance Criteria:**
- Given a `prd.json` file, when parsed, then each task has: `id`, `title`, `description`, `acceptance_criteria`, `status` (pending/in_progress/done/failed), `dependencies` (list of task IDs)
- Given a task has unmet dependencies, when an agent selects the next task, then it skips that task and selects one with all dependencies met
- Given a task is marked `done`, when an agent reads the spec, then it does not reattempt that task

#### FR-M2-006: Agent SDK Integration

**Priority:** Must-Have
**Description:** The system shall use the Claude Agent SDK (Python) to spawn and manage agent sessions with programmatic tool control and hooks.
**Acceptance Criteria:**
- Given an iteration starts, when the Agent SDK is invoked, then it has access to: bash, file read, file write, file edit tools
- Given a `PreToolUse` hook is registered, when the agent attempts a tool call, then the hook can inspect and block the call (used for budget enforcement)
- Given a `PostToolUse` hook is registered, when a tool call completes, then the hook can log the result (used for progress tracking)

### Safety Layer (Cross-Cutting)

#### FR-SL-001: Token Budget Enforcement

**Priority:** Must-Have
**Description:** The system shall track cumulative token usage (input + output) across all iterations and enforce hard spending caps.
**Acceptance Criteria:**
- Given a `--budget N` flag (in tokens or USD), when cumulative usage reaches 80% of N, then the system logs a warning
- Given cumulative usage reaches 100% of N, when the threshold is hit, then the system terminates the loop immediately and logs the final state
- Given each iteration completes, when tokens are tallied, then the running total is persisted to a `budget.jsonl` file

#### FR-SL-002: Iteration Limits

**Priority:** Must-Have
**Description:** The system shall enforce a maximum number of loop iterations to prevent infinite runs.
**Acceptance Criteria:**
- Given `--max-iterations N` is set, when N iterations have executed, then the loop terminates gracefully
- Given no `--max-iterations` flag is provided, when the framework starts, then it defaults to 100 iterations

#### FR-SL-003: Gutter Detection

**Priority:** Must-Have
**Description:** The system shall detect when an agent is thrashing -- repeating the same failed action across consecutive iterations -- and intervene.
**Acceptance Criteria:**
- Given the last 3 iterations in `progress.jsonl` all failed on the same task with similar error signatures, when a new iteration starts, then the framework skips that task (marks it `blocked`) and moves to the next
- Given a task is marked `blocked`, when logged, then the block reason and error history are recorded in `progress.jsonl`

#### FR-SL-004: Idempotency Guard

**Priority:** Should-Have
**Description:** The system shall prevent duplicate side-effects when an agent retries an action it already completed.
**Acceptance Criteria:**
- Given an agent attempts to commit changes identical to the previous commit, when the commit is attempted, then the framework blocks it and logs a duplicate detection
- Given an agent attempts to overwrite a file with identical content, when the write is attempted, then the framework skips the write

#### FR-SL-005: Kill Switch

**Priority:** Must-Have
**Description:** The system shall provide an immediate termination mechanism that halts the loop, kills any running agent process, and preserves current state.
**Acceptance Criteria:**
- Given the user sends SIGINT (Ctrl+C), when received, then the framework waits for the current tool call to complete (up to 30s timeout), saves state, and exits cleanly
- Given a `kill` file is created in the project root, when the framework detects it at iteration boundaries, then it terminates gracefully

### M3: Infrastructure (Minimal MVP)

#### FR-M3-001: CI Pipeline Generation

**Priority:** Should-Have
**Description:** The system shall generate a basic CI configuration (GitHub Actions) for the built project.
**Acceptance Criteria:**
- Given all `prd.json` tasks are marked `done`, when the build is complete, then the framework generates a `.github/workflows/ci.yml` that runs the project's test suite
- Given the CI config is generated, when pushed to GitHub, then it runs tests on every push

#### FR-M3-002: Deploy Configuration

**Priority:** Nice-to-Have
**Description:** The system shall generate deployment configuration for a single target platform.
**Acceptance Criteria:**
- Given a `deploy_target` field in `prd.json` (e.g., "vercel", "docker"), when the build is complete, then the framework generates the appropriate deployment config (vercel.json or Dockerfile)

### CLI Interface

#### FR-CLI-001: Run Command

**Priority:** Must-Have
**Description:** The system shall provide a `run` CLI command that starts the autonomous build loop.
**Acceptance Criteria:**
- Given `agent-loops run --prd spec.json --dir ./project --max-iterations 50 --budget 100000`, when invoked, then the framework starts the loop with the specified parameters
- Given required flags are missing, when invoked, then the CLI prints usage help and exits with code 1

#### FR-CLI-002: Status Command

**Priority:** Should-Have
**Description:** The system shall provide a `status` command to inspect the current state of a running or completed loop.
**Acceptance Criteria:**
- Given `agent-loops status --dir ./project`, when invoked, then it displays: iterations completed, tasks done/pending/blocked, tokens consumed, estimated cost, elapsed time

#### FR-CLI-003: Init Command

**Priority:** Should-Have
**Description:** The system shall provide an `init` command to create a template `prd.json` from a markdown PRD or interactively.
**Acceptance Criteria:**
- Given `agent-loops init --from prd.md`, when invoked, then it parses the markdown and generates a `prd.json` with tasks extracted from functional requirements
- Given `agent-loops init`, when invoked without arguments, then it prompts interactively for project name, tasks, and test command

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric | Requirement |
|--------|-------------|
| Loop restart latency | < 5 seconds between iterations (agent exit to new agent prompt sent) |
| Prompt construction time | < 2 seconds to assemble context from state files |
| Overnight throughput | Process 50-100 iterations in 8-12 hours (depends on task complexity) |

### 5.2 Security

- The framework shall not persist API keys in state files (`progress.jsonl`, `prd.json`). Keys are read from environment variables only.
- Agent tool permissions shall be scoped: file operations restricted to the target project directory, no network access unless explicitly enabled in config.
- Generated code shall be scanned by the agent for common vulnerabilities (OWASP top 10) as part of the test-driven cycle.

### 5.3 Reliability

| Metric | Requirement |
|--------|-------------|
| Crash recovery | On unexpected termination, the next `agent-loops run` shall resume from the last committed state |
| State integrity | `prd.json` and `progress.jsonl` shall always be valid JSON/JSONL; writes use atomic file replacement |
| Git safety | No force-pushes; no rebase of existing commits; clean working tree required at loop start |

### 5.4 Scalability

- MVP targets single-agent, single-project loops. The architecture (Agent SDK, JSONL state) shall not preclude future multi-agent parallel execution.
- State files use append-only JSONL to support concurrent readers without locking.

### 5.5 Compatibility

- Python 3.11+
- Claude Agent SDK (latest)
- Git 2.30+
- Linux and macOS (Windows via WSL)

---

## 6. User Stories Overview

| ID | As a... | I want to... | So that... | Priority |
|----|---------|-------------|------------|----------|
| US-001 | Founder | run `agent-loops run --prd spec.json` and walk away | my app is built overnight without me babysitting | Must-Have |
| US-002 | Founder | set a token budget cap | I don't wake up to a $500 API bill | Must-Have |
| US-003 | Founder | review `progress.jsonl` in the morning | I can see exactly what the agent did, what worked, and what failed | Must-Have |
| US-004 | Founder | hit Ctrl+C at any point | the loop stops cleanly without corrupting state | Must-Have |
| US-005 | Founder | run `agent-loops status` | I can check progress without reading raw log files | Should-Have |
| US-006 | Founder | run `agent-loops init --from prd.md` | I can convert my markdown PRD into a machine-readable spec | Should-Have |
| US-007 | Agent Actor | read `prd.json` at the start of my session | I know exactly which task to work on next | Must-Have |
| US-008 | Agent Actor | read recent `progress.jsonl` entries | I learn from previous iterations' successes and failures | Must-Have |
| US-009 | Agent Actor | write to `progress.jsonl` before exiting | the next agent knows what I attempted and learned | Must-Have |

---

## 7. Success Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|--------------------|
| Overnight task completion rate | 0% (no framework) | 80%+ of prd.json tasks marked `done` | Count done/total tasks after overnight run |
| API cost per overnight run | Unbounded | < $50 USD for a small SaaS (~20 tasks) | Sum token costs from `budget.jsonl` |
| Agent iteration success rate | Unknown | > 60% of iterations produce a passing commit | Ratio of `success` to total entries in `progress.jsonl` |
| Unattended runtime | Minutes | 8-12 hours continuous | Wall clock from first to last `progress.jsonl` entry |
| Safety incidents | N/A | 0 runaway costs, 0 data loss, 0 corrupted state | Budget cap triggers + git integrity checks |
| Loop restart latency | N/A | < 5 seconds | Timestamp delta between consecutive iterations in `progress.jsonl` |

---

## 8. Dependencies

| Dependency | Type | Status | Impact if Unavailable |
|------------|------|--------|-----------------------|
| Claude Agent SDK (Python) | External | Available | Cannot run agent loops; would fall back to CLI subprocess |
| Anthropic API | External | Available | Framework cannot operate; requires API access |
| Git | External | Available | Cannot externalize state; core functionality blocked |
| Python 3.11+ | External | Available | Cannot run framework |

---

## 9. Assumptions

- The Anthropic API remains available with current rate limits and pricing throughout development and operation.
- Claude Agent SDK Python provides `PreToolUse` and `PostToolUse` hooks for intercepting tool calls (as documented in SDK).
- A well-structured `prd.json` with ~20 tasks can produce a working small SaaS app (API backend + basic frontend).
- The agent (Claude Sonnet 4.6 or Opus 4.6) is capable of implementing typical SaaS features (CRUD APIs, auth, database models) within a single iteration when given clear task descriptions.
- Git commit history provides sufficient "memory" for fresh agent sessions to understand project state.

---

## 10. Key Architectural Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| AD-1 | Claude Agent SDK (not CLI subprocess) | Programmatic control via hooks enables budget enforcement, progress logging, and tool scoping at the framework level. |
| AD-2 | Structured JSONL for progress (not freeform markdown) | Machine-parseable for gutter detection, metrics, and automated analysis. Agents can still read recent entries as context. |
| AD-3 | Single-agent per iteration for MVP | Multi-agent swarms add exponential complexity for debugging and constraint enforcement. Defer to post-MVP. |
| AD-4 | Safety Layer as cross-cutting concern (not separate phase) | Guardrails must exist before any autonomous loop runs. Cannot bolt on safety after the fact. |
| AD-5 | Each generated product gets its own repo | agent-loops is the "factory", not the product. Isolation ensures clean ownership, independent scaling, and no cross-contamination. |
| AD-6 | Privacy-by-design from MVP | PRIS Act takes effect July 2026. Framework must not persist PII in state files; generated code must follow data minimization patterns. |

---

## 11. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Runaway API costs | High | High | FR-SL-001: Hard token budget with process kill at 100% |
| Agent thrashing on same failure | High | Medium | FR-SL-003: Gutter detection skips blocked tasks after 3 consecutive failures |
| Context degradation over long sessions | Medium | High | Core design: fresh agent per iteration, externalized state |
| Generated code has security vulnerabilities | Medium | High | FR-M2-004: Test-driven cycle includes security linting |
| Claude API rate limits or outages | Medium | Low | Exponential backoff with jitter; graceful pause/resume |
| `prd.json` format insufficient for complex projects | Medium | Medium | Start simple; extend schema as real usage reveals gaps |
| PRIS Act non-compliance in generated products | Low | High | AD-6: Privacy-by-design embedded from MVP; full M5 ships before July 2026 |

---

## 12. Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | What is the optimal task granularity in `prd.json`? (Too coarse = agent can't finish; too fine = overhead) | Valter | Open |
| 2 | How should the framework handle dirty git state or merge conflicts at startup? | Valter | Open |
| 3 | Should the framework support resuming a partially-completed loop from a specific iteration? | Valter | Open |
| 4 | What Claude model should be the default? Sonnet 4.6 (faster, cheaper) vs Opus 4.6 (more capable)? | Valter | Open |
| 5 | Should `prd.json` support task-level model selection (e.g., use Opus for complex tasks, Sonnet for simple)? | Valter | Open |

---

## Traceability: Brief -> PRD Coverage

| Brief Feature | PRD Requirements |
|--------------|------------------|
| Ralph Wiggum Loop Harness | FR-M2-001, FR-M2-002, FR-M2-003 |
| Safety Guardrails ("Durable Box") | FR-SL-001, FR-SL-002, FR-SL-003, FR-SL-004, FR-SL-005 |
| Structured Spec Input (`prd.json`) | FR-M2-005 |
| Observable Progress | FR-M2-002 (JSONL logging), FR-CLI-002 (status command) |
| CLI Interface | FR-CLI-001, FR-CLI-002, FR-CLI-003 |
| Test-Driven Build Cycle | FR-M2-004 |
| Agent SDK Integration | FR-M2-006 |
| CI Pipeline (constraint: minimal M3) | FR-M3-001 |
| Deploy Config (constraint: minimal M3) | FR-M3-002 |

All 5 brief features and 2 constraints map to at least one functional requirement. No orphan requirements.

---

_This PRD was generated during the Requirements phase. Next step: run `/create-architecture` to design the technical architecture._
