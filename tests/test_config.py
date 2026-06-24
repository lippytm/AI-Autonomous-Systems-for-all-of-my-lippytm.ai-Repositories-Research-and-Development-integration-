"""
Tests for configuration management.
"""
import os
import textwrap
from pathlib import Path

import pytest

from src.core.config import Config


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    cfg = tmp_path / "config.yml"
    cfg.write_text(
        textwrap.dedent(
            """
            github:
              token: "file_token"
              repositories:
                - "owner/repo1"
              default_branch: "develop"
              pr_labels:
                - "custom-label"

            ai:
              provider: "anthropic"
              model: "claude-3-opus-20240229"
              max_tokens: 2048
              temperature: 0.5
              max_retries: 5

            agents:
              code_improvement:
                enabled: false

            orchestrator:
              run_interval: 1800
              max_concurrent_agents: 2
              log_level: "DEBUG"
              reports_dir: "my_reports"

            notifications:
              github_issues: false
              assignees:
                - "octocat"
            """
        )
    )
    return cfg


def test_github_token_from_file(config_file: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    config = Config(str(config_file))
    assert config.github_token == "file_token"


def test_github_token_env_overrides_file(config_file: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_TOKEN", "env_token")
    config = Config(str(config_file))
    assert config.github_token == "env_token"


def test_github_repositories(config_file: Path):
    config = Config(str(config_file))
    assert config.github_repositories == ["owner/repo1"]


def test_github_repositories_from_env(config_file: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITHUB_REPOSITORIES", "owner/a,owner/b")
    config = Config(str(config_file))
    assert config.github_repositories == ["owner/a", "owner/b"]


def test_ai_provider(config_file: Path):
    config = Config(str(config_file))
    assert config.ai_provider == "anthropic"


def test_ai_model(config_file: Path):
    config = Config(str(config_file))
    assert config.ai_model == "claude-3-opus-20240229"


def test_agent_config(config_file: Path):
    config = Config(str(config_file))
    agent_cfg = config.agent_config("code_improvement")
    assert agent_cfg.get("enabled") is False


def test_orchestrator_settings(config_file: Path):
    config = Config(str(config_file))
    assert config.run_interval == 1800
    assert config.max_concurrent_agents == 2
    assert config.log_level == "DEBUG"
    assert config.reports_dir == "my_reports"


def test_notifications(config_file: Path):
    config = Config(str(config_file))
    assert config.notify_github_issues is False
    assert config.notification_assignees == ["octocat"]


def test_missing_config_file():
    config = Config("/nonexistent/path/config.yml")
    assert config.github_repositories == []


def test_dot_notation_get(config_file: Path):
    config = Config(str(config_file))
    assert config.get("ai.provider") == "anthropic"
    assert config.get("nonexistent.key", "default") == "default"
