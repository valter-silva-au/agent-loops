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

## Status

**Phase: Requirements** -- PRD complete, architecture design next.

## Documentation

| Document | Description |
|----------|-------------|
| [Product Brief](docs/product-brief.md) | Vision, problem statement, target users, key features |
| [PRD](docs/prd.md) | Full product requirements with acceptance criteria |
| [Research](docs/RESEARCH.md) | Background research on autonomous agent loops and SaaS automation |

## Roadmap

- **MVP**: Agent Loop Framework -- core loop harness, safety guardrails, CLI
- **Phase Beta**: Market Intelligence Engine (autonomous ideation)
- **Phase Gamma**: Infrastructure Autopilot (self-healing deployment)
- **Phase Delta**: Revenue Engine (Stripe ACP, autonomous GTM)
- **Phase Omega**: Compliance Engine (PRIS Act automation)

## Tech Stack

- Python (Claude Agent SDK)
- Structured JSONL for state management
- Git for externalized memory

## License

TBD
