"""
Orchestrator — coordinates all agents across all configured repositories.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from src.agents.base_agent import AgentResult, BaseAgent
from src.agents.code_improvement_agent import CodeImprovementAgent
from src.agents.repository_agent import RepositoryAgent
from src.agents.research_agent import ResearchAgent
from src.core.config import Config
from src.core.logger import get_logger
from src.integrations.ai_integration import AIIntegration
from src.integrations.github_integration import GitHubIntegration


logger = get_logger(__name__)


class Orchestrator:
    """Coordinates all AI autonomous agents across all configured repositories.

    Usage::

        config = Config()
        orchestrator = Orchestrator(config)
        report = orchestrator.run()
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        logger.setLevel(config.log_level)

        self._github = GitHubIntegration(config)
        self._ai = AIIntegration(config)

        self._agents: List[BaseAgent] = [
            RepositoryAgent(config, self._github, self._ai),
            CodeImprovementAgent(config, self._github, self._ai),
            ResearchAgent(config, self._github, self._ai),
        ]

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def run(self, repositories: Optional[List[str]] = None) -> Dict:
        """Run all agents against all configured repositories.

        Args:
            repositories: Optional list to override config-defined repositories.

        Returns:
            Summary report as a dict.
        """
        repos = repositories or self._config.github_repositories
        if not repos:
            logger.warning("No repositories configured. Set GITHUB_REPOSITORIES or config.yml.")
            return {"error": "No repositories configured", "results": []}

        start = time.monotonic()
        all_results: List[AgentResult] = []

        for repo_name in repos:
            logger.info("=== Processing repository: %s ===", repo_name)
            for agent in self._agents:
                result = agent.run(repo_name)
                all_results.append(result)

        elapsed = time.monotonic() - start
        report = self._build_report(all_results, elapsed)
        self._save_report(report)
        return report

    def run_continuously(self, repositories: Optional[List[str]] = None) -> None:
        """Run the orchestrator in a loop, sleeping between runs."""
        interval = self._config.run_interval
        logger.info("Starting continuous mode. Run interval: %ds", interval)
        while True:
            try:
                self.run(repositories)
            except Exception as exc:  # noqa: BLE001
                logger.error("Run failed: %s", exc)
            logger.info("Sleeping %ds until next run…", interval)
            time.sleep(interval)

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _build_report(self, results: List[AgentResult], elapsed: float) -> Dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "total_findings": sum(len(r.findings) for r in results),
            "total_actions": sum(len(r.actions_taken) for r in results),
            "total_errors": sum(len(r.errors) for r in results),
            "results": [
                {
                    "agent": r.agent_name,
                    "repository": r.repository,
                    "timestamp": r.timestamp,
                    "findings": r.findings,
                    "actions_taken": r.actions_taken,
                    "errors": r.errors,
                }
                for r in results
            ],
        }

    def _save_report(self, report: Dict) -> None:
        reports_dir = Path(self._config.reports_dir)
        reports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        report_path = reports_dir / f"report_{timestamp}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info("Report saved to %s", report_path)
