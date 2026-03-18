"""GitHub repository manager for all lippytm repositories.

Provides a unified interface for reading metadata, issues, commits, and
triggering workflows across every repository in the lippytm organisation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests


@dataclass
class RepoInfo:
    """Lightweight summary of a GitHub repository."""

    name: str
    full_name: str
    description: str
    language: str
    html_url: str
    default_branch: str
    stars: int
    forks: int
    open_issues: int
    tags: list[str] = field(default_factory=list)
    last_updated: str = ""


@dataclass
class IssueInfo:
    """Summary of a GitHub issue."""

    number: int
    title: str
    state: str
    created_at: str
    updated_at: str
    labels: list[str] = field(default_factory=list)
    body: str = ""


@dataclass
class CommitInfo:
    """Summary of a GitHub commit."""

    sha: str
    message: str
    author: str
    date: str
    url: str


class GitHubRepoManager:
    """Manages integration with all lippytm GitHub repositories.

    Uses the GitHub REST API v3.  A personal-access token (PAT) stored in
    the ``GITHUB_TOKEN`` environment variable is recommended to avoid rate
    limiting and to access private repositories.
    """

    BASE_URL = "https://api.github.com"
    OWNER = "lippytm"

    # Canonical list of all lippytm repositories
    ALL_REPOS: list[str] = [
        "Transparency-Logic-Time-Machine-Bots-",
        "Web3AI",
        "AllBots.com",
        "AI-Full-Stack-AI-DevOps-Synthetic-Intelligence-Engines-AgentsBots-Web3-Websites-",
        "gatsby-starter-blog",
        "Chatlippytm.ai.Bots",
        "lippytm-lippytm.ai-tower-control-ai",
        "The-Encyclopedia-of-Everything-Applied-ChatAIBots",
        "Time-Machines-Builders-",
        "lippytm.ai",
        "AI-Time-Machines",
        "AllBots.com.ai",
        "Factory.ai",
        "OpenClaw-lippytm.AI-",
        "AI-Autonomous-Systems-for-all-of-my-lippytm.ai-Repositories-Research-and-Development-integration-",
        "AI-Intergalactic-Zoological-Social-Multimedia-Agency-Networks-",
        "Evolutionary-Evolutions-Social-Multimedia-Networks-Agency-",
    ]

    def __init__(self, token: str | None = None) -> None:
        self._token = token or os.getenv("GITHUB_TOKEN", "")
        self._session = requests.Session()
        if self._token:
            self._session.headers["Authorization"] = f"Bearer {self._token}"
        self._session.headers["Accept"] = "application/vnd.github+json"
        self._session.headers["X-GitHub-Api-Version"] = "2022-11-28"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Perform a GET request and return the parsed JSON body."""
        url = f"{self.BASE_URL}{path}"
        response = self._session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Repository metadata
    # ------------------------------------------------------------------

    def get_repo(self, repo_name: str) -> RepoInfo:
        """Fetch metadata for a single repository."""
        data = self._get(f"/repos/{self.OWNER}/{repo_name}")
        return RepoInfo(
            name=data["name"],
            full_name=data["full_name"],
            description=data.get("description") or "",
            language=data.get("language") or "",
            html_url=data["html_url"],
            default_branch=data.get("default_branch", "main"),
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            open_issues=data.get("open_issues_count", 0),
            last_updated=data.get("updated_at", ""),
        )

    def list_all_repos(self) -> list[RepoInfo]:
        """Return metadata for every lippytm repository."""
        results: list[RepoInfo] = []
        for name in self.ALL_REPOS:
            try:
                results.append(self.get_repo(name))
            except requests.HTTPError:
                continue
        return results

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    def list_issues(
        self,
        repo_name: str,
        state: str = "open",
        per_page: int = 30,
    ) -> list[IssueInfo]:
        """List issues for a repository."""
        data = self._get(
            f"/repos/{self.OWNER}/{repo_name}/issues",
            params={"state": state, "per_page": per_page},
        )
        issues: list[IssueInfo] = []
        for item in data:
            if "pull_request" in item:
                continue  # skip PRs
            issues.append(
                IssueInfo(
                    number=item["number"],
                    title=item["title"],
                    state=item["state"],
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                    labels=[lb["name"] for lb in item.get("labels", [])],
                    body=item.get("body") or "",
                )
            )
        return issues

    def list_all_issues(self, state: str = "open") -> dict[str, list[IssueInfo]]:
        """Return issues for every repository, keyed by repo name."""
        return {
            name: self.list_issues(name, state=state)
            for name in self.ALL_REPOS
        }

    # ------------------------------------------------------------------
    # Commits
    # ------------------------------------------------------------------

    def list_commits(self, repo_name: str, per_page: int = 10) -> list[CommitInfo]:
        """List recent commits for a repository."""
        data = self._get(
            f"/repos/{self.OWNER}/{repo_name}/commits",
            params={"per_page": per_page},
        )
        commits: list[CommitInfo] = []
        for item in data:
            commit = item.get("commit", {})
            author = commit.get("author") or {}
            commits.append(
                CommitInfo(
                    sha=item["sha"],
                    message=commit.get("message", "").split("\n")[0],
                    author=author.get("name", "unknown"),
                    date=author.get("date", ""),
                    url=item.get("html_url", ""),
                )
            )
        return commits

    # ------------------------------------------------------------------
    # Cross-repository summary
    # ------------------------------------------------------------------

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Return a high-level summary of the entire repository portfolio."""
        repos = self.list_all_repos()
        total_stars = sum(r.stars for r in repos)
        total_issues = sum(r.open_issues for r in repos)
        languages: dict[str, int] = {}
        for repo in repos:
            if repo.language:
                languages[repo.language] = languages.get(repo.language, 0) + 1

        return {
            "owner": self.OWNER,
            "total_repos": len(repos),
            "total_stars": total_stars,
            "total_open_issues": total_issues,
            "languages": languages,
            "repos": [
                {
                    "name": r.name,
                    "description": r.description,
                    "language": r.language,
                    "stars": r.stars,
                    "open_issues": r.open_issues,
                    "url": r.html_url,
                    "last_updated": r.last_updated,
                }
                for r in repos
            ],
            "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        }

    # ------------------------------------------------------------------
    # Repository dispatch (trigger workflows)
    # ------------------------------------------------------------------

    def trigger_workflow(
        self,
        repo_name: str,
        event_type: str,
        client_payload: dict[str, Any] | None = None,
    ) -> bool:
        """Send a repository_dispatch event to trigger a GitHub Actions workflow."""
        url = f"{self.BASE_URL}/repos/{self.OWNER}/{repo_name}/dispatches"
        payload: dict[str, Any] = {"event_type": event_type}
        if client_payload:
            payload["client_payload"] = client_payload
        response = self._session.post(url, json=payload, timeout=30)
        return response.status_code == 204
