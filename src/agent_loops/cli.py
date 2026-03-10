"""CLI interface for agent-loops."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click

from .engine import LoopEngine
from .models import LoopConfig
from .spec import SpecParser, SpecValidationError
from .state import StateManager


@click.group()
@click.version_option(package_name="agent-loops")
def cli() -> None:
    """Autonomous software building via AI agent loops."""


@cli.command()
@click.option("--prd", required=True, type=click.Path(exists=True), help="Path to prd.json spec file")
@click.option("--dir", "project_dir", default=".", type=click.Path(exists=True), help="Target project directory")
@click.option("--max-iterations", default=100, type=int, help="Maximum loop iterations")
@click.option("--budget", default=50.0, type=float, help="Budget cap in USD")
@click.option("--model", default="claude-sonnet-4-6", help="Claude model to use")
def run(prd: str, project_dir: str, max_iterations: int, budget: float, model: str) -> None:
    """Start the autonomous build loop."""
    config = LoopConfig(
        prd_path=Path(prd),
        project_dir=Path(project_dir),
        max_iterations=max_iterations,
        budget_usd=budget,
        model=model,
    )

    click.echo(f"Starting agent-loops: {config.prd_path}")
    click.echo(f"  project: {config.project_dir}")
    click.echo(f"  max_iterations: {config.max_iterations}")
    click.echo(f"  budget: ${config.budget_usd:.2f}")
    click.echo(f"  model: {config.model}")

    engine = LoopEngine(config)

    try:
        result = asyncio.run(engine.run())
    except RuntimeError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"\n{'='*50}")
    click.echo(f"Loop finished: {result.exit_reason}")
    click.echo(f"  Iterations: {result.iterations_completed}")
    click.echo(f"  Tasks done: {result.tasks_done}")
    click.echo(f"  Tasks pending: {result.tasks_pending}")
    click.echo(f"  Tasks failed: {result.tasks_failed}")
    click.echo(f"  Tasks blocked: {result.tasks_blocked}")
    click.echo(f"  Total cost: ${result.total_cost_usd:.2f}")


@cli.command()
@click.option("--dir", "project_dir", default=".", type=click.Path(exists=True), help="Target project directory")
def status(project_dir: str) -> None:
    """Display current loop state."""
    project = Path(project_dir)
    state_dir = project / ".agent-loops"
    if not state_dir.exists():
        click.echo("No agent-loops session found in this directory.", err=True)
        sys.exit(1)

    state = StateManager(project)

    # Read spec
    try:
        spec_data = state.read_spec()
        spec = SpecParser(spec_data)
        summary = spec.summary()
    except (FileNotFoundError, SpecValidationError):
        summary = {}

    # Read progress
    progress = state.read_progress(last_n=0)
    total_iterations = len(progress)

    # Read budget
    cost = state.get_cumulative_cost()

    # Calculate elapsed time
    elapsed = ""
    if progress:
        first_ts = progress[0].get("timestamp", "")
        last_ts = progress[-1].get("timestamp", "")
        if first_ts and last_ts:
            elapsed = f"{first_ts} → {last_ts}"

    click.echo(f"Agent-loops status for {project_dir}")
    click.echo(f"  Iterations completed: {total_iterations}")
    for status_name, count in sorted(summary.items()):
        click.echo(f"  Tasks {status_name}: {count}")
    click.echo(f"  Total cost: ${cost:.2f}")
    if elapsed:
        click.echo(f"  Time range: {elapsed}")


@cli.command()
@click.option("--from", "from_path", type=click.Path(exists=True), help="Markdown PRD to convert")
def init(from_path: str | None) -> None:
    """Generate a template prd.json."""
    if from_path:
        click.echo(f"Generating prd.json from {from_path}")
        # TODO: Parse markdown into tasks (S7.3)
        click.echo("Markdown parsing not yet implemented. Use interactive mode instead.")
    else:
        name = click.prompt("Project name")
        test_command = click.prompt("Test command", default="pytest")

        tasks = []
        click.echo("Add tasks (empty ID to finish):")
        while True:
            task_id = click.prompt("  Task ID", default="", show_default=False)
            if not task_id:
                break
            title = click.prompt("  Title")
            description = click.prompt("  Description")
            tasks.append({
                "id": task_id,
                "title": title,
                "description": description,
                "acceptance_criteria": [],
                "status": "pending",
                "dependencies": [],
            })

        if not tasks:
            click.echo("No tasks added. Aborting.", err=True)
            sys.exit(1)

        spec = {
            "name": name,
            "test_command": test_command,
            "tasks": tasks,
        }

        output = Path("prd.json")
        output.write_text(json.dumps(spec, indent=2) + "\n")
        click.echo(f"Created {output}")
