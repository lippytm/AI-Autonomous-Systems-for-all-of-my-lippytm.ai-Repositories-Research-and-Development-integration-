"""
Base autonomous agent interface.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from src.core.config import Config
from src.core.logger import get_logger
from src.integrations.ai_integration import AIIntegration
from src.integrations.github_integration import GitHubIntegration


@dataclass
class AgentResult:
    """Structured result returned by every agent run."""

    agent_name: str
    repository: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    findings: List[Dict[str, Any]] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def add_finding(self, category: str, description: str, severity: str = "info") -> None:
        self.findings.append(
            {"category": category, "description": description, "severity": severity}
        )

    def add_action(self, description: str) -> None:
        self.actions_taken.append(description)

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def summary(self) -> str:
        lines = [
            f"Agent: {self.agent_name}",
            f"Repository: {self.repository}",
            f"Timestamp: {self.timestamp}",
            f"Findings: {len(self.findings)}",
            f"Actions taken: {len(self.actions_taken)}",
            f"Errors: {len(self.errors)}",
        ]
        return "\n".join(lines)


class BaseAgent(abc.ABC):
    """Abstract base class for all AI autonomous agents."""

    #: Human-readable name used in logs and reports.
    name: str = "base"

    def __init__(
        self,
        config: Config,
        github: GitHubIntegration,
        ai: AIIntegration,
    ) -> None:
        self._config = config
        self._github = github
        self._ai = ai
        self._logger = get_logger(f"agents.{self.name}")
        self._agent_config = config.agent_config(self.name)

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def run(self, repository: str) -> AgentResult:
        """Execute the agent against *repository* (``owner/repo``).

        Returns an :class:`AgentResult` regardless of success or failure.
        """
        result = AgentResult(agent_name=self.name, repository=repository)
        self._logger.info("Starting %s on %s", self.name, repository)
        try:
            repo = self._github.get_repository(repository)
            self._run(repo, result)
        except Exception as exc:  # noqa: BLE001
            msg = f"Unhandled error: {exc}"
            self._logger.error(msg)
            result.add_error(msg)
        self._logger.info("Finished %s on %s — %s", self.name, repository, result.summary())
        return result

    # ------------------------------------------------------------------ #
    # Abstract                                                             #
    # ------------------------------------------------------------------ #

    @abc.abstractmethod
    def _run(self, repo: Any, result: AgentResult) -> None:
        """Agent-specific logic. Subclasses must implement this."""
