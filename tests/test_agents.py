"""
Tests for autonomous agents (using mocks so no live API calls are needed).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.base_agent import AgentResult
from src.agents.code_improvement_agent import CodeImprovementAgent
from src.agents.repository_agent import RepositoryAgent
from src.agents.research_agent import ResearchAgent
from src.core.config import Config


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #


@pytest.fixture()
def mock_config() -> MagicMock:
    config = MagicMock(spec=Config)
    config.notify_github_issues = False
    config.notification_assignees = []
    config.github_pr_labels = ["ai-autonomous"]
    config.agent_config.return_value = {}
    return config


@pytest.fixture()
def mock_github() -> MagicMock:
    github = MagicMock()
    repo = MagicMock()
    repo.full_name = "owner/repo"
    repo.open_issues_count = 5
    github.get_repository.return_value = repo
    github.list_files.return_value = ["src/main.py", "src/utils.py"]
    github.get_file_content.return_value = None
    return github


@pytest.fixture()
def mock_ai() -> MagicMock:
    ai = MagicMock()
    ai.analyze_code.return_value = "1. Use type hints\n2. Add docstrings"
    ai.summarize_repository.return_value = "A Python project for testing."
    ai.complete.return_value = "1. Add tests\n2. Use CI\n3. Document APIs"
    return ai


# ------------------------------------------------------------------ #
# AgentResult                                                          #
# ------------------------------------------------------------------ #


def test_agent_result_success():
    result = AgentResult(agent_name="test", repository="owner/repo")
    assert result.success is True


def test_agent_result_failure():
    result = AgentResult(agent_name="test", repository="owner/repo")
    result.add_error("something broke")
    assert result.success is False


def test_agent_result_summary():
    result = AgentResult(agent_name="test", repository="owner/repo")
    result.add_finding("quality", "fix this")
    result.add_action("created issue")
    summary = result.summary()
    assert "test" in summary
    assert "owner/repo" in summary


# ------------------------------------------------------------------ #
# RepositoryAgent                                                      #
# ------------------------------------------------------------------ #


def test_repository_agent_flags_missing_readme(mock_config, mock_github, mock_ai):
    mock_github.get_file_content.return_value = None  # all files missing
    mock_github.list_files.return_value = []
    mock_config.agent_config.return_value = {
        "enabled": True,
        "check_missing_files": ["README.md"],
    }

    agent = RepositoryAgent(mock_config, mock_github, mock_ai)
    result = agent.run("owner/repo")

    categories = [f["category"] for f in result.findings]
    assert "repository_health" in categories


def test_repository_agent_no_findings_when_files_present(mock_config, mock_github, mock_ai):
    # README present, no CI issue raised for a healthy repo
    mock_github.get_file_content.side_effect = lambda repo, path, **kw: (
        "# README" if path == "README.md" else None
    )
    mock_config.agent_config.return_value = {
        "enabled": True,
        "check_missing_files": ["README.md"],
    }

    agent = RepositoryAgent(mock_config, mock_github, mock_ai)
    result = agent.run("owner/repo")

    categories = [f["category"] for f in result.findings]
    assert "repository_health" not in categories


def test_repository_agent_disabled(mock_config, mock_github, mock_ai):
    mock_config.agent_config.return_value = {"enabled": False}
    agent = RepositoryAgent(mock_config, mock_github, mock_ai)
    result = agent.run("owner/repo")
    assert result.findings == []


# ------------------------------------------------------------------ #
# CodeImprovementAgent                                                 #
# ------------------------------------------------------------------ #


def test_code_improvement_agent_generates_findings(mock_config, mock_github, mock_ai):
    mock_github.list_files.return_value = ["src/main.py"]
    mock_github.get_file_content.return_value = "\n".join(["x = 1"] * 10)
    mock_config.agent_config.return_value = {
        "enabled": True,
        "target_extensions": [".py"],
        "max_files_per_run": 5,
        "min_lines": 5,
    }

    agent = CodeImprovementAgent(mock_config, mock_github, mock_ai)
    result = agent.run("owner/repo")

    assert len(result.findings) == 1
    assert result.findings[0]["category"] == "code_quality"


def test_code_improvement_agent_skips_small_files(mock_config, mock_github, mock_ai):
    mock_github.list_files.return_value = ["src/tiny.py"]
    mock_github.get_file_content.return_value = "x = 1"  # only 1 line
    mock_config.agent_config.return_value = {
        "enabled": True,
        "target_extensions": [".py"],
        "max_files_per_run": 5,
        "min_lines": 5,
    }

    agent = CodeImprovementAgent(mock_config, mock_github, mock_ai)
    result = agent.run("owner/repo")
    assert result.findings == []


def test_code_improvement_agent_disabled(mock_config, mock_github, mock_ai):
    mock_config.agent_config.return_value = {"enabled": False}
    agent = CodeImprovementAgent(mock_config, mock_github, mock_ai)
    result = agent.run("owner/repo")
    assert result.findings == []


# ------------------------------------------------------------------ #
# ResearchAgent                                                        #
# ------------------------------------------------------------------ #


def test_research_agent_generates_findings(mock_config, mock_github, mock_ai):
    mock_github.get_file_content.return_value = "# README"
    mock_github.list_files.return_value = ["main.py"]
    mock_config.agent_config.return_value = {
        "enabled": True,
        "research_topics": ["best practices"],
        "max_tasks_per_run": 1,
    }

    agent = ResearchAgent(mock_config, mock_github, mock_ai)
    result = agent.run("owner/repo")

    categories = [f["category"] for f in result.findings]
    assert "repository_summary" in categories
    assert "research_best_practices" in categories


def test_research_agent_disabled(mock_config, mock_github, mock_ai):
    mock_config.agent_config.return_value = {"enabled": False}
    agent = ResearchAgent(mock_config, mock_github, mock_ai)
    result = agent.run("owner/repo")
    assert result.findings == []
