#!/usr/bin/env python3
"""CLI entry point for the AI Autonomous Systems platform.

Usage:
    python main.py --help
    python main.py status
    python main.py repos list
    python main.py repos summary
    python main.py quality check
    python main.py content generate --repo Web3AI --type blog_post
    python main.py ads create --repo Chatlippytm.ai.Bots --channel twitter
    python main.py research report
    python main.py bots list
    python main.py bots chat --bot-id allbots-main --message "Hello"
    python main.py web3 networks
    python main.py serve
"""

from __future__ import annotations

import json
import sys

import click

from src.orchestrator import Orchestrator, OrchestratorConfig


def _get_orchestrator() -> Orchestrator:
    return Orchestrator(OrchestratorConfig())


def _print_json(data: object) -> None:
    click.echo(json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option("1.0.0", prog_name="lippytm-ai")
def cli() -> None:
    """lippytm.ai – AI Autonomous Systems integration platform.

    Manages all lippytm GitHub repositories with full-stack AI agents for
    content generation, advertising, research, bot management, and Web3.
    """


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@cli.command()
def status() -> None:
    """Show orchestrator status."""
    orch = _get_orchestrator()
    s = orch.get_status()
    click.echo(click.style("\n🤖 lippytm.ai – AI Autonomous Systems", fg="cyan", bold=True))
    click.echo(f"  Status        : {click.style('running', fg='green')}")
    click.echo(f"  Total repos   : {s.total_repos}")
    click.echo(f"  Active agents : {', '.join(s.agents_active)}")
    click.echo(f"  Last sync     : {s.last_sync}")
    click.echo(f"  Health score  : {s.portfolio_health_score:.2f}")
    click.echo(f"  Generated at  : {s.generated_at}\n")


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

@cli.group()
def repos() -> None:
    """Repository management commands."""


@repos.command("list")
def repos_list() -> None:
    """List all lippytm repositories."""
    orch = _get_orchestrator()
    click.echo(click.style("Fetching repositories…", fg="yellow"))
    data = orch.sync_repositories()
    click.echo(click.style(f"\n📦 {len(data)} Repositories\n", fg="cyan", bold=True))
    for repo in data:
        lang = f"[{repo['language']}]" if repo.get("language") else ""
        issues = repo.get("open_issues", 0)
        click.echo(
            f"  {click.style(repo['name'], bold=True)} {lang} "
            f"⭐{repo.get('stars', 0)}  "
            f"{'🔴' if issues > 10 else '🟡' if issues > 5 else '🟢'}{issues} issues"
        )
    click.echo()


@repos.command("summary")
def repos_summary() -> None:
    """Show high-level portfolio summary."""
    orch = _get_orchestrator()
    click.echo(click.style("Generating portfolio summary…", fg="yellow"))
    _print_json(orch.get_portfolio_summary())


@repos.command("integrations")
def repos_integrations() -> None:
    """Show integration opportunities across repositories."""
    orch = _get_orchestrator()
    click.echo(click.style("Analysing integration opportunities…", fg="yellow"))
    opps = orch.get_integration_opportunities()
    click.echo(click.style(f"\n🔗 {len(opps)} Integration Opportunities\n", fg="cyan", bold=True))
    for opp in opps:
        click.echo(f"  [{opp['priority'].upper()}] {opp['type']}: {opp['description']}")
    click.echo()


# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------

@cli.group()
def quality() -> None:
    """Quality assurance commands."""


@quality.command("check")
def quality_check() -> None:
    """Run QA health check across all repositories."""
    orch = _get_orchestrator()
    click.echo(click.style("Running health check…", fg="yellow"))
    report = orch.run_health_check()
    score = report["overall_score"]
    color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
    click.echo(click.style(f"\n🏥 Portfolio Health Score: {score:.2f}", fg=color, bold=True))
    click.echo(f"  Healthy : {report['healthy']}")
    click.echo(f"  Warning : {report['warning']}")
    click.echo(f"  Critical: {report['critical']}")
    click.echo(click.style("\n📋 Global Recommendations:", bold=True))
    for rec in report["global_recommendations"]:
        click.echo(f"  • {rec}")
    click.echo()


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

@cli.group()
def content() -> None:
    """Content generation commands."""


@content.command("generate")
@click.option("--repo", required=True, help="Repository name")
@click.option(
    "--type",
    "content_type",
    default="blog_post",
    type=click.Choice(["blog_post", "readme", "release_notes", "social_media", "tutorial"]),
    help="Type of content to generate",
)
@click.option("--topic", default="", help="Content topic")
def content_generate(repo: str, content_type: str, topic: str) -> None:
    """Generate AI content for a repository."""
    orch = _get_orchestrator()
    click.echo(click.style(f"Generating {content_type} for {repo}…", fg="yellow"))
    result = orch.generate_content(repo, content_type, topic)
    click.echo(click.style(f"\n📝 {result['title']}\n", fg="cyan", bold=True))
    click.echo(result["body"])
    click.echo(click.style(f"\nTags: {', '.join(result['tags'])}", fg="blue"))
    click.echo(click.style(f"Words: {result['word_count']}  Model: {result['model']}", fg="blue"))
    click.echo()


@content.command("digest")
def content_digest() -> None:
    """Generate a weekly portfolio digest."""
    orch = _get_orchestrator()
    click.echo(click.style("Generating portfolio digest…", fg="yellow"))
    result = orch.generate_portfolio_digest()
    click.echo(click.style(f"\n📰 {result['title']}\n", fg="cyan", bold=True))
    click.echo(result["body"])
    click.echo()


# ---------------------------------------------------------------------------
# Advertising
# ---------------------------------------------------------------------------

@cli.group()
def ads() -> None:
    """Advertising management commands."""


@ads.command("create")
@click.option("--repo", required=True, help="Repository name")
@click.option(
    "--channel",
    default="twitter",
    type=click.Choice(["twitter", "linkedin", "discord", "github_sponsors", "web3_defi", "newsletter"]),
)
@click.option("--audience", default="developers", help="Target audience")
@click.option("--budget", default=100.0, type=float, help="Budget in USD")
def ads_create(repo: str, channel: str, audience: str, budget: float) -> None:
    """Create an AI-generated ad campaign."""
    orch = _get_orchestrator()
    click.echo(click.style(f"Creating {channel} campaign for {repo}…", fg="yellow"))
    result = orch.create_ad_campaign(repo, channel, audience, budget)
    click.echo(click.style(f"\n📣 Campaign: {result['campaign_id']}", fg="cyan", bold=True))
    click.echo(f"  Headline : {result['headline']}")
    click.echo(f"  Body     : {result['body']}")
    click.echo(f"  CTA      : {result['cta']}")
    click.echo(f"  Status   : {result['status']}")
    click.echo()


@ads.command("report")
def ads_report() -> None:
    """Show advertising portfolio report."""
    orch = _get_orchestrator()
    _print_json(orch.get_ad_report())


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

@cli.group()
def research() -> None:
    """Research and analysis commands."""


@research.command("report")
@click.option("--focus", default="", help="Optional focus area")
def research_report(focus: str) -> None:
    """Run AI research analysis on the portfolio."""
    orch = _get_orchestrator()
    click.echo(click.style("Running research analysis…", fg="yellow"))
    result = orch.run_research(focus_area=focus or None)
    click.echo(click.style(f"\n🔬 {result['title']}\n", fg="cyan", bold=True))
    click.echo(result["summary"])
    click.echo(click.style("\nKey Findings:", bold=True))
    for finding in result["findings"]:
        click.echo(f"  • {finding}")
    click.echo(click.style("\nRecommendations:", bold=True))
    for rec in result["recommendations"]:
        click.echo(f"  → {rec}")
    click.echo()


@research.command("trends")
def research_trends() -> None:
    """Show technology trend analysis."""
    orch = _get_orchestrator()
    _print_json(orch.research_agent.generate_technology_trend_report())


# ---------------------------------------------------------------------------
# Bots
# ---------------------------------------------------------------------------

@cli.group()
def bots() -> None:
    """Bot management commands."""


@bots.command("list")
def bots_list() -> None:
    """List all managed bots."""
    orch = _get_orchestrator()
    fleet = orch.get_bot_fleet_status()
    click.echo(click.style(f"\n🤖 {fleet['total_bots']} Bots in Fleet\n", fg="cyan", bold=True))
    for bot in fleet["bots"]:
        status_icon = {"active": "🟢", "idle": "🟡", "error": "🔴", "stopped": "⚫"}.get(bot["status"], "⚪")
        click.echo(
            f"  {status_icon} {click.style(bot['name'], bold=True)} "
            f"[{bot['platform']}]  📦 {bot['repo']}  "
            f"💬 {bot['messages']} msgs"
        )
    click.echo()


@bots.command("chat")
@click.option("--bot-id", required=True, help="Bot identifier")
@click.option("--message", required=True, help="Message to send")
def bots_chat(bot_id: str, message: str) -> None:
    """Send a message to a bot."""
    orch = _get_orchestrator()
    try:
        result = orch.send_bot_message(bot_id, message)
        click.echo(click.style(f"\n💬 {result['bot_id']} says:", fg="cyan", bold=True))
        click.echo(f"  {result['response']}\n")
    except ValueError as exc:
        click.echo(click.style(f"Error: {exc}", fg="red"), err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Web3
# ---------------------------------------------------------------------------

@cli.group()
def web3() -> None:
    """Web3 and blockchain commands."""


@web3.command("networks")
def web3_networks() -> None:
    """Show supported blockchain networks."""
    orch = _get_orchestrator()
    _print_json(orch.get_web3_summary())


@web3.command("defi")
@click.option("--protocol", required=True, help="Protocol name")
@click.option("--tvl", default=1_000_000.0, type=float, help="Total value locked (USD)")
@click.option("--apy", default=5.0, type=float, help="Annual percentage yield (%)")
@click.option(
    "--risk",
    default="medium",
    type=click.Choice(["low", "medium", "high"]),
    help="Risk level",
)
def web3_defi(protocol: str, tvl: float, apy: float, risk: str) -> None:
    """Run AI-powered DeFi analysis."""
    orch = _get_orchestrator()
    click.echo(click.style(f"Analysing {protocol}…", fg="yellow"))
    result = orch.analyse_defi(protocol, tvl, apy, risk)
    click.echo(click.style(f"\n🔗 {result['protocol']} Analysis\n", fg="cyan", bold=True))
    click.echo(result["summary"])
    click.echo(click.style("\nRecommendations:", bold=True))
    for rec in result["recommendations"]:
        click.echo(f"  → {rec}")
    click.echo()


# ---------------------------------------------------------------------------
# Serve
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind")
@click.option("--port", default=8000, type=int, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable hot reload (development)")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the FastAPI web server."""
    try:
        import uvicorn  # type: ignore[import]
        click.echo(
            click.style(
                f"\n🚀 Starting lippytm.ai server on http://{host}:{port}\n",
                fg="green",
                bold=True,
            )
        )
        uvicorn.run("src.web.app:app", host=host, port=port, reload=reload)
    except ImportError:
        click.echo(click.style("uvicorn not installed. Run: pip install uvicorn", fg="red"), err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
