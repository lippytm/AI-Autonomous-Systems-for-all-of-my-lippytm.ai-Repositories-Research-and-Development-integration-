"""Tests for GitHubRepoManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.integration.repo_manager import (
    CommitInfo,
    GitHubRepoManager,
    IssueInfo,
    RepoInfo,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_repo_data() -> dict:
    return {
        "name": "Web3AI",
        "full_name": "lippytm/Web3AI",
        "description": "Web3 AI integration platform",
        "language": "Python",
        "html_url": "https://github.com/lippytm/Web3AI",
        "default_branch": "main",
        "stargazers_count": 2,
        "forks_count": 0,
        "open_issues_count": 16,
        "updated_at": "2026-02-05T20:29:15Z",
    }


@pytest.fixture()
def manager() -> GitHubRepoManager:
    return GitHubRepoManager(token="test-token")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGitHubRepoManager:
    def test_init_sets_token(self) -> None:
        m = GitHubRepoManager(token="my-token")
        assert m._token == "my-token"

    def test_init_uses_env_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "env-token")
        m = GitHubRepoManager()
        assert m._token == "env-token"

    def test_all_repos_contains_expected_repos(self, manager: GitHubRepoManager) -> None:
        assert "Web3AI" in manager.ALL_REPOS
        # Verify bot and factory repos are tracked (using exact list membership, not URL check)
        assert any(r == "AllBots.com" for r in manager.ALL_REPOS)
        assert any(r == "Factory.ai" for r in manager.ALL_REPOS)
        assert len(manager.ALL_REPOS) == 17

    def test_get_repo_returns_repo_info(
        self, manager: GitHubRepoManager, mock_repo_data: dict
    ) -> None:
        with patch.object(manager, "_get", return_value=mock_repo_data):
            repo = manager.get_repo("Web3AI")
        assert isinstance(repo, RepoInfo)
        assert repo.name == "Web3AI"
        assert repo.language == "Python"
        assert repo.stars == 2
        assert repo.open_issues == 16

    def test_get_repo_handles_missing_fields(self, manager: GitHubRepoManager) -> None:
        minimal = {
            "name": "minimal-repo",
            "full_name": "lippytm/minimal-repo",
            "html_url": "https://github.com/lippytm/minimal-repo",
        }
        with patch.object(manager, "_get", return_value=minimal):
            repo = manager.get_repo("minimal-repo")
        assert repo.description == ""
        assert repo.language == ""
        assert repo.stars == 0

    def test_list_all_repos_skips_http_errors(self, manager: GitHubRepoManager) -> None:
        import requests

        def side_effect(path: str, **kwargs):
            if "Web3AI" in path:
                raise requests.HTTPError("404")
            return {
                "name": path.split("/")[-1],
                "full_name": f"lippytm/{path.split('/')[-1]}",
                "html_url": "https://github.com/lippytm/repo",
            }

        with patch.object(manager, "_get", side_effect=side_effect):
            repos = manager.list_all_repos()
        # Should still return the ones that didn't error
        assert all(r.name != "Web3AI" for r in repos)

    def test_list_issues_filters_prs(self, manager: GitHubRepoManager) -> None:
        raw = [
            {"number": 1, "title": "Bug fix", "state": "open",
             "created_at": "2026-01-01", "updated_at": "2026-01-02", "labels": [], "body": ""},
            {"number": 2, "title": "PR title", "state": "open",
             "created_at": "2026-01-01", "updated_at": "2026-01-02", "labels": [], "body": "",
             "pull_request": {}},
        ]
        with patch.object(manager, "_get", return_value=raw):
            issues = manager.list_issues("Web3AI")
        assert len(issues) == 1
        assert issues[0].number == 1

    def test_list_commits_returns_commit_info(self, manager: GitHubRepoManager) -> None:
        raw = [
            {
                "sha": "abc123",
                "html_url": "https://github.com/lippytm/Web3AI/commit/abc123",
                "commit": {
                    "message": "feat: add Web3 support\n\nDetails here",
                    "author": {"name": "lippytm", "date": "2026-01-01T10:00:00Z"},
                },
            }
        ]
        with patch.object(manager, "_get", return_value=raw):
            commits = manager.list_commits("Web3AI")
        assert len(commits) == 1
        assert commits[0].sha == "abc123"
        assert commits[0].message == "feat: add Web3 support"

    def test_get_portfolio_summary_structure(
        self, manager: GitHubRepoManager, mock_repo_data: dict
    ) -> None:
        with patch.object(manager, "list_all_repos", return_value=[
            RepoInfo(
                name="Web3AI",
                full_name="lippytm/Web3AI",
                description="AI",
                language="Python",
                html_url="https://github.com/lippytm/Web3AI",
                default_branch="main",
                stars=2,
                forks=0,
                open_issues=5,
            )
        ]):
            summary = manager.get_portfolio_summary()
        assert summary["owner"] == "lippytm"
        assert summary["total_repos"] == 1
        assert summary["languages"]["Python"] == 1
        assert "generated_at" in summary

    def test_trigger_workflow_returns_true_on_204(self, manager: GitHubRepoManager) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 204
        manager._session.post = MagicMock(return_value=mock_response)
        result = manager.trigger_workflow("Web3AI", "deploy")
        assert result is True

    def test_trigger_workflow_returns_false_on_error(self, manager: GitHubRepoManager) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        manager._session.post = MagicMock(return_value=mock_response)
        result = manager.trigger_workflow("Web3AI", "deploy")
        assert result is False
