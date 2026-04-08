"""
CLI entry point for AI Autonomous Systems.

Usage examples::

    python main.py run
    python main.py run --repo lippytm/my-repo
    python main.py run --continuous
"""
from __future__ import annotations

import sys

import click

from src.core.config import Config
from src.core.logger import get_logger
from src.core.orchestrator import Orchestrator


logger = get_logger(__name__)


@click.group()
def cli() -> None:
    """AI Autonomous Systems — automated improvements across all repositories."""


@cli.command()
@click.option(
    "--repo",
    "repositories",
    multiple=True,
    help="Repository to process (owner/repo). Repeatable. Overrides config.",
)
@click.option(
    "--continuous",
    is_flag=True,
    default=False,
    help="Run continuously on the configured interval.",
)
@click.option(
    "--config",
    "config_path",
    default=None,
    help="Path to config.yml (default: config.yml in repo root).",
)
def run(
    repositories: tuple,
    continuous: bool,
    config_path: str | None,
) -> None:
    """Run all autonomous agents against configured repositories."""
    config = Config(config_path)

    if not config.github_token:
        click.echo(
            "Error: GITHUB_TOKEN environment variable is not set.", err=True
        )
        sys.exit(1)

    try:
        orchestrator = Orchestrator(config)
    except Exception as exc:
        click.echo(f"Failed to initialise orchestrator: {exc}", err=True)
        sys.exit(1)

    repo_list = list(repositories) or None

    if continuous:
        orchestrator.run_continuously(repo_list)
    else:
        report = orchestrator.run(repo_list)
        click.echo(
            f"\nRun complete. "
            f"Findings: {report.get('total_findings', 0)}, "
            f"Actions: {report.get('total_actions', 0)}, "
            f"Errors: {report.get('total_errors', 0)}"
        )
        if report.get("total_errors", 0) > 0:
            sys.exit(1)


if __name__ == "__main__":
    cli()
