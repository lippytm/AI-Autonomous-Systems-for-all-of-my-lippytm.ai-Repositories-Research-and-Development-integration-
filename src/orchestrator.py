"""Top-level orchestrator that wires all autonomous subsystems together.

Typical usage::

    from src.orchestrator import Orchestrator
    orch = Orchestrator.from_config("config/config.yaml")
    orch.run_once()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import yaml

from src.autonomous.ad_manager import AdManager
from src.autonomous.content_generator import ContentGenerator
from src.autonomous.research_agent import ResearchAgent
from src.integration.repo_manager import RepoManager
from src.quality.qa_monitor import QAMonitor

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates the content, advertising, research, QA, and integration subsystems.

    Parameters
    ----------
    config:
        Parsed configuration dictionary (matches ``config/config.yaml`` schema).
    project_root:
        Filesystem path used by the QA monitor.  Defaults to ``.``.
    """

    def __init__(self, config: Dict[str, Any], project_root: str = ".") -> None:
        self._cfg = config
        self._project_root = project_root
        dry_run: bool = config.get("system", {}).get("dry_run", False)

        content_cfg = config.get("content", {})
        self.content_generator = ContentGenerator(
            platforms=content_cfg.get("platforms", ["blog"]),
            topics=content_cfg.get("topics", ["AI"]),
            max_items_per_run=content_cfg.get("max_items_per_run", 5),
            dry_run=dry_run,
        )

        ad_cfg = config.get("advertising", {})
        self.ad_manager = AdManager(
            platforms=ad_cfg.get("target_platforms", ["google_ads"]),
            budget_limit_usd=ad_cfg.get("budget_limit_usd", 100.0),
            max_campaigns_per_run=ad_cfg.get("max_campaigns_per_run", 3),
            dry_run=dry_run,
        )

        research_cfg = config.get("research", {})
        self.research_agent = ResearchAgent(
            sources=research_cfg.get("sources", ["arxiv"]),
            dry_run=dry_run,
        )

        qa_cfg = config.get("quality", {})
        self.qa_monitor = QAMonitor(
            project_root=project_root,
            checks=qa_cfg.get("checks", ["lint", "test", "coverage"]),
            coverage_threshold=qa_cfg.get("coverage_threshold", 80.0),
            dry_run=dry_run,
        )

        integration_cfg = config.get("integration", {}).get("github", {})
        self.repo_manager = RepoManager(
            org=integration_cfg.get("org", "lippytm"),
            dry_run=dry_run,
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, config_path: str, project_root: str = ".") -> "Orchestrator":
        """Instantiate from a YAML config file."""
        with open(config_path, "r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
        return cls(config, project_root=project_root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self) -> Dict[str, Any]:
        """Execute one full cycle across all subsystems.

        Returns a summary dict with results from each subsystem.
        """
        logger.info("=== Orchestrator: starting run cycle ===")

        repos = self.repo_manager.discover()
        research_results = self.research_agent.run("autonomous AI systems")
        content_items = self.content_generator.run()
        topics = list({r.target_topic for r in self.ad_manager.get_campaigns()}) or [
            i.topic for i in content_items[:3]
        ]
        campaigns = self.ad_manager.run(topics) if topics else []
        qa_results = self.qa_monitor.run()

        summary = {
            "repos_discovered": len(repos),
            "research_findings": len(research_results),
            "content_items": len(content_items),
            "campaigns_created": len(campaigns),
            "qa_passed": self.qa_monitor.all_passed(qa_results),
            "qa_details": [r.to_dict() for r in qa_results],
        }

        logger.info("=== Orchestrator: cycle complete — %s ===", summary)
        return summary

    def run_qa_only(self) -> List[Any]:
        """Run quality-assurance checks and return results."""
        return self.qa_monitor.run()

    def run_content_only(self) -> List[Any]:
        """Run the content-generation cycle and return items produced."""
        return self.content_generator.run()

    def run_ads_only(self, topics: List[str]) -> List[Any]:
        """Run an ad campaign cycle for the given topics."""
        return self.ad_manager.run(topics)
