"""Main Orchestrator for the AI Autonomous Systems platform.

Coordinates all agents (content, ads, research, bots, web3) and the
GitHub repository integration layer.  Supports both one-shot execution
and scheduled continuous operation.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.autonomous.ad_manager import AdChannel, AdManagerAgent
from src.autonomous.bot_manager import BotManagerAgent
from src.autonomous.content_generator import ContentGeneratorAgent
from src.autonomous.research_agent import ResearchAgent
from src.autonomous.web3_agent import Web3Agent
from src.integration.repo_manager import GitHubRepoManager
from src.quality.qa_monitor import QAMonitor

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    """Runtime configuration for the orchestrator."""

    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    ai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    ai_provider: str = field(default_factory=lambda: os.getenv("AI_PROVIDER", "openai"))
    ai_model: str = field(default_factory=lambda: os.getenv("AI_MODEL", "gpt-4o"))
    web3_rpc_url: str = field(default_factory=lambda: os.getenv("WEB3_RPC_URL", ""))
    max_concurrent_agents: int = 5
    sync_interval_minutes: int = 60


@dataclass
class OrchestratorStatus:
    """Runtime status snapshot of the orchestrator."""

    running: bool
    total_repos: int
    agents_active: list[str]
    last_sync: str
    last_health_check: str
    portfolio_health_score: float
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat() + "Z")


class Orchestrator:
    """Central AI orchestrator that manages all lippytm repository integrations.

    Responsibilities:
    - Maintain a live snapshot of all repositories
    - Coordinate AI agents for content, ads, research, bots, and Web3
    - Run quality-assurance checks and surface actionable insights
    - Provide a unified API for the CLI and web interface
    """

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        self.config = config or OrchestratorConfig()

        # Initialise all sub-systems
        self.repo_manager = GitHubRepoManager(token=self.config.github_token)
        self.content_agent = ContentGeneratorAgent(
            api_key=self.config.ai_api_key,
            provider=self.config.ai_provider,
            model=self.config.ai_model,
        )
        self.ad_agent = AdManagerAgent(
            api_key=self.config.ai_api_key,
            provider=self.config.ai_provider,
            model=self.config.ai_model,
        )
        self.research_agent = ResearchAgent(
            api_key=self.config.ai_api_key,
            provider=self.config.ai_provider,
            model=self.config.ai_model,
        )
        self.bot_agent = BotManagerAgent(
            api_key=self.config.ai_api_key,
            provider=self.config.ai_provider,
            model=self.config.ai_model,
        )
        self.web3_agent = Web3Agent(
            api_key=self.config.ai_api_key,
            provider=self.config.ai_provider,
            model=self.config.ai_model,
            web3_rpc_url=self.config.web3_rpc_url,
        )
        self.qa_monitor = QAMonitor()

        # Cached state
        self._repo_cache: list[dict[str, Any]] = []
        self._last_sync: str = ""
        self._last_health_check: str = ""
        self._portfolio_score: float = 0.0

    # ------------------------------------------------------------------
    # Repository synchronisation
    # ------------------------------------------------------------------

    def sync_repositories(self) -> list[dict[str, Any]]:
        """Fetch metadata for all repositories and refresh the local cache."""
        logger.info("Syncing all lippytm repositories…")
        try:
            repos = self.repo_manager.list_all_repos()
            self._repo_cache = [
                {
                    "name": r.name,
                    "full_name": r.full_name,
                    "description": r.description,
                    "language": r.language,
                    "url": r.html_url,
                    "stars": r.stars,
                    "open_issues": r.open_issues,
                    "last_updated": r.last_updated,
                }
                for r in repos
            ]
            self._last_sync = datetime.now(timezone.utc).isoformat() + "Z"
            logger.info("Synced %d repositories", len(self._repo_cache))
        except Exception as exc:
            logger.error("Repository sync failed: %s", exc)
        return self._repo_cache

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Return a high-level portfolio summary, using cache if available."""
        if not self._repo_cache:
            self.sync_repositories()
        return self.repo_manager.get_portfolio_summary()

    # ------------------------------------------------------------------
    # Quality assurance
    # ------------------------------------------------------------------

    def run_health_check(self) -> dict[str, Any]:
        """Run a QA health check across all repositories."""
        if not self._repo_cache:
            self.sync_repositories()

        report = self.qa_monitor.analyse_portfolio(self._repo_cache)
        self._portfolio_score = report.overall_score
        self._last_health_check = datetime.now(timezone.utc).isoformat() + "Z"

        return {
            "overall_score": report.overall_score,
            "total_repos": report.total_repos,
            "healthy": report.healthy_repos,
            "warning": report.warning_repos,
            "critical": report.critical_repos,
            "global_recommendations": report.global_recommendations,
            "repo_scores": [
                {
                    "name": s.repo_name,
                    "score": s.overall_score,
                    "issues": s.issues,
                    "recommendations": s.recommendations,
                }
                for s in report.repo_scores
            ],
            "generated_at": report.generated_at,
        }

    # ------------------------------------------------------------------
    # Content generation
    # ------------------------------------------------------------------

    def generate_content(
        self,
        repo_name: str,
        content_type: str = "blog_post",
        topic: str = "",
    ) -> dict[str, Any]:
        """Generate AI content for a repository."""
        result = self.content_agent.generate_for_repo(
            repo_name=repo_name,
            content_type=content_type,
            topic=topic or f"the latest developments in {repo_name}",
        )
        return {
            "repo": result.repo_name,
            "type": result.content_type,
            "title": result.title,
            "body": result.body,
            "tags": result.tags,
            "word_count": result.word_count,
            "model": result.model_used,
        }

    def generate_portfolio_digest(self) -> dict[str, Any]:
        """Generate a weekly digest covering all repositories."""
        if not self._repo_cache:
            self.sync_repositories()
        names = [r["name"] for r in self._repo_cache]
        result = self.content_agent.generate_portfolio_digest(names)
        return {
            "title": result.title,
            "body": result.body,
            "tags": result.tags,
            "word_count": result.word_count,
            "model": result.model_used,
        }

    # ------------------------------------------------------------------
    # Advertising
    # ------------------------------------------------------------------

    def create_ad_campaign(
        self,
        repo_name: str,
        channel: str = "twitter",
        target_audience: str = "developers",
        budget_usd: float = 100.0,
    ) -> dict[str, Any]:
        """Create an AI-generated ad campaign for a repository."""
        ch = AdChannel(channel)
        campaign = self.ad_agent.create_campaign(repo_name, ch, target_audience, budget_usd)
        return {
            "campaign_id": campaign.campaign_id,
            "repo": campaign.repo_name,
            "channel": campaign.channel.value,
            "headline": campaign.headline,
            "body": campaign.body_copy,
            "cta": campaign.call_to_action,
            "status": campaign.status.value,
        }

    def get_ad_report(self) -> dict[str, Any]:
        """Return the advertising portfolio report."""
        return self.ad_agent.get_portfolio_report()

    # ------------------------------------------------------------------
    # Research
    # ------------------------------------------------------------------

    def run_research(self, focus_area: str | None = None) -> dict[str, Any]:
        """Run an AI research analysis on the portfolio."""
        if not self._repo_cache:
            self.sync_repositories()
        report = self.research_agent.generate_research_report(
            self._repo_cache, focus_area=focus_area
        )
        return {
            "title": report.title,
            "summary": report.summary,
            "findings": report.findings,
            "recommendations": report.recommendations,
            "technologies": report.technologies,
            "related_repos": report.related_repos,
            "model": report.model_used,
            "generated_at": report.generated_at,
        }

    def get_integration_opportunities(self) -> list[dict[str, Any]]:
        """Identify integration opportunities across repositories."""
        if not self._repo_cache:
            self.sync_repositories()
        return self.research_agent.identify_integration_opportunities(self._repo_cache)

    # ------------------------------------------------------------------
    # Bot management
    # ------------------------------------------------------------------

    def get_bot_fleet_status(self) -> dict[str, Any]:
        """Return status of all managed bots."""
        return self.bot_agent.get_fleet_status()

    def send_bot_message(self, bot_id: str, message: str) -> dict[str, Any]:
        """Send a message to a specific bot and get an AI response."""
        msg = self.bot_agent.process_message(bot_id, message)
        return {
            "bot_id": msg.bot_id,
            "input": msg.user_input,
            "response": msg.bot_response,
            "platform": msg.platform.value,
            "timestamp": msg.timestamp,
        }

    # ------------------------------------------------------------------
    # Web3
    # ------------------------------------------------------------------

    def get_web3_summary(self) -> dict[str, Any]:
        """Return the Web3/blockchain network summary."""
        return self.web3_agent.get_network_summary()

    def analyse_defi(
        self, protocol: str, tvl_usd: float, apy: float, risk_level: str = "medium"
    ) -> dict[str, Any]:
        """Run AI-powered DeFi analysis."""
        report = self.web3_agent.analyse_defi_opportunity(protocol, tvl_usd, apy, risk_level)
        return {
            "protocol": protocol,
            "analysis_type": report.analysis_type,
            "summary": report.summary,
            "details": report.details,
            "recommendations": report.recommendations,
            "generated_at": report.generated_at,
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> OrchestratorStatus:
        """Return a lightweight status snapshot."""
        return OrchestratorStatus(
            running=True,
            total_repos=len(self._repo_cache) or len(self.repo_manager.ALL_REPOS),
            agents_active=[
                "ContentGeneratorAgent",
                "AdManagerAgent",
                "ResearchAgent",
                "BotManagerAgent",
                "Web3Agent",
                "QAMonitor",
            ],
            last_sync=self._last_sync or "never",
            last_health_check=self._last_health_check or "never",
            portfolio_health_score=self._portfolio_score,
        )
