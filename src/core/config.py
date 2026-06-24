"""
Configuration management for AI Autonomous Systems.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv


load_dotenv()


class Config:
    """Manages system configuration from YAML file and environment variables."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        if config_path is None:
            config_path = os.environ.get(
                "CONFIG_PATH",
                str(Path(__file__).parent.parent.parent / "config.yml"),
            )
        self._path = config_path
        self._data: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self._path, "r") as f:
                self._data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            self._data = {}

    # ------------------------------------------------------------------ #
    # GitHub                                                               #
    # ------------------------------------------------------------------ #

    @property
    def github_token(self) -> str:
        return os.environ.get("GITHUB_TOKEN", self._data.get("github", {}).get("token", ""))

    @property
    def github_repositories(self) -> List[str]:
        env_repos = os.environ.get("GITHUB_REPOSITORIES", "")
        if env_repos:
            return [r.strip() for r in env_repos.split(",") if r.strip()]
        return self._data.get("github", {}).get("repositories", [])

    @property
    def github_default_branch(self) -> str:
        return self._data.get("github", {}).get("default_branch", "main")

    @property
    def github_pr_labels(self) -> List[str]:
        return self._data.get("github", {}).get("pr_labels", ["ai-autonomous"])

    # ------------------------------------------------------------------ #
    # AI Model                                                             #
    # ------------------------------------------------------------------ #

    @property
    def ai_provider(self) -> str:
        return os.environ.get(
            "AI_PROVIDER",
            self._data.get("ai", {}).get("provider", "openai"),
        )

    @property
    def ai_model(self) -> str:
        return os.environ.get(
            "AI_MODEL",
            self._data.get("ai", {}).get("model", "gpt-4o"),
        )

    @property
    def ai_max_tokens(self) -> int:
        return int(self._data.get("ai", {}).get("max_tokens", 4096))

    @property
    def ai_temperature(self) -> float:
        return float(self._data.get("ai", {}).get("temperature", 0.2))

    @property
    def ai_max_retries(self) -> int:
        return int(self._data.get("ai", {}).get("max_retries", 3))

    # ------------------------------------------------------------------ #
    # Agents                                                               #
    # ------------------------------------------------------------------ #

    def agent_config(self, agent_name: str) -> Dict[str, Any]:
        return self._data.get("agents", {}).get(agent_name, {})

    # ------------------------------------------------------------------ #
    # Orchestrator                                                         #
    # ------------------------------------------------------------------ #

    @property
    def run_interval(self) -> int:
        return int(self._data.get("orchestrator", {}).get("run_interval", 3600))

    @property
    def max_concurrent_agents(self) -> int:
        return int(self._data.get("orchestrator", {}).get("max_concurrent_agents", 3))

    @property
    def log_level(self) -> str:
        return os.environ.get(
            "LOG_LEVEL",
            self._data.get("orchestrator", {}).get("log_level", "INFO"),
        )

    @property
    def reports_dir(self) -> str:
        return self._data.get("orchestrator", {}).get("reports_dir", "reports")

    # ------------------------------------------------------------------ #
    # Notifications                                                        #
    # ------------------------------------------------------------------ #

    @property
    def notify_github_issues(self) -> bool:
        return bool(self._data.get("notifications", {}).get("github_issues", True))

    @property
    def notification_assignees(self) -> List[str]:
        return self._data.get("notifications", {}).get("assignees", [])

    def get(self, key: str, default: Any = None) -> Any:
        """Generic accessor for nested keys using dot notation."""
        keys = key.split(".")
        data: Any = self._data
        for k in keys:
            if not isinstance(data, dict):
                return default
            data = data.get(k, default)
        return data
