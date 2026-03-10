"""CLI interface for agent-loops."""

import click


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
    click.echo(f"Starting agent-loops with {prd} in {project_dir}")
    click.echo(f"  max_iterations={max_iterations}, budget=${budget:.2f}, model={model}")
    # TODO: Wire up LoopEngine in S5.3


@cli.command()
@click.option("--dir", "project_dir", default=".", type=click.Path(exists=True), help="Target project directory")
def status(project_dir: str) -> None:
    """Display current loop state."""
    click.echo(f"Checking status in {project_dir}")
    # TODO: Wire up StateManager reads in S7.2


@cli.command()
@click.option("--from", "from_path", type=click.Path(exists=True), help="Markdown PRD to convert")
def init(from_path: str | None) -> None:
    """Generate a template prd.json."""
    if from_path:
        click.echo(f"Generating prd.json from {from_path}")
    else:
        click.echo("Interactive prd.json creation")
    # TODO: Wire up SpecParser generation in S7.3/S7.4
